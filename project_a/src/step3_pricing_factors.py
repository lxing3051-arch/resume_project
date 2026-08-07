"""
Step 3：定价因子分析
- 清洗 Getaround 定价数据
- 数值/分类因子与 rental_price_per_day 的相关性
- 分组对比 + 业务解读
- 输出 CSV + 图表（供 Step 4 回归建模选型）
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from config import DB_PATH, RAW_DIR

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
PRICING_CSV = RAW_DIR / "get_around_pricing_project.csv"

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 配置类因子（0/1）
CONFIG_FEATURES = [
    "private_parking_available",
    "has_gps",
    "has_air_conditioning",
    "automatic_car",
    "has_getaround_connect",
    "has_speed_regulator",
    "winter_tires",
]


def load_pricing() -> pd.DataFrame:
    """优先读原始 CSV（含配置因子），否则读 SQLite。"""
    if PRICING_CSV.exists():
        df = pd.read_csv(PRICING_CSV)
        df = df.rename(columns={"Unnamed: 0": "listing_id"})
    else:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql("SELECT * FROM getaround_pricing", conn)
    return df


def clean_pricing(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out[out["rental_price_per_day"] > 0]
    out = out[out["mileage"] >= 0]
    out = out[out["engine_power"] > 0]
    out = out[out["rental_price_per_day"] < 500]  # 去掉极端挂牌价
    out["log_mileage"] = np.log1p(out["mileage"])
    out["mileage_bin"] = pd.qcut(out["mileage"], q=4, labels=["Q1_low", "Q2", "Q3", "Q4_high"])
    for col in CONFIG_FEATURES:
        if col in out.columns:
            out[col] = out[col].astype(int)
    if all(c in out.columns for c in CONFIG_FEATURES):
        out["config_score"] = out[CONFIG_FEATURES].sum(axis=1)
    return out


def numeric_correlation(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["rental_price_per_day", "mileage", "log_mileage", "engine_power"]
    if "config_score" in df.columns:
        cols.append("config_score")
    corr = df[cols].corr(method="spearman").round(3)
    return corr


def categorical_summary(df: pd.DataFrame, col: str) -> pd.DataFrame:
    agg = (
        df.groupby(col)["rental_price_per_day"]
        .agg(["count", "mean", "median", "std"])
        .round(2)
        .reset_index()
        .sort_values("median", ascending=False)
    )
    agg.columns = [col, "count", "avg_rent", "median_rent", "std_rent"]
    return agg


def config_factor_lift(df: pd.DataFrame) -> pd.DataFrame:
    """各配置项：有 vs 无 的租金中位数差异。"""
    rows = []
    base_median = df["rental_price_per_day"].median()
    for col in CONFIG_FEATURES:
        if col not in df.columns:
            continue
        for val, label in [(1, "yes"), (0, "no")]:
            sub = df[df[col] == val]
            if sub.empty:
                continue
            med = sub["rental_price_per_day"].median()
            rows.append(
                {
                    "feature": col,
                    "value": label,
                    "count": len(sub),
                    "median_rent": round(med, 2),
                    "lift_vs_overall": round(med - base_median, 2),
                }
            )
    return pd.DataFrame(rows).sort_values("lift_vs_overall", ascending=False)


def plot_correlation_heatmap(corr: pd.DataFrame) -> None:
    plt.figure(figsize=(7, 5))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1)
    plt.title("Spearman Correlation: Price vs Numeric Factors")
    plt.tight_layout()
    out = OUTPUT_DIR / "step3_correlation_heatmap.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"图表: {out}")


def plot_categorical_factors(df: pd.DataFrame, car_type: pd.DataFrame, mileage_bin: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].barh(car_type["car_type"], car_type["median_rent"], color="#3498db")
    axes[0].set_title("Median Daily Rent by car_type")
    axes[0].set_xlabel("USD/day")
    axes[0].invert_yaxis()

    axes[1].bar(mileage_bin["mileage_bin"], mileage_bin["median_rent"], color="#9b59b6")
    axes[1].set_title("Median Daily Rent by Mileage Quartile")
    axes[1].set_xlabel("Mileage bin")
    axes[1].set_ylabel("USD/day")

    plt.tight_layout()
    out = OUTPUT_DIR / "step3_categorical_factors.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"图表: {out}")


def print_insights(
    df: pd.DataFrame, corr: pd.DataFrame, car_type: pd.DataFrame, config_lift: pd.DataFrame
) -> None:
    print("\n=== Step 3 定价因子分析摘要 ===")
    print(f"样本量: {len(df)} 条")

    price_corr = corr["rental_price_per_day"].drop("rental_price_per_day")
    top = price_corr.abs().sort_values(ascending=False).head(3)
    print("\n【数值因子】与租金 Spearman 相关（绝对值 Top3）:")
    for feat, val in top.items():
        direction = "正相关" if price_corr[feat] > 0 else "负相关"
        print(f"  - {feat}: {price_corr[feat]:+.3f} ({direction})")

    best_type = car_type.iloc[0]
    worst_type = car_type.iloc[-1]
    print(f"\n【车型】租金最高: {best_type['car_type']}  median={best_type['median_rent']}")
    print(f"【车型】租金最低: {worst_type['car_type']}  median={worst_type['median_rent']}")

    if not config_lift.empty:
        best_cfg = config_lift.iloc[0]
        print(
            f"\n【配置】溢价最高: {best_cfg['feature']}={best_cfg['value']}  "
            f"lift={best_cfg['lift_vs_overall']:+.0f} USD/day vs 总体中位数"
        )

    print("\n【业务结论（Step 4 建模输入）】")
    print("  1. car_type / engine_power 是强因子 → 分类+数值特征入模")
    print("  2. mileage 与租金负相关 → 车越老租金越低")
    print("  3. 配置项（GPS/自动挡等）有溢价 → 可作为 dummy 特征")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_pricing()
    df = clean_pricing(df)
    print(f"清洗后样本: {len(df)} 条")

    corr = numeric_correlation(df)
    car_type_sum = categorical_summary(df, "car_type")
    fuel_sum = categorical_summary(df, "fuel")
    mileage_sum = categorical_summary(df, "mileage_bin")
    config_lift = config_factor_lift(df)

    corr.to_csv(OUTPUT_DIR / "step3_correlation_matrix.csv")
    car_type_sum.to_csv(OUTPUT_DIR / "step3_factor_car_type.csv", index=False)
    fuel_sum.to_csv(OUTPUT_DIR / "step3_factor_fuel.csv", index=False)
    mileage_sum.to_csv(OUTPUT_DIR / "step3_factor_mileage_bin.csv", index=False)
    if not config_lift.empty:
        config_lift.to_csv(OUTPUT_DIR / "step3_factor_config_lift.csv", index=False)

    plot_correlation_heatmap(corr)
    plot_categorical_factors(df, car_type_sum, mileage_sum)
    print_insights(df, corr, car_type_sum, config_lift)
    print(f"\n输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
