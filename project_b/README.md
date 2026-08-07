# 项目 B：租赁资产价值分层与退网预警

对齐地上铁 JD **岗位职责 2**：客户价值分层、聚类 / RFM、流失预警模型的特征筛选。

## 选题说明

JD 原文说的是「客户价值分层」「流失预警」。公开数据里没有客户 ID，但**分析方法完全一致**，
本项目把分析对象从「客户」换成「车辆资产」，更贴合岗位的**资产运营方向**：

| JD 关键词 | 项目 B 对应 |
|-----------|-------------|
| 客户价值分层 | 资产价值分层（RFM + K-Means） |
| 聚类 / RFM | R=距末次活跃月数，F=活跃月份数，M=累计维保投入 |
| 客户画像标签 | 资产画像标签（4 类） |
| 流失预警模型的特征筛选 | 退网（churn）预警：预测期内是否仍有运营活动 |

面试话术：「方法论与客户 RFM 一致，只是分析主体换成资产，可直接迁移到客户维度。」

## 快速开始

```bash
cd project_b
python src/build_features.py      # Step 1：RFM + 趋势特征表
python src/rfm_segmentation.py    # Step 2：分层 + 聚类
python src/churn_model.py         # Step 3：退网预警模型
python src/step4_report.py        # Step 4：结论报告
```

数据复用 `../project_a/data/greenlease.db`，需先跑完项目 A 的 ETL。

## 时间窗口设计（关键方法点）

```
观察期 2021-01 ~ 2022-06  ->  构造 RFM 特征
预测期 2022-07 ~ 2023-02  ->  是否仍有活动，定义 churned 标签
```

**为什么这样切？** 项目 A 的 `disposal` 表是按「末次维保早于 2022」定义的，
若直接拿它当标签、又用 Recency 当特征，会造成**标签泄露**（特征本身就决定了标签）。
改用观察期 / 预测期分离，是流失建模的标准做法。

## 当前进度

- [x] Step 1：RFM + 趋势特征表（21,569 辆，churn rate 49.0%）
- [x] Step 2：RFM 分层 + K-Means 聚类（分层间退网率差 22 pct-pts）
- [x] Step 3：退网预警模型（最优 AUC 0.650，top30% 覆盖 40% 退网车）
- [x] Step 4：结论与运营建议

## 输出文件

| 文件 | 内容 |
|------|------|
| `data/output/b_step1_asset_rfm_features.csv` | 车辆级 RFM + 趋势特征 + churn 标签 |
| `data/output/b_step2_asset_segments.csv` | 含 RFM 分数、资产标签、聚类编号 |
| `data/output/b_step2_tier_profile.csv` | 规则分层画像 |
| `data/output/b_step2_cluster_profile.csv` | K-Means 画像 |
| `data/output/b_step2_segmentation.png` | 分层可视化 |
| `data/output/b_step3_model_metrics.csv` | 特征集 × 模型 对比 |
| `data/output/b_step3_decile_lift.csv` | 十分位提升表 |
| `data/output/b_step3_permutation_importance.csv` | 特征重要性 |
| `data/output/b_step3_risk_scored_vehicles.csv` | 车辆级退网风险名单 |
| `data/output/b_step3_churn_model.png` | ROC + 提升度 + 重要性 |

## 文档

- [项目 B 方案与分层结论](docs/项目B-资产分层与退网预警.md)
- [Step 4 结论与运营建议（面试 / 简历主文档）](docs/step4-项目B结论与建议.md)
