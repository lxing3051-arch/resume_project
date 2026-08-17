# 日租金回归模型

## 模型目标

在车型中位数规则价基础上，评估车辆属性是否能降低样本外日租金预测误差。

## 设计

| 组件 | 设置 | 业务含义 |
|---|---|---|
| Baseline | 训练集内同车型租金中位数 | 可执行的规则定价基准 |
| 模型 | Ridge 回归 | 控制相关特征的系数波动并保留可解释性 |
| 特征 | 车型、燃料、动力、对数里程、配置项 | 覆盖车辆定位、损耗和配置差异 |
| 切分 | 固定随机种子的 80/20 hold-out | 保持模型对比可复现 |
| 指标 | MAPE、RMSE、MAE、R² | 同时衡量相对误差、绝对误差和解释度 |

## 运行

```bash
python project_a/src/step4_pricing_model.py
```

## 输出

| 文件 | 内容 |
|---|---|
| `step4_model_metrics.csv` | Baseline 与 Ridge 测试集指标 |
| `step4_feature_importance.csv` | 标准化处理后的 Ridge 系数 |
| `step4_test_predictions.csv` | 测试集真实值与预测值 |
| `step4_model_comparison.png` | 误差和拟合效果对比 |

## 应用边界

模型输出适合作为价格参考和异常检查，不包含实时供需、节假日、库存、竞争对手价格等动态信号。生产定价需加入价格上下限、人工审核和持续误差监控。
