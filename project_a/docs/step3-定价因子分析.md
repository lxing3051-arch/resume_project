# 租金定价因子分析

## 分析目标

量化车辆连续变量、类别属性和配置项与日租金之间的关系，为规则定价和回归模型提供特征依据。

## 分析方法

- 连续变量：计算 Pearson 相关系数并检查变量分布。
- 里程：使用 `log1p` 处理长尾后比较租金关系。
- 类别变量：按车型、燃料和里程区间汇总样本量、中位数与均值。
- 配置项：比较有无配置车辆的租金中位数差异和相对提升。

相关性用于描述线性关联，不解释为因果效应。类别对比同时报告样本量，避免将小样本差异视为稳定结论。

## 运行

```bash
python project_a/src/step3_pricing_factors.py
```

## 输出

| 文件 | 内容 |
|---|---|
| `step3_correlation_matrix.csv` | 数值变量相关矩阵 |
| `step3_factor_car_type.csv` | 车型租金分布 |
| `step3_factor_fuel.csv` | 燃料类型租金分布 |
| `step3_factor_mileage_bin.csv` | 里程区间租金分布 |
| `step3_factor_config_lift.csv` | 配置项租金差异 |
| `step3_correlation_heatmap.png` | 相关性热力图 |
| `step3_categorical_factors.png` | 类别因子对比图 |

## 应用边界

公开数据缺少地区供需、节假日、库存和竞品动态价格，因子分析仅覆盖车辆侧结构性差异。进入定价模型的字段需在训练集内完成预处理，避免测试集信息进入拟合过程。
