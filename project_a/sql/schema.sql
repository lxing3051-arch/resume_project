-- 项目 A · 公开数据版 schema
-- 主 fleet：Zenodo 租车维保（vehicle_asset / cost_monthly / city_factor / disposal）
-- 辅表：Getaround 定价与租赁活动（定价模型 & 利用率分析）

CREATE TABLE IF NOT EXISTS data_source (
    id              INTEGER PRIMARY KEY,
    table_name      TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    loaded_at       TEXT NOT NULL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS vehicle_asset (
    vehicle_id      TEXT PRIMARY KEY,       -- Zenodo CARID
    brand           TEXT NOT NULL,
    model           TEXT NOT NULL,
    segment         TEXT NOT NULL,
    fuel_type       TEXT NOT NULL,
    model_year      INTEGER NOT NULL,
    city_id         INTEGER NOT NULL,
    purchase_price  REAL NOT NULL,          -- USD，Segment MSRP + Year 调整
    purchase_date   TEXT NOT NULL,          -- 推算入库日（首条维保日 - 30 天）
    data_source     TEXT NOT NULL DEFAULT 'zenodo'
);

CREATE TABLE IF NOT EXISTS cost_monthly (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id      TEXT NOT NULL,
    month           TEXT NOT NULL,          -- YYYY-MM
    depreciation    REAL NOT NULL,          -- 直线折旧（USD）
    insurance       REAL NOT NULL,          -- Segment 行业均值（USD）
    maintenance     REAL NOT NULL,          -- Zenodo 真实发票汇总（USD）
    parking         REAL NOT NULL,          -- 城市 tier 均值（USD）
    data_source     TEXT NOT NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicle_asset(vehicle_id),
    UNIQUE (vehicle_id, month)
);

CREATE TABLE IF NOT EXISTS city_factor (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id             INTEGER NOT NULL,
    month               TEXT NOT NULL,
    fleet_size          INTEGER NOT NULL,       -- 该月活跃车辆数
    avg_maintenance     REAL NOT NULL,          -- 月人均维保（USD，真实）
    competitor_avg_rent REAL NOT NULL,          -- Getaround 全球中位日租 × 30（USD）
    demand_index        REAL NOT NULL,          -- 相对全网均值的标准化需求
    data_source         TEXT NOT NULL,
    UNIQUE (city_id, month)
);

CREATE TABLE IF NOT EXISTS disposal (
    vehicle_id      TEXT PRIMARY KEY,
    disposal_date   TEXT NOT NULL,          -- 末次维保日
    residual_value  REAL NOT NULL,          -- 采购价 × 残值率（USD）
    data_source     TEXT NOT NULL DEFAULT 'zenodo',
    FOREIGN KEY (vehicle_id) REFERENCES vehicle_asset(vehicle_id)
);

-- Getaround 定价清单（4843 辆，含真实日租金）
CREATE TABLE IF NOT EXISTS getaround_pricing (
    listing_id              INTEGER PRIMARY KEY,
    model_key               TEXT NOT NULL,
    mileage                 REAL,
    engine_power            REAL,
    fuel                    TEXT,
    paint_color             TEXT,
    car_type                TEXT,
    rental_price_per_day    REAL NOT NULL,  -- EUR-ish unit from dataset
    data_source             TEXT NOT NULL DEFAULT 'getaround'
);

-- Getaround 租赁活动（21310 条，无起止日期，保留真实 state / delay）
CREATE TABLE IF NOT EXISTS getaround_rental_activity (
    rental_id                               INTEGER PRIMARY KEY,
    car_id                                  INTEGER NOT NULL,
    checkin_type                            TEXT,
    state                                   TEXT NOT NULL,
    delay_at_checkout_in_minutes            REAL,
    previous_ended_rental_id                REAL,
    time_delta_with_previous_rental_minutes REAL,
    data_source                             TEXT NOT NULL DEFAULT 'getaround'
);

-- 按 Segment 聚合的 Getaround 租金基准（用于 Zenodo fleet 收益敏感性分析）
CREATE TABLE IF NOT EXISTS segment_rent_benchmark (
    segment                 TEXT PRIMARY KEY,
    median_daily_rent       REAL NOT NULL,
    median_monthly_rent     REAL NOT NULL,  -- daily × 30
    sample_size             INTEGER NOT NULL,
    mapping_note            TEXT NOT NULL,
    data_source             TEXT NOT NULL DEFAULT 'getaround'
);
