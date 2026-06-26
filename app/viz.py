"""Visualização das funções de pertinência (membership functions).

Gera gráficos das variáveis fuzzy usando matplotlib. Útil para o README e
para a interface Streamlit. Pode ser executado diretamente para salvar as
imagens em ``data/``::

    python app/viz.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib

matplotlib.use("Agg")  # backend sem display (gera arquivos)
import matplotlib.pyplot as plt  # noqa: E402

from app.fuzzy_engine import UNIVERSE, FuzzyAddressEngine  # noqa: E402


def plot_memberships(engine: FuzzyAddressEngine | None = None):
    """Retorna uma figura matplotlib com as MFs de todas as variáveis."""
    engine = engine or FuzzyAddressEngine()
    variables = [
        ("Similaridade da Rua", engine.street),
        ("Similaridade do Número", engine.number),
        ("Similaridade da Cidade", engine.city),
        ("Similaridade do CEP", engine.cep),
        ("Similaridade Final (saída)", engine.final),
    ]

    fig, axes = plt.subplots(len(variables), 1, figsize=(8, 12))
    for ax, (title, var) in zip(axes, variables):
        for term in var.terms:
            ax.plot(UNIVERSE, var[term].mf, label=term, linewidth=2)
        ax.set_title(title)
        ax.set_xlabel("similaridade (0–100)")
        ax.set_ylabel("pertinência")
        ax.set_ylim(-0.05, 1.05)
        ax.legend(loc="upper center", ncol=len(var.terms), fontsize=8)
        ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def main() -> None:
    out_dir = os.path.join(os.path.dirname(__file__), os.pardir, "data")
    out_path = os.path.abspath(os.path.join(out_dir, "membership_functions.png"))
    fig = plot_memberships()
    fig.savefig(out_path, dpi=120)
    print(f"Gráfico salvo em: {out_path}")


if __name__ == "__main__":
    main()
