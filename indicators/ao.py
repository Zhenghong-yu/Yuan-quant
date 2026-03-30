# -*- coding: utf-8 -*-
"""
指标模块 - AO（Awesome Oscillator，神奇震荡指标）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模块职责】
  本模块只负责「计算」，输出原始指标数值和辅助信息（柱色）。
  交易信号的判断请使用 signals/sig_ao.py。

  数据流：K线数据 → indicators/ao.py（计算值）→ signals/sig_ao.py（信号）→ strategies/

【计算公式】
  中间价 = (High + Low) / 2
  AO     = SMA(中间价, 5) - SMA(中间价, 34)

【柱色定义】
  green   : 当前 AO > 前一根 AO（动能增强）
  red     : 当前 AO < 前一根 AO（动能减弱）
  neutral : 首根

参考：https://cn.tradingview.com/support/solutions/43000501826/
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
    计算 Awesome Oscillator 值。

    Parameters
    ----------
    high : K 线最高价
    low  : K 线最低价
    fast : 快速 SMA 窗口，默认 5
    slow : 慢速 SMA 窗口，默认 34

    Returns
    -------
    pd.Series  列名为 'AO'
    """
    midpoint = (high + low) / 2.0
    ao = midpoint.rolling(window=fast).mean() - midpoint.rolling(window=slow).mean()
    ao.name = "AO"
    return ao


def ao_color(ao: pd.Series) -> pd.Series:
    """
    计算每根 K 线 AO 柱的颜色（辅助信息，供信号模块使用）。

    Returns
    -------
    pd.Series[str]  'green' / 'red' / 'neutral'
    """
    diff = ao.diff()
    color = diff.apply(
        lambda x: "green" if x > 0 else ("red" if x < 0 else "neutral")
    )
    color.iloc[0] = "neutral"
    color.name = "AO_Color"
    return color


if __name__ == "__main__":
    import sys
    import os
    import numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from signals.sig_ao import (
        ao_zero_cross_signal, ao_saucer_signal,
        ao_color_change_signal, ao_twin_peaks_signal,
    )
    from visualization.plot_indicators import plot_ao_with_signals

    print("=== AO 指标模块测试 ===")
    np.random.seed(42)
    n     = 200
    idx   = pd.date_range("2024-01-01", periods=n, freq="h")
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5), index=idx)
    high  = close + np.abs(np.random.randn(n) * 0.3)
    low   = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close - np.random.randn(n) * 0.1
    df    = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})

    # 计算指标
    ao     = calculate_ao(high, low)
    colors = ao_color(ao)
    print(f"[calculate_ao] 非空值: {ao.notna().sum()}  最新: {ao.iloc[-1]:.6f}")
    print(f"[ao_color] green: {(colors=='green').sum()}  red: {(colors=='red').sum()}")

    # 信号（通过 signals 层）
    s1 = ao_zero_cross_signal(ao)
    s2 = ao_saucer_signal(ao)
    s3 = ao_color_change_signal(ao, colors)
    s4 = ao_twin_peaks_signal(ao)
    for name, s in [("零轴穿越", s1), ("蝶形形态", s2),
                    ("颜色变化", s3), ("双峰双谷", s4)]:
        print(f"[{name}] 买入: {(s==1).sum()}  卖出: {(s==-1).sum()}")

    print("=== 测试完成 ===")
    # 可视化
    plot_ao_with_signals(df=df, ao=ao, signals=s1,
                         signal_label="Zero Cross",
                         title="AO 指标 - 零轴穿越信号",
                         save=True, show=True)
    plot_ao_with_signals(df=df, ao=ao, signals=s3,
                         signal_label="Color Change",
                         title="AO 指标 - 颜色变化信号",
                         save=True, show=True)
