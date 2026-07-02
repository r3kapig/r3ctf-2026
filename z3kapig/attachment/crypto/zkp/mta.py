from dataclasses import dataclass
import gmpy2
from crypto.zkp.affg import ProofAffg
from crypto.common.ec import ECOperations, Point
from crypto.common.paillier import PublicKey
from crypto.common.numbers import random_positive_int


@dataclass
class MtAOut:
    Dji: int
    Fji: int
    sij: int
    rij: int
    beta: int
    Proofji: ProofAffg

def new_mta(
    ssid: int,
    ec: ECOperations,
    Kj: int,
    gamma_i: int,
    BigGamma_i: Point,
    pkj: PublicKey,
    pki: PublicKey,
    NCap: int,
    s: int,
    t: int,
) -> MtAOut:
    q = gmpy2.mpz(ec.n)
    gamma_i_mpz = gmpy2.mpz(gamma_i)
    Kj_mpz = gmpy2.mpz(Kj)

    beta_neg = gmpy2.mpz(random_positive_int(pkj.n))
    beta = (-beta_neg) % q

    gamma_i_mod_nj = gamma_i_mpz % pkj.n
    gammaK = pkj.homo_mult(int(gamma_i_mod_nj), int(Kj_mpz))

    Dji, sij = pkj.encrypt_and_return_randomness(int(beta_neg))
    Dji = pkj.homo_add(gammaK, Dji)

    beta_neg_mod_ni = beta_neg % pki.n
    Fji, rij = pki.encrypt_and_return_randomness(int(beta_neg_mod_ni))

    gamma_i_mod_q = gamma_i_mpz % q
    proof = ProofAffg.new_proof(
        ssid, ec, pkj, pki, NCap, s, t,
        int(Kj_mpz), Dji, Fji,
        BigGamma_i, int(gamma_i_mod_q), int(beta_neg),
        sij, rij,
    )

    return MtAOut(
        Dji=Dji,
        Fji=Fji,
        sij=sij,
        rij=rij,
        beta=int(beta),
        Proofji=proof,
    )
