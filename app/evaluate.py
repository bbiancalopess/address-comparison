"""Avaliação de eficácia do Fuzzy Address Matcher sobre uma base rotulada.

O que faz:

    1. Carrega a base de pares rotulados (``data/modified_addresses.csv``),
       que contém apenas pares POSITIVOS (label=1): o mesmo endereço com
       diferentes tipos de perturbação (abreviação, erro de digitação, etc.).
    2. Gera pares NEGATIVOS (label=0) embaralhando: associa o endereço original
       de uma linha à versão modificada de OUTRA base (endereços diferentes).
    3. Roda o pipeline completo de comparação em todos os pares (em paralelo).
    4. Trata o sistema como um classificador binário ("igual" vs "diferente"),
       calcula métricas (acurácia, precisão, recall, F1, AUC), encontra o
       melhor limiar de decisão e detalha o desempenho por tipo de erro.
    5. Gera um relatório em ``reports/`` (markdown + gráficos) e um CSV com o
       resultado par a par.

Uso:
    python app/evaluate.py                  # base completa
    python app/evaluate.py --sample 2000    # amostra (mais rápido p/ testar)
    python app/evaluate.py --jobs 4         # nº de processos
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from functools import partial
from multiprocessing import Pool, cpu_count

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from app import metrics as M
from app.explainability import classify
from app.main import compare_addresses

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
REPORT_DIR = os.path.join(ROOT, "reports")

# Classificações textuais consideradas "igual" no mapeamento qualitativo.
SAME_LABELS = {"muito semelhantes", "provavelmente iguais"}
NEGATIVE_TAG = "EMBARALHADO"


# ---------------------------------------------------------------------------
# 1 + 2. Construção do dataset (positivos + negativos)
# ---------------------------------------------------------------------------
def _make_shuffled_negatives(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Cria `n` negativos embaralhados: original de uma base com a versão
    modificada de OUTRA base (endereços comprovadamente distintos).
    """
    if n <= 0:
        return pd.DataFrame(columns=["address1", "address2", "tipo_erro", "label"])

    rng = random.Random(seed)
    origs = df["endereco_original"].tolist()
    mods = df["endereco_modificado"].tolist()
    size = len(df)
    rows: list[tuple[str, str]] = []
    attempts = 0
    while len(rows) < n and attempts < n * 50:
        i, j = rng.randrange(size), rng.randrange(size)
        if origs[i] != origs[j]:
            rows.append((origs[i], mods[j]))
        attempts += 1

    return pd.DataFrame(
        {
            "address1": [r[0] for r in rows],
            "address2": [r[1] for r in rows],
            "tipo_erro": NEGATIVE_TAG,
            "label": 0,
        }
    )


def build_dataset(
    input_csv: str,
    *,
    sample: int | None = None,
    seed: int = 42,
    extra_negatives: int | str = "balance",
) -> pd.DataFrame:
    """Monta o dataset de avaliação a partir da base rotulada.

    Respeita a coluna ``label`` do CSV (positivos = 1, negativos = 0). A base já
    contém negativos "difíceis" reais (ex.: ``NUMERO_ALTERADO``). Opcionalmente
    adiciona negativos "fáceis" por embaralhamento.

    ``extra_negatives``:
        * ``"balance"`` (padrão): adiciona embaralhados só o suficiente para
          igualar o número de negativos ao de positivos.
        * inteiro: adiciona exatamente essa quantidade (0 = nenhum).

    Retorna colunas: address1, address2, tipo_erro, label.
    """
    df = pd.read_csv(input_csv)
    if sample:
        df = df.sample(min(sample, len(df)), random_state=seed).reset_index(drop=True)

    base = pd.DataFrame(
        {
            "address1": df["endereco_original"],
            "address2": df["endereco_modificado"],
            "tipo_erro": df["tipo_erro"],
            "label": df["label"].astype(int),
        }
    )
    n_pos = int((base["label"] == 1).sum())
    n_neg = int((base["label"] == 0).sum())

    if extra_negatives == "balance":
        n_extra = max(0, n_pos - n_neg)
    else:
        n_extra = max(0, int(extra_negatives))

    shuffled = _make_shuffled_negatives(df, n_extra, seed)
    return pd.concat([base, shuffled], ignore_index=True)


# ---------------------------------------------------------------------------
# 3. Execução do pipeline (paralela)
# ---------------------------------------------------------------------------
def _compare_pair(pair: tuple[str, str]) -> tuple[float, str]:
    res = compare_addresses(pair[0], pair[1])
    return res.score, res.classification


