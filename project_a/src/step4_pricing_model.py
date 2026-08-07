"""
Step 4：动态租金定价模型
- Baseline：按 car_type 中位数的规则定价
- 模型：Ridge 回归（可解释、对齐 JD）
- 对比 MAPE / RMSE / MAE / R²
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from step3_pricing_factors import CONFIG_FEATURES, clean_pricing, load_pricing

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
RANDOM_STATE = 42

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

NUMERIC_FEATURES = ["engine_power", "log_mileage"]
CATEGORICAL_FEATURES = ["car_type", "fuel"]


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def build_baseline(df: pd.DataFrame) -> pd.Series:
    """规则定价：同 car_type 的训练集历史中位数。"""
    medians = df.groupby("car_type")["rental_price_per_day"].median()
    return df["car_type"].map(medians)


def build_model() -> Pipeline:
    config_cols = [c for c in CONFIG_FEATURES]
    numeric_cols = NUMERIC_FEATURES + config_cols

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(
        [
            ("prep", preprocessor),
            ("model", Ridge(alpha=1.0, random_state=RANDOM_STATE)),
        ]
    )


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "MAPE_pct": round(mape(y_true, y_pred), 2),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "R2": round(float(r2_score(y_true, y_pred)), 3),
    }


def extract_feature_names(pipeline: Pipeline) -> list[str]:
    prep: ColumnTransformer = pipeline.named_steps["prep"]
    num_names = NUMERIC_FEATURES + [c for c in CONFIG_FEATURES]
    cat_encoder: OneHotEncoder = prep.named_transformers_["cat"]
    cat_names = cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES).tolist()
    return num_names + cat_names


def feature_importance(pipeline: Pipeline) -> pd.DataFrame:
    """Ridge 标准化系数绝对值，作因子重要性 proxy。"""
    names = extract_feature_names(pipeline)
    coefs = pipeline.named_steps["model"].coef_
    imp = pd.DataFrame({"feature": names, "coef": coefs, "abs_coef": np.abs(coefs)})
    return imp.sort_values("abs_coef", ascending=False).reset_index(drop=True)


def plot_comparison(metrics: pd.DataFrame, test: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    m = metrics.set_index("model")
    axes[0].bar(m.index, m["MAPE_pct"], color=["#95a5a6", "#2980b9"])
    axes[0].set_title("MAPE Comparison (lower is better)")
    axes[0].set_ylabel("MAPE %")

    axes[1].scatter(test["y_true"], test["y_pred_baseline"], alpha=0.2, s=8, label="Baseline", c="#95a5a6")
    axes[1].scatter(test["y_true"], test["y_pred_model"], alpha=0.2, s=8, label="Ridge", c="#2980b9")
    lim = [test["y_true"].min(), test["y_true"].max()]
    axes[1].plot(lim, lim, "k--", linewidth=0.8)
    axes[1].set_xlabel("Actual rent (USD/day)")
    axes[1].set_ylabel("Predicted rent (USD/day)")
    axes[1].set_title("Actual vs Predicted (Test Set)")
    axes[1].legend()

    plt.tight_layout()
    out = OUTPUT_DIR / "step4_model_comparison.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"图表: {out}")


def print_insights(metrics: pd.DataFrame, imp: pd.DataFrame) -> None:
    base = metrics[metrics["model"] == "Baseline"].iloc[0]
    model = metrics[metrics["model"] == "Ridge"].iloc[0]
    mape_drop = base["MAPE_pct"] - model["MAPE_pct"]
    mape_drop_pct = mape_drop / base["MAPE_pct"] * 100

    print("\n=== Step 4 定价模型摘要 ===")
    print(f"Baseline  MAPE={base['MAPE_pct']}%  RMSE={base['RMSE']}  R2={base['R2']}")
    print(f"Ridge     MAPE={model['MAPE_pct']}%  RMSE={model['RMSE']}  R2={model['R2']}")
    print(f"MAPE 较 Baseline 降低: {mape_drop:.2f} pct-pts ({mape_drop_pct:.1f}%)")

    print("\n【Top5 因子（|系数|）】")
    for _, r in imp.head(5).iterrows():
        sign = "+" if r["coef"] >= 0 else "-"
        print(f"  {r['feature']}: {sign}{abs(r['coef']):.3f}")

    print("\n【业务建议】")
    print("  1. 高功率/高配置车型可适度溢价")
    print("  2. 高里程车应下调日租金")
    print("  3. coupe/suv 等 car_type 溢价需在规则价基础上动态调整")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = clean_pricing(load_pricing())
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES + [c for c in CONFIG_FEATURES if c in df.columns]
    X = df[feature_cols]
    y = df["rental_price_per_day"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )

    # Baseline：仅在训练集上算 car_type 中位数，避免数据泄露
    train_df = X_train.copy()
    train_df["rental_price_per_day"] = y_train
    baseline_medians = train_df.groupby("car_type")["rental_price_per_day"].median()
    y_pred_base = X_test["car_type"].map(baseline_medians).fillna(np.median(y_train)).values

    pipeline = build_model()
    pipeline.fit(X_train, y_train)
    y_pred_model = pipeline.predict(X_test)

    metrics = pd.DataFrame(
        [
            {"model": "Baseline", **evaluate(y_test, y_pred_base)},
            {"model": "Ridge", **evaluate(y_test, y_pred_model)},
        ]
    )
    imp = feature_importance(pipeline)

    test_out = X_test.copy()
    test_out["y_true"] = y_test
    test_out["y_pred_baseline"] = y_pred_base
    test_out["y_pred_model"] = y_pred_model
    test_out["error_baseline"] = test_out["y_true"] - test_out["y_pred_baseline"]
    test_out["error_model"] = test_out["y_true"] - test_out["y_pred_model"]

    metrics.to_csv(OUTPUT_DIR / "step4_model_metrics.csv", index=False)
    imp.to_csv(OUTPUT_DIR / "step4_feature_importance.csv", index=False)
    test_out.to_csv(OUTPUT_DIR / "step4_test_predictions.csv", index=False)
    with open(OUTPUT_DIR / "step4_model_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics.set_index("model").to_dict(), f, indent=2)

    plot_comparison(metrics, test_out)
    print_insights(metrics, imp)
    print(f"\n输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
