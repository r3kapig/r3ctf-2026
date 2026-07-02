import hashlib
import gmpy2
from crypto.common.ec import Point, ECOperations
from crypto.zkp.hv import ProofST, second_base_point
from crypto.zkp.logstar import ProofLogstar
from ecdsa.messages import PresigOutputData, SigningMessage
from ecdsa.errors import VerificationError

class Signing:

    def __init__(
        self, id: int, ec: ECOperations, presig_data: PresigOutputData, X: Point
    ):
        self.id = id
        self.ec = ec
        self.X = X
        self.R = presig_data.R
        self.H = second_base_point(ec)
        self.ssid = presig_data.ssid


        self.r = gmpy2.mpz(self.R.x) % self.ec.n
        if self.r == 0:
            raise ValueError("r cannot be 0 in ECDSA")


        self.k_i = gmpy2.mpz(presig_data.k_i)
        self.chi_i = gmpy2.mpz(presig_data.chi_i)
        self.R_k_i = presig_data.R_k_i or self.ec.scalar_mult(int(self.k_i), self.R)
        self.R_chi_i = presig_data.R_chi_i or self.ec.scalar_mult(
            int(self.chi_i), self.R
        )
        self.K_i_ct = presig_data.K_i_ct
        self.K_j_ct = presig_data.K_j_ct
        self.rho_i = presig_data.rho_i
        self.paillier_pub_i = presig_data.paillier_pub_i
        self.paillier_pub_j = presig_data.paillier_pub_j
        self.si = presig_data.si
        self.ti = presig_data.ti
        self.sj = presig_data.sj
        self.tj = presig_data.tj
        self.sigma_i: gmpy2.mpz = None

    def sign(self, message: bytes) -> SigningMessage:
        h = gmpy2.mpz(int.from_bytes(hashlib.sha256(message).digest(), "big"))
        self.sigma_i = (self.k_i * h + self.chi_i * self.r) % self.ec.n
        sigma_point = self.ec.scalar_mult(int(self.sigma_i), self.R)

        blind = self.ec.random_scalar()
        t_commit = self.ec.point_add(
            self.ec.scalar_mult(int(self.sigma_i)),
            self.ec.scalar_mult(blind, self.H),
        )
        proof_st = ProofST.new_proof(
            self.ec, sigma_point, t_commit, self.R, self.H, int(self.sigma_i), blind
        )

        proof_logstar_k = ProofLogstar.new_proof(
            self.ssid,
            self.ec,
            self.paillier_pub_i,
            self.K_i_ct,
            self.R_k_i,
            self.R,
            self.rho_i,
            int(self.k_i),
            int(self.paillier_pub_j.n),
            int(self.sj),
            int(self.tj),
        )

        return SigningMessage(
            sigma=int(self.sigma_i),
            sigma_point=sigma_point,
            R_k=self.R_k_i,
            R_chi=self.R_chi_i,
            t_commit=t_commit,
            proof_st=proof_st.to_bytes_parts(),
            proof_logstar_k=proof_logstar_k.to_bytes_parts(),
        )

    def verify(self, message: bytes, msg_j: SigningMessage) -> bool:
        self._verify_peer_zk(message, msg_j)

        h = gmpy2.mpz(int.from_bytes(hashlib.sha256(message).digest(), "big"))

        s = (self.sigma_i + gmpy2.mpz(msg_j.sigma)) % self.ec.n
        if s == 0:
            raise VerificationError("Signature S cannot be 0.")


        if not self.ec.verify(self.X, int(h), (int(self.r), int(s))):
            raise VerificationError("Signature verification failed.")

        return True

    def _verify_peer_zk(self, message: bytes, msg_j: SigningMessage) -> None:
        if self.sigma_i is None:
            raise VerificationError("Local signature share has not been computed.")

        required = [
            msg_j.sigma_point,
            msg_j.R_k,
            msg_j.R_chi,
            msg_j.t_commit,
            msg_j.proof_st,
            msg_j.proof_logstar_k,
        ]
        if any(v is None for v in required):
            raise VerificationError("Signing message is missing ZK consistency data.")

        if self.ec.scalar_mult(int(msg_j.sigma), self.R) != msg_j.sigma_point:
            raise VerificationError("Peer sigma point does not match sigma scalar.")

        proof_st = ProofST.from_bytes(self.ec, msg_j.proof_st)
        if not proof_st.verify(self.ec, msg_j.sigma_point, msg_j.t_commit, self.R, self.H):
            raise VerificationError("Peer ST proof verification failed.")

        proof_logstar_k = ProofLogstar.from_bytes(self.ec, msg_j.proof_logstar_k)
        if not proof_logstar_k.verify(
            self.ssid,
            self.ec,
            self.paillier_pub_j,
            self.K_j_ct,
            msg_j.R_k,
            self.R,
            int(self.paillier_pub_i.n),
            int(self.si),
            int(self.ti),
        ):
            raise VerificationError("Peer nonce Logstar proof verification failed.")

        h = gmpy2.mpz(int.from_bytes(hashlib.sha256(message).digest(), "big")) % self.ec.n
        expected_sigma_point = self.ec.point_add(
            self.ec.scalar_mult(int(h), msg_j.R_k),
            self.ec.scalar_mult(int(self.r), msg_j.R_chi),
        )
        if expected_sigma_point != msg_j.sigma_point:
            raise VerificationError("Peer signature share point equation failed.")
