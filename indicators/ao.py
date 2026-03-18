# -*- coding: utf-8 -*-
"""
AO（Awesome Oscillator，动量震荡指标）

参考资料：
https://cn.tradingview.com/support/solutions/43000501826/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【指标说明】
  AO（Awesome Oscillator）由 Bill Williams 创立，衡量市场近期动能与较长期动能之差。

  计算公式：
      中间价  = (High + Low) / 2
      AO      = SMA(中间价, 5) - SMA(中间价, 34)
  其中 SMA 为简单移动平均。

【柱色定义】
  - 绿色（Green）：当前 AO 值 > 前一根 AO 值（动能增强）
  - 红色（Red）  ：当前 AO 值 < 前一根 AO 值（动能减弱）

【信号种类】
  1. 零轴穿越（Zero Cross）
     - AO 由负转正（上穿零轴）→ 买入信号
     - AO 由正转负（下穿零轴）→ 卖出信号

  2. 蝶形形态（Saucer）
     - 蝶形买入：三根均在零轴上方，第二根绝对值最小（谷底），第三根向上翻绿
     - 蝶形卖出：三根均在零轴下方，第二根绝对值最小（峰顶），第三根向下翻红
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd


def calculate_ao(
    high: pd.Series,
    low: pd.Series,
    fast: int = 5,
    slow: int = 34,
) -> pd.Series:
    """
    计算 Awesome Oscillator（AO）值。

    Parameters
    ----------
    high : pd.Series  K 线最高价
    low  : pd.Series  K 线最低价
    fast : int        快速 SMA 窗口，默认 5
    slow : int        慢速 SMA 窗口，默认 34

    Returns
    -------
    pd.Series  AO 值序列，索引与输入相同，列名为 "AO"
    """
    midpoint = (high + low) / 2.0
    ao = midpoint.rolling(window=fast).mean() - midpoint.rolling(window=slow).mean()
    ao.name = "AO"
    return ao


def ao_color(ao: pd.Series) -> pd.Series:
    """
    计算每根 K 线 AO 柱的颜色。

    Returns
    -------
    pd.Series[str]  取值为 'green'（上升）、'red'（下降）或 'neutral'（首根）
    """
    diff = ao.diff()
    color = diff.apply(
        lambda x: "green" if x > 0 else ("red" if x < 0 else "neutral")
    )
    color.iloc[0] = "neutral"
    color.name = "AO_Color"
    return color


def ao_zero_cross_signal(ao: pd.Series) -> pd.Series:
    """
    基于零轴穿越生成交易信号。

    Returns
    -------
    pd.Series[int]
       1  → 买入（AO 由负转正，上穿零轴）
      -1  → 卖出（AO 由正转负，下穿零轴）
       0  → 无信号
    """
    prev = ao.shift(1)
    signal = pd.Series(0, index=ao.index, dtype=int, name="AO_ZeroCross_Signal")
    signal[(ao > 0) & (prev <= 0)] = 1
    signal[(ao < 0) & (prev >= 0)] = -1
    return signal


def ao_saucer_signal(ao: pd.Series) -> pd.Series:
    """
    基于蝶形形态（Saucer）生成交易信号。

    Returns
    -------
    pd.Series[int]
       1  → 蝶形买入
      -1  → 蝶形卖出
       0  → 无信号
    """
    signal = pd.Series(0, index=ao.index, dtype=int, name="AO_Saucer_Signal")
    ao_vals = ao.values

    for i in range(2, len(ao_vals)):
        a, b, c = ao_vals[i - 2], ao_vals[i - 1], ao_vals[i]
        if any(v != v for v in (a, b, c)):  # NaN 检查
            continue
        # 蝶形买入：三根均为负值，第二根绝对值小于第一根，第三根大于第二根
        if a < 0 and b < 0 and c < 0:
            if abs(b) < abs(a) and c > b:
                signal.iloc[i] = 1
        # 蝶形卖出：三根均为正值，第二根绝对值小于第一根，第三根小于第二根
        if a > 0 and b > 0 and c > 0:
            if abs(b) < abs(a) and c < b:
                signal.iloc[i] = -1
    return signal


if __name__ == "__main__":
    import numpy as np

    print("=== AO 指标模块测试 ===")

    # 构造模拟 K 线数据（200 根）
    np.random.seed(42)
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5), index=idx)
    high  = close + np.abs(np.random.randn(n) * 0.3)
    low   = close - np.abs(np.random.randn(n) * 0.3)

    # 1. 测试 calculate_ao
    ao = calculate_ao(high, low)
    print(f"[calculate_ao] 共 {len(ao)} 根，非空值 {ao.notna().sum()} 根")
    print(f"  AO 最新值: {ao.iloc[-1]:.6f}")
    print(f"  AO 最大值: {ao.max():.6f}  最小值: {ao.min():.6f}")

    # 2. 测试 ao_color
    colors = ao_color(ao)
    green_cnt = (colors == "green").sum()
    red_cnt   = (colors == "red").sum()
    print(f"[ao_color] 绿色柱: {green_cnt} 根  红色柱: {red_cnt} 根")

    # 3. 测试 ao_zero_cross_signal
    zc_signal = ao_zero_cross_signal(ao)
    buy_cnt  = (zc_signal == 1).sum()
    sell_cnt = (zc_signal == -1).sum()
    print(f"[ao_zero_cross_signal] 买入信号: {buy_cnt} 次  卖出信号: {sell_cnt} 次")

    # 4. 测试 ao_saucer_signal
    saucer = ao_saucer_signal(ao)
    s_buy  = (saucer == 1).sum()
    s_sell = (saucer == -1).sum()
    print(f"[ao_saucer_signal] 蝶形买入: {s_buy} 次  蝶形卖出: {s_sell} 次")

    print("=== 测试完成 ===")