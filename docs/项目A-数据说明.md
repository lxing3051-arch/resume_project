# 项目 A · 数据说明

> 本文档说明 Step 1 入库后的 **数据逻辑、表结构、字段口径、ER 图**。  
> 公开数据集下载与加载方式见：[公开数据源说明.md](./公开数据源说明.md)

---

## 一、整体数据逻辑

Step 1 把 **两份公开数据** 清洗后写入 SQLite（`project_a/data/greenlease.db`），形成能支撑 **成本 → 收益 → 盈利** 分析的底表。

```
┌─────────────────────────────────────────────────────────────┐
│  数据源 1：Zenodo 租车维保（国际租车公司真实发票）              │
│  → 主 fleet：约 3 万辆、67 个城市、24 万+ 维保记录             │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   vehicle_asset     cost_monthly       city_factor
   （车是谁）         （每月花多少）      （城市层面汇总）
         │                 │
         └────────┬────────┘
                  ▼
              disposal
            （哪些车已处置）

┌─────────────────────────────────────────────────────────────┐
│  数据源 2：Getaround（欧洲共享租车平台公开数据）               │
│  → 辅表：真实日租金 + 租赁活动记录                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
 getaround_pricing   getaround_rental_activity   segment_rent_benchmark
 （定价特征+日租金）   （租赁频次/延迟）          （Segment 租金基准，桥接表）
```

**重要：** Zenodo 与 Getaround 使用 **不同的车辆 ID**，不能按「同一辆车」直接 JOIN；通过 `segment`（车型级别）和 `segment_rent_benchmark` 桥接。

---

## 二、ER 图（实体关系图）

```mermaid
erDiagram
    vehicle_asset ||--o{ cost_monthly : "vehicle_id"
    vehicle_asset ||--o| disposal : "vehicle_id"
    vehicle_asset }o..o{ city_factor : "city_id"
    vehicle_asset }o..|| segment_rent_benchmark : "segment"

    data_source {
        int id PK
        text table_name
        text source_name
        text source_url
        text loaded_at
        text notes
    }

    vehicle_asset {
        text vehicle_id PK "Zenodo CARID"
        text brand
        text model
        text segment "车型级别 B~F"
        text fuel_type
        int model_year "年款"
        int city_id "城市编码"
        real purchase_price "USD 估算"
        text purchase_date "首条维保-30天"
        text data_source
    }

    cost_monthly {
        int id PK
        text vehicle_id FK
        text month "YYYY-MM"
        real depreciation
        real insurance
        real maintenance "真实发票"
        real parking
        text data_source
    }

    city_factor {
        int id PK
        int city_id
        text month
        int fleet_size "活跃车辆数"
        real avg_maintenance
        real competitor_avg_rent
        real demand_index "fleet_size/均值"
        text data_source
    }

    disposal {
        text vehicle_id PK_FK
        text disposal_date
        real residual_value
        text data_source
    }

    getaround_pricing {
        int listing_id PK
        text model_key
        real mileage
        real engine_power
        text fuel
        text car_type
        real rental_price_per_day
        text data_source
    }

    getaround_rental_activity {
        int rental_id PK
        int car_id "Getaround车ID"
        text state
        real delay_at_checkout_in_minutes
        real time_delta_with_previous_rental_minutes
        text data_source
    }

    segment_rent_benchmark {
        text segment PK
        real median_daily_rent
        real median_monthly_rent
        int sample_size
        text mapping_note
        text data_source
    }
```

### 图例

| 符号 | 含义 |
|------|------|
| `\|\|--o{` | 一对多，有外键，可 SQL JOIN |
| `}o..o{` | 逻辑多对多，靠 `city_id` 等关联，无直接外键 |
| `}o..\|\|` | 多对一逻辑关联，如多辆车对应一个 Segment 租金基准 |

### 表间关系摘要

| 关系 | 说明 |
|------|------|
| `vehicle_asset` → `cost_monthly` | 一车多个月成本记录 |
| `vehicle_asset` → `disposal` | 部分车辆已处置（0 或 1 条） |
| `vehicle_asset` ↔ `city_factor` | 相同 `city_id`，城市维度汇总 |
| `vehicle_asset` ↔ `segment_rent_benchmark` | 相同 `segment`，Step 2 估算租金用 |
| `getaround_pricing` / `getaround_rental_activity` | 独立子系统，与 Zenodo **不按 vehicle_id 关联** |

---

## 三、数据流（Step 1 → Step 2）

```
Zenodo 维保原始数据
    │
    ├─→ vehicle_asset（每辆车静态信息）
    ├─→ cost_monthly（每车每月成本，maintenance = 真实发票）
    ├─→ city_factor（每城每月 fleet_size、demand_index）
    └─→ disposal（已退网车辆 + 残值）

Getaround 定价数据
    │
    ├─→ getaround_pricing（日租金 + 车型特征）
    ├─→ getaround_rental_activity（租赁活动，无日期/租金字段）
    └─→ segment_rent_benchmark（car_type → Segment 映射后的租金基准）
              │
              └──→ Step 2：vehicle_asset.segment JOIN segment → 估算月收入
```

