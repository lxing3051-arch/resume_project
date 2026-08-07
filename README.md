# 秋招项目 · 地上铁商业分析（资产运营方向）

## 简历项目

| 项目 | 对齐 JD | 状态 |
|------|---------|------|
| [项目 A：资产收益测算与动态租金定价](project_a/) | 岗位职责 1（TCO、盈利复盘、动态定价） | 五步完成 |
| [项目 B：资产价值分层与退网预警](project_b/) | 岗位职责 2（RFM、聚类、流失预警） | 四步完成 |

## 文档

| 文件 | 说明 |
|------|------|
| [地上铁-商业分析专员-岗位解读与概念说明.md](docs/地上铁-商业分析专员-岗位解读与概念说明.md) | JD 解读 + 概念详解 |
| [项目A-资产收益测算方案.md](docs/项目A-资产收益测算方案.md) | 项目 A 方案与步骤 |
| [项目A-数据说明.md](docs/项目A-数据说明.md) | **表结构、字段口径、ER 图、数据逻辑** |
| [公开数据源说明.md](docs/公开数据源说明.md) | 公开数据集下载与加载 |
| [项目A · Step 5 结论与运营建议](project_a/docs/step5-结论与运营建议.md) | **面试 / 简历主文档** |
| [项目B · 资产分层与退网预警](project_b/docs/项目B-资产分层与退网预警.md) | 项目 B 方案与分层结论 |
| [项目B · Step 4 结论与建议](project_b/docs/step4-项目B结论与建议.md) | **面试 / 简历主文档** |

## 快速开始

```bash
# 项目 A：先跑 ETL 建库（项目 B 复用该库）
cd project_a
pip install -r requirements.txt
python src/load_public_data.py
python src/step2_profitability.py
python src/step3_pricing_factors.py
python src/step4_pricing_model.py
python src/step5_report.py

# 项目 B
cd ../project_b
python src/build_features.py
python src/rfm_segmentation.py
python src/churn_model.py
python src/step4_report.py
```
