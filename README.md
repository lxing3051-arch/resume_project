# 租赁车辆资产分析

本仓库包含两条相互衔接的车辆资产分析流程：

- [项目 A：资产收益测算与租金定价](project_a/)：构建资产、成本与定价数据层，完成 TCO、盈利能力和定价模型分析。
- [项目 B：资产分层与退网预警](project_b/)：复用项目 A 的车辆月度活动数据，完成资产分层、风险评分和运营优先级排序。

## 分析链路

```text
公开数据与业务参数
        ↓
数据清洗、口径统一与 SQLite 建模
        ↓
TCO / 盈利能力 / 定价因子 / 定价模型
        ↓
RFM 资产分层 / 聚类验证 / 退网风险评分
        ↓
管理摘要、运营清单与监控指标
```

## 数据来源

核心数据来自 Zenodo 租车维保数据与 Getaround 公开定价、租赁活动数据。采购价、折旧、保险、停车和利用率等缺失字段采用显式配置的情景参数，不与原始观测字段混用。完整血缘与口径见：

- [公开数据源与参数说明](docs/公开数据源说明.md)
- [项目 A 数据模型](docs/项目A-数据说明.md)
- [资产收益测算方案](docs/项目A-资产收益测算方案.md)

## 运行顺序

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r project_a/requirements.txt

python project_a/src/load_public_data.py
python project_a/src/step2_profitability.py
python project_a/src/step3_pricing_factors.py
python project_a/src/step4_pricing_model.py
python project_a/src/step5_report.py

python project_b/src/build_features.py
python project_b/src/rfm_segmentation.py
python project_b/src/churn_model.py
python project_b/src/step4_report.py
```

## 主要交付物

| 模块 | 交付物 |
|---|---|
| 项目 A | Segment/城市盈利表、成本结构、定价因子、模型对比、管理摘要 |
| 项目 B | 车辆 RFM 特征、资产标签、聚类画像、风险名单、提升度分析、管理摘要 |

## 使用边界

本仓库用于公开数据条件下的方法验证与决策框架演示。跨数据集结果仅在 Segment 层做基准桥接，不进行车辆级关联；涉及收入和固定成本的结论属于情景测算，正式经营决策需替换为同市场、同币种、同期间的内部业务数据。
