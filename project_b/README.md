# 项目 B：车辆资产分层与退网预警

项目 B 复用项目 A 的车辆月度维保活动数据，建立资产活跃度分层和退网风险评分流程。输出面向车队盘点、调拨、维保资源配置与处置优先级管理。

## 业务目标

- 将车辆月度活动压缩为可解释的 RFM 与趋势特征。
- 用规则分层和 K-Means 聚类识别差异化资产画像。
- 在独立预测窗口定义退网代理标签，降低时间泄露风险。
- 生成车辆级风险名单，并用 Lift 与累计捕获率衡量运营筛选效率。

## 时间窗口

```text
观察期 2021-01 至 2022-06：构造 RFM 与趋势特征
预测期 2022-07 至 2023-02：以无维保活动定义退网代理标签
```

`disposal` 表由末次维保日期派生，不直接作为训练标签，避免 Recency 与标签之间的定义性泄露。

## 分析流程

项目 B 依赖 `project_a/data/greenlease.db`，需先运行项目 A 的 ETL。

```bash
python project_b/src/build_features.py
python project_b/src/rfm_segmentation.py
python project_b/src/churn_model.py
python project_b/src/step4_report.py
```

1. `build_features.py`：生成车辆级 RFM、趋势特征和预测期标签。
2. `rfm_segmentation.py`：形成规则分层、K-Means 聚类与画像汇总。
3. `churn_model.py`：比较多组特征和模型，输出概率、风险分位与重要性。
4. `step4_report.py`：汇总模型表现、运营优先级和数据限制。

## 核心口径

| 指标 | 定义 |
|---|---|
| Recency | 观察期末距末次活跃月的月数 |
| Frequency | 观察期内有维保活动的月份数 |
| Monetary | 观察期累计维保金额，代表资产投入强度 |
| 退网代理标签 | 预测期内无维保活动 |
| 累计捕获率 | 风险排序前若干分位覆盖的实际退网车辆比例 |

## 主要输出

- `data/output/b_step2_tier_profile.csv`
- `data/output/b_step2_cluster_profile.csv`
- `data/output/b_step3_model_metrics.csv`
- `data/output/b_step3_decile_lift.csv`
- `data/output/b_step3_permutation_importance.csv`
- `data/output/b_step4_executive_summary.md`

## 分析边界

- Monetary 为维保投入代理，不等同于资产收入或价值贡献。
- 预测期无活动是退网代理标签，可能包含长期闲置或外部维修车辆。
- 风险模型用于排序而非自动处置；正式运营需叠加合同、里程、故障工单和残值信息。
