# -*- coding: utf-8 -*-
"""
工具模块 - 通用辅助函数 (utils/helpers.py)
"""

import pandas as pd
import MetaTrader5 as mt5
from config import TIMEFRAMES


def pips_to_price(symbol: str, pips: float) -> float:
    """
    将点数（pips）转换为价格偏移量。
    不同品种的 point 值不同（如 EURUSD point=0.00001）。
    """
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"无法获取品种信息: {symbol}")
    return pips * info.point


def price_to_pips(symbol: str, price_diff: float) -> float:
    """将价格偏移量转换为点数。"""
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"无法获取品种信息: {symbol}")
    return price_diff / info.point


def timeframe_to_mt5(timeframe: str) -> int:
    """将时间框架字符串转为 MT5 常量。"""
    tf = TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        raise ValueError(f"未知时间框架: {timeframe}")
    return tf


def ensure_series(data, name: str = None) -> pd.Series:
    """确保输入为 pd.Series，若为 DataFrame 则取第一列。"""
    if isinstance(data, pd.DataFrame):
        data = data.iloc[:, 0]
    if name:
        data = data.rename(name)
    return data


if __name__ == "__main__":
    print("=== helpers 工具模块测试 ===")

    # 1. 测试 timeframe_to_mt5（不需要 MT5 连接）
    tf_cases = ["M1", "M5", "M15", "H1", "H4", "D1"]
    for tf in tf_cases:
        val = timeframe_to_mt5(tf)
        print(f"[timeframe_to_mt5] {tf} -> MT5常量值: {val}")

    # 测试非法时间框架
    try:
        timeframe_to_mt5("X99")
    except ValueError as e:
        print(f"[timeframe_to_mt5] 非法输入捕获正常: {e}")

    # 2. 测试 ensure_series
    df_test = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
    s = ensure_series(df_test, name="test_col")
    assert isinstance(s, pd.Series), "ensure_series 应返回 pd.Series"
    assert s.name == "test_col", "列名应为 test_col"
    print(f"[ensure_series] DataFrame -> Series 转换成功，name={s.name}, values={s.values}")

    s2 = ensure_series(pd.Series([10, 20, 30]), name="renamed")
    assert s2.name == "renamed"
    print(f"[ensure_series] Series 重命名成功，name={s2.name}")

    # 3. 测试 pips_to_price / price_to_pips（需要 MT5 连接，跳过并提示）
    print("[pips_to_price / price_to_pips] 需要 MT5 连接，跳过（在实盘环境中测试）")

    print("=== 测试完成 ===")
