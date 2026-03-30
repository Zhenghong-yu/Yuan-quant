# -*- coding: utf-8 -*-
"""
信号模块 - AO 震荡指标信号 (signals/sig_ao.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模块说明】
  本模块基于 indicators/ao.py 计算出的 AO 值和柱色，定义多种 AO 信号。
  信号函数只做「判断」，不做「计算」，输入均为已算好的指标序列。

【信号列表】
  1. ao_zero_cross_signal    AO 零轴穿越信号
     由负转正 → 做多；由正转负 → 做空

  2. ao_saucer_signal        AO 蝶形形态信号
     零轴上方三根特定形态 → 做多；零轴下方 → 做空

  3. ao_color_change_signal  AO 颜色变化信号（弱转强）
     零轴上方由红变绿 → 做多；零轴下方由绿变红 → 做空

  4. ao_twin_peaks_signal    AO 双峰/双谷信号（顶底背离）
     零轴上方两峰，第二峰更低 → 做空
     零轴下方两谷，第二谷更高 → 做多
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
from signals.base import SIG_BUY, SIG_SELL, SIG_NONE


def ao_zero_cross_signal(ao: pd.Series) -> pd.Series:
    """
    AO 零轴穿越信号。
    由负转正 → 做多；由正转负 → 做空。
    """
    prev   = ao.shift(1)
    signal = pd.Series(SIG_NONE, index=ao.index, dtype=int,
                       name="AO_ZeroCross_Signal")
    signal[(ao > 0) & (prev <= 0)] = SIG_BUY
    signal[(ao < 0) & (prev >= 0)] = SIG_SELL
    return signal


def ao_saucer_signal(ao: pd.Series) -> pd.Series:
    """
    AO 蝶形形态信号（Saucer）。
    蝶形买入：三根均在零轴上方，中间根绝对值最小，第三根向上
    蝶形卖出：三根均在零轴下方，中间根绝对值最小，第三根向下
    """
    signal   = pd.Series(SIG_NONE, index=ao.index, dtype=int,
                         name="AO_Saucer_Signal")
    ao_vals  = ao.values
    for i in range(2, len(ao_vals)):
        a, b, c = ao_vals[i - 2], ao_vals[i - 1], ao_vals[i]
        if any(v != v for v in (a, b, c)):
            continue
        if a < 0 and b < 0 and c < 0 and abs(b) < abs(a) and c > b:
            signal.iloc[i] = SIG_BUY
        if a > 0 and b > 0 and c > 0 and abs(b) < abs(a) and c < b:
            signal.iloc[i] = SIG_SELL
    return signal


def ao_color_change_signal(ao: pd.Series, colors: pd.Series) -> pd.Series:
    """
    AO 颜色变化信号（弱转强）。

    Parameters
    ----------
    ao     : AO 值序列（由 indicators.ao.calculate_ao 生成）
    colors : AO 柱色序列（由 indicators.ao.ao_color 生成）

    Returns
    -------
    pd.Series[int]
       1  → 零轴上方由红变绿（动能由弱转强，做多）
      -1  → 零轴下方由绿变红（动能由弱转强，做空）
       0  → 无信号
    """
    prev_color = colors.shift(1)
    signal = pd.Series(SIG_NONE, index=ao.index, dtype=int,
                       name="AO_ColorChange_Signal")
    signal[
        (ao > 0) & (prev_color == "red") & (colors == "green")
    ] = SIG_BUY
    signal[
        (ao < 0) & (prev_color == "green") & (colors == "red")
    ] = SIG_SELL
    return signal


def ao_twin_peaks_signal(ao: pd.Series, window: int = 10) -> pd.Series:
    """
    AO 双峰/双谷信号（顶底背离）。

    Parameters
    ----------
    ao     : AO 值序列
    window : 回溯窗口（在最近 window 根内寻找前峰/前谷）

    Returns
    -------
    pd.Series[int]
       1  → 零轴下方双谷且第二谷更高（底背离，做多）
      -1  → 零轴上方双峰且第二峰更低（顶背离，做空）
       0  → 无信号
    """
    signal  = pd.Series(SIG_NONE, index=ao.index, dtype=int,
                        name="AO_TwinPeaks_Signal")
    ao_vals = ao.values

    for i in range(window + 1, len(ao_vals)):
        cur = ao_vals[i]
        if cur != cur:
            continue
        lookback = ao_vals[i - window: i]

        # 顶背离：当前在零轴上方，是局部峰值，且比前一个峰更低
        if cur > 0:
            prev_peak = max((v for v in lookback if v > 0), default=None)
            if prev_peak is not None and cur < prev_peak:
                signal.iloc[i] = SIG_SELL

        # 底背离：当前在零轴下方，是局部谷值，且比前一个谷更高
        if cur < 0:
            prev_trough = min((v for v in lookback if v < 0), default=None)
            if prev_trough is not None and cur > prev_trough:
                signal.iloc[i] = SIG_BUY

    return signal


if __name__ == "__main__":
    import sys
    import os
    import numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from indicators.ao import calculate_ao, ao_color

    print("=== sig_ao 信号模块测试 ===")
    np.random.seed(42)
    n     = 200
    idx   = pd.date_range("2024-01-01", periods=n, freq="h")
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5), index=idx)
    high  = close + np.abs(np.random.randn(n) * 0.3)
    low   = close - np.abs(np.random.randn(n) * 0.3)

    ao      = calculate_ao(high, low)
    colors  = ao_color(ao)

    s1 = ao_zero_cross_signal(ao)
    s2 = ao_saucer_signal(ao)
    s3 = ao_color_change_signal(ao, colors)
    s4 = ao_twin_peaks_signal(ao)

    for name, s in [
        ("零轴穿越", s1), ("蝶形形态", s2),
        ("颜色变化", s3), ("双峰双谷", s4)
    ]:
        print(f"[{name}] 买入: {(s==1).sum()}  卖出: {(s==-1).sum()}")
    print("=== 测试完成 ===")
