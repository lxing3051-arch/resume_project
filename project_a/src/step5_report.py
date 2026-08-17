"""汇总项目 A 的分析结果并生成管理摘要。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
DOCS_DIR = ROOT / "docs"


def load_csv(name: str) -> pd.DataFrame:
    """读取分析阶段产出的汇总表。"""
    return pd.read_csv(OUTPUT_DIR / name)


def build_report() -> str:
    """根据最新计算结果生成面向经营决策的 Markdown 摘要。"""
    seg = load_csv("step2_segment_profitability.csv")
    city = load_csv("step2_city_profitability.csv")
    metrics = load_csv("step4_model_metrics.csv")

    best_seg = seg.loc[seg["avg_est_profit"].idxmax()]
    worst_seg = seg.loc[seg["avg_est_profit"].idxmin()]
    best_city = city.loc[city["avg_est_profit"].idxmax()]
    worst_city = city.loc[city["avg_est_profit"].idxmin()]
    baseline = metrics.loc[metrics["model"] == "Baseline"].iloc[0]
    ridge = metrics.loc[metrics["model"] == "Ridge"].iloc[0]
    mape_drop = baseline["MAPE_pct"] - ridge["MAPE_pct"]
    relative_drop = mape_drop / baseline["MAPE_pct"]

    segment_rows = "\n".join(
        f"| {row['segment']} | {row['vehicle_cnt']:,.0f} | "
        f"{row['avg_total_cost']:,.2f} | {row['avg_est_profit']:,.2f} | "
        f"{row['profit_margin']:.1%} |"
        for _, row in seg.sort_values("avg_est_profit", ascending=False).iterrows()
    )

    return f"""# 车辆资产收益与定价分析：管理摘要

## 执行摘要

公开维保与租金数据被整合为车辆资产、月度成本和定价分析层。情景测算显示，
Segment **{best_seg['segment']}** 的平均利润率最高（{best_seg['profit_margin']:.1%}），
Segment **{worst_seg['segment']}** 的平均月利润最低（{worst_seg['avg_est_profit']:,.2f} USD）。
Ridge 定价模型的测试集 MAPE 为 **{ridge['MAPE_pct']:.2f}%**，较车型中位数基线
下降 **{mape_drop:.2f} 个百分点**（相对下降 {relative_drop:.1%}）。

## 资产盈利能力

| Segment | 车辆数 | 平均月度 TCO | 平均情景月利润 | 利润率 |
|---|---:|---:|---:|---:|
{segment_rows}

- 盈利表现最佳城市：City {int(best_city['city_id'])}，平均情景月利润 {best_city['avg_est_profit']:,.2f} USD。
- 盈利表现最弱城市：City {int(worst_city['city_id'])}，平均情景月利润 {worst_city['avg_est_profit']:,.2f} USD。
- 维保费用采用 P99 封顶值参与经营口径计算，原始金额仍保留用于异常审计。

## 定价模型表现

| 模型 | MAPE | RMSE | MAE | R² |
|---|---:|---:|---:|---:|
| 车型中位数基线 | {baseline['MAPE_pct']:.2f}% | {baseline['RMSE']:.2f} | {baseline['MAE']:.2f} | {baseline['R2']:.3f} |
| Ridge | {ridge['MAPE_pct']:.2f}% | {ridge['RMSE']:.2f} | {ridge['MAE']:.2f} | {ridge['R2']:.3f} |

模型结果支持在车型规则价基础上加入动力、里程和配置差异，但不替代供需、库存、
节假日和竞争环境等实时定价信号。

## 建议动作

1. 对 Segment {worst_seg['segment']} 建立单车成本审计清单，区分事故型大额维保与持续性高成本。
2. 对 City {int(worst_city['city_id'])} 复核停车层级、车型结构和调度效率，再决定调拨或压缩规模。
3. 以 Ridge 输出作为定价参考区间，保留人工规则和价格上下限，并持续监控 MAPE 与残差分布。
4. 将利用率、真实出租天数和订单收入接入后，替换当前 Segment 收入基准，形成可核算的单车损益。

## 口径与限制

- Zenodo 与 Getaround 无共同车辆标识，只在 Segment 层进行租金基准桥接。
- 采购价、折旧、保险、停车与利用率为配置参数，盈利结果属于情景测算。
- 数据来源跨市场且币种口径有限，结果适用于方法验证和优先级识别，不作为财务确认依据。
"""


def main() -> None:
    report = build_report()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    doc_path = DOCS_DIR / "step5-结论与运营建议.md"
    output_path = OUTPUT_DIR / "step5_executive_summary.md"
    doc_path.write_text(report, encoding="utf-8")
    output_path.write_text(report, encoding="utf-8")
    print(f"报告已生成:\n  {doc_path}\n  {output_path}")


if __name__ == "__main__":
    main()
