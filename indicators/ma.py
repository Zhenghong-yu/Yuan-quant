# -*- coding: utf-8 -*-
"""
指标模块 - MA（Moving Average，移动平均线）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模块职责】
  本模块只负责「计算」，输出原始指标数值。
  交易信号的判断请使用 signals/sig_ma.py。

  数据流：K线数据 → indicators/ma.py（计算值）→ signals/sig_ma.py（信号）→ strategies/

【支持均线类型】
  SMA（Simple Moving Average）      简单移动平均
  EMA（Exponential Moving Average） 指数移动平均
  WMA（Weighted Moving Average）    加权移动平均

【常用周期】
  MA5 / MA10 / MA20 / MA60 / MA120 / MA250
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
from typing import Literal

DEFAULT_PERIODS = [5, 10, 20, 60, 120, 250]


def calculate_ma(
    close: pd.Series,
    period: int,
    ma_type: Literal["SMA", "EMA", "WMA"] = "SMA",
) -> pd.Series:
    """
    计算单条移动平均线。

    Parameters
    ----------
    close   : 收盘价序列
    period  : 均线周期
    ma_type : 均线类型 ('SMA' | 'EMA' | 'WMA')，默认 'SMA'

    Returns
    -------
    pd.Series  列名格式：'{MA_TYPE}{period}'，如 'SMA20'
    """
    ma_type = ma_type.upper()
    if ma_type == "SMA":
        result = close.rolling(window=period).mean()
    elif ma_type == "EMA":
        result = close.ewm(span=period, adjust=False).mean()
    elif ma_type == "WMA":
        weights = pd.Series(range(1, period + 1), dtype=float)
        result = close.rolling(window=period).apply(
            lambda x: (x * weights.values).sum() / weights.sum(), raw=True
        )
    else:
        raise ValueError(f"不支持的均线类型: {ma_type}，请选择 'SMA' / 'EMA' / 'WMA'")
    result.name = f"{ma_type}{period}"
    return result


def calculate_ma_group(
    close: pd.Series,
    periods: list = None,
    ma_type: Literal["SMA", "EMA", "WMA"] = "SMA",
) -> pd.DataFrame:
    """
    批量计算多条移动平均线。

    Parameters
    ----------
    close   : 收盘价序列
    periods : 周期列表，默认 [5, 10, 20, 60, 120, 250]
    ma_type : 均线类型，默认 'SMA'

    Returns
    -------
    pd.DataFrame  每列一条均线，列名如 'SMA5', 'SMA20' ...
    """
    if periods is None:
        periods = DEFAULT_PERIODS
    return pd.DataFrame(
        {f"{ma_type}{p}": calculate_ma(close, p, ma_type) for p in periods}
    )


if __name__ == "__main__":
    import sys
    import os
    import numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from signals.sig_ma import (
        ma_bull_alignment_signal, ma_cross_signal,
        ma_price_cross_signal, ma_fan_signal,
    )
    from visualization.plot_indicators import plot_ma_with_signals

    print("=== MA 指标模块测试 ===")
    np.random.seed(0)
    n     = 300
    idx   = pd.date_range("2024-01-01", periods=n, freq="h")
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5), index=idx)
    high  = close + np.abs(np.random.randn(n) * 0.3)
    low   = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close - np.random.randn(n) * 0.15
    df    = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})

    # 计算均线
    mas  = calculate_ma_group(close, periods=[5, 10, 20, 60, 120])
    fast = calculate_ma(close, 20)
    slow = calculate_ma(close, 60)
    print(f"[calculate_ma_group] 列: {list(mas.columns)}")
    print(f"[最新值]\n{mas.iloc[-1].to_string()}")

    # 信号（通过 signals 层）
    s_align = ma_bull_alignment_signal(mas)
    s_cross = ma_cross_signal(fast, slow)
    s_price = ma_price_cross_signal(close, slow)
    s_fan   = ma_fan_signal(fast, slow)
    for name, s in [("多头排列", s_align), ("金叉死叉", s_cross),
                    ("价格穿线", s_price), ("均线发散", s_fan)]:
        print(f"[{name}] 买入: {(s==1).sum()}  卖出: {(s==-1).sum()}")

    print("=== 测试完成 ===")
    # 可视化
    mas_vis = calculate_ma_group(close, periods=[5, 20, 60])
    plot_ma_with_signals(df=df, mas=mas_vis, signals=s_cross,
                         title="MA 指标 - 金叉死叉信号（MA20×MA60）",
                         save=True, show=True)
