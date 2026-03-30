# Yuan-Quant 隅安量化

> 基于 Python + MetaTrader5 的量化交易系统  
> 核心理念：**低交易频率 · 高胜率 · 严格风险控制**

---

## 项目结构

```
Yuan-quant/
├── main.py                      # 统一入口文件（实盘/回测一键启动）
├── requirements.txt             # 依赖包列表
│
├── config/                      # 基础配置模块
│   ├── settings.py              # MT5账户、品种、时间框架、风险、日志全局配置
│   └── strategy_config.py       # 各策略独立参数（修改此处无需动策略代码）
│
├── indicators/                  # 指标模块（只负责计算，不含信号判断）
│   ├── ao.py                    # AO 计算：calculate_ao(), ao_color()
│   └── ma.py                    # MA 计算：calculate_ma(), calculate_ma_group()
│
├── signals/                     # 信号模块（只负责判断，不含计算，不含执行）
│   ├── base.py                  # 信号常量：SIG_BUY/SELL/NONE，combine_signals() 组合工具
│   ├── sig_ma.py                # MA 信号：多头排列、金叉死叉、价格穿线、均线发散
│   └── sig_ao.py                # AO 信号：零轴穿越、蝶形、颜色变化、双峰双谷
│
├── strategies/                  # 策略模块（组合多种信号，面向信号层编程）
│   ├── str_ma_cross.py          # 均线交叉策略（金叉死叉 + 多头排列过滤，AND 共振）
│   └── str_ao_mtf.py            # AO 多时间框架共振策略（M1/M5/M15）
│
├── connector/                   # MT5 链接模块
│   ├── mt5_client.py            # MT5初始化、登录、K线数据获取
│   └── order_manager.py         # 开仓、平仓、查询持仓
│
├── backtest/                    # 回测模块
│   ├── engine.py                # 通用向量化回测引擎（信号驱动，输出完整绩效统计）
│   ├── run_ma_cross.py          # MA Cross 策略回测入口
│   └── run_ao_mtf.py            # AO MTF 策略回测入口
│
├── visualization/               # 可视化模块
│   ├── plot_result.py           # 回测三联图（价格+信号 / 权益曲线 / 回撤）
│   └── plot_indicators.py       # 指标图（MA叠加+信号标注 / AO柱状+信号标注）
│
├── utils/                       # 工具模块
│   ├── logger.py                # 统一日志（控制台 + 滚动文件）
│   └── helpers.py               # 辅助函数（点数转换、时间框架映射等）
│
├── logs/                        # 运行日志目录（自动生成）
└── results/                     # 回测结果图表保存目录
```

---

## 架构设计：指标 → 信号 → 策略 → 执行

```
K线数据
  └─▶ indicators/（纯计算，输出指标值）
          └─▶ signals/（纯判断，输出 1/-1/0 信号序列）
                  └─▶ strategies/（信号组合 + 决策）
                          └─▶ connector/（MT5 下单执行）
```

**设计原则：**
- `indicators/` 只做数学计算，输入 K 线价格，输出指标数值（`pd.Series`）
- `signals/` 只做逻辑判断，输入指标数值，输出信号（`1` 做多 / `-1` 做空 / `0` 无信号）
- `strategies/` 只面向信号，通过 `combine_signals()` 组合多个信号决定入场/出场
- 三层完全解耦，可独立测试、独立替换

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置账户

编辑 `config/settings.py`，填写 MT5 账户信息：

```python
MT5_ACCOUNT = {
    "login":    your_account_number,
    "password": "your_password",
    "server":   "your_broker_server",
}
```

### 3. 运行回测

```bash
# MA 均线交叉策略回测
python main.py --mode backtest --strategy ma_cross

# AO MTF 策略回测（2000 根 M1 K线）
python main.py --mode backtest --strategy ao_mtf --bars 2000

# 指定品种和时间框架
python main.py --mode backtest --strategy ma_cross --symbol XAUUSD --timeframe H4 --bars 1000
```

### 4. 实盘交易

```bash
# MA 均线交叉策略实盘
python main.py --mode live --strategy ma_cross

# AO 多时间框架共振策略实盘
python main.py --mode live --strategy ao_mtf
```

---

## 模块说明

### 指标模块 (`indicators/`)

> 只计算，不判断。输出原始指标数值。

| 文件 | 职责 | 核心函数 |
|------|------|----------|
| `ao.py` | AO 值计算 | `calculate_ao(high, low)` → AO 序列<br>`ao_color(ao)` → 柱色序列（green/red/neutral）|
| `ma.py` | MA 值计算 | `calculate_ma(close, period, type)` → 单条均线<br>`calculate_ma_group(close, periods)` → 多条均线 DataFrame |

