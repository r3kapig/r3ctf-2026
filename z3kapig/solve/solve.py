import os
from pathlib import Path

os.environ.setdefault("DOT_SAGE", "/tmp/sage")
Path(os.environ["DOT_SAGE"]).mkdir(parents=True, exist_ok=True)

from pwn import *
import json
import math
import random
import sys
import time
from sympy.ntheory.modular import crt
from dataclasses import astuple
from datetime import datetime
from party import Party
from proof_of_work import POW_ALGORITHM, solve_pow
from crypto.common.paillier import PublicKey, PrivateKey
from crypto.common.utils import serialize_point, deserialize_point, serialize_bytes_list, deserialize_bytes_list
from crypto.common.numbers import rejection_sample
from crypto.zkp.hash import sha512_256i
from crypto.zkp.prm import ProofPrm
from crypto.zkp.fac import ProofFac
from crypto.zkp.mod import ProofMod
from crypto.zkp.enc import ProofEnc
from crypto.zkp.logstar import ProofLogstar
from crypto.zkp.affg import ProofAffg
from ecdsa.messages import *
from sage.all import preparser, Matrix, ZZ
from lll_cvp import solve_inequality

preparser(False)

def progress(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)

def affg_challenge(ssid, ec, pk0, pk1, NCap, s, t, C, D, Y, X, proof):
    e_hash = sha512_256i(
        ssid,
        ec.curve.b,
        ec.n,
        ec.p,
        pk0.n,
        pk1.n,
        NCap,
        s,
        t,
        C,
        D,
        Y,
        X.x,
        X.y,
        proof.S,
        proof.T,
        proof.A,
        proof.Bx.x,
        proof.Bx.y,
        proof.By,
        proof.E,
        proof.F,
    )
    return rejection_sample(int(ec.n), e_hash)

def recover_residue_with_lattice(N, M, dec, prime, mask_bound, known_high=0, shift=0):
    # Solve known_high * 2^shift - dec + residue * M + mask + k * N = 0
    # with 0 <= residue < prime and 0 <= mask < mask_bound.
    const = int(known_high) * (1 << int(shift)) - int(dec)
    mat = Matrix(ZZ, [
        [const, 1, 0, 0],
        [int(M), 0, 1, 0],
        [1, 0, 0, 1],
        [int(N), 0, 0, 0],
    ])
    lb = [0, 1, 0, 0]
    ub = [0, 1, int(prime), int(mask_bound)]
    ans = solve_inequality(mat, lb, ub)
    residue = int(ans[2])

    candidates = [residue]
    if prime:
        candidates.extend([residue % int(prime), (-residue) % int(prime)])

    high_part = int(known_high) * (1 << int(shift))
    for candidate in candidates:
        if not 0 <= candidate < prime:
            continue
        mask = (int(dec) - candidate * int(M) - high_part) % int(N)
        if 0 <= mask < mask_bound:
            return candidate, mask

    mask = int(ans[3])
    raise RuntimeError(
        f"lattice returned out-of-range residue/mask: {residue}, {mask}"
    )

