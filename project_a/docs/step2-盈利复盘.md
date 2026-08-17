# 月度 TCO 与盈利能力分析

## 分析范围

该阶段将车辆月度成本与 Segment 租金基准结合，形成单车、Segment 和城市三级的情景盈利结果。

## 处理逻辑

1. 从 SQLite 读取车辆属性与月度成本。
2. 对维保费用计算全样本 P99，并生成封顶后的经营分析口径。
3. 按 Segment 连接月租金基准和配置利用率。
4. 计算情景月收入、月利润和利润率。
5. 输出 Segment、城市和成本结构汇总。

## 核心公式

```text
月度 TCO = 折旧 + 保险 + P99 封顶维保 + 停车
情景月收入 = Segment 月租金基准 × 利用率参数
情景月利润 = 情景月收入 − 月度 TCO
利润率 = 情景月利润 / 情景月收入
```

## 运行

```bash
python project_a/src/step2_profitability.py
```

## 输出

| 文件 | 内容 |
|---|---|
| `step2_vehicle_monthly_tco.csv` | 单车月度成本与情景利润明细 |
| `step2_segment_profitability.csv` | Segment 盈利汇总 |
| `step2_city_profitability.csv` | 城市盈利汇总 |
| `step2_segment_cost_breakdown.csv` | Segment 成本结构 |
| `step2_segment_charts.png` | 利润与成本结构图 |

## 参数与限制

- 维保 P99 封顶用于降低极端发票对均值的影响，原始金额未被覆盖。
- 利用率为情景参数；缺少真实出租天数时，收入结果不作为财务确认依据。
- 无租金基准映射的 Segment 不参与情景利润比较。
