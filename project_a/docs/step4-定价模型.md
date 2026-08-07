# Step 4：回归定价模型（实操指南）

## 一、Step 4 要回答的业务问题

1. **能否用因子预测日租金？**  
2. **比「按车型取中位数」的规则定价好多少？**  
3. **哪些因子对定价贡献最大？**  

---

## 二、运行

```bash
cd project_a
python src/step4_pricing_model.py
```

---

## 三、建模设计

| 组件 | 选择 | 原因 |
|------|------|------|
| **Baseline** | 同 `car_type` 训练集租金中位数 | 业务常有的规则定价 |
| **模型** | Ridge 回归 | 可解释、不易过拟合，对齐 JD「回归分析」 |
| **特征** | Step 3 结论：`car_type`, `fuel`, `engine_power`, `log_mileage`, 配置 dummy | 因子分析驱动 |
| **评估** | MAPE / RMSE / MAE / R² | 面试常问 |
| **切分** | 80% 训练 / 20% 测试 | 标准 hold-out |

---

## 四、输出文件

| 文件 | 内容 |
|------|------|
| `step4_model_metrics.csv` | Baseline vs Ridge 指标 |
| `step4_feature_importance.csv` | Ridge 系数（因子重要性） |
| `step4_test_predictions.csv` | 测试集预测 vs 真实 |
| `step4_model_comparison.png` | MAPE 对比 + 散点图 |

---

## 五、简历填数

跑完后从 `step4_model_metrics.csv` 取：

> 基于 engine_power、log_mileage、car_type 等 8+ 因子构建 Ridge 动态定价模型，较 car_type 规则定价 **MAPE 降低 X%**，R² 达 **X.XX**。

---

*下一步：Step 5 结论与运营建议汇总*
