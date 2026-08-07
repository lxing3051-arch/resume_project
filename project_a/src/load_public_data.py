"""
从公开数据集清洗并加载 SQLite。
主 fleet：Zenodo 租车维保 | 辅表：Getaround 定价 & 租赁活动
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    DB_PATH,
    DEFAULT_INSURANCE_USD,
    DEFAULT_SEGMENT_MSRP_USD,
    DEPRECIATION_MONTHS,
    DISPOSAL_CUTOFF,
    GETAROUND_DELAY_URL,
    GETAROUND_PRICING_URL,
    PARKING_TIER_USD,
    RAW_DIR,
    RESIDUAL_RATE,
    SCHEMA_PATH,
    SEGMENT_INSURANCE_USD,
    SEGMENT_MSRP_USD,
    ZENODO_URL,
)

# Getaround car_type → Zenodo Segment 映射（用于租金基准桥接）
CAR_TYPE_TO_SEGMENT: dict[str, str] = {
    "subcompact": "B",
    "hatchback": "B",
    "sedan": "C",
    "estate": "D",
    "suv": "D",
    "coupe": "C",
    "convertible": "E",
    "van": "D",
}

NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def monthly_depreciation(purchase_price: float) -> float:
    return purchase_price * (1 - RESIDUAL_RATE) / DEPRECIATION_MONTHS


def purchase_price_for_segment(segment: str, model_year: int) -> float:
    base = SEGMENT_MSRP_USD.get(str(segment).upper(), DEFAULT_SEGMENT_MSRP_USD)
    year_adj = 1 + (int(model_year) - 2018) * 0.02
    return round(base * max(year_adj, 0.85), 2)


def insurance_for_segment(segment: str) -> float:
    return SEGMENT_INSURANCE_USD.get(str(segment).upper(), DEFAULT_INSURANCE_USD)


def load_zenodo_maintenance() -> pd.DataFrame:
    path = RAW_DIR / "car_maintenance_clean.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"缺少 Zenodo 数据: {path}\n请先下载: {ZENODO_URL}")
    usecols = [
        "CARID",
        "Brand",
        "Model",
        "Segment",
        "Year",
        "FuelType",
        "CityID",
        "InvoiceDate",
        "GrandTotal",
    ]
    df = pd.read_excel(path, usecols=usecols)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    return df


def load_getaround_pricing() -> pd.DataFrame:
    path = RAW_DIR / "get_around_pricing_project.csv"
    if not path.exists():
        raise FileNotFoundError(f"缺少 Getaround 定价数据: {path}")
    df = pd.read_csv(path)
    df = df.rename(columns={"Unnamed: 0": "listing_id"})
    return df


def load_getaround_delay() -> pd.DataFrame:
    path = RAW_DIR / "get_around_delay_analysis.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"缺少 Getaround 租赁活动数据: {path}")
    return pd.read_excel(path)


def build_vehicle_asset(maint: pd.DataFrame) -> pd.DataFrame:
    first = (
        maint.sort_values("InvoiceDate")
        .groupby("CARID", as_index=False)
        .first()[["CARID", "Brand", "Model", "Segment", "Year", "FuelType", "CityID", "InvoiceDate"]]
    )
    first["purchase_date"] = (first["InvoiceDate"] - pd.Timedelta(days=30)).dt.strftime("%Y-%m-%d")
    first["purchase_price"] = first.apply(
        lambda r: purchase_price_for_segment(r["Segment"], r["Year"]), axis=1
    )
    return pd.DataFrame(
        {
            "vehicle_id": first["CARID"].astype(str),
            "brand": first["Brand"],
            "model": first["Model"],
            "segment": first["Segment"].astype(str),
            "fuel_type": first["FuelType"],
            "model_year": first["Year"].astype(int),
            "city_id": first["CityID"].astype(int),
            "purchase_price": first["purchase_price"],
            "purchase_date": first["purchase_date"],
            "data_source": "zenodo",
        }
    )


def city_parking_tiers(maint: pd.DataFrame) -> dict[int, str]:
    counts = maint.groupby("CityID")["CARID"].nunique().sort_values(ascending=False)
    n = len(counts)
    large_cut = counts.iloc[max(int(n * 0.25) - 1, 0)]
    medium_cut = counts.iloc[max(int(n * 0.5) - 1, 0)]
    tiers: dict[int, str] = {}
    for city_id, cnt in counts.items():
        if cnt >= large_cut:
            tiers[int(city_id)] = "large"
        elif cnt >= medium_cut:
            tiers[int(city_id)] = "medium"
        else:
            tiers[int(city_id)] = "small"
    return tiers


def build_cost_monthly(maint: pd.DataFrame, vehicles: pd.DataFrame) -> pd.DataFrame:
    real_maint = (
        maint.groupby(["CARID", "month"], as_index=False)["GrandTotal"]
        .sum()
        .rename(columns={"CARID": "vehicle_id", "GrandTotal": "maintenance"})
    )
    real_maint["vehicle_id"] = real_maint["vehicle_id"].astype(str)

    v = vehicles.set_index("vehicle_id")
    tiers = city_parking_tiers(maint)

    rows = []
    for _, r in real_maint.iterrows():
        vid = r["vehicle_id"]
        if vid not in v.index:
            continue
        info = v.loc[vid]
        tier = tiers.get(int(info["city_id"]), "medium")
        rows.append(
            {
                "vehicle_id": vid,
                "month": r["month"],
                "depreciation": round(monthly_depreciation(info["purchase_price"]), 2),
                "insurance": insurance_for_segment(info["segment"]),
                "maintenance": round(float(r["maintenance"]), 2),
                "parking": PARKING_TIER_USD[tier],
                "data_source": "zenodo_maintenance + industry_params",
            }
        )
    return pd.DataFrame(rows)


def build_city_factor(maint: pd.DataFrame, global_monthly_rent: float) -> pd.DataFrame:
    city_month = (
        maint.groupby(["CityID", "month"])
        .agg(fleet_size=("CARID", "nunique"), avg_maintenance=("GrandTotal", "mean"))
        .reset_index()
    )
    overall = city_month["fleet_size"].mean()
    rows = []
    for _, r in city_month.iterrows():
        rows.append(
            {
                "city_id": int(r["CityID"]),
                "month": r["month"],
                "fleet_size": int(r["fleet_size"]),
                "avg_maintenance": round(float(r["avg_maintenance"]), 2),
                "competitor_avg_rent": round(global_monthly_rent, 2),
                "demand_index": round(float(r["fleet_size"] / overall), 3),
                "data_source": "zenodo + getaround_rent_median",
            }
        )
    return pd.DataFrame(rows)


def build_disposal(maint: pd.DataFrame, vehicles: pd.DataFrame) -> pd.DataFrame:
    last = maint.groupby("CARID")["InvoiceDate"].max().reset_index()
    cutoff = pd.Timestamp(DISPOSAL_CUTOFF)
    disposed = last[last["InvoiceDate"] < cutoff].copy()
    v = vehicles.set_index("vehicle_id")
    rows = []
    for _, r in disposed.iterrows():
        vid = str(r["CARID"])
        if vid not in v.index:
            continue
        price = float(v.loc[vid, "purchase_price"])
        rows.append(
            {
                "vehicle_id": vid,
                "disposal_date": r["InvoiceDate"].strftime("%Y-%m-%d"),
                "residual_value": round(price * RESIDUAL_RATE, 2),
                "data_source": "zenodo",
            }
        )
    return pd.DataFrame(rows)


def build_segment_rent_benchmark(pricing: pd.DataFrame) -> pd.DataFrame:
    p = pricing.copy()
    p["segment"] = p["car_type"].map(CAR_TYPE_TO_SEGMENT).fillna("C")
    agg = (
        p.groupby("segment")["rental_price_per_day"]
        .agg(["median", "count"])
        .reset_index()
    )
    rows = []
    for _, r in agg.iterrows():
        daily = float(r["median"])
        rows.append(
            {
                "segment": r["segment"],
                "median_daily_rent": round(daily, 2),
                "median_monthly_rent": round(daily * 30, 2),
                "sample_size": int(r["count"]),
                "mapping_note": "Getaround car_type → Zenodo Segment",
                "data_source": "getaround",
            }
        )
    return pd.DataFrame(rows)


def build_getaround_pricing(pricing: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "listing_id",
        "model_key",
        "mileage",
        "engine_power",
        "fuel",
        "paint_color",
        "car_type",
        "rental_price_per_day",
    ]
    df = pricing[cols].copy()
    df["data_source"] = "getaround"
    return df


def build_getaround_rental_activity(delay: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rental_id": delay["rental_id"].astype(int),
            "car_id": delay["car_id"].astype(int),
            "checkin_type": delay["checkin_type"],
            "state": delay["state"],
            "delay_at_checkout_in_minutes": delay["delay_at_checkout_in_minutes"],
            "previous_ended_rental_id": delay["previous_ended_rental_id"],
            "time_delta_with_previous_rental_minutes": delay[
                "time_delta_with_previous_rental_in_minutes"
            ],
            "data_source": "getaround",
        }
    )


def write_provenance(conn: sqlite3.Connection, notes: list[tuple[str, str, str, str]]) -> None:
    rows = [(t, s, u, NOW, n) for t, s, u, n in notes]
    conn.executemany(
        "INSERT INTO data_source (table_name, source_name, source_url, loaded_at, notes) VALUES (?,?,?,?,?)",
        rows,
    )


def write_table(conn: sqlite3.Connection, name: str, df: pd.DataFrame) -> None:
    df.to_sql(name, conn, if_exists="replace", index=False)


def print_summary(conn: sqlite3.Connection) -> None:
    tables = [
        "vehicle_asset",
        "cost_monthly",
        "city_factor",
        "disposal",
        "getaround_pricing",
        "getaround_rental_activity",
        "segment_rent_benchmark",
    ]
    print("\n=== 公开数据加载完成 ===")
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:30s} {n:>8,} 行")
    print(f"\n数据库: {DB_PATH}")


def main() -> None:
    print("读取 Zenodo 维保数据（约 24 万行，需 1～2 分钟）...")
    maint = load_zenodo_maintenance()
    pricing = load_getaround_pricing()
    delay = load_getaround_delay()

    vehicles = build_vehicle_asset(maint)
    costs = build_cost_monthly(maint, vehicles)
    global_monthly_rent = float(pricing["rental_price_per_day"].median()) * 30
    city_factors = build_city_factor(maint, global_monthly_rent)
    disposals = build_disposal(maint, vehicles)
    segment_benchmark = build_segment_rent_benchmark(pricing)
    ga_pricing = build_getaround_pricing(pricing)
    ga_activity = build_getaround_rental_activity(delay)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        write_table(conn, "vehicle_asset", vehicles)
        write_table(conn, "cost_monthly", costs)
        write_table(conn, "city_factor", city_factors)
        write_table(conn, "disposal", disposals)
        write_table(conn, "getaround_pricing", ga_pricing)
        write_table(conn, "getaround_rental_activity", ga_activity)
        write_table(conn, "segment_rent_benchmark", segment_benchmark)
        write_provenance(
            conn,
            [
                (
                    "vehicle_asset",
                    "Zenodo Car Rental Maintenance",
                    ZENODO_URL,
                    "CARID/Brand/Model/Segment/CityID；采购价=Segment MSRP公开参数",
                ),
                (
                    "cost_monthly",
                    "Zenodo + industry params",
                    ZENODO_URL,
                    "maintenance=真实发票汇总；depreciation/insurance/parking=公开假设",
                ),
                (
                    "city_factor",
                    "Zenodo + Getaround",
                    GETAROUND_PRICING_URL,
                    "competitor_avg_rent=Getaround全样本日租金中位数×30",
                ),
                ("disposal", "Zenodo", ZENODO_URL, f"末次维保早于 {DISPOSAL_CUTOFF}"),
                ("getaround_pricing", "Getaround Pricing", GETAROUND_PRICING_URL, "4843 listings"),
                (
                    "getaround_rental_activity",
                    "Getaround Delay Analysis",
                    GETAROUND_DELAY_URL,
                    "21310 rentals; 无起止日期字段",
                ),
                (
                    "segment_rent_benchmark",
                    "Getaround Pricing",
                    GETAROUND_PRICING_URL,
                    "car_type映射至Zenodo Segment",
                ),
            ],
        )
        print_summary(conn)


if __name__ == "__main__":
    main()
