from dataclasses import dataclass, asdict, is_dataclass
from typing import List, get_type_hints, get_origin, get_args
import json
import gmpy2
from crypto.common.utils import (
    serialize_point,
    deserialize_point,
    serialize_bytes_list,
    deserialize_bytes_list,
)
from crypto.common.ec import Point
from crypto.common.paillier import PrivateKey, PublicKey


class ProtocolMessage:

    def to_dict(self) -> dict:
        data = {}
        for key, value in asdict(self).items():
            if isinstance(value, Point):
                data[key] = serialize_point(value)
            elif isinstance(value, list) and value and isinstance(value[0], bytes):
                data[key] = serialize_bytes_list(value)
            elif isinstance(value, gmpy2.mpz):

                data[key] = int(value)
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: dict):
        if not is_dataclass(cls):
            raise TypeError("from_dict can only be called on a dataclass")

        kwargs = {}
        type_hints = get_type_hints(cls)

        for field_name, field_type in type_hints.items():
            if field_name not in data:
                continue

            value = data[field_name]

            if field_type is Point:
                kwargs[field_name] = deserialize_point(value)
                continue

            origin = get_origin(field_type)
            args = get_args(field_type)
            if origin is list and args and args[0] is bytes:
                kwargs[field_name] = deserialize_bytes_list(value)
            else:
                kwargs[field_name] = value

        return cls(**kwargs)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        return cls.from_dict(json.loads(json_str))

@dataclass
class KeygenRound1Message(ProtocolMessage):

    id: int
    V: int

@dataclass
class KeygenRound2Message(ProtocolMessage):

    rid: int
    X: Point
    A: Point

@dataclass
class KeygenRound3Message(ProtocolMessage):

    schX: List[bytes]
    schA: List[bytes]
    psi: int

@dataclass
class KeygenOutputMessage(ProtocolMessage):

    X: Point

@dataclass
class AuxRound1Message(ProtocolMessage):

    id: int
    V: int

@dataclass
class AuxRound2Message(ProtocolMessage):

    n: int
    s: int
    t: int
    prm: List[bytes]
    rho: int

@dataclass
class AuxRound3Message(ProtocolMessage):

    mod: List[bytes]
    fac: List[bytes]

@dataclass
class AuxOutputMessage(ProtocolMessage):

    n: int

@dataclass
class PresigningRound1Message(ProtocolMessage):

    K_ct: int
    G_ct: int
    proofenc: List[bytes]

@dataclass
class PresigningRound2Message(ProtocolMessage):

    Gamma: Point
    D: int
    _D: int
    F: int
    _F: int
    psi_affg_gamma: List[bytes]                               
    psi_affg_xi: List[bytes]                          
    psi_logstar_gamma: List[bytes]                          

@dataclass
class PresigningRound3Message(ProtocolMessage):

    delta: int
    vdelta: Point
    psi: List[bytes]

@dataclass
class PresigningOutputMessage(ProtocolMessage):

    R: Point

@dataclass
class SigningMessage(ProtocolMessage):

    sigma: int
    sigma_point: Point = None
    R_k: Point = None
    R_chi: Point = None
    t_commit: Point = None
    proof_st: List[bytes] = None
    proof_logstar_k: List[bytes] = None

@dataclass
class KeygenOutputData:

    ssid: int                                                         
    xi: int                                  
    Xi: Point                                  
    Xj: Point                                       
    X: Point                                  


@dataclass
class AuxOutputData:

    paillier_priv_i: PrivateKey                                      
    paillier_pub_i: PublicKey                                     
    si: int                                             
    ti: int                                             
    paillier_pub_j: PublicKey                                          
    sj: int                                                  
    tj: int                                                  


@dataclass
class PresigOutputData:

    R: Point                                                          
    k_i: int                             
    chi_i: int                                           
    ssid: int = None
    R_k_i: Point = None
    R_chi_i: Point = None
    K_i_ct: int = None
    K_j_ct: int = None
    rho_i: int = None
    paillier_pub_i: PublicKey = None
    paillier_pub_j: PublicKey = None
    si: int = None
    ti: int = None
    sj: int = None
    tj: int = None
