"""Comparação em lote via CSV + benchmark de desempenho.

Lê um CSV com colunas ``address1`` e ``address2`` (e opcionalmente
``expected``), compara todos os pares e grava os resultados.

Uso:
    python app/batch.py data/sample_addresses.csv data/results.csv
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from app.main import compare_addresses


def run_batch(input_csv: str, output_csv: str | None = None) -> pd.DataFrame:
    """Compara todos os pares de um CSV e retorna um DataFrame de resultados."""
    df = pd.read_csv(input_csv)
    rows = []
    start = time.perf_counter()
    for _, row in df.iterrows():
        res = compare_addresses(str(row["address1"]), str(row["address2"]))
        rows.append(
            {
                "address1": row["address1"],
                "address2": row["address2"],
                "score": res.score,
                "classification": res.classification,
                **({"expected": row["expected"]} if "expected" in df.columns else {}),
            }
        )
    elapsed = time.perf_counter() - start

    out = pd.DataFrame(rows)
    n = len(out)
    print(f"Comparados {n} pares em {elapsed:.3f}s "
          f"({1000 * elapsed / max(n, 1):.1f} ms/par)")

    if "expected" in out.columns:
        acc = (out["classification"] == out["expected"]).mean()
        print(f"Acurácia vs. esperado: {acc:.0%}")

    if output_csv:
        out.to_csv(output_csv, index=False)
        print(f"Resultados salvos em: {output_csv}")
    return out


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    input_csv = argv[0] if argv else "data/sample_addresses.csv"
    output_csv = argv[1] if len(argv) > 1 else "data/results.csv"
    df = run_batch(input_csv, output_csv)
    print()
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