---

### 信号模块 (`signals/`)

> 只判断，不计算。输入指标序列，输出 `1 / -1 / 0` 信号。

#### `base.py` — 信号常量与组合工具

| 名称 | 说明 |
|------|------|
| `SIG_BUY = 1` | 做多信号常量 |
| `SIG_SELL = -1` | 做空信号常量 |
| `SIG_NONE = 0` | 无信号常量 |
| `combine_signals(signals, mode)` | 组合多个信号序列，支持 `"all"`（AND共振）/ `"any"`（OR）/ `"vote"`（投票）|

#### `sig_ma.py` — MA 信号

| 函数 | 信号说明 |
|------|----------|
| `ma_bull_alignment_signal(mas)` | 均线多头排列（MA5>MA20>MA60...）→ 1；空头排列 → -1 |
| `ma_cross_signal(fast, slow)` | 快线上穿慢线（金叉）→ 1；下穿（死叉）→ -1 |
| `ma_price_cross_signal(close, ma)` | 收盘价上穿均线 → 1；下穿 → -1 |
| `ma_fan_signal(fast, slow)` | 均线发散扩大（多头方向）→ 1；空头方向 → -1 |

#### `sig_ao.py` — AO 信号

| 函数 | 信号说明 |
|------|----------|
| `ao_zero_cross_signal(ao)` | AO 上穿零轴 → 1；下穿零轴 → -1 |
| `ao_saucer_signal(ao)` | 蝶形买入形态 → 1；蝶形卖出形态 → -1 |
| `ao_color_change_signal(ao, colors)` | 零轴上方由红变绿（弱转强）→ 1；零轴下方由绿变红 → -1 |
| `ao_twin_peaks_signal(ao)` | 零轴下方双谷且第二谷更高（底背离）→ 1；上方双峰且第二峰更低（顶背离）→ -1 |

---

### 策略模块 (`strategies/`)

> 只面向信号层，通过 `combine_signals()` 组合多个信号决策。

| 文件 | 策略 | 信号组合 |
|------|------|----------|
| `str_ma_cross.py` | 均线交叉策略（H1）| `ma_cross_signal(MA20, MA60)` + `ma_bull_alignment_signal` → AND 共振 |
| `str_ao_mtf.py` | AO 多时间框架共振 | `ao_color_change_signal` × M1/M5/M15 三框架同向共振 |

---

### 回测引擎 (`backtest/engine.py`)

- 输入：任意信号序列（`1 / -1 / 0`）+ K 线 DataFrame
- 输出：`BacktestResult` 对象，包含：
  - 总交易次数、盈利次数、亏损次数、胜率
  - 净盈亏、平均每笔、最大回撤、盈亏比、夏普比率
  - 权益曲线（`pd.Series`）、交易明细（`pd.DataFrame`）
- 图表自动保存至 `results/` 目录

---

## 扩展开发

### 新增指标
1. 在 `indicators/` 新建 `xxx.py`，只写计算函数，不含信号判断
2. 在 `indicators/__init__.py` 中导出

### 新增信号
1. 在 `signals/` 新建 `sig_xxx.py`
2. 函数签名：输入指标序列 → 输出 `pd.Series[int]`（`1 / -1 / 0`）
3. 在 `signals/__init__.py` 中导出

### 新增策略
1. 在 `strategies/` 新建 `str_xxx.py`
2. 只从 `signals/` 层消费信号，通过 `combine_signals()` 组合
3. 在 `config/strategy_config.py` 中添加策略参数
4. 在 `main.py` 的 `run_live()` 和 `run_backtest()` 中注册
5. 在 `backtest/` 新建对应回测入口文件

---

## 更新日志

### 2026-03-30
- 新增 `signals/` 信号模块，实现指标与信号解耦
- `signals/base.py`：信号常量（SIG_BUY/SELL/NONE）+ `combine_signals()` 多信号组合工具
- `signals/sig_ma.py`：MA 多头排列、金叉死叉、价格穿线、均线发散 四种信号
- `signals/sig_ao.py`：AO 零轴穿越、蝶形、颜色变化、双峰双谷 四种信号
- 重构 `indicators/`：移除信号函数，只保留纯计算
- 重构 `strategies/`：改为只消费 `signals/` 层输出
- 新增 `visualization/plot_indicators.py`：带买卖信号标注的指标可视化图表

### 2026-03-17
- 初始化项目架构
- 实现 AO 指标计算与 MA 指标计算
- 实现 MT5 连接模块（登录、K线获取、开平仓管理）
- 实现均线交叉策略（H1, MA20/MA60）
- 实现 AO 多时间框架共振策略（M1/M5/M15）
- 实现通用向量化回测引擎
- 实现可视化模块
