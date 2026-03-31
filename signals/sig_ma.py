# -*- coding: utf-8 -*-
"""
信号模块 - MA 均线信号 (signals/sig_ma.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模块说明】
  本模块基于 indicators/ma.py 计算出的均线值，定义多种 MA 信号。
  信号函数只做「判断」，不做「计算」，输入均为已算好的指标序列。

【信号列表】
  1. ma_bull_alignment_signal  均线多头排列信号
     条件：MA5 > MA10 > MA20 > MA60 > MA120（全部多头排列）
     多头排列出现 → 1，空头排列出现 → -1，否则 → 0

  2. ma_cross_signal           双均线金叉/死叉信号
     条件：快线上穿慢线 → 金叉做多；快线下穿慢线 → 死叉做空

  3. ma_price_cross_signal     价格与均线交叉信号
     条件：收盘价上穿某条均线 → 做多；下穿 → 做空

  4. ma_fan_signal             均线发散信号（均线之间距离扩大，趋势加速）
     条件：MA5-MA20 差值扩大 → 方向信号
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from signals.base import SIG_BUY, SIG_SELL, SIG_NONE


def ma_bull_alignment_signal(mas: pd.DataFrame) -> pd.Series:
    """
    均线多头/空头排列信号。
    输入 mas 的列必须按周期从小到大排列（如 SMA5, SMA20, SMA60 ...）。

    Returns
    -------
    pd.Series[int]
       1  → 多头排列（短期 > 中期 > 长期，做多）
      -1  → 空头排列（短期 < 中期 < 长期，做空）
       0  → 无明显排列
    """
    def _check(row):
        vals = row.values
        if any(v != v for v in vals):  # NaN 检查
            return SIG_NONE
        if all(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
            return SIG_BUY
        if all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
            return SIG_SELL
        return SIG_NONE

    return mas.apply(_check, axis=1).rename("MA_Alignment_Signal").astype(int)


def ma_cross_signal(fast_ma: pd.Series, slow_ma: pd.Series) -> pd.Series:
    """
    双均线金叉/死叉信号。

    Parameters
    ----------
    fast_ma : 快速均线（周期较小，如 MA20）
    slow_ma : 慢速均线（周期较大，如 MA60）

    Returns
    -------
    pd.Series[int]
       1  → 金叉（fast 上穿 slow，做多）
      -1  → 死叉（fast 下穿 slow，做空）
       0  → 无信号
    """
    prev_fast = fast_ma.shift(1)
    prev_slow = slow_ma.shift(1)
    signal = pd.Series(SIG_NONE, index=fast_ma.index, dtype=int,
                       name=f"MA_Cross_{fast_ma.name}x{slow_ma.name}")
    signal[(prev_fast <= prev_slow) & (fast_ma > slow_ma)] = SIG_BUY
    signal[(prev_fast >= prev_slow) & (fast_ma < slow_ma)] = SIG_SELL
    return signal


def ma_price_cross_signal(close: pd.Series, ma: pd.Series) -> pd.Series:
    """
    价格与均线交叉信号：收盘价穿越某条均线。

    Parameters
    ----------
    close : 收盘价序列
    ma    : 某条均线序列

    Returns
    -------
    pd.Series[int]
       1  → 价格上穿均线（做多）
      -1  → 价格下穿均线（做空）
       0  → 无信号
    """
    prev_close = close.shift(1)
    prev_ma    = ma.shift(1)
    signal = pd.Series(SIG_NONE, index=close.index, dtype=int,
                       name=f"Price_Cross_{ma.name}")
    signal[(prev_close <= prev_ma) & (close > ma)] = SIG_BUY
    signal[(prev_close >= prev_ma) & (close < ma)] = SIG_SELL
    return signal


def ma_fan_signal(
    fast_ma: pd.Series,
    slow_ma: pd.Series,
    threshold: float = 0.0,
) -> pd.Series:
    """
    均线发散信号：快慢线之间的差值持续扩大，趋势加速。

    Parameters
    ----------
    fast_ma   : 快速均线
    slow_ma   : 慢速均线
    threshold : 发散阈值（差值绝对值最小值），默认 0

    Returns
    -------
    pd.Series[int]
       1  → 多头发散（fast > slow 且差值扩大）
      -1  → 空头发散（fast < slow 且差值扩大）
       0  → 收敛或无信号
    """
    diff      = fast_ma - slow_ma
    prev_diff = diff.shift(1)
    signal = pd.Series(SIG_NONE, index=fast_ma.index, dtype=int,
                       name=f"MA_Fan_{fast_ma.name}x{slow_ma.name}")
    # 多头发散：diff > 0 且绝对值在增大
    signal[(diff > threshold) & (diff > prev_diff.abs())] = SIG_BUY
    # 空头发散：diff < 0 且绝对值在增大
    signal[(diff < -threshold) & (diff.abs() > prev_diff.abs())] = SIG_SELL
    return signal


if __name__ == "__main__":
    import sys
    import os
    import numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from indicators.ma import calculate_ma, calculate_ma_group

    print("=== sig_ma 信号模块测试 ===")
    np.random.seed(1)
    n     = 300
    idx   = pd.date_range("2024-01-01", periods=n, freq="h")
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5), index=idx)

    mas = calculate_ma_group(close, periods=[5, 20, 60, 120])
    fast = calculate_ma(close, 20)
    slow = calculate_ma(close, 60)

    s1 = ma_bull_alignment_signal(mas)
    s2 = ma_cross_signal(fast, slow)
    s3 = ma_price_cross_signal(close, slow)
    s4 = ma_fan_signal(fast, slow)

    for name, s in [("多头排列", s1), ("金叉死叉", s2), ("价格穿线", s3), ("均线发散", s4)]:
        print(f"[{name}] 买入: {(s==1).sum()}  卖出: {(s==-1).sum()}")
    print("=== 测试完成 ===")
