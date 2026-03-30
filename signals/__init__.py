# -*- coding: utf-8 -*-
from .base import SIG_BUY, SIG_SELL, SIG_NONE, combine_signals
from .sig_ma import (
    ma_bull_alignment_signal,
    ma_cross_signal,
    ma_price_cross_signal,
    ma_fan_signal,
)
from .sig_ao import (
    ao_zero_cross_signal,
    ao_saucer_signal,
    ao_color_change_signal,
    ao_twin_peaks_signal,
)

__all__ = [
    # 常量
    "SIG_BUY", "SIG_SELL", "SIG_NONE",
    # 工具
    "combine_signals",
    # MA 信号
    "ma_bull_alignment_signal",
    "ma_cross_signal",
    "ma_price_cross_signal",
    "ma_fan_signal",
    # AO 信号
    "ao_zero_cross_signal",
    "ao_saucer_signal",
    "ao_color_change_signal",
    "ao_twin_peaks_signal",
]
