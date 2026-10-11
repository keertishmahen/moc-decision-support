"""
Generate matplotlib figures + metrics.json for docs/model_validation_report.md
Reuses training logic from train_predictor.py (no API keys required).

Run from repo root:
  python scripts/generate_model_validation_figures.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import (
    confusion_matrix,
    ConfusionMatrixDisplay,
    mean_absolute_error,
    mean_absolute_percentage_error,
)
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Repo root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from train_predictor import (  # noqa: E402
    GROUND_TRUTH,
    FEATURES,
    FEATURE_WEIGHTS,
    build_df,
)
from core.seed_neo4j import MOCS  # noqa: E402

OUT_DIR = os.path.join(ROOT, "docs", "model_validation", "figures")
METRICS_PATH = os.path.join(ROOT, "docs", "model_validation", "metrics.json")


def _loo_knn_predictions():
    df = build_df()
    X_raw = df[FEATURES].values.astype(float)
    y_cost = df["cost"].values
    y_dt = df["downtime"].values
    Xw = X_raw * FEATURE_WEIGHTS
    scaler = StandardScaler()
    Xs = scaler.fit_transform(Xw)
    cost_m = KNeighborsRegressor(n_neighbors=2, weights="distance", metric="euclidean")
    dt_m = KNeighborsRegressor(n_neighbors=2, weights="distance", metric="euclidean")
    loo = LeaveOneOut()
    yc = cross_val_predict(cost_m, Xs, y_cost, cv=loo)
    yd = cross_val_predict(dt_m, Xs, y_dt, cv=loo)
    return y_cost, y_dt, yc, yd, df


def _cost_tier(v: float) -> int:
    if v < 50_000:
        return 0  # Low
    if v < 110_000:
        return 1  # Medium
    return 2  # High


def _dt_tier(v: float) -> int:
    if v < 45:
        return 0
    if v < 95:
        return 1
    return 2


def _baseline_mae(y_true: np.ndarray, strategy: str) -> float:
    if strategy == "mean":
        pred = np.full_like(y_true, float(np.mean(y_true)), dtype=float)
    elif strategy == "median":
        pred = np.full_like(y_true, float(np.median(y_true)), dtype=float)
    else:
        raise ValueError(strategy)
    return float(mean_absolute_error(y_true, pred))


def _retrieval_proxy_tfidf():
    """
    Offline proxy: TF-IDF cosine similarity over title+description.
    Production RAG uses OpenAI embeddings (different geometry); this is a reproducible benchmark.
    """
    ids = [m["id"] for m in MOCS]
    docs = [f"{m['title']} {m['description']}" for m in MOCS]
    queries = [
        ("MoC-001", "feed pump P-101 replacement mechanical reliability"),
        ("MoC-002", "feed heater control valve FV-103 smart valve upgrade"),
        ("MoC-003", "reactor R-201 temperature setpoint increase catalyst yield"),
        ("MoC-004", "cyclone separator C-203 erosion inspection repair"),
        ("MoC-005", "catalyst slide valve SV-204 actuator advanced feedback"),
        ("MoC-006", "catalyst stripper steam optimization control valve"),
        ("MoC-007", "flue gas expander EX-403 blades seals energy recovery"),
        ("MoC-008", "fractionator reflux pump P-502 bearing seal failures"),
        ("MoC-009", "emergency shutdown procedure operator training audit"),
        ("MoC-010", "catalyst transfer line CTL-205 reinforcement weld inspection"),
    ]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=4000)
    X_doc = vec.fit_transform(docs)

    def precision_at_k(qtext: str, rel_id: str, k: int) -> float:
        qv = vec.transform([qtext])
        sims = cosine_similarity(qv, X_doc).ravel()
        top_idx = np.argsort(-sims)[:k]
        top_ids = [ids[i] for i in top_idx]
        return 1.0 if rel_id in top_ids else 0.0

    p1 = np.mean([precision_at_k(q, mid, 1) for mid, q in queries])
    p3 = np.mean([precision_at_k(q, mid, 3) for mid, q in queries])
    p5 = np.mean([precision_at_k(q, mid, 5) for mid, q in queries])
    return {"precision_at_1": p1, "precision_at_3": p3, "precision_at_5": p5, "method": "TF-IDF cosine (proxy; not OpenAI embeddings)"}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("ggplot")

    y_cost, y_dt, yc, yd, df = _loo_knn_predictions()

    cost_mae = float(mean_absolute_error(y_cost, yc))
    cost_mape = float(mean_absolute_percentage_error(y_cost, yc) * 100)
    dt_mae = float(mean_absolute_error(y_dt, yd))
    dt_mape = float(mean_absolute_percentage_error(y_dt + 1, yd + 1) * 100)

    baselines = {
        "cost_mae_mean_baseline": _baseline_mae(y_cost, "mean"),
        "cost_mae_median_baseline": _baseline_mae(y_cost, "median"),
        "downtime_mae_mean_baseline": _baseline_mae(y_dt, "mean"),
        "downtime_mae_median_baseline": _baseline_mae(y_dt, "median"),
    }

    # --- Figures: actual vs predicted ---
    def scatter_actual_pred(y, yhat, title, fname, xlabel, ylabel):
        fig, ax = plt.subplots(figsize=(6, 6))
        lim_max = max(float(np.max(y)), float(np.max(yhat))) * 1.05
        ax.scatter(y, yhat, s=70, edgecolors="k", alpha=0.85)
        ax.plot([0, lim_max], [0, lim_max], "r--", lw=1.5, label="Perfect fit")
        for i, r in enumerate(GROUND_TRUTH):
            ax.annotate(
                r["moc_id"],
                (y[i], yhat[i]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend(loc="upper left")
        ax.set_xlim(0, lim_max)
        ax.set_ylim(0, lim_max)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, fname), dpi=150)
        plt.close(fig)

    scatter_actual_pred(y_cost, yc, "KNN cost — LOO actual vs predicted", "knn_cost_actual_vs_pred.png", "Actual cost ($)", "Predicted cost ($)")
    scatter_actual_pred(y_dt, yd, "KNN downtime — LOO actual vs predicted", "knn_downtime_actual_vs_pred.png", "Actual downtime (h)", "Predicted downtime (h)")

    # Residuals
    def residual_plot(y, yhat, title, fname, xlab):
        res = yhat - y
        fig, ax = plt.subplots(figsize=(7, 4.2))
        ax.axhline(0, color="r", linestyle="--", lw=1.2)
        ax.scatter(np.arange(len(res)), res, s=65, edgecolors="k")
        for i, r in enumerate(GROUND_TRUTH):
            ax.annotate(
                r["moc_id"],
                (i, res[i]),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=8,
            )
        ax.set_title(title)
        ax.set_xlabel("MoC index (enumeration order)")
        ax.set_ylabel("Prediction error (predicted − actual)")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, fname), dpi=150)
        plt.close(fig)

    residual_plot(y_cost, yc, "KNN cost — LOO residual by MoC", "knn_residuals_cost.png", "")
    residual_plot(y_dt, yd, "KNN downtime — LOO residual by MoC", "knn_residuals_downtime.png", "")

    # Confusion matrices (tiered regression targets)
    yc_cls = np.array([_cost_tier(v) for v in y_cost])
    yc_hat_cls = np.array([_cost_tier(v) for v in yc])
    yd_cls = np.array([_dt_tier(v) for v in y_dt])
    yd_hat_cls = np.array([_dt_tier(v) for v in yd])
    labels_cost = ["Low <$50k", "Med $50–110k", "High ≥$110k"]
    labels_dt = ["Low <45h", "Med 45–95h", "High ≥95h"]

    def plot_cm(y_true, y_pred, labels, title, fname):
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
        fig, ax = plt.subplots(figsize=(5.5, 4.8))
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
        disp.plot(ax=ax, cmap="Blues", colorbar=False)
        ax.set_title(title)
        plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, fname), dpi=150)
        plt.close(fig)

    plot_cm(yc_cls, yc_hat_cls, labels_cost, "Cost tier — LOO (actual vs KNN-predicted tier)", "confusion_cost_tier.png")
    plot_cm(yd_cls, yd_hat_cls, labels_dt, "Downtime tier — LOO (actual vs KNN-predicted tier)", "confusion_downtime_tier.png")

    tier_accuracy_cost = float(np.mean(yc_cls == yc_hat_cls))
    tier_accuracy_dt = float(np.mean(yd_cls == yd_hat_cls))

    # Benchmark bar chart (separate panels — cost $ and downtime h have different scales)
    fig, (ax_c, ax_d) = plt.subplots(1, 2, figsize=(9.5, 4.5))
    cats_c = ["KNN\nLOO", "Mean\nbl.", "Median\nbl."]
    vals_c = [
        cost_mae,
        baselines["cost_mae_mean_baseline"],
        baselines["cost_mae_median_baseline"],
    ]
    cols_c = ["#2c7fb8", "#bdc9e1", "#bdc9e1"]
    ax_c.bar(cats_c, vals_c, color=cols_c, edgecolor="k")
    ax_c.set_title("Cost — MAE ($)")
    ax_c.set_ylabel("MAE (USD)")

    vals_d = [
        dt_mae,
        baselines["downtime_mae_mean_baseline"],
        baselines["downtime_mae_median_baseline"],
    ]
    ax_d.bar(cats_c, vals_d, color=cols_c, edgecolor="k")
    ax_d.set_title("Downtime — MAE (hours)")
    ax_d.set_ylabel("MAE (hours)")
    fig.suptitle("KNN (LOO) vs naive baselines", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "benchmark_mae_bar.png"), dpi=150)
    plt.close(fig)

    # Feature weights
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ypos = np.arange(len(FEATURES))
    ax.barh(ypos, FEATURE_WEIGHTS, color="#3182bd", edgecolor="k")
    ax.set_yticks(ypos)
    ax.set_yticklabels(FEATURES)
    ax.invert_yaxis()
    ax.set_xlabel("Manual feature weight (before StandardScaler)")
    ax.set_title("Feature engineering — relative weights in weighted KNN")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "feature_weights.png"), dpi=150)
    plt.close(fig)

    # Retrieval proxy
    retr = _retrieval_proxy_tfidf()
    fig, ax = plt.subplots(figsize=(5.5, 4))
    ks = ["P@1", "P@3", "P@5"]
    vs = [retr["precision_at_1"], retr["precision_at_3"], retr["precision_at_5"]]
    ax.bar(ks, vs, color="#31a354", edgecolor="k")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Mean precision (10 held-out style queries)")
    ax.set_title("Retrieval proxy — TF-IDF (not production embeddings)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "retrieval_precision_proxy.png"), dpi=150)
    plt.close(fig)

    # k-sweep (in-sample fit on full data — informational only; small N)
    Xw = df[FEATURES].values.astype(float) * FEATURE_WEIGHTS
    scaler = StandardScaler()
    Xs = scaler.fit_transform(Xw)
    ks = list(range(1, 6))
    maes_cost = []
    maes_dt = []
    for k in ks:
        kc = KNeighborsRegressor(n_neighbors=k, weights="distance", metric="euclidean")
        kd = KNeighborsRegressor(n_neighbors=k, weights="distance", metric="euclidean")
        kc.fit(Xs, y_cost)
        kd.fit(Xs, y_dt)
        maes_cost.append(mean_absolute_error(y_cost, kc.predict(Xs)))
        maes_dt.append(mean_absolute_error(y_dt, kd.predict(Xs)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.2))
    ax1.plot(ks, maes_cost, marker="o", color="#2c7fb8")
    ax1.set_xticks(ks)
    ax1.set_xlabel("k (neighbors)")
    ax1.set_ylabel("MAE (USD)")
    ax1.set_title("Cost — in-sample MAE (optimistic)")
    ax2.plot(ks, maes_dt, marker="s", color="#31a354")
    ax2.set_xticks(ks)
    ax2.set_xlabel("k (neighbors)")
    ax2.set_ylabel("MAE (hours)")
    ax2.set_title("Downtime — in-sample MAE (optimistic)")
    fig.suptitle("k sensitivity (informational; prefer LOO for k choice)", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "knn_k_sweep_insample_mae.png"), dpi=150)
    plt.close(fig)

    per_moc = []
    for i, r in enumerate(GROUND_TRUTH):
        per_moc.append({
            "moc_id": r["moc_id"],
            "actual_cost": float(y_cost[i]),
            "pred_cost_loo": float(yc[i]),
            "abs_pct_err_cost": float(abs(yc[i] - y_cost[i]) / max(y_cost[i], 1) * 100),
            "actual_downtime": float(y_dt[i]),
            "pred_downtime_loo": float(yd[i]),
            "abs_pct_err_downtime": float(abs(yd[i] - y_dt[i]) / max(y_dt[i], 1) * 100),
        })

    payload = {
        "dataset": {
            "n_samples": int(len(GROUND_TRUTH)),
            "source": "train_predictor.GROUND_TRUTH (curated 10-row table aligned with MoC narrative features)",
            "train_test_protocol": "Leave-One-Out cross-validation (no fixed 80/20 split due to N=10)",
        },
        "knn": {
            "implementation": "sklearn.neighbors.KNeighborsRegressor",
            "n_neighbors": 2,
            "weights": "distance",
            "metric": "euclidean",
            "preprocessing": "elementwise multiply by FEATURE_WEIGHTS then StandardScaler fit on full matrix before LOO",
        },
        "regression_metrics_loo": {
            "cost_mae_usd": cost_mae,
            "cost_mape_pct": cost_mape,
            "downtime_mae_hours": dt_mae,
            "downtime_mape_pct": dt_mape,
        },
        "tier_accuracy_loo": {
            "cost_tier_accuracy": tier_accuracy_cost,
            "downtime_tier_accuracy": tier_accuracy_dt,
            "cost_tier_definitions": labels_cost,
            "downtime_tier_definitions": labels_dt,
        },
        "baselines_mae": baselines,
        "retrieval_proxy": retr,
        "per_moc_loo": per_moc,
        "figures_relative_to_docs": "model_validation/figures/",
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote metrics to {METRICS_PATH}")
    print(f"Wrote figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
