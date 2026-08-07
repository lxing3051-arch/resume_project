"""
Step 2：TCO 与盈利复盘
- 计算单车/分 Segment/分城市 月 TCO
- 维保 outlier 封顶（P99）
- 用 Getaround Segment 租金基准估算月利润（65% 利用率假设）
- 输出 CSV + 图表
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from config import DB_PATH

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
UTILIZATION_RATE = 0.65  # Getaround ended 租赁占比 ~85%，保守取 65% 作为 fleet 利用率

# 图表中文（Windows 无 CJK 字体时回退英文标签）
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def load_tco(conn: sqlite3.Connection) -> pd.DataFrame:
    sql = """
    SELECT
        c.vehicle_id,
        v.segment,
        v.city_id,
        v.brand,
        v.model,
        c.month,
        c.depreciation,
        c.insurance,
        c.maintenance,
        c.parking,
        (c.depreciation + c.insurance + c.maintenance + c.parking) AS total_cost
    FROM cost_monthly c
    JOIN vehicle_asset v ON c.vehicle_id = v.vehicle_id
    """
    return pd.read_sql(sql, conn)


def cap_maintenance_outliers(df: pd.DataFrame, percentile: float = 0.99) -> pd.DataFrame:
    """维保 P99 封顶：保留真实数据主体，削弱极端发票对均值的扭曲。"""
    cap = df["maintenance"].quantile(percentile)
    out = df.copy()
    out["maintenance_capped"] = out["maintenance"].clip(upper=cap)
    out["total_cost_capped"] = (
        out["depreciation"] + out["insurance"] + out["maintenance_capped"] + out["parking"]
    )
    out["maintenance_cap"] = cap
    return out


def load_rent_benchmark(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM segment_rent_benchmark", conn)


def add_profit_estimate(tco: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    b = benchmark.set_index("segment")
    out = tco.copy()
    out["est_monthly_revenue"] = out["segment"].map(
        lambda s: b.loc[s, "median_monthly_rent"] * UTILIZATION_RATE if s in b.index else None
    )
    out["est_monthly_profit"] = out["est_monthly_revenue"] - out["total_cost_capped"]
    return out


def summarize_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    valid = df.dropna(subset=["est_monthly_revenue"])
    agg = (
        valid.groupby("segment")
        .agg(
            vehicle_cnt=("vehicle_id", "nunique"),
            record_cnt=("vehicle_id", "count"),
            avg_depreciation=("depreciation", "mean"),
            avg_maintenance=("maintenance_capped", "mean"),
            avg_total_cost=("total_cost_capped", "mean"),
            avg_est_revenue=("est_monthly_revenue", "mean"),
            avg_est_profit=("est_monthly_profit", "mean"),
        )
        .round(2)
        .reset_index()
    )
    agg["profit_margin"] = (agg["avg_est_profit"] / agg["avg_est_revenue"]).round(3)
    return agg.sort_values("avg_est_profit")


def summarize_by_city(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby("city_id")
        .agg(
            vehicle_cnt=("vehicle_id", "nunique"),
            avg_maintenance=("maintenance_capped", "mean"),
            avg_total_cost=("total_cost_capped", "mean"),
            avg_est_profit=("est_monthly_profit", "mean"),
        )
        .round(2)
        .reset_index()
    )
    return agg.sort_values("avg_est_profit")


def print_insights(seg: pd.DataFrame, city: pd.DataFrame, cap: float) -> None:
    print("\n=== Step 2 盈利复盘摘要 ===")
    print(f"维保 P99 封顶线: {cap:,.2f} USD")
    print(f"利用率假设: {UTILIZATION_RATE:.0%}（租金基准来自 Getaround Segment 中位数 × 30 天）")

    worst = seg.iloc[0]
    best = seg.iloc[-1]
    print(f"\n【Segment】成本最高: {worst['segment']}  avg TCO={worst['avg_total_cost']:,.0f}  est profit={worst['avg_est_profit']:,.0f}")
    print(f"【Segment】成本最低: {best['segment']}  avg TCO={best['avg_total_cost']:,.0f}  est profit={best['avg_est_profit']:,.0f}")

    city_worst = city.iloc[0]
    city_best = city.iloc[-1]
    print(f"\n【CityID】盈利最差: {city_worst['city_id']}  est profit={city_worst['avg_est_profit']:,.0f}")
    print(f"【CityID】盈利最好: {city_best['city_id']}  est profit={city_best['avg_est_profit']:,.0f}")

    loss_seg = seg[seg["avg_est_profit"] < 0]
    if not loss_seg.empty:
        print(f"\n[警告] 估算亏损 Segment: {', '.join(loss_seg['segment'].tolist())}")
    else:
        print("\n[OK] 所有 Segment 在当前假设下均为正利润")


def plot_segment_charts(seg: pd.DataFrame, cost_breakdown: pd.DataFrame) -> None:
    """生成分 Segment 成本结构与盈利对比图。"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左：估算月利润
    colors = ["#e74c3c" if p < 0 else "#27ae60" for p in seg["avg_est_profit"]]
    axes[0].bar(seg["segment"], seg["avg_est_profit"], color=colors)
    axes[0].axhline(0, color="gray", linewidth=0.8)
    axes[0].set_title("Est. Monthly Profit by Segment")
    axes[0].set_xlabel("Segment")
    axes[0].set_ylabel("USD")

    # 右：成本结构（折旧/维保/保险+停车）
    x = cost_breakdown["segment"]
    axes[1].bar(x, cost_breakdown["avg_depreciation"], label="Depreciation")
    axes[1].bar(
        x,
        cost_breakdown["avg_maintenance"],
        bottom=cost_breakdown["avg_depreciation"],
        label="Maintenance",
    )
    axes[1].bar(
        x,
        cost_breakdown["avg_other"],
        bottom=cost_breakdown["avg_depreciation"] + cost_breakdown["avg_maintenance"],
        label="Insurance+Parking",
    )
    axes[1].set_title("Monthly Cost Structure by Segment")
    axes[1].set_xlabel("Segment")
    axes[1].set_ylabel("USD")
    axes[1].legend(fontsize=8)

    plt.tight_layout()
    out = OUTPUT_DIR / "step2_segment_charts.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"图表已保存: {out}")