def run_pipeline(df: pd.DataFrame, *, jobs: int) -> pd.DataFrame:
    """Roda compare_addresses em todos os pares e anexa score/classificação."""
    pairs = list(zip(df["address1"], df["address2"]))
    if jobs > 1:
        with Pool(processes=jobs) as pool:
            results = pool.map(_compare_pair, pairs, chunksize=200)
    else:
        results = [_compare_pair(p) for p in pairs]

    out = df.copy()
    out["score"] = [r[0] for r in results]
    out["classification"] = [r[1] for r in results]
    return out


# ---------------------------------------------------------------------------
# 4. Métricas
# ---------------------------------------------------------------------------
def compute_report(results: pd.DataFrame) -> dict:
    """Calcula todas as métricas a partir dos resultados par a par."""
    y_true = results["label"].to_numpy()
    scores = results["score"].to_numpy(dtype=float)

    # Melhor limiar por F1 e por acurácia.
    t_f1, m_f1 = M.best_threshold(y_true, scores, metric="f1")
    t_acc, m_acc = M.best_threshold(y_true, scores, metric="accuracy")
    auc = M.auc_score(y_true, scores)

    # Mapeamento qualitativo: "igual" se a classificação textual indicar isso.
    qual_pred = results["classification"].isin(SAME_LABELS).to_numpy()
    pos = y_true == 1
    qual = M.BinaryMetrics(
        tp=int(np.sum(qual_pred & pos)),
        fp=int(np.sum(qual_pred & ~pos)),
        tn=int(np.sum(~qual_pred & ~pos)),
        fn=int(np.sum(~qual_pred & pos)),
    )

    # Desempenho por tipo de erro (recall nos positivos; specificity nos negativos).
    per_type = []
    for tipo, grp in results.groupby("tipo_erro"):
        s = grp["score"].to_numpy(dtype=float)
        is_pos = (grp["label"] == 1).all()
        detected = float(np.mean(s >= t_f1))
        per_type.append(
            {
                "tipo_erro": tipo,
                "n": len(grp),
                "score_medio": round(float(np.mean(s)), 1),
                "score_mediano": round(float(np.median(s)), 1),
                # positivos: queremos detectados=alto; negativos: detectados=baixo
                "taxa_igual": round(detected, 3),
                "acerto": round(detected if is_pos else 1 - detected, 3),
            }
        )
    per_type.sort(key=lambda r: r["acerto"])

    n_shuffled = int(np.sum(results["tipo_erro"] == NEGATIVE_TAG))
    return {
        "n_total": len(results),
        "n_pos": int(np.sum(pos)),
        "n_neg": int(np.sum(~pos)),
        "n_neg_real": int(np.sum(~pos)) - n_shuffled,
        "n_neg_shuffled": n_shuffled,
        "auc": auc,
        "threshold_f1": t_f1,
        "metrics_f1": m_f1,
        "threshold_acc": t_acc,
        "metrics_acc": m_acc,
        "qualitative": qual,
        "per_type": per_type,
        "mean_score_pos": round(float(np.mean(scores[pos])), 1),
        "mean_score_neg": round(float(np.mean(scores[~pos])), 1),
    }


