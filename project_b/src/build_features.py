"""
项目 B Step 1：构建资产 RFM 特征表

时间窗口设计（防止标签泄露）：
  观察期 OBSERVE_START ~ OBSERVE_END  -> 构造 RFM 与属性特征
  预测期 OUTCOME_START ~ OUTCOME_END  -> 是否仍有运营活动，定义退网标签
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from config import (
    DB_PATH,
    OBSERVE_END,
    OBSERVE_START,
    OUTCOME_END,
    OUTCOME_START,
    OUTPUT_DIR,
    RECENCY_ANCHOR,
)


def month_to_index(month: str) -> int:
    """'2021-03' -> 自 2000-01 起的月序号，便于算月份差。"""
    year, mon = month.split("-")
    return int(year) * 12 + int(mon)


def load_monthly_activity(conn: sqlite3.Connection) -> pd.DataFrame:
    sql = """
    SELECT c.vehicle_id, c.month, c.maintenance,
           v.segment, v.model_year, v.city_id, v.purchase_price, v.fuel_type, v.brand
    FROM cost_monthly c
    JOIN vehicle_asset v ON c.vehicle_id = v.vehicle_id
    """
    return pd.read_sql(sql, conn)


def build_rfm(observe: pd.DataFrame) -> pd.DataFrame:
    """R=距观察期末的月数，F=活跃月份数，M=累计维保金额。"""
    anchor = month_to_index(RECENCY_ANCHOR)
    obs = observe.copy()
    obs["month_idx"] = obs["month"].map(month_to_index)

    rfm = (
        obs.groupby("vehicle_id")
        .agg(
            first_active_idx=("month_idx", "min"),
            last_active_idx=("month_idx", "max"),
            frequency=("month", "nunique"),
            monetary=("maintenance", "sum"),
            avg_maintenance=("maintenance", "mean"),
            max_maintenance=("maintenance", "max"),
            std_maintenance=("maintenance", "std"),
        )
        .reset_index()
    )
    rfm["recency_months"] = anchor - rfm["last_active_idx"]
    rfm["tenure_months"] = anchor - rfm["first_active_idx"] + 1
    # 活跃密度：活跃月数 / 在册月数，衡量运营连续性
    rfm["active_density"] = (rfm["frequency"] / rfm["tenure_months"]).round(3)
    rfm["std_maintenance"] = rfm["std_maintenance"].fillna(0).round(2)
    rfm["monetary"] = rfm["monetary"].round(2)
    rfm["avg_maintenance"] = rfm["avg_maintenance"].round(2)
    rfm["max_maintenance"] = rfm["max_maintenance"].round(2)
    return rfm.drop(columns=["first_active_idx", "last_active_idx"])


def build_trend_features(observe: pd.DataFrame) -> pd.DataFrame:
    """时序趋势特征：近期活跃度、维保投入的前后半段变化。"""
    anchor = month_to_index(RECENCY_ANCHOR)
    obs = observe.copy()
    obs["month_idx"] = obs["month"].map(month_to_index)
    obs["months_before_anchor"] = anchor - obs["month_idx"]

    recent_3 = obs[obs["months_before_anchor"] < 3]
    recent_6 = obs[obs["months_before_anchor"] < 6]
    early = obs[obs["months_before_anchor"] >= 9]
    late = obs[obs["months_before_anchor"] < 9]

    base = obs[["vehicle_id"]].drop_duplicates()

    def agg_window(frame: pd.DataFrame, suffix: str) -> pd.DataFrame:
        return (
            frame.groupby("vehicle_id")
            .agg(**{
                f"active_months_{suffix}": ("month", "nunique"),
                f"maint_{suffix}": ("maintenance", "sum"),
            })
            .reset_index()
        )

    out = base
    for frame, suffix in [(recent_3, "last3m"), (recent_6, "last6m"),
                          (early, "early9m"), (late, "late9m")]:
        out = out.merge(agg_window(frame, suffix), on="vehicle_id", how="left")

    out = out.fillna(0)
    # 后半段 vs 前半段维保投入比值，>1 表示投入在上升
    out["maint_trend_ratio"] = (
        (out["maint_late9m"] + 1) / (out["maint_early9m"] + 1)
    ).round(3)
    out["active_trend_ratio"] = (
        (out["active_months_late9m"] + 1) / (out["active_months_early9m"] + 1)
    ).round(3)
    return out


def attach_attributes(rfm: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    attrs = (
        activity.groupby("vehicle_id")
        .agg(
            segment=("segment", "first"),
            model_year=("model_year", "first"),
            city_id=("city_id", "first"),
            purchase_price=("purchase_price", "first"),
            fuel_type=("fuel_type", "first"),
            brand=("brand", "first"),
        )
        .reset_index()
    )
    return rfm.merge(attrs, on="vehicle_id", how="left")


def attach_churn_label(features: pd.DataFrame, outcome: pd.DataFrame) -> pd.DataFrame:
    """预测期内无任何运营活动 -> churned=1（退网/流失）。"""
    active_later = set(outcome["vehicle_id"].unique())
    out = features.copy()
    out["churned"] = (~out["vehicle_id"].isin(active_later)).astype(int)
    return out


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        activity = load_monthly_activity(conn)

    observe = activity[(activity["month"] >= OBSERVE_START) & (activity["month"] <= OBSERVE_END)]
    outcome = activity[(activity["month"] >= OUTCOME_START) & (activity["month"] <= OUTCOME_END)]

    rfm = build_rfm(observe)
    trend = build_trend_features(observe)
    features = rfm.merge(trend, on="vehicle_id", how="left")
    features = attach_attributes(features, observe)
    features = attach_churn_label(features, outcome)

    out_path = OUTPUT_DIR / "b_step1_asset_rfm_features.csv"
    features.to_csv(out_path, index=False)

    print("=== 项目 B Step 1：RFM 特征表 ===")
    print(f"观察期 {OBSERVE_START} ~ {OBSERVE_END} | 预测期 {OUTCOME_START} ~ {OUTCOME_END}")
    print(f"观察期活跃车辆: {len(features):,} 辆")
    print(f"退网率(churn rate): {features['churned'].mean():.1%}")
    print()
    print(features[["recency_months", "frequency", "monetary"]].describe().round(2).to_string())
    print()
    print("退网 vs 留存的 RFM 均值对比:")
    print(
        features.groupby("churned")[["recency_months", "frequency", "monetary"]]
        .mean()
        .round(2)
        .to_string()
    )
    print(f"\n输出: {out_path}")


if __name__ == "__main__":
    main()