---

## 四、关键字段口径说明

### 4.1 年款（`model_year`）

**年款 = 车辆出厂/型号年份**，来自 Zenodo 原始字段 `Year`。

| 例子 | 含义 |
|------|------|
| `2019` | 2019 年款 |
| `2021` | 2021 年款 |

用途：判断车龄；估算采购价时，年款越新在 Segment 基准价上略上调（代码：每年 +2%）。

---

### 4.2 入库日期（`purchase_date`）

**入库日期 = 车辆进入租赁 fleet、开始计成本的日期**（投入运营日）。

公开数据无真实采购日，采用：

```
purchase_date = 该车首条维保日期 − 30 天
```

| 原因 | 说明 |
|------|------|
| 新车不会当天维保 | 首条发票通常发生在运营一段时间后 |
| 折旧需要起点 | 折旧从入库月开始，不能从首条发票才开始 |
| 30 天为合理 proxy | 假设运营约 1 个月内产生首条维保记录 |

---

### 4.3 Fleet 与 Fleet Size

| 术语 | 含义 |
|------|------|
| **Fleet（车队）** | 租赁公司全部运营车辆集合；本项目主 fleet ≈ Zenodo 3 万辆 |
| **Fleet Size** | 某维度下活跃/有记录的车辆数 |

在 `city_factor.fleet_size` 中：

```
fleet_size = 该 city_id 在该 month 有维保记录的去重车辆数（DISTINCT CARID）
```

例：City 63、2022-01、`fleet_size = 3004` → 该城该月约 3004 辆车有维保 activity。

---

### 4.4 需求指数（`demand_index`）

```python
demand_index = 该城该月 fleet_size / 全网各城各月 fleet_size 的平均值
```

| 值 | 解读 |
|----|------|
| > 1 | 该城该月活跃车数高于全网平均 |
| = 1 | 接近平均 |
| < 1 | 低于平均 |

**注意：** 用 fleet 规模作需求 proxy，非真实订单量；面试需说明为简化假设。

---

### 4.5 Mapping Note（`segment_rent_benchmark.mapping_note`）

说明 **Getaround 与 Zenodo 两套分类如何对齐**。Zenodo 用 Segment（B/C/D/E），Getaround 用 `car_type`（sedan/suv 等），映射规则：

| Getaround `car_type` | → Zenodo `segment` |
|----------------------|---------------------|
| subcompact, hatchback | B |
| sedan, coupe | C |
| estate, suv, van | D |
| convertible | E |

`mapping_note = "Getaround car_type → Zenodo Segment"` 表示：租金基准经上述映射从 Getaround 聚合到 Zenodo Segment。

---

### 4.6 为什么只有 `city_id`，没有城市名？

Zenodo 原始数据 **只提供 `CityID` 数字编码**（共 67 个），不含城市名字段。常见原因：脱敏、跨国格式不统一、按编号分析即可。

| city_id | 约车辆数 | 说明 |
|---------|----------|------|
| 63 | 20,362 | fleet 规模最大 |
| 5 | 1,988 | — |
| … | … | 共 67 个城市编码 |

分析可直接用 `city_id`；报告可写「City 63（fleet 规模最大）」。无官方对照表时不应强行映射为「深圳、广州」等真实地名。

---

## 五、每张表与字段说明

### 5.1 `data_source` — 数据血缘

记录每张表的来源，面试「数据从哪来」查此表。

| 列名 | 含义 |
|------|------|
| `table_name` | 表名 |
| `source_name` | 数据集名称 |
| `source_url` | 下载链接 |
| `loaded_at` | 加载时间 |
| `notes` | 口径说明 |

---

### 5.2 `vehicle_asset` — 车辆资产主表

约 **29,995 行**，一行一辆车（Zenodo 主 fleet）。

| 列名 | 含义 | 来源 |
|------|------|------|
| `vehicle_id` | 车辆唯一编号 | Zenodo `CARID` |
| `brand` | 品牌 | Zenodo 真实 |
| `model` | 型号 | Zenodo 真实 |
| `segment` | 车型级别 A～F | Zenodo 真实 |
| `fuel_type` | Diesel / Petrol / Hybrid / Electric | Zenodo 真实 |
| `model_year` | 年款 | Zenodo `Year` |
| `city_id` | 城市编码 | Zenodo `CityID` |
| `purchase_price` | 采购价（USD） | Segment MSRP 公开参数 + 年款调整 |
| `purchase_date` | 入库日期 | 首条维保日 − 30 天 |
| `data_source` | 来源标记 | `zenodo` |

---

### 5.3 `cost_monthly` — 月度成本表

约 **86,995 行**，有维保记录的车辆 × 月份。

| 列名 | 含义 | 来源 |
|------|------|------|
| `vehicle_id` | 哪辆车 | FK → `vehicle_asset` |
| `month` | 月份 `YYYY-MM` | 发票日期汇总 |
| `depreciation` | 月折旧（USD） | 直线法：采购价 × 65% / 60 |
| `insurance` | 月保险（USD） | Segment 行业均值 |
| `maintenance` | 月维保（USD） | **Zenodo 真实发票 `GrandTotal` 按月汇总** |
| `parking` | 月停车费（USD） | 按城市 fleet 规模分大/中/小三档 |
| `data_source` | 混合来源说明 | — |

