"""
项目 B Step 2：RFM 打分 + K-Means 聚类，输出资产画像标签

两套分层方法并行，便于对比与业务解释：
  1) RFM 规则打分（R/F/M 各 1~4 分）—— 业务方好理解
  2) K-Means 聚类（标准化后）—— 数据驱动，用于验证规则分层是否合理
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from config import N_CLUSTERS, OUTPUT_DIR, RANDOM_STATE, RFM_BINS

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

FEATURE_FILE = OUTPUT_DIR / "b_step1_asset_rfm_features.csv"
CLUSTER_FEATURES = ["recency_months", "frequency", "log_monetary"]


def score_rank(series: pd.Series, bins: int, ascending: bool) -> pd.Series:
    """按分位排名打分。ascending=True 表示值越大分越高。"""
    ranked = series.rank(method="first", ascending=ascending)
    return pd.qcut(ranked, q=bins, labels=range(1, bins + 1)).astype(int)


def add_rfm_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Recency 越小越好 -> ascending=False 使小值拿高分
    out["R_score"] = score_rank(out["recency_months"], RFM_BINS, ascending=False)
    out["F_score"] = score_rank(out["frequency"], RFM_BINS, ascending=True)
    out["M_score"] = score_rank(out["monetary"], RFM_BINS, ascending=True)
    out["RFM_total"] = out["R_score"] + out["F_score"] + out["M_score"]
    return out


def label_asset_tier(row: pd.Series) -> str:
    """资产画像标签：结合活跃度(R/F)与维保投入(M)。"""
    r, f, m = row["R_score"], row["F_score"], row["M_score"]
    active = (r + f) / 2
    if active >= 3 and m >= 3:
        return "高投入活跃资产"
    if active >= 3 and m < 3:
        return "低成本健康资产"
    if active < 3 and m >= 3:
        return "高成本沉默资产"
    return "低活跃待评估资产"


def run_kmeans(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    work = df.copy()
    work["log_monetary"] = np.log1p(work["monetary"])
    X = StandardScaler().fit_transform(work[CLUSTER_FEATURES])

    km = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    work["cluster"] = km.fit_predict(X)

    sample = min(5000, len(work))
    idx = np.random.RandomState(RANDOM_STATE).choice(len(work), sample, replace=False)
    sil = float(silhouette_score(X[idx], work["cluster"].values[idx]))

    return work, {"silhouette": round(sil, 3), "inertia": round(float(km.inertia_), 1)}


def cluster_profile(df: pd.DataFrame) -> pd.DataFrame:
    prof = (
        df.groupby("cluster")
        .agg(
            vehicle_cnt=("vehicle_id", "count"),
            avg_recency=("recency_months", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            churn_rate=("churned", "mean"),
        )
        .round(3)
        .reset_index()
    )
    return prof.sort_values("churn_rate", ascending=False)


def tier_profile(df: pd.DataFrame) -> pd.DataFrame:
    prof = (
        df.groupby("asset_tier")
        .agg(
            vehicle_cnt=("vehicle_id", "count"),
            avg_recency=("recency_months", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            churn_rate=("churned", "mean"),
        )
        .round(3)
        .reset_index()
    )
    return prof.sort_values("churn_rate", ascending=False)


def plot_segments(tier: pd.DataFrame, cluster: pd.DataFrame, df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].barh(tier["asset_tier"], tier["churn_rate"], color="#e67e22")
    axes[0].set_title("Churn Rate by RFM Asset Tier")
    axes[0].set_xlabel("churn rate")
    axes[0].invert_yaxis()

    axes[1].bar(cluster["cluster"].astype(str), cluster["churn_rate"], color="#16a085")
    axes[1].set_title("Churn Rate by K-Means Cluster")
    axes[1].set_xlabel("cluster")
    axes[1].set_ylabel("churn rate")

    sc = axes[2].scatter(
        df["recency_months"],
        df["frequency"],
        c=df["cluster"],
        cmap="viridis",
        alpha=0.35,
        s=8,
    )
    axes[2].set_xlabel("Recency (months)")
    axes[2].set_ylabel("Frequency (active months)")
    axes[2].set_title("Clusters in R-F Space")
    plt.colorbar(sc, ax=axes[2], label="cluster")

    plt.tight_layout()
    out = OUTPUT_DIR / "b_step2_segmentation.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"图表: {out}")


def main() -> None:
    df = pd.read_csv(FEATURE_FILE)

    df = add_rfm_scores(df)
    df["asset_tier"] = df.apply(label_asset_tier, axis=1)
    df, km_metrics = run_kmeans(df)

    tier = tier_profile(df)
    cluster = cluster_profile(df)

    df.to_csv(OUTPUT_DIR / "b_step2_asset_segments.csv", index=False)
    tier.to_csv(OUTPUT_DIR / "b_step2_tier_profile.csv", index=False)
    cluster.to_csv(OUTPUT_DIR / "b_step2_cluster_profile.csv", index=False)

    plot_segments(tier, cluster, df)

    print("=== 项目 B Step 2：资产价值分层 ===")
    print(f"K-Means: k={N_CLUSTERS}, silhouette={km_metrics['silhouette']}")
    print("\n【RFM 规则分层】")
    print(tier.to_string(index=False))
    print("\n【K-Means 聚类画像】")
    print(cluster.to_string(index=False))

    worst = tier.iloc[0]
    best = tier.iloc[-1]
    print(
        f"\n退网风险最高分层: {worst['asset_tier']}  churn={worst['churn_rate']:.1%}  "
        f"({int(worst['vehicle_cnt']):,} 辆)"
    )
    print(f"退网风险最低分层: {best['asset_tier']}  churn={best['churn_rate']:.1%}")
    print(f"\n输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
