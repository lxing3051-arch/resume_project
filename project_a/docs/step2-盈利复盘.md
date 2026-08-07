# Step 2：TCO 与盈利复盘（实操指南）

## 一、Step 2 要回答的业务问题

1. **每类车（Segment）每月花多少？** → 月 TCO  
2. **每类车大概赚多少？** → 估算月利润  
3. **哪个 Segment / CityID 要重点关注？** → 亏损或高成本资产  

---

## 二、运行

```bash
cd project_a
python src/step2_profitability.py
```

---

## 三、代码分 5 步（对应 `step2_profitability.py`）

### Step 2.1 用 SQL 拉取单车月度成本

```sql
SELECT c.*, v.segment, v.city_id,
       (c.depreciation + c.insurance + c.maintenance + c.parking) AS total_cost
FROM cost_monthly c
JOIN vehicle_asset v ON c.vehicle_id = v.vehicle_id;
```

函数：`load_tco()`

---

### Step 2.2 维保异常值封顶（P99）

Zenodo 真实发票里有极端大额（如单次 28 万美元），会把均值拉偏。

```python
maintenance_capped = maintenance.clip(upper=P99)
total_cost_capped = 折旧 + 保险 + maintenance_capped + 停车
```

函数：`cap_maintenance_outliers()`

---

### Step 2.3 估算月收入

Getaround 的 Segment 租金基准 × 利用率：

```python
est_monthly_revenue = segment_rent_benchmark.median_monthly_rent × 0.65
```

函数：`add_profit_estimate()`

---

### Step 2.4 算估算月利润

```python
est_monthly_profit = est_monthly_revenue - total_cost_capped
```

---

### Step 2.5 分组汇总 + 出图

| 函数 | 输出 |
|------|------|
| `summarize_by_segment()` | 分 Segment 盈利表 |
| `summarize_by_city()` | 分 CityID 盈利表 |
| `plot_segment_charts()` | 盈利 + 成本结构图 |

---

## 四、输出文件

| 文件 | 内容 |
|------|------|
| `step2_vehicle_monthly_tco.csv` | 单车 × 月明细 |
| `step2_segment_profitability.csv` | 分 Segment 汇总 |
| `step2_city_profitability.csv` | 分 CityID 汇总 |
| `step2_segment_cost_breakdown.csv` | 分 Segment 成本结构 |
| `step2_segment_charts.png` | 可视化图表 |

---

## 五、核心口径

| 指标 | 公式 |
|------|------|
| 月 TCO | 折旧 + 保险 + 维保（P99 封顶）+ 停车 |
| 估算月收入 | `median_monthly_rent × 65%` |
| 估算月利润 | 估算月收入 − 月 TCO |
| 利润率 | 估算月利润 / 估算月收入 |

---

## 六、面试必讲的 3 个假设

1. **维保 P99 封顶** — 真实数据有 outlier，封顶后均值更稳健  
2. **利用率 65%** — 两数据集无法车级关联，保守估计出租率  
3. **Segment F 无 Getaround 映射** — 不参与租金估算  

---

## 七、可在 SQLite Viewer 里跑的 SQL

```sql
-- 各 Segment 平均月 TCO（未封顶版，感受 outlier 影响）
SELECT v.segment,
       ROUND(AVG(c.maintenance), 2) AS avg_maint_raw,
       ROUND(AVG(c.depreciation + c.insurance + c.maintenance + c.parking), 2) AS avg_tco_raw
FROM cost_monthly c
JOIN vehicle_asset v ON c.vehicle_id = v.vehicle_id
GROUP BY v.segment
ORDER BY avg_tco_raw DESC;

-- 租金基准
SELECT * FROM segment_rent_benchmark;
```

---

## 八、简历一句话（填真实数字）

> 基于公开维保数据完成分 Segment/分城市 TCO 复盘，识别 Segment E 估算亏损（TCO 高于租金覆盖能力），Segment C 利润率约 29%，提出高成本 Segment 调价或退网建议。

---

*下一步：Step 3 定价因子分析（Getaround 数据 + 相关性）*