**月 TCO（Step 2）** = `depreciation + insurance + maintenance + parking`

---

### 5.4 `city_factor` — 城市因子表

约 **2,045 行**，`city_id × month` 汇总。

| 列名 | 含义 | 来源 |
|------|------|------|
| `city_id` | 城市编码 | Zenodo |
| `month` | 月份 | Zenodo |
| `fleet_size` | 该月活跃车辆数 | Zenodo 统计 |
| `avg_maintenance` | 该城该月平均每车维保费 | Zenodo 真实 |
| `competitor_avg_rent` | 市场参考月租 | Getaround 全球日租金中位数 × 30 |
| `demand_index` | 需求指数 | `fleet_size / 全网 fleet_size 均值` |
| `data_source` | 混合来源 | — |

---

### 5.5 `disposal` — 处置表

约 **10,603 行**，末次维保早于 **2022-01-01** 的车辆视为已处置。

| 列名 | 含义 | 来源 |
|------|------|------|
| `vehicle_id` | 哪辆车 | Zenodo |
| `disposal_date` | 处置日 | 最后一次维保日期 |
| `residual_value` | 处置残值（USD） | 采购价 × 35% |
| `data_source` | — | `zenodo` |

---

### 5.6 `getaround_pricing` — Getaround 定价清单

约 **4,843 行**，用于 Step 3/4 定价模型。

| 列名 | 含义 |
|------|------|
| `listing_id` | 挂牌编号 |
| `model_key` | 车型描述 |
| `mileage` | 里程 |
| `engine_power` | 发动机功率 |
| `fuel` | 燃料类型 |
| `paint_color` | 颜色 |
| `car_type` | sedan / suv / hatchback 等 |
| `rental_price_per_day` | **真实日租金** |
| `data_source` | `getaround` |

---

### 5.7 `getaround_rental_activity` — Getaround 租赁活动

约 **21,310 行**。**无起止日期、无租金金额**。

| 列名 | 含义 |
|------|------|
| `rental_id` | 租赁单号 |
| `car_id` | Getaround 车辆 ID（≠ Zenodo `vehicle_id`） |
| `checkin_type` | 取车方式，如 mobile |
| `state` | `ended` 完成 / `canceled` 取消 |
| `delay_at_checkout_in_minutes` | 还车延迟（分钟，负值=提前） |
| `previous_ended_rental_id` | 上一单 ID |
| `time_delta_with_previous_rental_minutes` | 与上一单时间间隔 |
| `data_source` | `getaround` |

---

### 5.8 `segment_rent_benchmark` — Segment 租金基准（桥接表）

**4 行**（Segment B / C / D / E）。

| 列名 | 含义 |
|------|------|
| `segment` | 对应 `vehicle_asset.segment` |
| `median_daily_rent` | 该 Segment 在 Getaround 的日租金中位数 |
| `median_monthly_rent` | 日租金 × 30 |
| `sample_size` | 映射后样本车数 |
| `mapping_note` | car_type → Segment 映射说明 |
| `data_source` | `getaround` |

---

## 六、表与原始数据集对照

| 目标表 | 主要数据来源 | 补充 / 推算 |
|--------|--------------|-------------|
| `vehicle_asset` | Zenodo | 采购价、入库日期 |
| `cost_monthly` | Zenodo 维保（真实） | 折旧、保险、停车费 |
| `city_factor` | Zenodo 聚合 | 竞品租金来自 Getaround 全局中位数 |
| `disposal` | Zenodo | 残值率 35% |
| `getaround_pricing` | Getaround | — |
| `getaround_rental_activity` | Getaround | — |
| `segment_rent_benchmark` | Getaround 聚合 | car_type → Segment 映射 |
| `data_source` | 元数据 | — |

---

## 七、常用验证 SQL

```sql
-- 数据血缘
SELECT table_name, source_name, notes FROM data_source;

-- 某城市车辆与 Segment 分布
SELECT city_id, segment, COUNT(*) AS cnt
FROM vehicle_asset
GROUP BY city_id, segment
ORDER BY city_id, cnt DESC
LIMIT 20;

-- Segment 租金基准
SELECT * FROM segment_rent_benchmark;

-- 单车月度 TCO 样例
SELECT vehicle_id, month,
       depreciation + insurance + maintenance + parking AS monthly_tco
FROM cost_monthly
LIMIT 10;
```

---

## 八、加载与文件位置

```bash
cd project_a
python src/load_public_data.py
```

| 路径 | 说明 |
|------|------|
| `project_a/data/raw/` | 原始 xlsx / csv |
| `project_a/data/greenlease.db` | SQLite 数据库 |
| `project_a/sql/schema.sql` | 建表 DDL |
| `project_a/src/load_public_data.py` | ETL 脚本 |

---

*文档版本：v1.0 | 更新日期：2026-08-03*
