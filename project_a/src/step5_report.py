"""
Step 5：汇总结论、运营建议与面试材料
读取 Step 2/3/4 输出，生成 executive summary Markdown
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
DOCS_DIR = ROOT / "docs"


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / name)


def build_report() -> str:
    seg = load_csv("step2_segment_profitability.csv")
    city = load_csv("step2_city_profitability.csv")
    metrics = load_csv("step4_model_metrics.csv")
    car_type = load_csv("step3_factor_car_type.csv")

    best_seg = seg.loc[seg["avg_est_profit"].idxmax()]
    worst_seg = seg.loc[seg["avg_est_profit"].idxmin()]
    best_city = city.loc[city["avg_est_profit"].idxmax()]
    worst_city = city.loc[city["avg_est_profit"].idxmin()]
    base = metrics[metrics["model"] == "Baseline"].iloc[0]
    ridge = metrics[metrics["model"] == "Ridge"].iloc[0]
    mape_improve = round(base["MAPE_pct"] - ridge["MAPE_pct"], 2)
    mape_improve_pct = round(mape_improve / base["MAPE_pct"] * 100, 1)

    return f"""# 项目 A · 结论与运营建议（Step 5）

> 自动生成于 Step 2/3/4 输出汇总 | 地上铁商业分析（资产运营方向）

---

## 一、30 秒项目介绍（面试开场）

> 基于 Zenodo 国际租车维保公开数据（3 万辆、24 万+ 发票）与 Getaround 定价数据，搭建租赁资产 **TCO 测算 → 盈利复盘 → 动态定价** 分析框架。完成分 Segment/分城市成本复盘，识别 Segment E 估算亏损；构建 Ridge 定价模型，较 car_type 规则定价 **MAPE 降低 {mape_improve_pct}%**（{base['MAPE_pct']}%→{ridge['MAPE_pct']}%），R²={ridge['R2']}。

---

## 二、核心发现

### 2.1 资产成本与盈利（Step 2）

| Segment | 月均 TCO (USD) | 估算月利润 | 利润率 |
|---------|----------------|------------|--------|
| C | {best_seg['avg_total_cost']} | **+{best_seg['avg_est_profit']}** | {best_seg['profit_margin']:.1%} |
| B | {seg[seg['segment']=='B']['avg_total_cost'].values[0]} | +{seg[seg['segment']=='B']['avg_est_profit'].values[0]} | {seg[seg['segment']=='B']['profit_margin'].values[0]:.1%} |
| E | {worst_seg['avg_total_cost']} | **{worst_seg['avg_est_profit']}** | {worst_seg['profit_margin']:.1%} |

- **最赚 Segment**：{best_seg['segment']}（利润率 {best_seg['profit_margin']:.1%}）
- **亏损 Segment**：{worst_seg['segment']}（估算月利润 {worst_seg['avg_est_profit']} USD）
- **成本结构**：维保（真实发票）> 折旧 > 保险+停车
- **城市**：City {int(best_city['city_id'])} 盈利最好（+{best_city['avg_est_profit']:.0f}），City {int(worst_city['city_id'])} 最差（{worst_city['avg_est_profit']:.0f}）

### 2.2 定价因子（Step 3）

- **engine_power** 与租金正相关最强（+0.64）
- **log_mileage** 负相关（−0.40）：里程越高租金越低
- **car_type**：coupe/suv 中位租金最高（151/133 USD/天），subcompact 最低（96）

### 2.3 定价模型（Step 4）

| 模型 | MAPE | RMSE | R² |
|------|------|------|-----|
| Baseline | {base['MAPE_pct']}% | {base['RMSE']} | {base['R2']} |
| Ridge | **{ridge['MAPE_pct']}%** | **{ridge['RMSE']}** | **{ridge['R2']}** |

---

## 三、三条运营建议

### 建议 1：Segment E 资产提质增效

**问题**：Segment E 估算月利润 {worst_seg['avg_est_profit']} USD，TCO（{worst_seg['avg_total_cost']:.0f}）高于租金覆盖能力。

**动作**：
- 审计高维保 outliers 车辆，评估退网/置换
- 对 Segment E 上调日租金或降低投放比例
- 优先将资源转向 Segment C（利润率 {best_seg['profit_margin']:.1%}）

### 建议 2：分城市差异化运维

**问题**：City {int(worst_city['city_id'])} 估算月利润 {worst_city['avg_est_profit']:.0f} USD，City {int(best_city['city_id'])} 为 +{best_city['avg_est_profit']:.0f} USD。

**动作**：
- 高成本城市：收紧维保预算、优化停车 tier
- 高盈利城市：适度扩 fleet，复制 Segment C 车型结构

### 建议 3：落地动态定价模型

**问题**：规则定价（car_type 中位数）MAPE {base['MAPE_pct']}%，无法反映里程、配置差异。

**动作**：
- 上线 Ridge 模型，按 engine_power / log_mileage / 配置项调价
- 高里程车自动降价，高配置车（GPS/自动挡）适度溢价
- 预期 MAPE 降至 ~{ridge['MAPE_pct']}%

---

## 四、简历描述（可直接粘贴）

**新能源租赁车辆资产收益测算与动态定价分析** | Python / SQL / sklearn

- 基于 Zenodo、Getaround 公开数据，搭建覆盖 3 万辆、67 城的租赁资产 TCO 测算框架（折旧/维保/保险/残值 6 类口径）
- 完成分 Segment/分城市盈利复盘，识别 Segment E 估算亏损，Segment C 利润率 29.4%
- 分析 engine_power、log_mileage、car_type 等定价因子，构建 Ridge 动态租金模型
- 较 car_type 规则定价 MAPE 降低 {mape_improve_pct}%（27.9%→18.4%），测试集 R²=0.64

---

## 五、面试高频追问

| 问题 | 回答要点 |
|------|----------|
| 数据是真实的吗？ | 维保/租金来自公开数据集；采购价/折旧/保险为公开行业参数，已标注 |
| 为什么只有 city_id？ | Zenodo 原始数据无城市名，用编号分析；可扩展 dim_city |
| Step 2 收入怎么估的？ | Getaround Segment 租金中位数 × 65% 利用率 |
| 为什么选 Ridge？ | 可解释、防过拟合，对齐 JD 回归分析要求 |
| 模型怎么验证？ | 80/20 hold-out，对比 Baseline MAPE/RMSE |

---

## 六、局限与改进

1. 两数据集无法车级关联 → 后续有内部数据可统一 ID
2. 国内 NEV 场景 → 框架可迁移，换 NDANEV 数据源
3. Step 4 可试 XGBoost / 分城市分模型 → 作 sensitivity

---

*项目 A 五步完成。*
"""


def main() -> None:
    report = build_report()
    out_md = DOCS_DIR / "step5-结论与运营建议.md"
    out_md.write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "step5_executive_summary.md").write_text(report, encoding="utf-8")
    print(f"报告已生成:\n  {out_md}\n  {OUTPUT_DIR / 'step5_executive_summary.md'}")


if __name__ == "__main__":
    main()
