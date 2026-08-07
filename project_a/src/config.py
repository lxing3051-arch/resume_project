"""公开数据 ETL 业务参数（有出处的行业假设，非随机生成）"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "greenlease.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"

# ---------------------------------------------------------------------------
# 数据来源
# ---------------------------------------------------------------------------
ZENODO_URL = "https://zenodo.org/records/7937227"
GETAROUND_PRICING_URL = (
    "https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_pricing_project.csv"
)
GETAROUND_DELAY_URL = (
    "https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_delay_analysis.xlsx"
)

# ---------------------------------------------------------------------------
# 折旧口径（企业直线折旧法，行业惯例）
# 参考：企业会计准则第4号——固定资产；租赁 fleet 常用 5 年生命周期
# ---------------------------------------------------------------------------
DEPRECIATION_MONTHS = 60
RESIDUAL_RATE = 0.35

# ---------------------------------------------------------------------------
# .segment 采购价基准（USD）
# 参考：欧洲 B/C/D 级乘用车公开市场均价区间（Statista / OEM 官网 MSRP 量级）
# 按 Segment 字母分级，再按车龄 Year 微调
# ---------------------------------------------------------------------------
SEGMENT_MSRP_USD: dict[str, float] = {
    "A": 16_000,
    "B": 20_000,
    "C": 25_000,
    "D": 32_000,
    "E": 45_000,
    "F": 60_000,
}
DEFAULT_SEGMENT_MSRP_USD = 25_000

# ---------------------------------------------------------------------------
# 月商业保险（USD / 月）
# 参考：欧美 commercial auto fleet 保险行业公开区间，按 Segment 分档
# ---------------------------------------------------------------------------
SEGMENT_INSURANCE_USD: dict[str, float] = {
    "A": 100,
    "B": 120,
    "C": 150,
    "D": 180,
    "E": 220,
    "F": 280,
}
DEFAULT_INSURANCE_USD = 150

# ---------------------------------------------------------------------------
# 月停车费（USD / 月）
# 按城市 fleet 规模分三档（大/中/小城市 proxy，来自 CityID 车辆数四分位）
# 参考：欧洲 urban monthly parking 公开收费区间
# ---------------------------------------------------------------------------
PARKING_TIER_USD = {"large": 180, "medium": 120, "small": 80}

# 处置判定：末次维保早于该日期视为已处置
DISPOSAL_CUTOFF = "2022-01-01"
