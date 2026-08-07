"""项目 B 配置：资产价值分层与退网预警"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 复用项目 A 已入库的公开数据
DB_PATH = ROOT.parent / "project_a" / "data" / "greenlease.db"
OUTPUT_DIR = ROOT / "data" / "output"

# ---------------------------------------------------------------------------
# 时间窗口设计（避免标签泄露的关键）
#   观察期：构造 RFM 特征
#   预测期：观察是否仍有运营活动，定义「退网/流失」标签
# ---------------------------------------------------------------------------
OBSERVE_START = "2021-01"
OBSERVE_END = "2022-06"
OUTCOME_START = "2022-07"
OUTCOME_END = "2023-02"

# Recency 基准点：观察期最后一个月
RECENCY_ANCHOR = OBSERVE_END

# RFM 分箱档位（每个维度 1~4 分）
RFM_BINS = 4

# 聚类
N_CLUSTERS = 4
RANDOM_STATE = 42
