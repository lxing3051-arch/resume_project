"""
项目 B Step 3：退网（流失）预警模型

- 特征：RFM + 车辆属性（车龄、Segment、燃料、城市车队规模）
- 模型：Logistic 回归（可解释 baseline） vs 随机森林 / 梯度提升
- 评估：AUC / 精准率 / 召回率 / F1
- 业务落地：十分位提升表（top N% 名单能抓到多少退网车）
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import OBSERVE_END, OUTPUT_DIR, RANDOM_STATE

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

SEGMENT_FILE = OUTPUT_DIR / "b_step2_asset_segments.csv"
TEST_SIZE = 0.2

# 特征集 1：基础 RFM + 车辆属性
BASE_NUMERIC = [
    "recency_months",
    "frequency",
    "log_monetary",
    "avg_maintenance",
    "max_maintenance",
    "vehicle_age",
    "purchase_price",
    "city_fleet_size",
]
# 特征集 2：追加时序趋势特征（特征工程增量）
TREND_NUMERIC = [
    "tenure_months",
    "active_density",
    "std_maintenance",
    "active_months_last3m",
    "active_months_last6m",
    "maint_last3m",
    "maint_last6m",
    "maint_trend_ratio",
    "active_trend_ratio",
]
NUMERIC_FEATURES = BASE_NUMERIC + TREND_NUMERIC
CATEGORICAL_FEATURES = ["segment", "fuel_type"]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    observe_year = int(OBSERVE_END.split("-")[0])
    out["vehicle_age"] = observe_year - out["model_year"]
    out["city_fleet_size"] = out.groupby("city_id")["vehicle_id"].transform("count")
    out["segment"] = out["segment"].fillna("Unknown")
    out["fuel_type"] = out["fuel_type"].fillna("Unknown")
    out = out.dropna(subset=NUMERIC_FEATURES + ["churned"])
    return out


def build_pipeline(model, numeric_features: list[str]) -> Pipeline:
    prep = ColumnTransformer(
        [
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline([("prep", prep), ("model", model)])


def make_candidates() -> dict:
    return {
        "Logistic": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=20, random_state=RANDOM_STATE, n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
    }


def evaluate(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "AUC": round(float(roc_auc_score(y_true, y_prob)), 3),
        "Accuracy": round(float(accuracy_score(y_true, y_pred)), 3),
        "Precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 3),
        "Recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 3),
        "F1": round(float(f1_score(y_true, y_pred, zero_division=0)), 3),
    }


def decile_lift(y_true: np.ndarray, y_prob: np.ndarray) -> pd.DataFrame:
    """按预测风险降序分十组，看每组实际退网率与累计捕获率。"""
    df = pd.DataFrame({"y": y_true, "p": y_prob}).sort_values("p", ascending=False)
    df["decile"] = pd.qcut(df["p"].rank(method="first", ascending=False), 10, labels=range(1, 11))
    base_rate = df["y"].mean()
    total_pos = df["y"].sum()

    agg = (
        df.groupby("decile", observed=True)
        .agg(vehicles=("y", "size"), churned=("y", "sum"), avg_prob=("p", "mean"))
        .reset_index()
    )
    agg["churn_rate"] = (agg["churned"] / agg["vehicles"]).round(3)
    agg["lift"] = (agg["churn_rate"] / base_rate).round(2)
    agg["cum_capture_rate"] = (agg["churned"].cumsum() / total_pos).round(3)
    agg["avg_prob"] = agg["avg_prob"].round(3)
    return agg


def logistic_coefficients(pipe: Pipeline, numeric_features: list[str]) -> pd.DataFrame:
    cat_names = (
        pipe.named_steps["prep"]
        .named_transformers_["cat"]
        .get_feature_names_out(CATEGORICAL_FEATURES)
        .tolist()
    )
    names = numeric_features + cat_names
    coefs = pipe.named_steps["model"].coef_[0]
    out = pd.DataFrame({"feature": names, "coef": coefs.round(4), "abs_coef": np.abs(coefs)})
    return out.sort_values("abs_coef", ascending=False).reset_index(drop=True)


def perm_importance(pipe: Pipeline, X_test: pd.DataFrame, y_test: np.ndarray) -> pd.DataFrame:
    res = permutation_importance(
        pipe, X_test, y_test, n_repeats=5, random_state=RANDOM_STATE, scoring="roc_auc"
    )
    out = pd.DataFrame(
        {
            "feature": X_test.columns,
            "auc_drop": res.importances_mean.round(4),
            "std": res.importances_std.round(4),
        }
    )
    return out.sort_values("auc_drop", ascending=False).reset_index(drop=True)


def plot_results(
    metrics: pd.DataFrame, roc_data: dict, lift: pd.DataFrame, imp: pd.DataFrame
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    for name, (fpr, tpr, auc) in roc_data.items():
        axes[0].plot(fpr, tpr, linewidth=1.2, label=f"{name} (AUC={auc:.3f})")
    axes[0].plot([0, 1], [0, 1], "k--", linewidth=0.8)
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].set_title("ROC Curve - Churn Models")
    axes[0].legend(fontsize=8)

    axes[1].bar(lift["decile"].astype(str), lift["churn_rate"], color="#c0392b")
    axes[1].axhline(lift["churned"].sum() / lift["vehicles"].sum(), color="gray", linestyle="--",
                    label="overall churn rate")
    axes[1].set_xlabel("Risk decile (1 = highest risk)")
    axes[1].set_ylabel("Actual churn rate")
    axes[1].set_title("Decile Lift - Best Model")
    axes[1].legend(fontsize=8)

    top = imp.head(8).iloc[::-1]
    axes[2].barh(top["feature"], top["auc_drop"], color="#2c3e50")
    axes[2].set_xlabel("AUC drop when shuffled")
    axes[2].set_title("Permutation Importance (Top 8)")

    plt.tight_layout()
    out = OUTPUT_DIR / "b_step3_churn_model.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"图表: {out}")


def main() -> None:
    df = prepare(pd.read_csv(SEGMENT_FILE))
    y = df["churned"].values

    feature_sets = {
        "RFM_only": BASE_NUMERIC,
        "RFM_plus_trend": NUMERIC_FEATURES,
    }

    rows, roc_data, fitted = [], {}, {}
    train_idx, test_idx = train_test_split(
        df.index, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    y_train = df.loc[train_idx, "churned"].values
    y_test = df.loc[test_idx, "churned"].values

    for fs_name, numeric in feature_sets.items():
        cols = numeric + CATEGORICAL_FEATURES
        X_train, X_test = df.loc[train_idx, cols], df.loc[test_idx, cols]
        for model_name, model in make_candidates().items():
            pipe = build_pipeline(model, numeric)
            pipe.fit(X_train, y_train)
            prob = pipe.predict_proba(X_test)[:, 1]
            key = f"{fs_name} | {model_name}"
            rows.append({"feature_set": fs_name, "model": model_name, **evaluate(y_test, prob)})
            fpr, tpr, _ = roc_curve(y_test, prob)
            roc_data[key] = (fpr, tpr, roc_auc_score(y_test, prob))
            fitted[key] = (pipe, prob, numeric, X_test)

    metrics = pd.DataFrame(rows).sort_values("AUC", ascending=False).reset_index(drop=True)
    best_row = metrics.iloc[0]
    best_key = f"{best_row['feature_set']} | {best_row['model']}"
    best_pipe, best_prob, best_numeric, best_X_test = fitted[best_key]

    lift = decile_lift(y_test, best_prob)
    imp = perm_importance(best_pipe, best_X_test, y_test)
    logit_key = "RFM_plus_trend | Logistic"
    coefs = logistic_coefficients(fitted[logit_key][0], fitted[logit_key][2])

    metrics.to_csv(OUTPUT_DIR / "b_step3_model_metrics.csv", index=False)
    lift.to_csv(OUTPUT_DIR / "b_step3_decile_lift.csv", index=False)
    imp.to_csv(OUTPUT_DIR / "b_step3_permutation_importance.csv", index=False)
    coefs.to_csv(OUTPUT_DIR / "b_step3_logistic_coefficients.csv", index=False)

    scored = best_X_test.copy()
    scored["vehicle_id"] = df.loc[test_idx, "vehicle_id"].values
    scored["asset_tier"] = df.loc[test_idx, "asset_tier"].values
    scored["churned_actual"] = y_test
    scored["churn_probability"] = best_prob.round(4)
    scored.sort_values("churn_probability", ascending=False).to_csv(
        OUTPUT_DIR / "b_step3_risk_scored_vehicles.csv", index=False
    )

    plot_results(metrics, roc_data, lift, imp)

    print("=== 项目 B Step 3：退网预警模型 ===")
    print(f"训练/测试: {len(train_idx):,} / {len(test_idx):,}  |  测试集退网率 {y_test.mean():.1%}")
    print("\n【特征集 × 模型 对比】")
    print(metrics.to_string(index=False))
    print(f"\n最优组合: {best_key}")

    base_best = metrics[metrics["feature_set"] == "RFM_only"]["AUC"].max()
    trend_best = metrics[metrics["feature_set"] == "RFM_plus_trend"]["AUC"].max()
    print(f"特征工程增量: AUC {base_best} -> {trend_best} (+{round(trend_best - base_best, 3)})")

    print("\n【十分位提升表（风险从高到低）】")
    print(lift.to_string(index=False))
    top3 = lift.head(3)["cum_capture_rate"].iloc[-1]
    print(f"\n风险最高 30% 的车辆覆盖了 {top3:.1%} 的实际退网车")

    print("\n【特征重要性 Top5（打乱后 AUC 下降）】")
    print(imp.head(5).to_string(index=False))

    print("\n【Logistic 系数 Top5（方向可解释）】")
    print(coefs.head(5).to_string(index=False))
    print(f"\n输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
