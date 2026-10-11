"""
train_predictor.py
Builds cost + downtime prediction models from the exact 10 MoC ground-truth records.

Strategy: Weighted KNN (k=2) with carefully tuned feature weights that prioritise
change_type and asset_category — the two strongest predictors. The scaler and weights
are saved so cost_predictor.py can apply them consistently.

Run: python train_predictor.py
"""
import os, joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sklearn.model_selection import LeaveOneOut, cross_val_predict

from core.config import MODEL_DIR, COST_MODEL_PATH, DOWN_MODEL_PATH, SCALER_PATH
from modules.cost_predictor import CHANGE_TYPE_MAP, ASSET_CATEGORY_MAP, RISK_LEVEL_MAP

# ── Ground truth: exact 10 MoC records ────────────────────────────────────
GROUND_TRUTH = [
    {"moc_id": "MoC-001", "change_type": "Mechanical",
     "asset_category": "Pump",              "risk_level": "High",
     "shutdown_required": 0, "hazop_required": 0, "pssr_required": 1,
     "n_dependencies": 2, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 118000, "downtime": 58},

    {"moc_id": "MoC-002", "change_type": "Instrumentation",
     "asset_category": "Control Valve",     "risk_level": "Medium",
     "shutdown_required": 1, "hazop_required": 1, "pssr_required": 1,
     "n_dependencies": 1, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 36500, "downtime": 26},

    {"moc_id": "MoC-003", "change_type": "Process Parameter",
     "asset_category": "Reactor",           "risk_level": "Medium",
     "shutdown_required": 0, "hazop_required": 1, "pssr_required": 1,
     "n_dependencies": 4, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 7500, "downtime": 15},

    {"moc_id": "MoC-004", "change_type": "Mechanical Maintenance",
     "asset_category": "Cyclone Separator", "risk_level": "High",
     "shutdown_required": 1, "hazop_required": 0, "pssr_required": 1,
     "n_dependencies": 2, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 102000, "downtime": 88},

    {"moc_id": "MoC-005", "change_type": "Instrumentation",
     "asset_category": "Control Valve",     "risk_level": "High",
     "shutdown_required": 1, "hazop_required": 1, "pssr_required": 1,
     "n_dependencies": 3, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 67500, "downtime": 52},

    {"moc_id": "MoC-006", "change_type": "Process & Instrumentation",
     "asset_category": "Control Valve",     "risk_level": "High",
     "shutdown_required": 1, "hazop_required": 1, "pssr_required": 1,
     "n_dependencies": 2, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 92000, "downtime": 82},

    {"moc_id": "MoC-007", "change_type": "Mechanical Efficiency Improvement",
     "asset_category": "Flue gas expander", "risk_level": "Medium",
     "shutdown_required": 1, "hazop_required": 0, "pssr_required": 1,
     "n_dependencies": 2, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 78000, "downtime": 310},

    {"moc_id": "MoC-008", "change_type": "Mechanical",
     "asset_category": "Pump",              "risk_level": "High",
     "shutdown_required": 1, "hazop_required": 1, "pssr_required": 1,
     "n_dependencies": 2, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 135000, "downtime": 108},

    {"moc_id": "MoC-009", "change_type": "Procedural",
     "asset_category": "Procedure",         "risk_level": "High",
     "shutdown_required": 0, "hazop_required": 1, "pssr_required": 1,
     "n_dependencies": 0, "n_hazards": 1, "n_mocs": 2, "n_work_orders": 2,
     "cost": 22000, "downtime": 35},

    {"moc_id": "MoC-010", "change_type": "Mechanical Integrity Improvement",
     "asset_category": "Piping",            "risk_level": "High",
     "shutdown_required": 1, "hazop_required": 1, "pssr_required": 1,
     "n_dependencies": 3, "n_hazards": 1, "n_mocs": 3, "n_work_orders": 3,
     "cost": 165000, "downtime": 146},
]

FEATURES = [
    "change_type_enc", "asset_category_enc", "risk_level_enc",
    "shutdown_required", "hazop_required", "pssr_required",
    "n_dependencies", "n_hazards", "n_mocs", "n_work_orders",
]

# Weights: change_type and asset_category dominate cost/downtime
# risk_level and shutdown_required are secondary drivers
# graph features (n_dependencies etc.) are tertiary
FEATURE_WEIGHTS = np.array([
    4.0,   # change_type_enc      — strongest predictor
    3.0,   # asset_category_enc   — second strongest
    2.0,   # risk_level_enc       — significant
    2.0,   # shutdown_required    — significant (adds cost + downtime)
    1.0,   # hazop_required       — moderate
    0.5,   # pssr_required        — minor
    0.8,   # n_dependencies       — minor
    0.5,   # n_hazards            — minor
    0.3,   # n_mocs               — minor
    1.0,   # n_work_orders        — moderate (more WOs = more downtime)
])


def encode_row(r: dict) -> dict:
    return {
        "change_type_enc":    CHANGE_TYPE_MAP.get(r["change_type"], 8),
        "asset_category_enc": ASSET_CATEGORY_MAP.get(r["asset_category"], 9),
        "risk_level_enc":     RISK_LEVEL_MAP.get(r["risk_level"], 1),
        "shutdown_required":  int(r.get("shutdown_required", 0)),
        "hazop_required":     int(r.get("hazop_required", 0)),
        "pssr_required":      int(r.get("pssr_required", 1)),
        "n_dependencies":     int(r.get("n_dependencies", 0)),
        "n_hazards":          int(r.get("n_hazards", 0)),
        "n_mocs":             int(r.get("n_mocs", 0)),
        "n_work_orders":      int(r.get("n_work_orders", 1)),
        "cost":               float(r["cost"]),
        "downtime":           float(r["downtime"]),
    }


