"""汇总项目 B 的分层、模型和运营优先级结果。"""

from __future__ import annotations

import pandas as pd

from config import (
    N_CLUSTERS,
    OBSERVE_END,
    OBSERVE_START,
    OUTCOME_END,
    OUTCOME_START,
    OUTPUT_DIR,
)

DOCS_DIR = OUTPUT_DIR.parent.parent / "docs"


def load(name: str) -> pd.DataFrame:
    """读取分析阶段产出的汇总表。"""
    return pd.read_csv(OUTPUT_DIR / name)


def build_report() -> str:
    """根据最新计算结果生成资产风险管理摘要。"""
    features = load("b_step1_asset_rfm_features.csv")
    tiers = load("b_step2_tier_profile.csv")
    clusters = load("b_step2_cluster_profile.csv")
    metrics = load("b_step3_model_metrics.csv")
    lift = load("b_step3_decile_lift.csv")
    importance = load("b_step3_permutation_importance.csv")

    n_vehicles = len(features)
    churn_rate = features["churned"].mean()
    best_model = metrics.iloc[0]
    top_decile = lift.iloc[0]
    top3_capture = lift.head(3)["cum_capture_rate"].iloc[-1]
    highest_risk_tier = tiers.iloc[0]
    lowest_risk_tier = tiers.iloc[-1]
    highest_risk_cluster = clusters.iloc[0]

    tier_rows = "\n".join(
        f"| {row['asset_tier']} | {int(row['vehicle_cnt']):,} | {row['avg_recency']:.1f} | "
        f"{row['avg_frequency']:.2f} | {row['avg_monetary']:,.0f} | {row['churn_rate']:.1%} |"
        for _, row in tiers.iterrows()
    )
    metric_rows = "\n".join(
        f"| {row['feature_set']} | {row['model']} | {row['AUC']:.3f} | "
        f"{row['Precision']:.3f} | {row['Recall']:.3f} | {row['F1']:.3f} |"
        for _, row in metrics.iterrows()
    )
    importance_rows = "\n".join(
        f"| {row['feature']} | {row['auc_drop']:.4f} |"
        for _, row in importance.head(8).iterrows()
    )

    return f"""# 车辆资产分层与退网预警：管理摘要

## 执行摘要

观察期内共有 **{n_vehicles:,}** 辆活跃车辆，预测期退网代理标签比例为
**{churn_rate:.1%}**。规则分层最高与最低风险组之间相差
**{(highest_risk_tier['churn_rate'] - lowest_risk_tier['churn_rate']):.1%}**。
最优模型为 **{best_model['feature_set']} / {best_model['model']}**，AUC 为
**{best_model['AUC']:.3f}**；风险排序前 30% 覆盖 **{top3_capture:.1%}** 的实际退网车辆。

## 数据与标签设计

```text
观察期 {OBSERVE_START} 至 {OBSERVE_END}：构造 RFM 与趋势特征
预测期 {OUTCOME_START} 至 {OUTCOME_END}：无维保活动定义为退网代理标签
```

`disposal` 表不参与标签构造，因为其定义依赖末次维保时间，与 Recency 同源，直接使用会造成定义性泄露。

## 资产分层

| 资产标签 | 车辆数 | Recency | Frequency | Monetary | 退网率 |
|---|---:|---:|---:|---:|---:|
{tier_rows}

K-Means 使用 k={N_CLUSTERS}。最高风险簇为 cluster
{int(highest_risk_cluster['cluster'])}，退网率 {highest_risk_cluster['churn_rate']:.1%}。
聚类用于检验规则分层的方向稳定性，不直接替代运营标签。

## 模型表现

| 特征集 | 模型 | AUC | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
{metric_rows}

最高风险 10% 车辆的实际退网率为 {top_decile['churn_rate']:.1%}，
相对总体基线提升 {top_decile['lift']:.2f} 倍。风险概率用于排序和资源分配，不解释为校准后的绝对退网概率。

## 主要特征

| 特征 | 打乱后 AUC 下降 |
|---|---:|
{importance_rows}

## 建议动作

1. 优先核查“{highest_risk_tier['asset_tier']}”车辆，区分调度、车况、合同和外部维修原因。
2. 每月刷新车辆风险分位，先覆盖最高风险 30%，并记录核查结果、处置动作和回收收益。
3. 将风险名单与里程、租约、故障工单和残值连接，建立可追踪的干预闭环。
4. 通过增量实验评估风险干预效果，避免仅用离线 AUC 评价业务价值。

## 口径与限制

- Monetary 为维保投入代理，不等同于收入贡献或资产价值。
- 无维保活动为退网代理标签，可能包含长期闲置或外部维修车辆。
- 当前模型区分能力有限，适合运营排序，不支持自动处置决策。
"""


def main() -> None:
    report = build_report()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    doc_path = DOCS_DIR / "step4-项目B结论与建议.md"
    output_path = OUTPUT_DIR / "b_step4_executive_summary.md"
    doc_path.write_text(report, encoding="utf-8")
    output_path.write_text(report, encoding="utf-8")
    print(f"报告已生成:\n  {doc_path}\n  {output_path}")


if __name__ == "__main__":
    main()
