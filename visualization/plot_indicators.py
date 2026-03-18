# -*- coding: utf-8 -*-
"""
可视化模块 - 指标图表 (visualization/plot_indicators.py)
绘制价格与指标叠加图（MA、AO 等），支持买卖信号标注。
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

MA_COLORS = {
    5:   "#FF9800",
    20:  "#2196F3",
    60:  "#9C27B0",
    120: "#F44336",
    250: "#4CAF50",
}


# ─────────────────────────────────────────────────────────────
# MA 均线图（含买卖信号）
# ─────────────────────────────────────────────────────────────

def plot_ma(
    df: pd.DataFrame,
    mas: pd.DataFrame,
    title: str = "Price & MA",
    save: bool = False,
    show: bool = True,
):
    """
    绘制收盘价与多条均线叠加图（不含信号标注）。

    Parameters
    ----------
    df   : K 线 DataFrame（含 close 列，time 为索引）
    mas  : 均线 DataFrame，每列一条均线（列名如 SMA5, SMA20 ...）
    """
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(df.index, df["close"], color="#37474F", linewidth=1,
            label="Close", alpha=0.8)

    for col in mas.columns:
        period = int("".join(filter(str.isdigit, col)))
        color  = MA_COLORS.get(period, "#607D8B")
        ax.plot(mas.index, mas[col], linewidth=1.2, label=col, color=color)

    ax.set_title(title, fontsize=13)
    ax.set_ylabel("Price")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()

    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        path = os.path.join(RESULTS_DIR, f"{title.replace(' ', '_')}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        print(f"图表已保存: {path}")

    if show:
        plt.show()
    plt.close(fig)


def plot_ma_with_signals(
    df: pd.DataFrame,
    mas: pd.DataFrame,
    signals: pd.Series,
    title: str = "Price & MA & Signals",
    save: bool = True,
    show: bool = True,
):
    """
    绘制 K 线收盘价 + 多条均线 + 金叉/死叉买卖信号三合一图。

    Parameters
    ----------
    df      : K 线 DataFrame（含 open/high/low/close 列，time 为索引）
    mas     : 均线 DataFrame（列名如 SMA5, SMA20 ...）
    signals : 信号序列（1=金叉买入, -1=死叉卖出, 0=无信号）
    title   : 图表标题
    save    : 是否保存到 results/ 目录
    show    : 是否弹窗显示
    """
    fig = plt.figure(figsize=(16, 8), facecolor="#1C1C2E")
    fig.suptitle(title, fontsize=14, fontweight="bold", color="#E0E0E0")
    gs = gridspec.GridSpec(3, 1, height_ratios=[4, 1, 0.6], hspace=0.08)

    # ── 子图1：K线 + 均线 + 信号 ──
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor("#12122A")

    # 绘制 K 线（蜡烛图简化为上涨绿/下跌红竖线 + close 折线）
    for i in range(len(df)):
        o = df["open"].iloc[i]
        c = df["close"].iloc[i]
        h = df["high"].iloc[i]
        lo = df["low"].iloc[i]
        x = df.index[i]
        color = "#00C853" if c >= o else "#FF1744"
        ax1.plot([x, x], [lo, h], color=color, linewidth=0.5, alpha=0.6)
        ax1.plot([x, x], [o, c],  color=color, linewidth=2.5)

    # 绘制均线
    for col in mas.columns:
        period = int("".join(filter(str.isdigit, col)))
        color  = MA_COLORS.get(period, "#90A4AE")
        ax1.plot(mas.index, mas[col], linewidth=1.3, label=col,
                 color=color, alpha=0.9)

    # 绘制买卖信号
    buy_idx  = signals[signals == 1].index
    sell_idx = signals[signals == -1].index
    if len(buy_idx):
        ax1.scatter(buy_idx,  df.loc[buy_idx,  "low"]  * 0.999,
                    marker="^", color="#00E676", s=120, zorder=6,
                    label="金叉买入", edgecolors="white", linewidths=0.5)
    if len(sell_idx):
        ax1.scatter(sell_idx, df.loc[sell_idx, "high"] * 1.001,
                    marker="v", color="#FF1744", s=120, zorder=6,
                    label="死叉卖出", edgecolors="white", linewidths=0.5)

    ax1.set_ylabel("Price", color="#B0BEC5")
    ax1.tick_params(colors="#B0BEC5", labelbottom=False)
    ax1.legend(loc="upper left", fontsize=8, facecolor="#1C1C2E",
               labelcolor="#E0E0E0", framealpha=0.7)
    ax1.grid(alpha=0.15, color="#455A64")
    for spine in ax1.spines.values():
        spine.set_edgecolor("#37474F")

    # ── 子图2：两条主均线差值（类似 MACD 柱） ──
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.set_facecolor("#12122A")

    # 取第一快线和最后慢线的差
    cols = list(mas.columns)
    if len(cols) >= 2:
        diff = mas[cols[0]] - mas[cols[-1]]
        bar_colors = ["#00C853" if v >= 0 else "#FF1744" for v in diff]
        ax2.bar(diff.index, diff.values, color=bar_colors, alpha=0.75, width=0.02)
        ax2.axhline(0, color="#90A4AE", linewidth=0.7, linestyle="--")
        ax2.set_ylabel(f"{cols[0]}-{cols[-1]}", color="#B0BEC5", fontsize=7)
    ax2.tick_params(colors="#B0BEC5", labelbottom=False)
    ax2.grid(alpha=0.15, color="#455A64")
    for spine in ax2.spines.values():
        spine.set_edgecolor("#37474F")

    # ── 子图3：信号条 ──
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.set_facecolor("#12122A")
    sig_colors = signals.map({1: "#00E676", -1: "#FF1744", 0: "#263238"})
    ax3.bar(signals.index, [1] * len(signals),
            color=sig_colors.values, width=0.02, alpha=0.9)
    ax3.set_yticks([])
    ax3.set_ylabel("Signal", color="#B0BEC5", fontsize=7)
    ax3.tick_params(colors="#B0BEC5")
    ax3.grid(alpha=0.1, color="#455A64")
    for spine in ax3.spines.values():
        spine.set_edgecolor("#37474F")

    plt.tight_layout()

    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        safe = title.replace(" ", "_").replace("/", "-").replace("&", "and")
        path = os.path.join(RESULTS_DIR, f"{safe}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"图表已保存: {path}")

    if show:
        plt.show()
    plt.close(fig)


# ─────────────────────────────────────────────────────────────
# AO 指标图（含买卖信号）
# ─────────────────────────────────────────────────────────────

def plot_ao(
    df: pd.DataFrame,
    ao: pd.Series,
    title: str = "Price & AO",
    save: bool = False,
    show: bool = True,
):
    """
    绘制收盘价与 AO 指标双联图（不含信号标注）。

    Parameters
    ----------
    df : K 线 DataFrame
    ao : AO 值序列
    """
    fig = plt.figure(figsize=(16, 8))
    gs  = gridspec.GridSpec(2, 1, height_ratios=[2, 1], hspace=0.25)

    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df.index, df["close"], color="#37474F", linewidth=1)
    ax1.set_ylabel("Price")
    ax1.set_title(title, fontsize=13)
    ax1.grid(alpha=0.3)

    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    diff = ao.diff()
    colors = ["#00C853" if d >= 0 else "#FF1744" for d in diff]
    ax2.bar(ao.index, ao.values, color=colors, width=0.6, alpha=0.85)
    ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax2.set_ylabel("AO")
    ax2.grid(alpha=0.3)

    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.tight_layout()

    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        path = os.path.join(RESULTS_DIR, f"{title.replace(' ', '_')}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        print(f"图表已保存: {path}")

    if show:
        plt.show()
    plt.close(fig)


def plot_ao_with_signals(
    df: pd.DataFrame,
    ao: pd.Series,
    signals: pd.Series,
    signal_label: str = "Zero Cross",
    title: str = "Price & AO & Signals",
    save: bool = True,
    show: bool = True,
):
    """
    绘制 K 线 + AO 柱状图 + 买卖信号三联图。

    Parameters
    ----------
    df           : K 线 DataFrame（含 open/high/low/close 列）
    ao           : AO 值序列
    signals      : 信号序列（1=买入, -1=卖出, 0=无信号）
    signal_label : 信号类型描述（用于图例），如 'Zero Cross' 或 'Saucer'
    title        : 图表标题
    save         : 是否保存图片
    show         : 是否弹窗显示
    """
    fig = plt.figure(figsize=(16, 10), facecolor="#1C1C2E")
    fig.suptitle(title, fontsize=14, fontweight="bold", color="#E0E0E0")
    gs = gridspec.GridSpec(3, 1, height_ratios=[3, 2, 0.6], hspace=0.08)

    # ── 子图1：K 线蜡烛图 + 买卖信号 ──
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor("#12122A")

    for i in range(len(df)):
        o  = df["open"].iloc[i]
        c  = df["close"].iloc[i]
        h  = df["high"].iloc[i]
        lo = df["low"].iloc[i]
        x  = df.index[i]
        color = "#00C853" if c >= o else "#FF1744"
        ax1.plot([x, x], [lo, h], color=color, linewidth=0.5, alpha=0.6)
        ax1.plot([x, x], [o, c],  color=color, linewidth=2.5)

    buy_idx  = signals[signals == 1].index
    sell_idx = signals[signals == -1].index
    if len(buy_idx):
        ax1.scatter(
            buy_idx, df.loc[buy_idx, "low"] * 0.999,
            marker="^", color="#00E676", s=130, zorder=6,
            label=f"{signal_label} 买入", edgecolors="white", linewidths=0.5,
        )
    if len(sell_idx):
        ax1.scatter(
            sell_idx, df.loc[sell_idx, "high"] * 1.001,
            marker="v", color="#FF5252", s=130, zorder=6,
            label=f"{signal_label} 卖出", edgecolors="white", linewidths=0.5,
        )

    ax1.set_ylabel("Price", color="#B0BEC5")
    ax1.tick_params(colors="#B0BEC5", labelbottom=False)
    ax1.legend(loc="upper left", fontsize=9, facecolor="#1C1C2E",
               labelcolor="#E0E0E0", framealpha=0.7)
    ax1.grid(alpha=0.15, color="#455A64")
    for spine in ax1.spines.values():
        spine.set_edgecolor("#37474F")

    # ── 子图2：AO 柱状图（绿涨红跌）+ 零轴 ──
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.set_facecolor("#12122A")

    ao_diff = ao.diff()
    ao_colors = ["#00C853" if (v == v and v >= 0) else "#FF1744" for v in ao_diff]
    ax2.bar(ao.index, ao.values, color=ao_colors, alpha=0.85, width=0.02)
    ax2.axhline(0, color="#90A4AE", linewidth=0.9, linestyle="--", alpha=0.8)

    # 在零轴穿越处标记信号
    if len(buy_idx):
        ax2.scatter(buy_idx, ao.loc[buy_idx],
                    marker="o", color="#00E676", s=60, zorder=6, alpha=0.9)
    if len(sell_idx):
        ax2.scatter(sell_idx, ao.loc[sell_idx],
                    marker="o", color="#FF5252", s=60, zorder=6, alpha=0.9)

    ax2.set_ylabel("AO", color="#B0BEC5")
    ax2.tick_params(colors="#B0BEC5", labelbottom=False)
    ax2.grid(alpha=0.15, color="#455A64")
    for spine in ax2.spines.values():
        spine.set_edgecolor("#37474F")

    # ── 子图3：信号条 ──
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.set_facecolor("#12122A")
    sig_colors = signals.map({1: "#00E676", -1: "#FF5252", 0: "#263238"})
    ax3.bar(signals.index, [1] * len(signals),
            color=sig_colors.values, width=0.02, alpha=0.9)
    ax3.set_yticks([])
    ax3.set_ylabel("Signal", color="#B0BEC5", fontsize=7)
    ax3.tick_params(colors="#B0BEC5")
    ax3.grid(alpha=0.1, color="#455A64")
    for spine in ax3.spines.values():
        spine.set_edgecolor("#37474F")

    plt.tight_layout()

    if save:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        safe = title.replace(" ", "_").replace("/", "-").replace("&", "and")
        path = os.path.join(RESULTS_DIR, f"{safe}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"图表已保存: {path}")

    if show:
        plt.show()
    plt.close(fig)
