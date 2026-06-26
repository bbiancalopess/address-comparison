"""Métricas de avaliação binária (sem dependências externas além de numpy).

Implementadas manualmente, de forma didática, para medir a eficácia do
comparador de endereços tratado como um classificador binário
(par "igual" = positivo / "diferente" = negativo).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BinaryMetrics:
    """Métricas a partir de uma matriz de confusão."""

    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total else 0.0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        """Sensibilidade / TPR — fração de positivos corretamente detectados."""
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def specificity(self) -> float:
        """TNR — fração de negativos corretamente rejeitados."""
        denom = self.tn + self.fp
        return self.tn / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def as_dict(self) -> dict:
        return {
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "specificity": round(self.specificity, 4),
            "f1": round(self.f1, 4),
            "tp": self.tp, "fp": self.fp, "tn": self.tn, "fn": self.fn,
        }


def confusion_at_threshold(
    y_true: np.ndarray, scores: np.ndarray, threshold: float
) -> BinaryMetrics:
    """Matriz de confusão prevendo "igual" quando score >= threshold."""
    pred = scores >= threshold
    pos = y_true == 1
    tp = int(np.sum(pred & pos))
    fp = int(np.sum(pred & ~pos))
    tn = int(np.sum(~pred & ~pos))
    fn = int(np.sum(~pred & pos))
    return BinaryMetrics(tp=tp, fp=fp, tn=tn, fn=fn)


def best_threshold(
    y_true: np.ndarray, scores: np.ndarray, *, metric: str = "f1"
) -> tuple[float, BinaryMetrics]:
    """Varre os limiares possíveis e retorna o que maximiza a métrica dada."""
    candidates = np.unique(np.concatenate([scores, [0.0, 100.0]]))
    best_val, best_t, best_m = -1.0, 50.0, None
    for t in candidates:
        m = confusion_at_threshold(y_true, scores, t)
        val = getattr(m, metric)
        if val > best_val:
            best_val, best_t, best_m = val, float(t), m
    return best_t, best_m


def roc_curve(y_true: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Retorna (fpr, tpr) ao varrer todos os limiares (do maior ao menor)."""
    order = np.argsort(-scores)
    y = y_true[order]
    n_pos = max(int(np.sum(y_true == 1)), 1)
    n_neg = max(int(np.sum(y_true == 0)), 1)
    tp = np.cumsum(y == 1)
    fp = np.cumsum(y == 0)
    tpr = np.concatenate([[0.0], tp / n_pos])
    fpr = np.concatenate([[0.0], fp / n_neg])
    return fpr, tpr


def auc_score(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Área sob a curva ROC via estatística de Mann–Whitney (ranks)."""
    pos = scores[y_true == 1]
    neg = scores[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    # corrige empates atribuindo o rank médio
    sorted_scores = scores[order]
    i = 0
    while i < len(sorted_scores):
        j = i
        while j + 1 < len(sorted_scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        if j > i:
            avg = (ranks[order[i]] + ranks[order[j]]) / 2
            for k in range(i, j + 1):
                ranks[order[k]] = avg
        i = j + 1
    sum_ranks_pos = np.sum(ranks[y_true == 1])
    n_pos, n_neg = len(pos), len(neg)
    return float((sum_ranks_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