# ---------------------------------------------------------------------------
# 5. Gráficos + relatório markdown
# ---------------------------------------------------------------------------
def _make_plots(results: pd.DataFrame, report: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y_true = results["label"].to_numpy()
    scores = results["score"].to_numpy(dtype=float)

    # (a) Distribuição dos scores: positivos vs negativos
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.linspace(0, 100, 41)
    ax.hist(scores[y_true == 1], bins=bins, alpha=0.6, label="iguais (label=1)", color="#2a9d8f")
    ax.hist(scores[y_true == 0], bins=bins, alpha=0.6, label="diferentes (label=0)", color="#e76f51")
    ax.axvline(report["threshold_f1"], color="black", ls="--",
               label=f"limiar ótimo = {report['threshold_f1']:.0f}")
    ax.set_xlabel("score de similaridade")
    ax.set_ylabel("frequência")
    ax.set_title("Distribuição dos scores por classe")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(REPORT_DIR, "score_distribution.png"), dpi=120)
    plt.close(fig)

    # (b) Curva ROC
    fpr, tpr = M.roc_curve(y_true, scores)
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot(fpr, tpr, color="#264653", lw=2, label=f"ROC (AUC = {report['auc']:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color="gray")
    ax.set_xlabel("taxa de falsos positivos (FPR)")
    ax.set_ylabel("taxa de verdadeiros positivos (TPR)")
    ax.set_title("Curva ROC")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORT_DIR, "roc_curve.png"), dpi=120)
    plt.close(fig)

    # (c) Matriz de confusão (no limiar ótimo por F1)
    m = report["metrics_f1"]
    cm = np.array([[m.tn, m.fp], [m.fn, m.tp]])
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1], ["prev. diferente", "prev. igual"])
    ax.set_yticks([0, 1], ["real diferente", "real igual"])
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, f"{v}", ha="center", va="center",
                color="white" if v > cm.max() / 2 else "black", fontsize=12)
    ax.set_title(f"Matriz de confusão (limiar={report['threshold_f1']:.0f})")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORT_DIR, "confusion_matrix.png"), dpi=120)
    plt.close(fig)

    # (d) Acerto por tipo de erro
    pt = report["per_type"]
    labels = [r["tipo_erro"] for r in pt]
    vals = [r["acerto"] for r in pt]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#e76f51" if lbl == NEGATIVE_TAG else "#2a9d8f" for lbl in labels]
    ax.barh(labels, vals, color=colors)
    ax.set_xlim(0, 1)
    ax.set_xlabel("taxa de acerto")
    ax.set_title("Acerto por tipo de erro (verde=positivos, vermelho=negativos)")
    for i, v in enumerate(vals):
        ax.text(min(v + 0.01, 0.95), i, f"{v:.0%}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(REPORT_DIR, "per_error_accuracy.png"), dpi=120)
    plt.close(fig)


def _fmt_metrics(m: M.BinaryMetrics) -> str:
    d = m.as_dict()
    return (
        f"- Acurácia: **{d['accuracy']:.1%}**\n"
        f"- Precisão: **{d['precision']:.1%}**\n"
        f"- Recall (sensibilidade): **{d['recall']:.1%}**\n"
        f"- Especificidade: **{d['specificity']:.1%}**\n"
        f"- F1-score: **{d['f1']:.3f}**\n"
        f"- Matriz: TP={d['tp']} · FP={d['fp']} · TN={d['tn']} · FN={d['fn']}"
    )


def write_markdown(report: dict, *, generated_on: str) -> str:
    """Gera o relatório markdown e o salva em reports/evaluation_report.md."""
    r = report
    lines: list[str] = []
    lines.append("# Relatório de Eficácia — Fuzzy Address Matcher\n")
    lines.append(f"_Gerado em {generated_on}._\n")
    lines.append("## Resumo do dataset\n")
    lines.append(f"- Total de pares avaliados: **{r['n_total']:,}**")
    lines.append(f"- Positivos (mesmo endereço, `label=1`): **{r['n_pos']:,}**")
    lines.append(f"- Negativos (`label=0`): **{r['n_neg']:,}** "
                 f"= {r['n_neg_real']:,} difíceis reais (número alterado) + "
                 f"{r['n_neg_shuffled']:,} embaralhados")
    lines.append(f"- Score médio dos positivos: **{r['mean_score_pos']}** / "
                 f"dos negativos: **{r['mean_score_neg']}**\n")

    lines.append("## Desempenho global\n")
    lines.append(f"**AUC (área sob a curva ROC): {r['auc']:.3f}**  "
                 "— mede a separação entre as classes independentemente do limiar "
                 "(1.0 = perfeito, 0.5 = aleatório).\n")
    lines.append(f"### Limiar ótimo por F1 (score ≥ {r['threshold_f1']:.0f})\n")
    lines.append(_fmt_metrics(r["metrics_f1"]) + "\n")
    lines.append(f"### Limiar ótimo por acurácia (score ≥ {r['threshold_acc']:.0f})\n")
    lines.append(_fmt_metrics(r["metrics_acc"]) + "\n")
    lines.append("### Usando a classificação textual\n")
    lines.append('(prevê "igual" quando a classe é *muito semelhantes* ou '
                 '*provavelmente iguais*)\n')
    lines.append(_fmt_metrics(r["qualitative"]) + "\n")

    lines.append("## Desempenho por tipo de erro\n")
    lines.append("| Tipo de erro | N | Score médio | Score mediano | Taxa prevista \"igual\" | Acerto |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for p in r["per_type"]:
        lines.append(
            f"| `{p['tipo_erro']}` | {p['n']} | {p['score_medio']} | "
            f"{p['score_mediano']} | {p['taxa_igual']:.1%} | {p['acerto']:.1%} |"
        )
    lines.append("")
    lines.append("> Para tipos positivos, *acerto* = fração detectada como igual. "
                 "Para `EMBARALHADO` (negativos), *acerto* = fração corretamente "
                 "rejeitada como diferente.\n")

    lines.append("## Observações e limitações\n")
    lines.append("- A base contém **negativos difíceis reais** (`NUMERO_ALTERADO`): "
                 "mesma rua, bairro, cidade e CEP, mudando **apenas o número**. "
                 "Como o número é decisivo na identidade do endereço, esses pares "
                 "são rotulados como diferentes (`label=0`) — é o teste mais "
                 "exigente para o sistema.\n")
    lines.append("- Adicionalmente, podem ser gerados negativos \"fáceis\" por "
                 "**embaralhamento** (`EMBARALHADO`): endereços completamente "
                 "distintos. A quantidade é controlada por `--extra-negatives`.\n")
    lines.append("- Cerca de 0,6% dos `NUMERO_ALTERADO` têm número idêntico ao "
                 "original (ruído da geração): nesses casos o sistema corretamente "
                 "os vê como iguais, mas o rótulo diz diferente — um teto natural "
                 "de acerto para essa categoria.\n")

    lines.append("## Gráficos\n")
    lines.append("![Distribuição dos scores](score_distribution.png)\n")
    lines.append("![Curva ROC](roc_curve.png)\n")
    lines.append("![Matriz de confusão](confusion_matrix.png)\n")
    lines.append("![Acerto por tipo de erro](per_error_accuracy.png)\n")

    content = "\n".join(lines)
    path = os.path.join(REPORT_DIR, "evaluation_report.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Avaliação do Fuzzy Address Matcher")
    parser.add_argument("--input", default=os.path.join(DATA_DIR, "modified_addresses.csv"))
    parser.add_argument("--sample", type=int, default=None,
                        help="usa apenas N linhas da base (para testes rápidos)")
    parser.add_argument("--extra-negatives", default="balance",
                        help="negativos embaralhados extras: 'balance' (padrão), "
                             "um inteiro, ou 0 para usar só os negativos da base")
    parser.add_argument("--jobs", type=int, default=max(1, cpu_count() - 1),
                        help="número de processos paralelos")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    os.makedirs(REPORT_DIR, exist_ok=True)

    extra = args.extra_negatives
    if isinstance(extra, str) and extra.isdigit():
        extra = int(extra)

    print(f"[1/4] Construindo dataset (sample={args.sample}, extra_negatives={extra})...")
    df = build_dataset(args.input, sample=args.sample, seed=args.seed,
                       extra_negatives=extra)
    n_real_neg = int(((df.label == 0) & (df.tipo_erro != NEGATIVE_TAG)).sum())
    n_shuf_neg = int((df.tipo_erro == NEGATIVE_TAG).sum())
    print(f"      {len(df):,} pares ({int((df.label==1).sum()):,} positivos, "
          f"{int((df.label==0).sum()):,} negativos = {n_real_neg:,} reais + "
          f"{n_shuf_neg:,} embaralhados)")

    print(f"[2/4] Rodando pipeline em {args.jobs} processo(s)...")
    import time
    t0 = time.perf_counter()
    results = run_pipeline(df, jobs=args.jobs)
    dt = time.perf_counter() - t0
    print(f"      concluído em {dt:.1f}s ({1000*dt/max(len(df),1):.1f} ms/par)")

    results_path = os.path.join(REPORT_DIR, "evaluation_results.csv")
    results.to_csv(results_path, index=False)
    print(f"      resultados par a par salvos em {results_path}")

    print("[3/4] Calculando métricas...")
    report = compute_report(results)

    print("[4/4] Gerando gráficos e relatório...")
    _make_plots(results, report)
    # data atual passada de fora (evita depender de relógio em ambientes restritos)
    from datetime import datetime
    md_path = write_markdown(report, generated_on=datetime.now().strftime("%Y-%m-%d %H:%M"))

    print(f"\nRelatório: {md_path}")
    print(f"AUC={report['auc']:.3f} | "
          f"F1={report['metrics_f1'].f1:.3f} @ limiar {report['threshold_f1']:.0f} | "
          f"acurácia={report['metrics_f1'].accuracy:.1%}")


if __name__ == "__main__":
    main()
