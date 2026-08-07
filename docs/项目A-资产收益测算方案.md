# 项目 A：新能源租赁车辆资产收益测算与动态租金定价分析

> 虚构业务背景：**绿行租赁** — 新能源 B2B 租赁平台，在多城市投放不同车型。  
> 目标：对齐地上铁 JD「岗位职责 1 — 车辆资产收益测算与建模支持」。

---

## 一、业务问题（简历 / 面试 30 秒版）

> 绿行租赁在不同城市投放不同新能源车型。运营需要回答：**每辆车赚不赚钱？租金定多少合理？哪些城市 / 车型要调价或退网？**

---

## 二、分析框架

```
① 资产成本层 → 全生命周期成本（TCO）
② 收益层     → 租金收入、处置残值
③ 盈利层     → 单城 / 单车型 unit economics
④ 策略层     → 动态定价因子 + 可解释回归模型
```

---

## 三、技术栈

| 模块 | 工具 |
|------|------|
| 数据存储 | SQLite（本地），面试可说「可迁移至 MySQL / Hive」 |
| 数据处理 | Python（pandas）+ SQL |
| 建模 | sklearn 线性回归 / Ridge |
| 可视化 | matplotlib / seaborn |
| 文档 | Jupyter Notebook + README（SOP 风格） |

---

## 四、数据表设计（公开数据版）

| 表名 | 用途 | 数据来源 |
|------|------|----------|
| `vehicle_asset` | 车辆资产主表 | Zenodo CARID / Brand / Model / CityID |
| `cost_monthly` | 月度成本 | Zenodo 真实维保 + 公开折旧/保险/停车参数 |
| `city_factor` | 城市因子 | Zenodo 聚合 + Getaround 租金中位数 |
| `disposal` | 处置残值 | Zenodo 末次维保早于 2022 的车辆 |
| `getaround_pricing` | 定价特征与日租金 | Getaround 4843 listings |
| `getaround_rental_activity` | 租赁活动/利用率 | Getaround 21310 rentals |
| `segment_rent_benchmark` | Segment 租金基准 | Getaround 按 car_type 映射聚合 |
| `data_source` | 数据血缘 | 各表来源 URL 与说明 |

> 数据表设计与 ER 图详见 [项目A-数据说明.md](./项目A-数据说明.md)；公开数据下载见 [公开数据源说明.md](./公开数据源说明.md)。

---

## 五、核心指标口径（面试必背）

| 指标 | 口径定义 |
|------|----------|
| **月折旧** | 采购价 × (1 - 残值率) / 折旧月数（默认 60 个月，残值率 35%） |
| **月租金收入** | 租期内按实际出租天数 × 日租金；未出租天数收入为 0 |
| **利用率** | 当月出租天数 / 当月日历天数 |
| **单车月利润** | 月租金收入 - 月折旧 - 月保险 - 月维保 - 月停车费 |
| **ROI** | (累计租金 + 残值 - 累计成本) / 累计成本 |

---

## 六、实施步骤

| 阶段 | 内容 | 产出 |
|------|------|------|
| **Step 1** | 公开数据 ETL 入库 | 资产测算底表（真实数据）✅ |
| **Step 2** | SQL / Python 算 TCO、盈利复盘 | 分 Segment / 分城市盈利表 ✅ |
| **Step 3** | 定价因子分析 | 相关矩阵 + 分组对比 + 图表 ✅ |
| **Step 4** | 回归定价模型 + 与规则定价对比 | MAPE / RMSE + 因子重要性 ✅ |
| **Step 5** | 结论 + 运营建议 | 面试 story + 简历描述 ✅ |

---

## 七、简历描述模板（跑完后填数字）

> 基于 Zenodo、Getaround 公开数据，搭建 3 万辆租赁资产 TCO 测算框架；完成分 Segment/分城市盈利复盘，Segment C 利润率 29.4%，Segment E 估算亏损；构建 Ridge 动态定价模型，较规则定价 MAPE 降低 34.1%（27.9%→18.4%），R²=0.64。

---

## 八、项目目录结构

```
project_a/
├── README.md
├── requirements.txt
├── sql/
│   └── schema.sql              # 建表语句（公开数据版）
├── src/
│   ├── load_public_data.py     # ★ 公开数据 ETL（默认入口）
│   ├── generate_data.py        # [已弃用] 模拟数据
│   └── config.py               # 行业参数与路径配置
├── data/
│   ├── raw/                    # 原始公开数据 xlsx/csv
│   └── greenlease.db           # SQLite（运行后生成）
└── notebooks/                  # 后续分析 notebook
```

---

*下一步：运行 `python src/load_public_data.py`，进入 Step 2 盈利复盘。*
