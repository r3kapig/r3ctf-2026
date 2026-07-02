#!/usr/bin/env python3
import hashlib
import os
import secrets
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT_DIR / "runtime"
RUNTIME_FLAG_DIR = RUNTIME_DIR / "flagfs"
RUNTIME_FLAG = RUNTIME_FLAG_DIR / "flag"

PORT = int(os.environ.get("PORT", "1337"))
RUN_TIMEOUT_SEC = int(os.environ.get("RUN_TIMEOUT_SEC", "420"))

POW_ZERO_PREFIX = "00000"
POW_TIMEOUT_SEC = 30
POW_NONCE_MAX = 128

active_proc = None


def log(msg):
	print(msg, flush=True)


def terminate_proc(proc):
	if proc.poll() is not None:
		return

	try:
		os.killpg(proc.pid, signal.SIGTERM)
	except ProcessLookupError:
		return

	deadline = time.time() + 5.0
	while time.time() < deadline:
		if proc.poll() is not None:
			return
		time.sleep(0.05)

	try:
		os.killpg(proc.pid, signal.SIGKILL)
	except ProcessLookupError:
		pass


def handle_signal(_signum, _frame):
	if active_proc is not None:
		terminate_proc(active_proc)
	raise KeyboardInterrupt


def prepare_runtime_flag():
	flag_file = os.environ.get("FLAG_FILE", "")
	flag_value = os.environ.get("FLAG", "")

	RUNTIME_FLAG_DIR.mkdir(parents=True, exist_ok=True)
	try:
		RUNTIME_FLAG.unlink()
	except FileNotFoundError:
		pass

	if flag_file:
		shutil.copyfile(flag_file, RUNTIME_FLAG)
	elif flag_value:
		RUNTIME_FLAG.write_text(flag_value + "\n", encoding="utf-8")
	else:
		shutil.copyfile(ROOT_DIR / "flag.txt", RUNTIME_FLAG)
	RUNTIME_FLAG.chmod(0o400)


def send(conn, data):
	conn.sendall(data.encode("ascii"))


def recv_line(conn, limit, timeout):
	conn.settimeout(timeout)
	data = bytearray()

	while len(data) < limit:
		chunk = conn.recv(1)
		if not chunk:
			raise ConnectionError("client disconnected")
		if chunk == b"\n":
			return bytes(data).rstrip(b"\r")
		data.extend(chunk)

	raise ValueError("line too long")


def verify_pow(conn):
	prefix = secrets.token_hex(16)

	send(conn, "== proof of work ==\n")
	send(conn, f"sha256(prefix + nonce) must start with {POW_ZERO_PREFIX}\n")
	send(conn, f"prefix: {prefix}\n")
	send(conn, "nonce: ")

	try:
		nonce = recv_line(conn, POW_NONCE_MAX, POW_TIMEOUT_SEC)
	except (ConnectionError, OSError, TimeoutError, ValueError):
		return False

	digest = hashlib.sha256(prefix.encode("ascii") + nonce).hexdigest()
	if digest.startswith(POW_ZERO_PREFIX):
		send(conn, "[+] pow ok\n\n")
		return True

	send(conn, "[-] invalid pow\n")
	return False


def relay_challenge(conn):
	global active_proc

	cmd = ["timeout", "--foreground", "-k", "5s", f"{RUN_TIMEOUT_SEC}s", "./run.sh"]
	proc = subprocess.Popen(
		cmd,
		cwd=ROOT_DIR,
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		start_new_session=True,
		bufsize=0,
	)
	active_proc = proc

	try:
		conn.setblocking(False)
		stdin_fd = proc.stdin.fileno()
		stdout_fd = proc.stdout.fileno()
		os.set_blocking(stdin_fd, False)
		os.set_blocking(stdout_fd, False)

		sel = selectors.DefaultSelector()
		sel.register(conn, selectors.EVENT_READ, "client")
		sel.register(stdout_fd, selectors.EVENT_READ, "child")

		while proc.poll() is None:
			for key, _mask in sel.select(timeout=0.5):
				if key.data == "client":
					try:
						data = conn.recv(4096)
					except BlockingIOError:
						continue
					if not data:
						terminate_proc(proc)
						return
					try:
						written = os.write(stdin_fd, data)
					except BlockingIOError:
						terminate_proc(proc)
						return
					except BrokenPipeError:
						continue
					if written != len(data):
						terminate_proc(proc)
						return
				else:
					try:
						data = os.read(stdout_fd, 4096)
					except BlockingIOError:
						continue
					if not data:
						continue
					try:
						conn.sendall(data)
					except OSError:
						terminate_proc(proc)
						return

		while True:
			try:
				data = os.read(stdout_fd, 4096)
			except BlockingIOError:
				break
			if not data:
				break
			try:
				conn.sendall(data)
			except OSError:
				break
	finally:
		if active_proc is proc:
			active_proc = None
		terminate_proc(proc)
		for stream in (proc.stdin, proc.stdout):
			try:
				stream.close()
			except OSError:
				pass
		proc.wait()


def handle_client(conn, addr):
	log(f"[*] connection from {addr[0]}:{addr[1]}")

	with conn:
		try:
			if not verify_pow(conn):
				return
			relay_challenge(conn)
		except (ConnectionError, OSError):
			return
		finally:
			log(f"[*] disconnected {addr[0]}:{addr[1]}")


def main():
	signal.signal(signal.SIGTERM, handle_signal)
	signal.signal(signal.SIGINT, handle_signal)

	prepare_runtime_flag()

	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
		srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		srv.bind(("0.0.0.0", PORT))
		srv.listen(8)
		log(f"[*] listening on 0.0.0.0:{PORT}")

		while True:
			conn, addr = srv.accept()
			handle_client(conn, addr)


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		sys.exit(0)
