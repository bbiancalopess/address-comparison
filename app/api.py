"""API REST (FastAPI) do Fuzzy Address Matcher.

Endpoints:
    POST /compare        -> compara dois endereços
    POST /compare/batch  -> compara vários pares de uma vez
    GET  /health         -> verificação de saúde

Execução:
    uvicorn app.api:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.main import compare_addresses

app = FastAPI(
    title="Fuzzy Address Matcher",
    description="Comparador inteligente de endereços usando Sistemas Nebulosos.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Modelos de entrada/saída (pydantic)
# ---------------------------------------------------------------------------
class CompareRequest(BaseModel):
    address1: str = Field(..., examples=["Av Afonso Pena 1000 Centro Belo Horizonte MG"])
    address2: str = Field(..., examples=["Avenida Afonso Pena, 1000, Centro, BH - MG"])


class CompareResponse(BaseModel):
    score: float
    classification: str
    details: dict
    explanation: str


class BatchRequest(BaseModel):
    pairs: list[CompareRequest]


class BatchResponse(BaseModel):
    results: list[CompareResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> CompareResponse:
    """Compara dois endereços e devolve score, classificação e explicação."""
    result = compare_addresses(req.address1, req.address2)
    return CompareResponse(**result.as_dict())


@app.post("/compare/batch", response_model=BatchResponse)
def compare_batch(req: BatchRequest) -> BatchResponse:
    """Compara uma lista de pares de endereços."""
    results = [
        CompareResponse(**compare_addresses(p.address1, p.address2).as_dict())
        for p in req.pairs
    ]
    return BatchResponse(results=results)
