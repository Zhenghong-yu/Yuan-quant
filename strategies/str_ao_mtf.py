# -*- coding: utf-8 -*-
"""
策略模块 - AO 多时间框架共振策略 (strategies/str_ao_mtf.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【策略说明】
  执行链：indicators → signals → [此策略] → connector

  核心信号 : ao_color_change_signal（弱转强）
  共振逻辑 : M1/M5/M15 三时间框架同时满足各自条件
  止损     : AO 信号反向且持仓亏损时平仓
  止盈     : 盈利且持仓满 2 根 M1 K线后平仓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config import AO_MTF_CONFIG
from connector import MT5Client, OrderManager
from indicators.ao import calculate_ao, ao_color
from signals.sig_ao import ao_color_change_signal
from signals.base import SIG_BUY, SIG_SELL
from utils.logger import get_logger

logger = get_logger(__name__)


class AOMTFStrategy:
    """AO 多时间框架共振策略（指标 → 信号 → 执行）。"""

    def __init__(self, config: dict = None):
        self.cfg             = config or AO_MTF_CONFIG
        self.client          = MT5Client()
        self.order_mgr       = OrderManager()
        self._candle_counter = {}  # ticket -> M1 K线计数

    def _tf_signal(self, timeframe: str) -> dict:
        """
        获取单时间框架 AO 信号状态。
        Returns 空 dict 表示数据不足。
        """
        df = self.client.get_rates(self.cfg["symbol"], timeframe, count=50)
        if df.empty or len(df) < 36:
            return {}

        # 指标层
        ao     = calculate_ao(df["high"], df["low"])
        colors = ao_color(ao)

        # 信号层
        sig = ao_color_change_signal(ao, colors)

        cur_ao   = ao.iloc[-2]
        cur_sig  = int(sig.iloc[-2])
        cur_col  = colors.iloc[-2]
        prev_col = colors.iloc[-3] if len(colors) > 2 else "neutral"

        return {
            "signal":     cur_sig,
            "above_zero": cur_ao > 0,
            "below_zero": cur_ao < 0,
            "color":      cur_col,
            "prev_color": prev_col,
        }

    def _check_long_signal(self) -> bool:
        """M1 由红变绿(零轴上方) + M5/M15 绿色或由红变绿(零轴上方)。"""
        tf_list = self.cfg["timeframes"]
        states  = {tf: self._tf_signal(tf) for tf in tf_list}
        if any(not s for s in states.values()):
            return False
        m1, m5, m15 = states[tf_list[0]], states[tf_list[1]], states[tf_list[2]]
        c_m1  = m1["above_zero"]  and m1["signal"] == SIG_BUY
        c_m5  = m5["above_zero"]  and (m5["signal"] == SIG_BUY or
                (m5["color"] == "green" and m5["prev_color"] == "green"))
        c_m15 = m15["above_zero"] and (m15["signal"] == SIG_BUY or
                (m15["color"] == "green" and m15["prev_color"] == "green"))
        return c_m1 and c_m5 and c_m15

    def _check_short_signal(self) -> bool:
        """M1 由绿变红(零轴下方) + M5/M15 红色或由绿变红(零轴下方)。"""
        tf_list = self.cfg["timeframes"]
        states  = {tf: self._tf_signal(tf) for tf in tf_list}
        if any(not s for s in states.values()):
            return False
        m1, m5, m15 = states[tf_list[0]], states[tf_list[1]], states[tf_list[2]]
        c_m1  = m1["below_zero"]  and m1["signal"] == SIG_SELL
        c_m5  = m5["below_zero"]  and (m5["signal"] == SIG_SELL or
                (m5["color"] == "red" and m5["prev_color"] == "red"))
        c_m15 = m15["below_zero"] and (m15["signal"] == SIG_SELL or
                (m15["color"] == "red" and m15["prev_color"] == "red"))
        return c_m1 and c_m5 and c_m15

    def _manage_positions(self):
        """检查止损/止盈。"""
        if mt5 is None:
            return
        positions = self.order_mgr.get_positions(
            symbol=self.cfg["symbol"], magic=self.cfg["magic"]
        )
        m1 = self._tf_signal(self.cfg["timeframes"][0])
        if not m1:
            return
        for pos in positions:
            t = pos.ticket
            self._candle_counter.setdefault(t, 0)
            self._candle_counter[t] += 1
            is_profit = pos.profit > 0
            is_long   = pos.type == mt5.ORDER_TYPE_BUY
            color_flip = ((is_long and m1["signal"] == SIG_SELL) or
                          (not is_long and m1["signal"] == SIG_BUY))
            if color_flip and not is_profit:
                logger.info(f"止损 ticket={t} profit={pos.profit:.2f}")
                self.order_mgr.close_position(pos)
                self._candle_counter.pop(t, None)
                continue
            if is_profit and self._candle_counter[t] >= self.cfg.get("tp_candles", 2):
                logger.info(f"止盈 ticket={t} profit={pos.profit:.2f}")
                self.order_mgr.close_position(pos)
                self._candle_counter.pop(t, None)

    def run_once(self):
        """执行一次完整策略检查。"""
        self._manage_positions()
        if self.order_mgr.get_positions(
            symbol=self.cfg["symbol"], magic=self.cfg["magic"]
        ):
            return
        if self._check_long_signal():
            logger.info("AO MTF 做多信号")
            self.order_mgr.open_buy(self.cfg["symbol"], self.cfg["lot"],
                                    magic=self.cfg["magic"],
                                    comment=self.cfg["comment"])
        elif self._check_short_signal():
            logger.info("AO MTF 做空信号")
            self.order_mgr.open_sell(self.cfg["symbol"], self.cfg["lot"],
                                     magic=self.cfg["magic"],
                                     comment=self.cfg["comment"])

    def run(self, interval_seconds: int = 30):
        """持续运行策略主循环。"""
        if not self.client.connect():
            logger.error("无法连接 MT5")
            return
        logger.info(f"AO MTF 策略启动 | {self.cfg['symbol']} {self.cfg['timeframes']}")
        try:
            while True:
                self.run_once()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("策略手动停止")
        finally:
            self.client.disconnect()


if __name__ == "__main__":
    print("=== AOMTFStrategy 测试 ===")
    strategy = AOMTFStrategy()
    if not strategy.client.connect():
        print("MT5 连接失败，测试中止")
        exit(1)
    from config import AO_MTF_CONFIG
    for tf in AO_MTF_CONFIG["timeframes"]:
        state = strategy._tf_signal(tf)
        if state:
            print(f"[{tf}] signal={state['signal']}  "
                  f"above={state['above_zero']}  "
                  f"color={state['color']}  prev={state['prev_color']}")
        else:
            print(f"[{tf}] 数据不足")
    print(f"做多共振: {strategy._check_long_signal()}")
    print(f"做空共振: {strategy._check_short_signal()}")
    strategy.client.disconnect()
    print("=== 测试完成 ===")
