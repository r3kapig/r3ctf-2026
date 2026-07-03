#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, random, sys
import fhe_core as fhe
from secret import FLAG
import signal

S = 4
N_DIGITS = 5
LUT_SIZE = S ** N_DIGITS
SETUP_DIR = os.path.join(os.path.dirname(__file__), "setup")
ROUNDS = 16

def _timeout(_signum, _frame):
    print("timeout")
    sys.stdout.flush()
    raise SystemExit(0)

def extract_radix(v: int, s: int, n: int):
    d = []
    for _ in range(n):
        d.append(v % s)
        v //= s
    return d

def combine_radix(d, s: int):
    v = 0
    for x in reversed(d):
        v = v * s + x
    return v

def write_setup():
    os.makedirs(SETUP_DIR, exist_ok=True)
    print("[*] generating keys...")
    sk, bsk, ksk = fhe.keygen()
    
    client_blob = fhe.serialize_client_key(sk)
    with open(os.path.join(SETUP_DIR, "client.bin"), "wb") as f:
        f.write(client_blob)
    print(f"[*] client.bin: {len(client_blob)/1e6:.1f} MB")

    bsk_blob = fhe.serialize_bsk(bsk)
    with open(os.path.join(SETUP_DIR, "bsk.bin"), "wb") as f:
        f.write(bsk_blob)
    print(f"[*] bsk.bin: {len(bsk_blob)/1e6:.1f} MB")

    ksk_blob = fhe.serialize_ksk(ksk)
    with open(os.path.join(SETUP_DIR, "ksk.bin"), "wb") as f:
        f.write(ksk_blob)
    print(f"[*] ksk.bin: {len(ksk_blob)/1e6:.1f} MB")
    print("[*] setup complete ->", SETUP_DIR)
    return

def load_setup():
    client_path = os.path.join(SETUP_DIR, "client.bin")
    if not (os.path.exists(client_path)):
        write_setup()
    with open(client_path, "rb") as f:
        client_blob = f.read()
    sk = fhe.parse_client_key(client_blob)
    return sk

def main() -> int:
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(120)
    sk = load_setup()
    lut = [int(token) for token in open("lut", "r").read().split()]
    if len(lut) != LUT_SIZE:
        raise ValueError(f"expected {LUT_SIZE} LUT entries, got {len(lut)}")
    print("=== Encrypted Activation-Layer Inference ===")
    print('''Each ciphertext carries one base-%d activation symbol (2 bits). 
Evaluate the published %d-bit activation table on the encrypted 
input using the provided keys, and return the encrypted output 
symbols.''' % (S, (S.bit_length()-1) * N_DIGITS))
    sys.stdout.flush()

    for idx in range(ROUNDS):
        x = fhe.rng.randrange(LUT_SIZE)
        in_digits = extract_radix(x, S, N_DIGITS)
        seeded_inputs = [fhe.encrypt_ciphertext(sk, d) for d in in_digits]
        payload = { 
            "round": idx + 1,
            "ciphertext": [(int.from_bytes(seed, 'big'), ct.b) for seed, ct in seeded_inputs],
        }
        print(json.dumps(payload))
        sys.stdout.flush()

        line = sys.stdin.readline()
        if not line:
            return 1
        line = line.strip()
        parts = [t for t in line.replace(",", " ").split() if t]
        if len(parts) != N_DIGITS:
            print("wrong"); sys.stdout.flush(); return 0

        try:
            out_cts = [fhe.parse_lwe_ciphertext(base64.b64decode(t, validate=True)) for t in parts]
        except Exception:
            print("wrong"); sys.stdout.flush(); return 0

        bad = False
        for c in out_cts:
            if len(c.a) != fhe.N:
                bad = True; break
            zero_cnt = sum(1 for v in c.a if v == 0)
            if zero_cnt > 16:        
                bad = True; break
            if len(set(c.a)) == 1:   
                bad = True; break
        if bad:
            print("wrong"); sys.stdout.flush(); return 0

        out_digits = [fhe.decrypt_ciphertext(sk, c) for c in out_cts]
        if any(d >= S for d in out_digits):
            print("wrong"); sys.stdout.flush(); return 0

        y = combine_radix(out_digits, S)
        if y != lut[x]:
            print("wrong"); sys.stdout.flush(); return 0

    print(FLAG)
    sys.stdout.flush()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