def _load_training_rows() -> list:
    """Prefer GOLD.mart_ml_moc_features; fall back to inline GROUND_TRUTH."""
    if os.getenv("MOC_ML_SOURCE", "auto").lower() == "ground_truth":
        return list(GROUND_TRUTH)
    try:
        from core.snowflake_client import fetch_all

        database = os.getenv("SNOWFLAKE_DATABASE", "MOC_DEV")
        gold = os.getenv("SNOWFLAKE_GOLD_SCHEMA", "GOLD")
        rows = fetch_all(
            f'select * from "{database}"."{gold}".mart_ml_moc_features'
        )
        if not rows:
            raise RuntimeError("mart_ml_moc_features returned 0 rows")
        # Normalize Snowflake uppercase keys
        out = []
        for r in rows:
            lower = {str(k).lower(): v for k, v in r.items()}
            out.append(
                {
                    "moc_id": lower["moc_id"],
                    "change_type": lower["change_type"],
                    "asset_category": lower["asset_category"],
                    "risk_level": lower["risk_level"],
                    "shutdown_required": int(lower.get("shutdown_required") or 0),
                    "hazop_required": int(lower.get("hazop_required") or 0),
                    "pssr_required": int(lower.get("pssr_required") or 0),
                    "n_dependencies": int(lower.get("n_dependencies") or 0),
                    "n_hazards": int(lower.get("n_hazards") or 0),
                    "n_mocs": int(lower.get("n_mocs") or 0),
                    "n_work_orders": int(lower.get("n_work_orders") or 0),
                    "cost": float(lower["cost"]),
                    "downtime": float(lower["downtime"]),
                }
            )
        print(f"Loaded {len(out)} rows from Snowflake GOLD.mart_ml_moc_features")
        return out
    except Exception as exc:
        print(f"Snowflake ML mart unavailable ({exc}); using inline GROUND_TRUTH")
        return list(GROUND_TRUTH)


def build_df(rows=None):
    rows = rows if rows is not None else _load_training_rows()
    return pd.DataFrame([encode_row(r) for r in rows]), rows


def train():
    df, rows = build_df()
    n = len(df)
    print(f"Training on {n} ground-truth MoC records")
    print(f"Cost range:     ${df['cost'].min():,.0f} – ${df['cost'].max():,.0f}")
    print(f"Downtime range: {df['downtime'].min():.0f}h – {df['downtime'].max():.0f}h")

    X_raw = df[FEATURES].values.astype(float)
    y_cost     = df["cost"].values
    y_downtime = df["downtime"].values

    # Apply feature weights then scale
    X_weighted = X_raw * FEATURE_WEIGHTS
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_weighted)

    # k=2, distance-weighted: best LOO accuracy on 10 samples
    cost_model = KNeighborsRegressor(n_neighbors=2, weights="distance", metric="euclidean")
    downtime_model = KNeighborsRegressor(n_neighbors=2, weights="distance", metric="euclidean")

    cost_model.fit(X_scaled, y_cost)
    downtime_model.fit(X_scaled, y_downtime)

    # LOO CV
    loo = LeaveOneOut()
    yc_pred = cross_val_predict(cost_model, X_scaled, y_cost, cv=loo)
    yd_pred = cross_val_predict(downtime_model, X_scaled, y_downtime, cv=loo)

    cost_mae  = mean_absolute_error(y_cost, yc_pred)
    cost_mape = mean_absolute_percentage_error(y_cost, yc_pred) * 100
    dt_mae    = mean_absolute_error(y_downtime, yd_pred)
    dt_mape   = mean_absolute_percentage_error(y_downtime + 1, yd_pred + 1) * 100

    print(f"\nLeave-One-Out CV (most honest evaluation on 10 samples):")
    print(f"  Cost     MAE: ${cost_mae:,.0f}  MAPE: {cost_mape:.1f}%")
    print(f"  Downtime MAE: {dt_mae:.1f}h    MAPE: {dt_mape:.1f}%")

    print(f"\nPer-MoC validation (LOO — each row predicted without itself):")
    print(f"  {'MoC':<10} {'Actual $':>10} {'Pred $':>10} {'Err%':>6}  "
          f"{'Actual h':>9} {'Pred h':>7} {'Err%':>6}")
    for i, r in enumerate(rows):
        ac = r["cost"];  pc = yc_pred[i]
        ad = r["downtime"]; pd_ = yd_pred[i]
        ce = abs(pc - ac) / ac * 100
        de = abs(pd_ - ad) / max(ad, 1) * 100
        flag_c = " ✓" if ce < 30 else (" ~" if ce < 60 else " ✗")
        flag_d = " ✓" if de < 30 else (" ~" if de < 60 else " ✗")
        print(f"  {r['moc_id']:<10} ${ac:>9,.0f} ${pc:>9,.0f} {ce:>5.1f}%{flag_c}  "
              f"{ad:>8.0f}h {pd_:>6.1f}h {de:>5.1f}%{flag_d}")

    # Save models + weights
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(cost_model,     COST_MODEL_PATH)
    joblib.dump(downtime_model, DOWN_MODEL_PATH)
    joblib.dump(scaler,         SCALER_PATH)
    joblib.dump(FEATURE_WEIGHTS, os.path.join(MODEL_DIR, "feature_weights.pkl"))

    print(f"\nModels saved to {MODEL_DIR}/")
    print("Retrain whenever new MoC data is added to Neo4j.")


if __name__ == "__main__":
    train()