def cost_breakdown_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    valid = df.dropna(subset=["est_monthly_revenue"])
    bd = (
        valid.groupby("segment")
        .agg(
            avg_depreciation=("depreciation", "mean"),
            avg_maintenance=("maintenance_capped", "mean"),
            avg_insurance=("insurance", "mean"),
            avg_parking=("parking", "mean"),
        )
        .round(2)
        .reset_index()
    )
    bd["avg_other"] = bd["avg_insurance"] + bd["avg_parking"]
    return bd


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        tco = load_tco(conn)
        benchmark = load_rent_benchmark(conn)

    tco = cap_maintenance_outliers(tco)
    tco = add_profit_estimate(tco, benchmark)
    seg_summary = summarize_by_segment(tco)
    city_summary = summarize_by_city(tco)
    cost_bd = cost_breakdown_by_segment(tco)

    tco.to_csv(OUTPUT_DIR / "step2_vehicle_monthly_tco.csv", index=False)
    seg_summary.to_csv(OUTPUT_DIR / "step2_segment_profitability.csv", index=False)
    city_summary.to_csv(OUTPUT_DIR / "step2_city_profitability.csv", index=False)
    cost_bd.to_csv(OUTPUT_DIR / "step2_segment_cost_breakdown.csv", index=False)

    plot_segment_charts(seg_summary, cost_bd)
    print_insights(seg_summary, city_summary, float(tco["maintenance_cap"].iloc[0]))
    print(f"\n输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
