import gmpy2
from crypto.common.ec import ECOperations, Point
from crypto.zkp.mta import new_mta
from crypto.zkp.affg import ProofAffg
from crypto.zkp.enc import ProofEnc
from crypto.zkp.logstar import ProofLogstar
from ecdsa.errors import VerificationError
from ecdsa.messages import (
    KeygenOutputData,
    AuxOutputData,
    PresigOutputData,
    PresigningRound1Message,
    PresigningRound2Message,
    PresigningRound3Message,
)

class Presigning:

    def __init__(
        self,
        party_id: int,
        ec: ECOperations,
        keygen_data: KeygenOutputData,
        aux_data: AuxOutputData,
    ):
        self.id = party_id
        self.ec = ec
        self.ssid = keygen_data.ssid


        self.xi = gmpy2.mpz(keygen_data.xi)
        self.Xi = keygen_data.Xi
        self.Xj = keygen_data.Xj
        self.paillier_pub_i = aux_data.paillier_pub_i
        self.paillier_priv_i = aux_data.paillier_priv_i
        self.si = gmpy2.mpz(aux_data.si)
        self.ti = gmpy2.mpz(aux_data.ti)
        self.paillier_pub_j = aux_data.paillier_pub_j
        self.sj = gmpy2.mpz(aux_data.sj)
        self.tj = gmpy2.mpz(aux_data.tj)


        self.k_i = gmpy2.mpz(self.ec.random_scalar())
        self.gamma_i = gmpy2.mpz(self.ec.random_scalar())
        self.K_i_ct, self.rho_i = self.paillier_pub_i.encrypt_and_return_randomness(
            int(self.k_i)
        )
        self.G_i_ct, self.nu_i = self.paillier_pub_i.encrypt_and_return_randomness(
            int(self.gamma_i)
        )
        self.Gamma_i = self.ec.scalar_mult(int(self.gamma_i))


        self.K_j_ct: int = None
        self.Gamma: Point = None
        self.vdelta_i: Point = None
        self.delta: gmpy2.mpz = None

    def round1(self) -> PresigningRound1Message:
        proof_enck_i = ProofEnc.new_proof(
            self.ssid,
            self.ec,
            self.paillier_pub_i,
            self.K_i_ct,
            int(self.paillier_pub_j.n),
            int(self.sj),
            int(self.tj),
            int(self.k_i),
            self.rho_i,
        )
        return PresigningRound1Message(
            K_ct=self.K_i_ct, G_ct=self.G_i_ct, proofenc=proof_enck_i.to_bytes_parts()
        )

    def round2(self, msg_j_r1: PresigningRound1Message) -> PresigningRound2Message:
        proof_enck_j = ProofEnc.from_bytes(msg_j_r1.proofenc)
        if not proof_enck_j.verify(
            self.ssid,
            self.ec,
            self.paillier_pub_j,
            int(self.paillier_pub_i.n),
            int(self.si),
            int(self.ti),
            msg_j_r1.K_ct,
        ):
            raise VerificationError("ProofEnc verification failed for other party.")

        self.K_j_ct = msg_j_r1.K_ct


        mtaG = new_mta(
            self.ssid,
            self.ec,
            self.K_j_ct,
            int(self.gamma_i),
            self.Gamma_i,
            self.paillier_pub_j,
            self.paillier_pub_i,
            int(self.paillier_pub_j.n),
            int(self.sj),
            int(self.tj),
        )
        self.beta_ij = gmpy2.mpz(mtaG.beta)


        mtaX = new_mta(
            self.ssid,
            self.ec,
            self.K_j_ct,
            int(self.xi),
            self.Xi,
            self.paillier_pub_j,
            self.paillier_pub_i,
            int(self.paillier_pub_j.n),
            int(self.sj),
            int(self.tj),
        )
        self._beta_ij = gmpy2.mpz(mtaX.beta)

        proof_logstar = ProofLogstar.new_proof(
            self.ssid,
            self.ec,
            self.paillier_pub_i,
            self.G_i_ct,
            self.Gamma_i,
            self.ec.G,
            self.nu_i,
            int(self.gamma_i),
            int(self.paillier_pub_j.n),
            int(self.sj),
            int(self.tj),
        )

        return PresigningRound2Message(
            Gamma=self.Gamma_i,
            D=mtaG.Dji,
            _D=mtaX.Dji,
            F=mtaG.Fji,
            _F=mtaX.Fji,
            psi_affg_gamma=mtaG.Proofji.to_bytes_parts(),
            psi_affg_xi=mtaX.Proofji.to_bytes_parts(),
            psi_logstar_gamma=proof_logstar.to_bytes_parts(),
        )

    def round3(
        self, G_j_ct: int, msg_j_r2: PresigningRound2Message
    ) -> PresigningRound3Message:
        psi_affg_gamma_ij = ProofAffg.from_bytes(self.ec, msg_j_r2.psi_affg_gamma)
        if not psi_affg_gamma_ij.verify(
            self.ssid,
            self.ec,
            self.paillier_pub_i,
            self.paillier_pub_j,
            int(self.paillier_pub_i.n),
            int(self.si),
            int(self.ti),
            self.K_i_ct,
            msg_j_r2.D,
            msg_j_r2.F,
            msg_j_r2.Gamma,
        ):
            raise VerificationError("First ProofAffg verification failed.")

        psi_affg_xi_ij = ProofAffg.from_bytes(self.ec, msg_j_r2.psi_affg_xi)
        if not psi_affg_xi_ij.verify(
            self.ssid,
            self.ec,
            self.paillier_pub_i,
            self.paillier_pub_j,
            int(self.paillier_pub_i.n),
            int(self.si),
            int(self.ti),
            self.K_i_ct,
            msg_j_r2._D,
            msg_j_r2._F,
            self.Xj,
        ):
            raise VerificationError("Second ProofAffg verification failed.")

        psi_logstar_gamma_ij = ProofLogstar.from_bytes(
            self.ec, msg_j_r2.psi_logstar_gamma
        )
        if not psi_logstar_gamma_ij.verify(
            self.ssid,
            self.ec,
            self.paillier_pub_j,
            G_j_ct,
            msg_j_r2.Gamma,
            self.ec.G,
            int(self.paillier_pub_i.n),
            int(self.si),
            int(self.ti),
        ):
            raise VerificationError("ProofLogstar verification failed.")

        self.Gamma = self.ec.point_add(self.Gamma_i, msg_j_r2.Gamma)
        self.vdelta_i = self.ec.scalar_mult(int(self.k_i), self.Gamma)

        alpha_ij = gmpy2.mpz(self.paillier_priv_i.decrypt(msg_j_r2.D))
        _alpha_ij = gmpy2.mpz(self.paillier_priv_i.decrypt(msg_j_r2._D))

        q = self.ec.n
        self.delta_i = (self.gamma_i * self.k_i + alpha_ij + self.beta_ij) % q
        self.chi_i = (self.xi * self.k_i + _alpha_ij + self._beta_ij) % q

        psi_logstar = ProofLogstar.new_proof(
            self.ssid,
            self.ec,
            self.paillier_pub_i,
            self.K_i_ct,
            self.vdelta_i,
            self.Gamma,
            self.rho_i,
            int(self.k_i),
            int(self.paillier_pub_j.n),
            int(self.sj),
            int(self.tj),
        )
        return PresigningRound3Message(
            delta=int(self.delta_i),
            vdelta=self.vdelta_i,
            psi=psi_logstar.to_bytes_parts(),
        )

    def round_out(self, msg_j_r3: PresigningRound3Message) -> PresigOutputData:
        psi_ij = ProofLogstar.from_bytes(self.ec, msg_j_r3.psi)
        if not psi_ij.verify(
            self.ssid,
            self.ec,
            self.paillier_pub_j,
            self.K_j_ct,
            msg_j_r3.vdelta,
            self.Gamma,
            int(self.paillier_pub_i.n),
            int(self.si),
            int(self.ti),
        ):
            raise VerificationError("Final ProofLogstar verification failed.")

        self.delta = (self.delta_i + gmpy2.mpz(msg_j_r3.delta)) % self.ec.n


        expected_point = self.ec.point_add(self.vdelta_i, msg_j_r3.vdelta)
        if self.ec.scalar_mult(int(self.delta)) != expected_point:
            raise VerificationError("Final delta verification failed.")

        delta_inv = gmpy2.invert(self.delta, self.ec.n)
        R = self.ec.scalar_mult(int(delta_inv), self.Gamma)
        R_k_i = self.ec.scalar_mult(int(self.k_i), R)
        R_chi_i = self.ec.scalar_mult(int(self.chi_i), R)

        return PresigOutputData(
            R=R,
            k_i=int(self.k_i),
            chi_i=int(self.chi_i),
            ssid=self.ssid,
            R_k_i=R_k_i,
            R_chi_i=R_chi_i,
            K_i_ct=self.K_i_ct,
            K_j_ct=self.K_j_ct,
            rho_i=self.rho_i,
            paillier_pub_i=self.paillier_pub_i,
            paillier_pub_j=self.paillier_pub_j,
            si=int(self.si),
            ti=int(self.ti),
            sj=int(self.sj),
            tj=int(self.tj),
        )
