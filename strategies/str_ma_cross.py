# -*- coding: utf-8 -*-
"""
策略模块 - 均线交叉策略 (strategies/str_ma_cross.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【策略说明】
  执行链：indicators → signals → [此策略] → connector

  主信号  : ma_cross_signal(MA20, MA60)   金叉做多 / 死叉做空
  过滤信号 : ma_bull_alignment_signal      多头排列时才允许做多，空头排列时才允许做空
  合并方式 : combine_signals(..., mode="all")  两个信号同向才入场
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from config.strategy_config import MA_CROSS_CONFIG
from connector import MT5Client, OrderManager
from indicators.ma import calculate_ma, calculate_ma_group
from signals.sig_ma import ma_cross_signal, ma_bull_alignment_signal
from signals.base import combine_signals, SIG_BUY, SIG_SELL
from utils.logger import get_logger
from utils.helpers import pips_to_price

logger = get_logger(__name__)


class MACrossStrategy:
    """
    均线交叉策略（指标 → 信号 → 执行）。
    信号层：ma_cross_signal(MA20, MA60)  +  ma_bull_alignment_signal 过滤。
    """

    def __init__(self, config: dict = None):
        self.cfg       = config or MA_CROSS_CONFIG
        self.client    = MT5Client()
        self.order_mgr = OrderManager()

    def _get_signal(self) -> int:
        """
        K线 → 指标 → 信号 → 返回最新已收盘 K 线信号。
        返回：1（做多）/ -1（做空）/ 0（无信号）
        """
        df = self.client.get_rates(
            symbol=self.cfg["symbol"],
            timeframe=self.cfg["timeframe"],
            count=max(self.cfg["slow_ma"], 120) + 10,
        )
        if df.empty:
            return 0

        close = df["close"]

        # ── 指标层 ──
        fast = calculate_ma(close, self.cfg["fast_ma"])
        slow = calculate_ma(close, self.cfg["slow_ma"])
        mas  = calculate_ma_group(close, periods=[5, 20, 60, 120])

        # ── 信号层 ──
        sig_cross = ma_cross_signal(fast, slow)
        sig_align = ma_bull_alignment_signal(mas)

        # ── 策略层：两个信号同向才入场（AND 共振）──
        combined = combine_signals(
            {"cross": sig_cross, "align": sig_align},
            mode="all",
        )
        return int(combined.iloc[-2])  # 取最后一根已收盘 K 线

    def _get_sl_tp(self, direction: int):
        """计算止损/止盈绝对价格。"""
        try:
            import MetaTrader5 as mt5
            tick      = mt5.symbol_info_tick(self.cfg["symbol"])
            sl_offset = pips_to_price(self.cfg["symbol"], self.cfg["sl_pips"])
            tp_offset = pips_to_price(self.cfg["symbol"], self.cfg["tp_pips"])
            if direction == SIG_BUY:
                price = tick.ask
                return (price - sl_offset) if self.cfg["sl_pips"] else 0.0, \
                       (price + tp_offset) if self.cfg["tp_pips"] else 0.0
            else:
                price = tick.bid
                return (price + sl_offset) if self.cfg["sl_pips"] else 0.0, \
                       (price - tp_offset) if self.cfg["tp_pips"] else 0.0
        except Exception:
            return 0.0, 0.0

    def run_once(self):
        """执行一次策略检查。"""
        signal = self._get_signal()
        if signal == 0:
            return

        symbol = self.cfg["symbol"]
        magic  = self.cfg["magic"]
        lot    = self.cfg["lot"]

        try:
            import MetaTrader5 as mt5
            positions = self.order_mgr.get_positions(symbol=symbol, magic=magic)
            for pos in positions:
                if (signal == SIG_BUY  and pos.type == mt5.ORDER_TYPE_SELL) or \
                   (signal == SIG_SELL and pos.type == mt5.ORDER_TYPE_BUY):
                    self.order_mgr.close_position(pos)
            if self.order_mgr.get_positions(symbol=symbol, magic=magic):
                return
        except ImportError:
            pass

        sl, tp = self._get_sl_tp(signal)
        if signal == SIG_BUY:
            self.order_mgr.open_buy(symbol, lot, sl=sl, tp=tp,
                                    magic=magic, comment=self.cfg["comment"])
        else:
            self.order_mgr.open_sell(symbol, lot, sl=sl, tp=tp,
                                     magic=magic, comment=self.cfg["comment"])

    def run(self, interval_seconds: int = 60):
        """持续运行策略主循环。"""
        if not self.client.connect():
            logger.error("无法连接 MT5，策略退出")
            return
        logger.info(f"MA Cross 策略启动 | {self.cfg['symbol']} {self.cfg['timeframe']}")
        try:
            while True:
                self.run_once()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("策略手动停止")
        finally:
            self.client.disconnect()


if __name__ == "__main__":
    print("=== MACrossStrategy 测试 ===")
    strategy = MACrossStrategy()
    if not strategy.client.connect():
        print("MT5 连接失败")
        exit(1)
    signal = strategy._get_signal()
    print(f"当前信号: {signal} ({'+做多' if signal==1 else '-做空' if signal==-1 else '无信号'})")
    strategy.client.disconnect()
    print("=== 测试完成 ===")
