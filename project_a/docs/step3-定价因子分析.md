# Step 3：定价因子分析（实操指南）

## 一、Step 3 要回答的业务问题

1. **日租金受哪些因素影响？**（车型、里程、功率、配置…）  
2. **各因子与租金的相关方向与强度？**  
3. **哪些因子应进入 Step 4 回归模型？**  

数据：**Getaround 定价清单**（4843 条真实 `rental_price_per_day`）

---

## 二、运行

```bash
cd project_a
python src/step3_pricing_factors.py
```

---

## 三、分析步骤

| 步骤 | 内容 |
|------|------|
| 3.1 清洗 | 去掉负里程、极端租金（>500 USD/天） |
| 3.2 特征 | `log_mileage`、里程四分位 `mileage_bin`、`config_score`（配置项求和） |
| 3.3 相关 | Spearman 相关（对非线性更稳健） |
| 3.4 分组 | 按 `car_type` / `fuel` / 里程段 看中位租金 |
| 3.5 配置溢价 | 有 GPS、自动挡等 vs 无，租金 lift |
| 3.6 出图 | 相关热力图 + 车型/里程柱状图 |

---

## 四、输出文件

| 文件 | 内容 |
|------|------|
| `step3_correlation_matrix.csv` | 数值因子相关矩阵 |
| `step3_factor_car_type.csv` | 分车型租金 |
| `step3_factor_fuel.csv` | 分燃料租金 |
| `step3_factor_mileage_bin.csv` | 分里程段租金 |
| `step3_factor_config_lift.csv` | 配置项溢价 |
| `step3_correlation_heatmap.png` | 相关热力图 |
| `step3_categorical_factors.png` | 车型 + 里程因子图 |

---

## 五、Step 4 衔接

将以下因子作为回归候选特征：

- 分类：`car_type`、`fuel`（one-hot）  
- 数值：`engine_power`、`log_mileage`  
- 配置：`has_gps`、`automatic_car` 等 dummy  

---

*下一步：Step 4 回归定价模型 + 与 baseline 对比*
