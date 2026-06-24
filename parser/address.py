from dataclasses import dataclass


@dataclass
class Endereco:
    logradouro: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    estado: str = ""
    cep: str = ""