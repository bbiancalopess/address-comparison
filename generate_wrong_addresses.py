import random
import pandas as pd
import unicodedata

ABREVIACOES = {
    "RUA": "R",
    "AVENIDA": "AV",
    "TRAVESSA": "TV",
    "ALAMEDA": "AL",
    "RODOVIA": "ROD",
    "PRAÇA": "PC",
    "PRACA": "PC"
}


def remover_acentos(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def abreviar_tipo(tipo):
    return ABREVIACOES.get(tipo.upper(), tipo)


def remover_tipo_logradouro(tipo):
    return ""


def erro_digitacao(texto):
    if not texto or len(texto) < 4:
        return texto

    pos = len(texto) // 2

    return texto[:pos] + texto[pos + 1:]


def trocar_numero(numero):

    try:
        numero = int(float(numero))
    except:
        return []

    return [
        str(numero - 2),
        str(numero - 1),
        str(numero + 1),
        str(numero + 2),
        str(numero + 10)
    ]


def montar_endereco(reg):

    partes = []

    tipo = reg["tipo_logradouro"].strip()
    logradouro = reg["logradouro"].strip()

    if tipo:
        partes.append(tipo)

    partes.append(logradouro)

    endereco = " ".join(partes)

    if reg["numero"]:
        endereco += f", {reg['numero']}"

    if reg["bairro"]:
        endereco += f", {reg['bairro']}"

    if reg["cep"]:
        endereco += f", {reg['cep']}"

    if reg["municipio"]:
        endereco += f", {reg['municipio']}"

    if reg["uf"]:
        endereco += f", {reg['uf']}"

    return endereco


def gerar_variacoes(registro):

    variacoes = []

    original = registro.copy()

    # endereço original
    variacoes.append({
        "tipo_erro": "ORIGINAL",
        "endereco": montar_endereco(original)
    })

    # abreviação do tipo
    novo = registro.copy()
    novo["tipo_logradouro"] = abreviar_tipo(
        novo["tipo_logradouro"]
    )

    variacoes.append({
        "tipo_erro": "ABREVIACAO",
        "endereco": montar_endereco(novo)
    })

    # remover tipo
    novo = registro.copy()
    novo["tipo_logradouro"] = ""

    variacoes.append({
        "tipo_erro": "SEM_TIPO",
        "endereco": montar_endereco(novo)
    })

    # remover acentos
    novo = registro.copy()

    for campo in [
        "tipo_logradouro",
        "logradouro",
        "bairro",
        "municipio"
    ]:
        novo[campo] = remover_acentos(
            novo[campo]
        )

    variacoes.append({
        "tipo_erro": "SEM_ACENTO",
        "endereco": montar_endereco(novo)
    })

    # erro no logradouro
    novo = registro.copy()

    novo["logradouro"] = erro_digitacao(
        novo["logradouro"]
    )

    variacoes.append({
        "tipo_erro": "ERRO_DIGITACAO",
        "endereco": montar_endereco(novo)
    })

    # remover bairro
    novo = registro.copy()
    novo["bairro"] = ""

    variacoes.append({
        "tipo_erro": "SEM_BAIRRO",
        "endereco": montar_endereco(novo)
    })

    # remover CEP
    novo = registro.copy()
    novo["cep"] = ""

    variacoes.append({
        "tipo_erro": "SEM_CEP",
        "endereco": montar_endereco(novo)
    })

    # trocar número
    for novo_numero in trocar_numero(
        registro["numero"]
    ):

        novo = registro.copy()
        novo["numero"] = novo_numero

        variacoes.append({
            "tipo_erro": "NUMERO_ALTERADO",
            "endereco": montar_endereco(novo)
        })

    return variacoes


def run_script():

    df = pd.read_csv(
        "original_addresses.csv",
        dtype=str
    )

    colunas = [
        "tipo_logradouro",
        "logradouro",
        "numero",
        "bairro",
        "cep",
        "municipio",
        "uf"
    ]

    df[colunas] = (
        df[colunas]
        .fillna("")
        .astype(str)
    )

    resultado = []

    for _, row in df.iterrows():

        registro = row.to_dict()

        endereco_original = montar_endereco(
            registro
        )

        variacoes = gerar_variacoes(
            registro
        )

        for v in variacoes:

            resultado.append({
                "endereco_original":
                    endereco_original,

                "endereco_modificado":
                    v["endereco"],

                "tipo_erro":
                    v["tipo_erro"],

                "label":
                    1
            })

    resultado = pd.DataFrame(resultado)

    resultado.to_csv(
        "modified_addresses.csv",
        index=False
    )

    print(
        f"{len(resultado)} registros gerados."
    )


if __name__ == "__main__":
    run_script()