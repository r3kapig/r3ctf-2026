#!/usr/bin/env python3

import sys
import asyncio
import json
import argparse
import httpx
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

def check(resp: httpx.Response, label: str, expected_status: int = 200) -> dict:
    if resp.status_code != expected_status:
        print(f"FAIL [{label}] HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    data = resp.json()
    print(f"OK   [{label}] {json.dumps(data)[:120]}")
    return data

def register(client: httpx.Client, handle: str, display_name: str, phone: str, base_url: str = BASE_URL, password: str = "smoke-test-pw") -> str:

    resp = client.post(f"{base_url}/auth/register", json={
        "handle": handle,
        "display_name": display_name,
        "phone": phone,
        "password": password,
    })
    data = check(resp, f"register {handle}", 200)
    return data["token"]

async def ws_receive_until(ws, event_type: str, timeout: float = 5.0) -> dict:

    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError(f"Did not receive '{event_type}' within {timeout}s")
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        frame = json.loads(raw)
        if frame.get("type") == event_type:
            return frame

async def run(base_url: str, ws_url: str):
    print(f"\n=== Whisper smoke test against {base_url} ===\n")

    with httpx.Client() as client:
        resp = client.post(f"{base_url}/admin/reset",
                           headers={"Authorization": "Bearer ctf-admin-token"})
        check(resp, "admin reset", 200)

    with httpx.Client() as client:
        attacker_token = register(client, "attacker", "Attacker", "+10000000001", base_url)
        victim_token = register(client, "victim", "Victim", "+10000000002", base_url)

        ah = {"Authorization": f"Bearer {attacker_token}"}
        vh = {"Authorization": f"Bearer {victim_token}"}

        me_resp = client.get(f"{base_url}/users/me", headers=ah)
        attacker = check(me_resp, "attacker profile", 200)
        me_resp2 = client.get(f"{base_url}/users/me", headers=vh)
        victim = check(me_resp2, "victim profile", 200)

        dm_resp = client.post(
            f"{base_url}/conversations/dm",
            params={"target_user_id": victim["id"]},
            headers=ah,
        )
        dm = check(dm_resp, "open DM", 200)
        conv_id = dm["conversation_id"]

        dm_resp2 = client.post(
            f"{base_url}/conversations/dm",
            params={"target_user_id": victim["id"]},
            headers=ah,
        )
        dm2 = check(dm_resp2, "open DM (attacker, repeat)", 200)
        assert dm2["conversation_id"] == conv_id, (
            f"Idempotency fail: second call returned {dm2['conversation_id']}, expected {conv_id}"
        )
        print(f"OK   [DM idempotency attacker->victim] same conv_id={conv_id}")

        dm_resp3 = client.post(
            f"{base_url}/conversations/dm",
            params={"target_user_id": attacker["id"]},
            headers=vh,
        )
        dm3 = check(dm_resp3, "open DM (victim->attacker)", 200)
        assert dm3["conversation_id"] == conv_id, (
            f"Idempotency fail: victim->attacker returned {dm3['conversation_id']}, expected {conv_id}"
        )
        print(f"OK   [DM idempotency victim->attacker] same conv_id={conv_id}")

        victim_ws_url = f"{ws_url}/ws?token={victim_token}"

    async with websockets.connect(victim_ws_url) as victim_ws:
        raw = await asyncio.wait_for(victim_ws.recv(), timeout=5)
        frame = json.loads(raw)
        assert frame["type"] == "connected", f"Expected 'connected', got {frame}"
        print(f"OK   [victim ws connect] user_id={frame['user_id']}")

        with httpx.Client() as client:
            ah = {"Authorization": f"Bearer {attacker_token}"}
            vh = {"Authorization": f"Bearer {victim_token}"}

            send_resp = client.post(f"{base_url}/messages", headers=ah, json={
                "conversation_id": conv_id,
                "type": "text",
                "body": "Hello from attacker!",
            })
            msg = check(send_resp, "send text message", 200)

            victim_msgs_resp = client.get(
                f"{base_url}/conversations/{conv_id}/messages", headers=vh
            )
            victim_msgs = check(victim_msgs_resp, "victim reads messages in shared conv", 200)
            assert any(m["body"] == "Hello from attacker!" for m in victim_msgs), \
                "Cross-party visibility fail: victim cannot see attacker's message"
            print(f"OK   [cross-party visibility] victim sees attacker's message in conv_id={conv_id}")

        frame = await ws_receive_until(victim_ws, "new_message", timeout=5)
        assert frame["message"]["body"] == "Hello from attacker!", \
            f"Wrong message body: {frame['message']['body']}"
        print(f"OK   [victim ws new_message] body='{frame['message']['body']}'")

        rcard_bytes = b"\x52\x43\x41\x52\x44\x00\x00\x01" + b"\x00" * 16
        with httpx.Client() as client:
            ah = {"Authorization": f"Bearer {attacker_token}"}
            vh = {"Authorization": f"Bearer {victim_token}"}

            upload_resp = client.post(
                f"{base_url}/attachments/upload",
                headers={**ah, "Content-Type": "application/octet-stream",
                         "X-Filename": "payload.rcard", "X-Kind": "rcard"},
                content=rcard_bytes,
            )
            att = check(upload_resp, "upload .rcard", 200)
            att_id = att["id"]
            assert att["kind"] == "rcard"

            att_msg_resp = client.post(f"{base_url}/messages", headers=ah, json={
                "conversation_id": conv_id,
                "type": "attachment",
                "attachment_id": att_id,
            })
            att_msg = check(att_msg_resp, "send attachment message", 200)
            assert att_msg["type"] == "attachment"
            assert att_msg["attachment_id"] == att_id

        frame = await ws_receive_until(victim_ws, "new_message", timeout=5)
        assert frame["message"]["type"] == "attachment", \
            f"Expected attachment message, got {frame['message']['type']}"
        assert frame["message"]["attachment_id"] == att_id
        print(f"OK   [victim ws new_message/attachment] att_id={att_id}")

        with httpx.Client() as client:
            vh = {"Authorization": f"Bearer {victim_token}"}
            dl_resp = client.get(f"{base_url}/attachments/{att_id}/download", headers=vh)
            if dl_resp.status_code != 200:
                print(f"FAIL [download attachment] HTTP {dl_resp.status_code}")
                sys.exit(1)
            assert dl_resp.content == rcard_bytes, "Downloaded bytes do not match uploaded bytes!"
            print(f"OK   [download .rcard] {len(dl_resp.content)} bytes, exact match")

        with httpx.Client() as client:
            vh = {"Authorization": f"Bearer {victim_token}"}
            msgs_resp = client.get(
                f"{base_url}/conversations/{conv_id}/messages", headers=vh
            )
            msgs = check(msgs_resp, "list messages", 200)
            assert len(msgs) == 2, f"Expected 2 messages, got {len(msgs)}"
            print(f"OK   [list messages] count={len(msgs)}")

        with httpx.Client() as client:
            vh = {"Authorization": f"Bearer {victim_token}"}
            read_resp = client.post(
                f"{base_url}/conversations/{conv_id}/read", headers=vh
            )
            check(read_resp, "mark read", 200)

        with httpx.Client() as client:
            vh = {"Authorization": f"Bearer {victim_token}"}
            convs_resp = client.get(f"{base_url}/conversations", headers=vh)
            convs = check(convs_resp, "list conversations", 200)
            assert len(convs) == 1
            print(f"OK   [list conversations] count={len(convs)}, unread={convs[0]['unread_count']}")

        odd_subtitle = "preview\x00\x01\x02\xff\xfe\U00010FFF end"
        preview_title = "Rich Card"

        attacker_ws_url = f"{ws_url}/ws?token={attacker_token}"
        async with websockets.connect(attacker_ws_url) as attacker_ws:
            raw = await asyncio.wait_for(attacker_ws.recv(), timeout=5)
            frame = json.loads(raw)
            assert frame["type"] == "connected", f"Expected 'connected', got {frame}"
            print(f"OK   [attacker ws connect] user_id={frame['user_id']}")

            att_msg_id = att_msg["id"]
            with httpx.Client() as client:
                vh = {"Authorization": f"Bearer {victim_token}"}
                prev_resp = client.post(
                    f"{base_url}/messages/{att_msg_id}/preview",
                    headers=vh,
                    json={"title": preview_title, "subtitle": odd_subtitle},
                )
                prev_data = check(prev_resp, "set message preview", 200)
                assert prev_data["preview"] is not None, "preview field missing in response"
                assert prev_data["preview"]["title"] == preview_title
                assert prev_data["preview"]["subtitle"] == odd_subtitle, (
                    f"Subtitle mismatch in response:\n"
                    f"  sent:     {repr(odd_subtitle)}\n"
                    f"  received: {repr(prev_data['preview']['subtitle'])}"
                )
                print(f"OK   [set preview] subtitle verbatim round-trip confirmed in POST response")

            ws_frame = await ws_receive_until(attacker_ws, "message_preview", timeout=5)
            assert ws_frame["message_id"] == att_msg_id
            assert ws_frame["preview"]["subtitle"] == odd_subtitle, (
                f"Subtitle mismatch in WS frame:\n"
                f"  sent:     {repr(odd_subtitle)}\n"
                f"  received: {repr(ws_frame['preview']['subtitle'])}"
            )
            print(f"OK   [attacker ws message_preview] subtitle verbatim in WS frame: {repr(ws_frame['preview']['subtitle'])[:80]}")

            with httpx.Client() as client:
                ah = {"Authorization": f"Bearer {attacker_token}"}
                msgs_resp = client.get(
                    f"{base_url}/conversations/{conv_id}/messages", headers=ah
                )
                msgs = check(msgs_resp, "list messages with preview", 200)
                att_msgs = [m for m in msgs if m["id"] == att_msg_id]
                assert att_msgs, "Attachment message not found in list"
                fetched_preview = att_msgs[0].get("preview")
                assert fetched_preview is not None, "preview field null in GET messages response"
                assert fetched_preview["subtitle"] == odd_subtitle, (
                    f"Subtitle mismatch in GET messages:\n"
                    f"  sent:     {repr(odd_subtitle)}\n"
                    f"  received: {repr(fetched_preview['subtitle'])}"
                )
                print(f"OK   [GET messages preview] subtitle verbatim round-trip confirmed via GET")
                print(f"     subtitle repr: {repr(fetched_preview['subtitle'])}")

    print("\n=== All smoke tests PASSED ===\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    ws_url = args.base_url.replace("http://", "ws://").replace("https://", "wss://")
    asyncio.run(run(args.base_url, ws_url))
