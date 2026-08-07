"""
项目 B Step 4：汇总结论、运营建议与简历/面试材料
读取 Step 1~3 输出，生成 Markdown 报告
"""

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
    return pd.read_csv(OUTPUT_DIR / name)


def build_report() -> str:
    features = load("b_step1_asset_rfm_features.csv")
    tier = load("b_step2_tier_profile.csv")
    cluster = load("b_step2_cluster_profile.csv")
    metrics = load("b_step3_model_metrics.csv")
    lift = load("b_step3_decile_lift.csv")
    imp = load("b_step3_permutation_importance.csv")

    n_vehicles = len(features)
    churn_rate = features["churned"].mean()

    best = metrics.iloc[0]
    base_auc = metrics[metrics["feature_set"] == "RFM_only"]["AUC"].max()
    trend_auc = metrics[metrics["feature_set"] == "RFM_plus_trend"]["AUC"].max()

    top1 = lift.iloc[0]
    top3_capture = lift.head(3)["cum_capture_rate"].iloc[-1]

    worst_tier = tier.iloc[0]
    best_tier = tier.iloc[-1]
    worst_cluster = cluster.iloc[0]

    tier_rows = "\n".join(
        f"| {r['asset_tier']} | {int(r['vehicle_cnt']):,} | {r['avg_recency']:.1f} | "
        f"{r['avg_frequency']:.2f} | {r['avg_monetary']:,.0f} | **{r['churn_rate']:.1%}** |"
        for _, r in tier.iterrows()
    )
    metric_rows = "\n".join(
        f"| {r['feature_set']} | {r['model']} | {r['AUC']} | {r['Precision']} | "
        f"{r['Recall']} | {r['F1']} |"
        for _, r in metrics.iterrows()
    )
    lift_rows = "\n".join(
        f"| {int(r['decile'])} | {int(r['vehicles'])} | {r['churn_rate']:.1%} | "
        f"{r['lift']:.2f} | {r['cum_capture_rate']:.1%} |"
        for _, r in lift.iterrows()
    )
    imp_rows = "\n".join(
        f"| {r['feature']} | {r['auc_drop']:.4f} |" for _, r in imp.head(6).iterrows()
    )

    return f"""# 项目 B · 结论与运营建议（Step 4）

> 自动生成于 Step 1~3 输出汇总 | 对齐地上铁 JD 岗位职责 2

---

## 一、30 秒项目介绍（面试开场）

> 基于 Zenodo 国际租车公开数据，对 **{n_vehicles:,} 辆在运营车辆** 做资产价值分层与退网预警。
> 采用观察期/预测期分离设计避免标签泄露，用 RFM + K-Means 输出 4 类资产画像，
> 分层间退网率差异达 **{(worst_tier['churn_rate'] - best_tier['churn_rate']) * 100:.0f} 个百分点**；
> 训练梯度提升/随机森林预警模型，**风险最高 30% 的名单覆盖 {top3_capture:.0%} 的实际退网车**，
> 可直接作为运营月度盘点的干预清单。

---

## 二、方法设计

### 2.1 时间窗口（核心方法点）

```
观察期 {OBSERVE_START} ~ {OBSERVE_END}  ->  构造 RFM 与趋势特征
预测期 {OUTCOME_START} ~ {OUTCOME_END}  ->  无运营活动即判定退网(churned=1)
```

**为什么不用项目 A 的 `disposal` 表当标签？**
该表定义为「末次维保早于 2022-01-01」，本身由 Recency 决定。
若同时把 Recency 当特征，会造成标签泄露、指标虚高。观察期/预测期分离是流失建模的标准做法。

### 2.2 分析主体的迁移

JD 写的是「客户价值分层」「流失预警」，公开数据无客户 ID。
本项目把主体换成**车辆资产**，方法论完全一致，且更贴合岗位的资产运营方向。

---

## 三、核心发现

### 3.1 样本与基线

| 指标 | 数值 |
|------|------|
| 观察期活跃车辆 | {n_vehicles:,} 辆 |
| 退网率（基线） | **{churn_rate:.1%}** |

### 3.2 资产价值分层（RFM 规则）

| 资产标签 | 车辆数 | 平均 Recency | 平均 Frequency | 平均 Monetary | 退网率 |
|----------|--------|--------------|----------------|---------------|--------|
{tier_rows}

- 最高风险分层：**{worst_tier['asset_tier']}**（{int(worst_tier['vehicle_cnt']):,} 辆，退网率 {worst_tier['churn_rate']:.1%}）
- 最低风险分层：**{best_tier['asset_tier']}**（退网率 {best_tier['churn_rate']:.1%}）

### 3.3 K-Means 交叉验证

k={N_CLUSTERS}。聚类结果与规则分层方向一致——Recency 高、Frequency 低的簇退网率最高
（cluster {int(worst_cluster['cluster'])}：{worst_cluster['churn_rate']:.1%}），
说明规则分层的业务边界合理，不是主观拍脑袋。

### 3.4 退网预警模型

| 特征集 | 模型 | AUC | 精准率 | 召回率 | F1 |
|--------|------|-----|--------|--------|-----|
{metric_rows}

最优组合：**{best['feature_set']} | {best['model']}**（AUC={best['AUC']}）

**一个诚实的负向结论：** 追加 9 个时序趋势特征后，AUC 从 {base_auc} 变为 {trend_auc}，
**没有实质提升**。说明该数据集下退网主要由 Recency/Frequency 主导，
要进一步提升需要引入里程、合同、车况等更丰富的数据，而非继续在现有字段上做衍生。

### 3.5 特征重要性（打乱后 AUC 下降）

| 特征 | AUC 下降 |
|------|----------|
{imp_rows}

### 3.6 十分位提升表（业务可用性）

| 风险分位 | 车辆数 | 实际退网率 | 提升度 | 累计捕获率 |
|----------|--------|------------|--------|------------|
{lift_rows}

**业务含义：** 最高风险 10% 的车辆实际退网率 {top1['churn_rate']:.1%}，
是整体基线的 **{top1['lift']:.2f} 倍**；只看前 30% 名单就能覆盖 {top3_capture:.0%} 的退网车。
在运营资源有限时，这就是「该先看哪几千辆车」的答案。

---

## 四、三条运营建议

### 建议 1：优先干预「{worst_tier['asset_tier']}」（{int(worst_tier['vehicle_cnt']):,} 辆）

维保投入不低但已长期不活跃，退网率 {worst_tier['churn_rate']:.1%}。
**动作**：逐台核查是调度问题还是车况问题；可调拨至高需求城市，或提前处置锁定残值。

### 建议 2：用模型输出月度预警名单，而非全量盘点

**动作**：每月对全车队打分，取风险最高 30%（当前样本约 {int(n_vehicles * 0.3):,} 辆）
交运营跟进，可覆盖约 {top3_capture:.0%} 的潜在退网，显著优于随机抽查。

### 建议 3：补齐数据字段以提升模型上限

当前 AUC 约 {best['AUC']}，趋势特征已证明无增量。
**动作**：接入里程、租约状态、故障工单等字段后重训，预期才有实质提升。

---

## 五、简历描述（可直接粘贴）

**租赁资产价值分层与退网预警** | Python / SQL / scikit-learn

- 基于 Zenodo 国际租车公开数据，对 {n_vehicles:,} 辆在运营车辆构建 RFM 特征体系，
  采用观察期/预测期分离设计规避标签泄露
- 用 RFM 规则打分 + K-Means 聚类输出 4 类资产画像，分层间退网率差异达
  {(worst_tier['churn_rate'] - best_tier['churn_rate']) * 100:.0f} 个百分点，两套方法交叉验证一致
- 对比 Logistic / 随机森林 / 梯度提升三类模型与两套特征集，最优 AUC {best['AUC']}；
  风险最高 30% 名单覆盖 {top3_capture:.0%} 实际退网车，可作为运营月度干预清单
- 通过特征工程对照实验验证趋势特征无增量，据此提出补齐里程与租约数据的改进方向

---

## 六、面试高频追问

| 问题 | 回答要点 |
|------|----------|
| 为什么用资产而不是客户做 RFM？ | 公开数据无客户 ID；方法论一致，可直接迁移到客户维度 |
| 怎么避免标签泄露？ | 观察期构造特征、预测期定义标签，两段时间不重叠 |
| AUC 只有 {best['AUC']}，是不是模型不行？ | 基线退网率 49%，模型头部十分位提升 {top1['lift']:.2f} 倍，业务上可用；已定位瓶颈在数据字段而非算法 |
| 为什么保留没有提升的趋势特征？ | 作为对照实验保留，用于说明改进方向，避免后续重复试错 |
| 分层怎么落地？ | 输出车辆级标签与风险分表，可接入运营看板按月刷新 |
| K-Means 的 k 怎么选？ | 取 k={N_CLUSTERS} 与规则分层对齐便于业务解释，并用 silhouette 校验 |

---

## 七、局限

1. Monetary 用维保金额代理资产投入，有内部租金数据时应替换为收入贡献
2. 「退网」以预测期无维保活动定义，可能混入长期闲置但未处置的车辆
3. 模型 AUC 上限受限于可用字段，需补齐里程/租约/工单数据

---

*项目 B 四步完成。*
"""


def main() -> None:
    report = build_report()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_md = DOCS_DIR / "step4-项目B结论与建议.md"
    out_md.write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "b_step4_executive_summary.md").write_text(report, encoding="utf-8")
    print(f"报告已生成:\n  {out_md}\n  {OUTPUT_DIR / 'b_step4_executive_summary.md'}")


if __name__ == "__main__":
    main()
