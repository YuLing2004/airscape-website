# Airscape 映射逻辑说明

本版本将小球运动逻辑严格收敛到 5 个空气运动参数，并按照表格中的含义建立一一对应的可视化映射，不再额外引入独立的 `Stagnation` 控件。系统中 64 个小球共享同一组全局参数，但每个小球保留轻微个体差异，以保证整体统一、局部自然。

## 参数与可视化映射

| 参数 | 控制内容 | 可视化行为 | 对应空气意义 |
| --- | --- | --- | --- |
| Wind Speed | 小球上下运动频率与节奏快慢 | 提高整体波动速度、加快目标高度更新速度 | 空气流动速度与风场变化 |
| Wave Amplitude | 小球上下位移高度 | 放大主波动位移范围，让升降幅度更明显 | 空气压力与扰动强度变化 |
| Turbulence | 随机偏移与不稳定抖动 | 增加噪声扰动与高频微抖动 | 空气湍流与局部不稳定状态 |
| Wave Complexity | 非同步复合运动 | 增加二级/三级波叠加与网格间相位差 | 城市空气中的多源干扰与复杂流场 |
| Pollution Density | 聚集、停滞与低速沉积 | 增加下沉偏移、减弱响应、增强中心聚集与滞留感 | 空气污染颗粒浓度与滞留状态 |

## 逻辑结构

### 1. Wind Speed
- 映射为 `flowSpeed`
- 同时映射为 `oscillationResponse`
- 含义：风速越高，整体振动节奏越快，小球追随目标位置的速度也越快

### 2. Wave Amplitude
- 映射为 `displacementRange`
- 含义：振幅越高，主波动产生的上下位移越大

### 3. Turbulence
- 映射为 `turbulenceStrength`
- 同时映射为 `turbulenceJitter`
- 含义：一部分生成连续噪声扰动，一部分生成更细碎的高频抖动，表现局部空气不稳定

### 4. Wave Complexity
- 映射为 `complexityStrength`
- 同时映射为 `phaseSpread`
- 含义：复杂度越高，不同小球之间的相位差、复合波成分和空间干扰越强，整体越不同步

### 5. Pollution Density
- 映射为 `densitySink`
- 同时映射为 `densityDamping`、`densityResponsiveness`、`densityClustering`
- 含义：污染越高，小球越容易向下沉积、运动响应越迟缓，并在密度高的区域形成更明显的聚集与滞留

## 单颗粒子的目标高度组成

每个小球的目标高度由以下部分组成：

`目标高度 = 基线高度 + 沉积偏移 - 波动位移 × 响应系数 + 湍流扰动 + 微抖动`

其中：
- `沉积偏移` 由 `Pollution Density` 主导
- `波动位移` 由 `Wind Speed + Wave Amplitude + Wave Complexity` 共同形成
- `湍流扰动` 与 `微抖动` 由 `Turbulence` 主导
- `响应系数` 会被污染密度削弱，模拟高浓度颗粒更滞重、不易被抬升

## 为什么这版更严谨

1. 参数和视觉行为是一一对应的，没有多余控制项。
2. `Pollution Density` 不只控制“下沉”，还同时控制“停滞、迟缓、聚集”，更贴近原表述。
3. `Wave Complexity` 不再只是简单加噪，而是明确作用于复合波、相位差和空间干扰。
4. `Turbulence` 被拆成连续扰动和微抖动两层，更符合“随机偏移 + 不稳定状态”的描述。
5. `Wind Speed` 与 `Wave Amplitude` 分别控制“快慢”和“高度”，职责清晰，不互相混淆。

## 当前实现结论

当前 `backup.html` 已按以上逻辑重写：
- 控件已调整为 5 项：`Wind Speed`、`Wave Amplitude`、`Turbulence`、`Wave Complexity`、`Pollution Density`
- 原本独立的 `Stagnation` 已移除
- 运动更新函数已经改为基于上述映射关系计算

后续如果你要，我可以继续把这份说明同步成：
1. 更学术/论文式版本
2. 更适合给客户展示的中文方案版
3. 中英双语版
