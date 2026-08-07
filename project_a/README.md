# 项目 A：新能源租赁车辆资产收益测算与动态租金定价

**数据版本：公开数据集**（Zenodo 租车维保 + Getaround 定价/租赁活动）

## 快速开始

```bash
cd project_a
pip install -r requirements.txt
python src/load_public_data.py
```

运行后在 `data/greenlease.db` 生成 SQLite 数据库（约 1～2 分钟）。

## 数据来源

| 表 | 来源 | 说明 |
|----|------|------|
| `vehicle_asset` | Zenodo | 约 3 万辆，真实 CARID / 城市 / 车型 |
| `cost_monthly` | Zenodo + 公开参数 | **维保=真实发票**；折旧/保险/停车=行业假设 |
| `city_factor` | Zenodo + Getaround | 城市 fleet 真实；竞品租金=Getaround 中位数 |
| `disposal` | Zenodo | 末次维保早于 2022 的车辆 |
| `getaround_pricing` | Getaround | 4843 条真实日租金 |
| `getaround_rental_activity` | Getaround | 21310 条租赁活动 |
| `segment_rent_benchmark` | Getaround | Segment 级租金基准（桥接两数据集） |

详细说明见 [项目A-数据说明.md](../docs/项目A-数据说明.md) 与 [公开数据源说明.md](../docs/公开数据源说明.md)。

## 文档

- [项目 A 数据说明（表结构 / ER 图 / 字段口径）](../docs/项目A-数据说明.md)
- [Step 5 结论与运营建议（面试/简历）](docs/step5-结论与运营建议.md)
- [岗位解读与概念说明](../docs/地上铁-商业分析专员-岗位解读与概念说明.md)
- [项目 A 完整方案](../docs/项目A-资产收益测算方案.md)
- [公开数据源说明](../docs/公开数据源说明.md)

## 当前进度

- [x] Step 1：公开数据 ETL 入库
- [x] Step 2：TCO 与盈利复盘（SQL + Python）
- [x] Step 3：定价因子分析
- [x] Step 4：回归定价模型
- [x] Step 5：结论与运营建议

## 原始数据

需先存在于 `data/raw/`（已下载可跳过）：

- `car_maintenance_clean.xlsx` — [Zenodo](https://zenodo.org/records/7937227)
- `get_around_pricing_project.csv` — [AWS S3](https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_pricing_project.csv)
- `get_around_delay_analysis.xlsx` — [AWS S3](https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_delay_analysis.xlsx)
