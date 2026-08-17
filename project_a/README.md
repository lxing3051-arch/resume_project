# 项目 A：车辆资产收益测算与租金定价

项目 A 建立车辆资产分析的数据底座，并依次完成月度 TCO、盈利能力、定价因子和租金预测分析。分析对象为公开租车维保与共享租车定价数据，所有非观测参数均集中配置并在输出中标记为情景假设。

## 业务目标

- 统一车辆、成本、城市和定价数据口径。
- 识别高成本、低收益的 Segment 与城市组合。
- 量化车辆属性与租金之间的关系。
- 比较规则定价与可解释回归模型的样本外表现。

## 数据模型

| 表 | 粒度 | 用途 |
|---|---|---|
| `vehicle_asset` | 一车一行 | 车辆属性与资产主数据 |
| `cost_monthly` | 一车一月一行 | 折旧、保险、维保和停车成本 |
| `city_factor` | 一城市一行 | 城市规模与成本层级 |
| `getaround_pricing` | 一挂牌车辆一行 | 定价特征与日租金 |
| `getaround_rental_activity` | 一笔租赁活动一行 | 租赁活动与周转信息 |
| `segment_rent_benchmark` | 一 Segment 一行 | 跨数据集租金基准 |
| `data_source` | 一来源一行 | 数据血缘与使用说明 |

详细字段、主键和血缘见 [项目 A 数据说明](../docs/项目A-数据说明.md)。

## 分析流程

```bash
pip install -r project_a/requirements.txt
python project_a/src/load_public_data.py
python project_a/src/step2_profitability.py
python project_a/src/step3_pricing_factors.py
python project_a/src/step4_pricing_model.py
python project_a/src/step5_report.py
```

1. `load_public_data.py`：下载或读取原始文件，完成字段映射、数据校验与 SQLite 入库。
2. `step2_profitability.py`：计算月度 TCO、情景收入、利润率及城市/Segment 汇总。
3. `step3_pricing_factors.py`：输出数值相关性与类别因子对比。
4. `step4_pricing_model.py`：比较车型中位数基线与 Ridge 回归模型。
5. `step5_report.py`：基于已生成结果形成管理摘要。

## 核心口径

| 指标 | 定义 |
|---|---|
| 月度 TCO | 折旧 + 保险 + P99 封顶后的维保 + 停车 |
| 情景月收入 | Segment 月租金基准 × 配置利用率 |
| 情景月利润 | 情景月收入 − 月度 TCO |
| 利润率 | 情景月利润 / 情景月收入 |
| MAPE | 日租金预测绝对百分比误差均值 |

## 主要输出

- `data/output/step2_segment_profitability.csv`
- `data/output/step2_city_profitability.csv`
- `data/output/step2_segment_cost_breakdown.csv`
- `data/output/step3_correlation_matrix.csv`
- `data/output/step4_model_metrics.csv`
- `docs/step5-结论与运营建议.md`

## 分析边界

- Zenodo 与 Getaround 无共同车辆标识，只在 Segment 层进行基准桥接。
- 采购价、折旧、保险、停车与利用率为显式情景参数，不代表企业账面值。
- 数据市场、币种与时间范围并不完全一致，因此盈利结果用于敏感性分析和优先级识别，不作为财务确认依据。