def recover_affg_residue_and_mask(ssid, p0, np0, dec, primei, D, F, X, proof_parts):
    proof = ProofAffg.from_bytes(p0.ec, proof_parts)
    e = affg_challenge(
        ssid,
        p0.ec,
        p0.presigning_protocol.paillier_pub_i,
        p0.presigning_protocol.paillier_pub_j,
        int(p0.presigning_protocol.paillier_pub_i.n),
        int(p0.presigning_protocol.si),
        int(p0.presigning_protocol.ti),
        p0.presigning_protocol.K_i_ct,
        D,
        F,
        X,
        proof,
    )

    N = int(p0.presigning_protocol.paillier_pub_i.n)
    if proof.Z2.bit_length() > 3 * p0.ec.n.bit_length():
        # tss-lib/WRITEUP.md case: an N-sized MtA mask leaks its high bits
        # through Z2 = e * mask + proof_blind.
        shift = N.bit_length() - 250
        observed_high = (proof.Z2 // e) >> shift
        max_carry = min(256, 1 << max(0, 252 - int(e).bit_length()))
        last_error = None
        for carry in range(max_carry + 1):
            known_high = observed_high - carry
            if known_high < 0:
                break
            try:
                residue, mask_low = recover_residue_with_lattice(
                    N,
                    np0,
                    dec,
                    primei,
                    1 << shift,
                    known_high,
                    shift,
                )
            except RuntimeError as exc:
                last_error = exc
                continue

            mask = known_high * (1 << shift) + mask_low
            proof_blind = proof.Z2 - e * mask
            if 0 < proof_blind < N:
                return residue, mask
            last_error = RuntimeError("reconstructed Aff-g proof blind is out of range")

        if last_error is not None:
            raise last_error
        raise RuntimeError("could not recover Aff-g mask high bits")

    # Current challenge case if Aff-g is tightened again: the same lattice
    # equation applies with a curve-sized unknown mask.
    return recover_residue_with_lattice(
        N,
        np0,
        dec,
        primei,
        int(p0.ec.n),
    )

def start_target():
    host = os.environ.get("RHOST")
    if host is None and "PORT" in os.environ:
        host = os.environ.get("HOST")
    if host:
        return remote(host, int(os.environ.get("PORT", "1337")))
    return process([sys.executable, str(Path(__file__).with_name("main.py"))])

def complete_pow(io):
    challenge_message = json.loads(io.recvline())
    if (
        challenge_message.get("type") != "pow"
        or challenge_message.get("algorithm") != POW_ALGORITHM
    ):
        raise RuntimeError(f"unexpected PoW challenge: {challenge_message}")

    challenge = bytes.fromhex(challenge_message["challenge"])
    difficulty = int(challenge_message["difficulty"])
    progress(f"solving {difficulty}-bit PoW")
    started = time.monotonic()
    nonce = solve_pow(challenge, difficulty)
    progress(f"PoW solved in {time.monotonic() - started:.2f}s")

    io.sendline(json.dumps({"nonce": nonce}).encode())
    response = json.loads(io.recvline())
    if response.get("status") != "ok":
        raise RuntimeError(f"PoW rejected: {response}")

    io.recvline()

def fake_mod_proof(ssid):
    pp = 164749022791188168631108908353403539035877921964276742418479713685623260643820944101104876318866742086619804587146844986287538445967320769639316849574286542038554967406262189485040459345102848218437027445769347835877251544977102383181474250605498126694266774100516051935157780534765989961839889283767115772383
    primes = [262147, 262151, 262153, 262187, 262193, 262217, 262231, 262237, 262253, 262261, 262271, 262303, 262313, 262321, 262331, 51421619175767008747828195587320027014833189255526574331070257779651247690557872623832309102953015421620103241832284838432465565940995693277648596456295113642337222016812809938709015867326542072748017151720349638705962170341709]
    N = 16158503035655503650357438344334975980222051334857742016065172713762327569433945446598600705761456731844358980460949009747059779575245460547544076193224141560315438683650498045875098875194826053398028819192033784138396109321380179000308733596026825062605356450615019631093426960503250130779167436263922484546662966335916298930586254657156418206965038954209852762617785012318248843464653570815735954712583243568635225572030518921744838918027895715082063968253608123043607091577446163730303533317458041570903283043923295778595848523270716509989836711104761332157129130262763472634038952197433461320998722457493023269061
    Iterations = 80
    phi_N = (pp - 1) * math.prod([pi - 1 for pi in primes])
    invN = pow(N, -1, phi_N)
    W = math.prod(primes)
    Y = [0] * Iterations
    for i in range(Iterations):
        prefix = [ssid, W, N] + Y[:i]
        ei = sha512_256i(*prefix)
        Y[i] = rejection_sample(N, ei)
    X = [0] * Iterations
    Z = [0] * Iterations
    Abz = bytearray([0xFF])
    Bbz = bytearray([0xFF])
    mp = (pp + 1)//4
    for i in range(Iterations):
        for j in range(4):
            a = (j & 1)
            b = 1
            Yi = Y[i] % N
            if a > 0:
                Yi = (-Yi) % N
            if b > 0:
                Yi = (W * Yi) % N
            Xpi = pow(Yi, pow(mp, 2, pp - 1), pp)
            Xi = (Xpi * W * pow(W, -1, pp)) % N
            if Yi != pow(Xi, 4, N):
                continue
            Zi = pow(Y[i] % N, invN, N)
            X[i], Z[i] = Xi, Zi
            Abz.append(a)
            Bbz.append(b)
            break
    A = int.from_bytes(bytes(Abz), 'big')
    B = int.from_bytes(bytes(Bbz), 'big')
    mod = ProofMod(W, X, A, B, Z)
    assert mod.verify(ssid, N)
    return N, primes, mod

def fake_logstar_proof(ssid, ec, pk, C, X, g, rho, x, NCap, s, t, prime):
    if any([c is None for c in[ec, pk, C, X, g, NCap, s, t, x, rho]]):
        raise ValueError("ProveLogstar constructor received nil value(s)")
    if ec.scalar_mult(C % ec.n, g) == X:
        raise ValueError("ProveLogstar is not provable")
    q = ec.n
    q3 = q * q * q
    qNCap = q * NCap
    q3NCap = q3 * NCap
    alpha = 1
    mu = random.randint(1, qNCap)
    r = random.randint(1, pk.n - 1)
    while math.gcd(r, pk.n) != 1:
        r = random.randint(1, pk.n - 1)
    gamma = random.randint(1, q3NCap)
    S = (pow(s, x, NCap) * pow(t, mu, NCap)) % NCap
    A = (pow(pk.gamma, alpha, pk.n_square) * pow(r, pk.n, pk.n_square)) % pk.n_square
    Y = ec.scalar_mult(alpha % q, g)
    D = (pow(s, alpha, NCap) * pow(t, gamma, NCap)) % NCap
    while True:
        e_hash = sha512_256i(ssid, pk.n, pk.gamma, ec.curve.b, ec.n, ec.p, C, X.x, X.y, g.x, g.y, S, A, Y.x, Y.y, D, NCap, s, t)
        e = rejection_sample(q, e_hash)
        if e % prime == 0:
            z1 = e * x + alpha
            z2 = (pow(rho % pk.n, e, pk.n) * (r % pk.n)) % pk.n
            z3 = e * mu + gamma
            return ProofLogstar(S, A, Y, D, z1, z2, z3).to_bytes_parts()
        else:
            alpha += 1
            A = (A * pk.gamma) % pk.n_square
            Y = ec.point_add(Y, g)
            D = (D * s) % NCap

def fake_enc_proof(ssid, ec, pk, K, NCap, s, t, k, rho, prime):
    q = ec.n
    q3 = q * q * q
    qNCap = q * NCap
    q3NCap = q3 * NCap
    alpha = 1
    mu = random.randint(1, qNCap)
    r = random.randint(1, pk.n - 1)
    while math.gcd(r, pk.n) != 1:
        r = random.randint(1, pk.n - 1)
    gamma = random.randint(1, q3NCap)
    S = (pow(s, k, NCap) * pow(t, mu, NCap)) % NCap
    A = (pow(pk.gamma, alpha, pk.n_square) * pow(r, pk.n, pk.n_square)) % pk.n_square
    C_ = (pow(s, alpha, NCap) * pow(t, gamma, NCap)) % NCap
    while True:
        e_hash = sha512_256i(ssid, pk.n, pk.gamma, ec.curve.b, ec.n, ec.p, NCap, s, t, K, S, A, C_)
        e = rejection_sample(q, e_hash)
        if e % prime == 0:
            z1 = e * k + alpha
            z2 = (pow(rho % pk.n, e, pk.n) * (r % pk.n)) % pk.n
            z3 = e * mu + gamma
            return ProofEnc(S, A, C_, z1, z2, z3)
        else:
            alpha += 1
            A = (A * pk.gamma) % pk.n_square
            C_ = (C_ * s) % NCap

io = start_target()
complete_pow(io)
protocol_started = time.monotonic()
p0 = Party(0)

p0.start_phase1()
io.sendline(json.dumps({"phase":1, "action":"start_phase"}).encode())
io.recvline()

recv = p0.phase1_round1()
id0, V0 = recv.id, recv.V
io.sendline(json.dumps({"phase":1, "action":"round1"}).encode())
recv = json.loads(io.recvline())["result"]
id1, V1 = [c for _, c in recv.items()]

msg_1_r1 = KeygenRound1Message(id=id1, V=V1)
recv = p0.phase1_round2(msg_1_r1)
rid0, X0, A0 = recv.rid, recv.X, recv.A
io.sendline(json.dumps({"phase":1, "action":"round2", "data":{"id": id0, "V": V0}}).encode())
recv = json.loads(io.recvline())["result"]
rid1, X1, A1 = [c for _, c in recv.items()]
X1 = deserialize_point(X1)
A1 = deserialize_point(A1)

msg_1_r2 = KeygenRound2Message(rid=rid1, X=X1, A=A1)
recv = p0.phase1_round3(msg_1_r2)
schX0, schA0, psi0 = recv.schX, recv.schA, recv.psi
io.sendline(json.dumps({"phase":1, "action":"round3", "data":{"rid": rid0, "X": serialize_point(X0), "A": serialize_point(A0)}}).encode())
recv = json.loads(io.recvline())["result"]
schX1, schA1, psi1 = [c for _, c in recv.items()]
schX1 = deserialize_bytes_list(schX1)
schA1 = deserialize_bytes_list(schA1)

msg_1_r3 = KeygenRound3Message(schX=schX1, schA=schA1, psi=psi1)
p0.phase1_round_out(msg_1_r3)
ssid = p0.keygen_data.ssid
io.sendline(json.dumps({"phase":1, "action":"round_out", "data":{"schX": serialize_bytes_list(schX0), "schA": serialize_bytes_list(schA0), "psi": psi0}}).encode())
recv = json.loads(io.recvline())["result"]

progress("building malicious aux setup")
id0 = 0
paillier_pub_0_n, primes, _ = fake_mod_proof(ssid)
p0_p = math.prod(primes)
p0_q = paillier_pub_0_n // p0_p
p0_pub = PublicKey(paillier_pub_0_n)
p0_priv = PrivateKey(
    paillier_pub_0_n,
    math.lcm(*[pi - 1 for pi in primes + [p0_q]]),
    math.prod([pi - 1 for pi in primes + [p0_q]]),
)
p0_lamd = random.randint(1, p0_priv.phi_n - 1)
r = random.randint(1, p0_pub.n - 1)
while math.gcd(r, p0_pub.n) != 1:
    r = random.randint(1, p0_pub.n - 1)
p0_ti = pow(r, 2, p0_pub.n)
p0_si = pow(p0_ti, p0_lamd, p0_pub.n)
p0_rhoi = random.randint(1, paillier_pub_0_n)
prm = ProofPrm.new_proof(ssid, p0_si, p0_ti, p0_priv.n, p0_priv.phi_n, p0_lamd)
p0_prm_parts = prm.to_bytes_parts()
prm_parts_0_ints = [int.from_bytes(part, "big") for part in p0_prm_parts]
V0 = sha512_256i(
    ssid,
    id0,
    paillier_pub_0_n,
    p0_si,
    p0_ti,
    *prm_parts_0_ints,
    p0_rhoi,
)

progress("starting target aux setup")
io.sendline(json.dumps({"phase":2, "action":"start_phase"}).encode())
io.recvline()
progress("target aux setup completed")

io.sendline(json.dumps({"phase":2, "action":"round1"}).encode())
recv = json.loads(io.recvline())["result"]
id1, V1 = [c for _, c in recv.items()]

msg_1_r1 = AuxRound1Message(id=id1, V=V1)
io.sendline(json.dumps({"phase":2, "action":"round2", "data":{"id": id0, "V": V0}}).encode())
recv = json.loads(io.recvline())["result"]
paillier_pub_1_n, s1, t1, prm1, rho1 = [c for _, c in recv.items()]
prm1 = deserialize_bytes_list(prm1)

# Cheat in aux - part 2
msg_1_r2 = AuxRound2Message(n=paillier_pub_1_n, s=s1, t=t1, prm=prm1, rho=rho1)
rho = p0_rhoi ^ rho1
_, _, mod0 = fake_mod_proof(ssid ^ rho)
mod_parts_0 = mod0.to_bytes_parts()
fac0 = ProofFac.new_proof(ssid ^ rho, p0.ec, paillier_pub_0_n, paillier_pub_1_n, s1, t1, p0_p, p0_q)
fac_parts_0 = fac0.to_bytes_parts()
# Done

io.sendline(json.dumps({"phase":2, "action":"round3", "data":{"n": paillier_pub_0_n, "s": int(p0_si), "t": int(p0_ti), "prm": serialize_bytes_list(p0_prm_parts), "rho": int(p0_rhoi)}}).encode())
recv = json.loads(io.recvline())["result"]
mod1, fac1 = [c for _, c in recv.items()]
mod1 = deserialize_bytes_list(mod1)
fac1 = deserialize_bytes_list(fac1)
io.sendline(json.dumps({"phase":2, "action":"round_out", "data":{"n": paillier_pub_0_n, "mod": serialize_bytes_list(mod_parts_0), "fac": serialize_bytes_list(fac_parts_0)}}).encode())
recv = json.loads(io.recvline())["result"]
p0.aux_data = AuxOutputData(
    paillier_priv_i=p0_priv,
    paillier_pub_i=p0_pub,
    si=int(p0_si),
    ti=int(p0_ti),
    paillier_pub_j=PublicKey(paillier_pub_1_n),
    sj=int(s1),
    tj=int(t1),
)

res = []
progress(f"{primes[:-1] = }")
for primei in primes[:-1]:
    np0 = paillier_pub_0_n // primei
    p0.start_phase3()
    io.sendline(json.dumps({"phase":3, "action":"start_phase"}).encode())
    io.recvline()

    # Cheat in Presigning - part 1
    _ = p0.phase3_round1()
    p0.presigning_protocol.k_i = 0
    p0.presigning_protocol.K_i_ct, p0.presigning_protocol.rho_i = p0.presigning_protocol.paillier_pub_i.encrypt_and_return_randomness(np0)
    p0.presigning_protocol.proof_enck_i = fake_enc_proof(ssid, p0.ec, p0.presigning_protocol.paillier_pub_i, p0.presigning_protocol.K_i_ct, p0.presigning_protocol.paillier_pub_j.n, p0.presigning_protocol.sj, p0.presigning_protocol.tj, p0.presigning_protocol.k_i, p0.presigning_protocol.rho_i, primei)
    p0.presigning_protocol.proof_enck_part_i = p0.presigning_protocol.proof_enck_i.to_bytes_parts()
    K0ct, G0ct, proofenc0 = p0.presigning_protocol.K_i_ct, p0.presigning_protocol.G_i_ct, p0.presigning_protocol.proof_enck_part_i
    # Done

    io.sendline(json.dumps({"phase":3, "action":"round1"}).encode())
    recv = json.loads(io.recvline())["result"]
    K1ct, G1ct, proofenc1 = [c for _, c in recv.items()]
    proofenc1 = deserialize_bytes_list(proofenc1)

    msg_1_r1 = PresigningRound1Message(K_ct = K1ct, G_ct = G1ct, proofenc=proofenc1)
    recv = p0.phase3_round2(msg_1_r1)
    Gamma0, D10, _D10, F10, _F10, psi_10, _psi_10, __psi_10 = astuple(recv)
    io.sendline(json.dumps({"phase":3, "action":"round2", "data":{"proofenc": serialize_bytes_list(proofenc0), "K_ct": K0ct, "G_ct": G0ct}}).encode())
    recv = json.loads(io.recvline())["result"]
    Gamma1, D01, _D01, F01, _F01, psi_01, _psi_01, __psi_01 = [c for _, c in recv.items()]
    Gamma1 = deserialize_point(Gamma1)
    D01 = int(D01)
    _D01 = int(_D01)
    F01 = int(F01)
    _F01 = int(_F01)
    psi_01 = deserialize_bytes_list(psi_01)
    _psi_01 = deserialize_bytes_list(_psi_01)
    __psi_01 = deserialize_bytes_list(__psi_01)

    msg_1_r2 = PresigningRound2Message(Gamma=Gamma1, D=D01, _D=_D01, F=F01, _F=_F01, psi_affg_gamma=psi_01, psi_affg_xi=_psi_01, psi_logstar_gamma=__psi_01)
    _ = p0.phase3_round3(msg_1_r2)

    alpha_ij = p0.presigning_protocol.paillier_priv_i.decrypt(msg_1_r2.D)
    _alpha_ij = p0.presigning_protocol.paillier_priv_i.decrypt(msg_1_r2._D)

    _, gamma_mask = recover_affg_residue_and_mask(
        ssid,
        p0,
        np0,
        alpha_ij,
        primei,
        msg_1_r2.D,
        msg_1_r2.F,
        Gamma1,
        psi_01,
    )
    xpi, xi_mask = recover_affg_residue_and_mask(
        ssid,
        p0,
        np0,
        _alpha_ij,
        primei,
        msg_1_r2._D,
        msg_1_r2._F,
        X1,
        _psi_01,
    )

    progress(f"x1 = {xpi} (mod {primei})")
    res.append(xpi)

    # Cheat in presigning - part 2
    alpha_ij = gamma_mask % p0.ec.n
    _alpha_ij = xi_mask % p0.ec.n
    delta_0 = (p0.presigning_protocol.gamma_i * p0.presigning_protocol.k_i + alpha_ij + p0.presigning_protocol.beta_ij) % p0.ec.n
    vdelta_0 = p0.ec.scalar_mult(p0.presigning_protocol.k_i, p0.presigning_protocol.Gamma)
    p0.presigning_protocol.vdelta_i = vdelta_0
    p0.presigning_protocol.delta_i = delta_0
    p0.presigning_protocol.chi_i = (p0.presigning_protocol.xi * p0.presigning_protocol.k_i + _alpha_ij + p0.presigning_protocol._beta_ij) % p0.ec.n
    psi_10_ = fake_logstar_proof(ssid, p0.ec, p0.presigning_protocol.paillier_pub_i, p0.presigning_protocol.K_i_ct, p0.presigning_protocol.vdelta_i, p0.presigning_protocol.Gamma, p0.presigning_protocol.rho_i, p0.presigning_protocol.k_i, p0.presigning_protocol.paillier_pub_j.n, p0.presigning_protocol.sj, p0.presigning_protocol.tj, primei)
    # Done

    io.sendline(json.dumps({"phase":3, "action":"round3", "data":{"Gamma": serialize_point(Gamma0), "G_ct": G0ct, "D": D10, "_D": _D10, "F": F10, "_F": _F10, "psi_affg_gamma": serialize_bytes_list(psi_10), "psi_affg_xi": serialize_bytes_list(_psi_10), "psi_logstar_gamma": serialize_bytes_list(__psi_10)}}).encode())
    recv = json.loads(io.recvline())["result"]
    delta_1, vdelta_1, psi_01_ = [c for _, c in recv.items()]
    delta_1 = int(delta_1)
    vdelta_1 = deserialize_point(vdelta_1)
    psi_01_ = deserialize_bytes_list(psi_01_)

    msg_1_r3 = PresigningRound3Message(delta=delta_1, vdelta=vdelta_1, psi=psi_01_)
    recv = p0.phase3_round_out(msg_1_r3)
    R0 = astuple(recv)
    io.sendline(json.dumps({"phase":3, "action":"round_out", "data":{"delta": int(delta_0), "vdelta": serialize_point(vdelta_0), "psi": serialize_bytes_list(psi_10_)}}).encode())
    recv = json.loads(io.recvline())["result"]
    R1 = [c for _, c in recv.items()]

    p0.start_phase4()
    io.sendline(json.dumps({"phase":4, "action":"start_phase"}).encode())
    io.recvline()

    msg = b"Hello, world!"
    msg_0_sign = p0.phase4_sign(msg)
    msg_0_sign.proof_logstar_k = fake_logstar_proof(
        ssid,
        p0.ec,
        p0.signing_protocol.paillier_pub_i,
        p0.signing_protocol.K_i_ct,
        p0.signing_protocol.R_k_i,
        p0.signing_protocol.R,
        p0.signing_protocol.rho_i,
        p0.signing_protocol.k_i,
        p0.signing_protocol.paillier_pub_j.n,
        p0.signing_protocol.sj,
        p0.signing_protocol.tj,
        primei,
    )
    io.sendline(json.dumps({"phase":4, "action":"sign", "data":{"message": msg.hex()}}).encode())
    recv = json.loads(io.recvline())["result"]
    msg_1_sign = SigningMessage.from_dict(recv)

    assert p0.phase4_verify(msg, msg_1_sign)
    io.sendline(json.dumps({"phase":4, "action":"verify", "data":msg_0_sign.to_dict()}).encode())
    recv = json.loads(io.recvline())
    if recv["status"] != "ok" or recv["result"]["verify"] is not True:
        raise RuntimeError(f"server rejected signing transcript: {recv}")

crt_modulus = math.prod(primes[:-1])
x1 = int(crt(primes[:-1], res)[0] % crt_modulus)
progress(f"{x1 = }")

for guess in range(x1, int(p0.ec.n), crt_modulus):
    progress(f"trying guess = {guess}")
    io.sendline(json.dumps({"action":"guess_key", "data":{"guess":guess}}).encode())
    response = json.loads(io.recvline())
    progress(json.dumps(response))
    if response.get("result", {}).get("correct") is True:
        progress(f"protocol completed in {time.monotonic() - protocol_started:.2f}s")
        break
else:
    raise RuntimeError("all CRT candidates were rejected")
