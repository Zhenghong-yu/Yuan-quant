# -*- coding: utf-8 -*-
"""
信号基类模块 (signals/base.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【设计说明】
  信号模块是指标层与策略层之间的桥梁。

  数据流向：
    K线数据
      └─▶ indicators/（纯计算，输出指标值 pd.Series / pd.DataFrame）
              └─▶ signals/（纯判断，输出信号 pd.Series[int] 1/-1/0）
                      └─▶ strategies/（组合多个信号，驱动执行）

  信号值约定：
    1  → 做多信号（Buy）
   -1  → 做空信号（Sell）
    0  → 无信号（Hold）

  所有信号函数遵循统一接口：
    输入：已计算好的指标值（pd.Series 或 pd.DataFrame）
    输出：pd.Series[int]，索引与输入对齐
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
from typing import Dict

# 信号值常量
SIG_BUY  =  1
SIG_SELL = -1
SIG_NONE =  0


def combine_signals(
    signals: Dict[str, pd.Series],
    mode: str = "all",
) -> pd.Series:
    """
    组合多个信号序列，生成最终交易信号。

    Parameters
    ----------
    signals : dict  {信号名: pd.Series[int]}，所有序列索引必须对齐
    mode    : str
        "all"   → 所有信号同向才触发（严格共振，AND 逻辑）
        "any"   → 任意信号触发即生效（宽松，OR 逻辑）
        "vote"  → 多数票决定（超过半数同向则触发）

    Returns
    -------
    pd.Series[int]  合并后的信号序列
    """
    if not signals:
        raise ValueError("signals 不能为空")

    series_list = list(signals.values())
    # 对齐索引
    index = series_list[0].index
    df = pd.DataFrame({k: v.reindex(index).fillna(0) for k, v in signals.items()})

    result = pd.Series(SIG_NONE, index=index, dtype=int, name="Combined_Signal")
    n = len(df.columns)

    if mode == "all":
        # 所有信号都为 1 → 做多；所有信号都为 -1 → 做空
        result[(df == SIG_BUY).all(axis=1)]  = SIG_BUY
        result[(df == SIG_SELL).all(axis=1)] = SIG_SELL

    elif mode == "any":
        # 任意信号为 1 且无反向信号 → 做多
        result[(df == SIG_BUY).any(axis=1)  & ~(df == SIG_SELL).any(axis=1)] = SIG_BUY
        result[(df == SIG_SELL).any(axis=1) & ~(df == SIG_BUY).any(axis=1)]  = SIG_SELL

    elif mode == "vote":
        buy_votes  = (df == SIG_BUY).sum(axis=1)
        sell_votes = (df == SIG_SELL).sum(axis=1)
        result[buy_votes  > n / 2] = SIG_BUY
        result[sell_votes > n / 2] = SIG_SELL

    else:
        raise ValueError(f"不支持的 mode: {mode}，请选择 'all' / 'any' / 'vote'")

    return result
