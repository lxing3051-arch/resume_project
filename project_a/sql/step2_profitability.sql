-- Step 2：TCO 与盈利复盘 SQL
-- 运行环境：project_a/data/greenlease.db

-- ---------------------------------------------------------------------------
-- 1. 单车月度 TCO（含真实维保 + 折旧/保险/停车）
-- ---------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_vehicle_monthly_tco AS
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
JOIN vehicle_asset v ON c.vehicle_id = v.vehicle_id;

-- ---------------------------------------------------------------------------
-- 2. 维保异常值封顶（P99，避免单笔巨额发票扭曲均值）
--    Zenodo 维保金额存在极端值，经营分析采用分位数封顶并保留原始字段供审计
-- ---------------------------------------------------------------------------
-- 见 Python step2_profitability.py 中 maintenance_capped 逻辑

-- ---------------------------------------------------------------------------
-- 3. 分 Segment 成本结构（Step 2 核心输出之一）
-- ---------------------------------------------------------------------------
-- SELECT
--     segment,
--     COUNT(DISTINCT vehicle_id) AS vehicle_cnt,
--     ROUND(AVG(depreciation), 2) AS avg_depreciation,
--     ROUND(AVG(maintenance), 2) AS avg_maintenance,
--     ROUND(AVG(total_cost), 2) AS avg_total_cost
-- FROM v_vehicle_monthly_tco
-- GROUP BY segment
-- ORDER BY avg_total_cost DESC;

-- ---------------------------------------------------------------------------
-- 4. 分城市（CityID）成本结构
-- ---------------------------------------------------------------------------
-- SELECT
--     city_id,
--     COUNT(DISTINCT vehicle_id) AS vehicle_cnt,
--     ROUND(AVG(total_cost), 2) AS avg_total_cost,
--     ROUND(AVG(maintenance), 2) AS avg_maintenance
-- FROM v_vehicle_monthly_tco
-- GROUP BY city_id
-- ORDER BY avg_total_cost DESC
-- LIMIT 20;

-- ---------------------------------------------------------------------------
-- 5. 盈利估算：Segment 租金基准 − 月 TCO
--    收入 = segment_rent_benchmark.median_monthly_rent × 利用率假设（Python 中 65%）
-- ---------------------------------------------------------------------------
-- 见 v_segment_profitability / v_city_profitability（Python 写入或动态查询）
