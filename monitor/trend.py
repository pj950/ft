# monitor/trend.py
import numpy as np
import talib
from futu import *
from .utils import cooldown_checker
from .trend_math import fft_signal, derivative_signal, wavelet_signal, rolling_regression_signal


def detect_signals(close, indicators, weights):
    """检测单周期信号，返回信号方向和来源"""
    signals = []
    sources = []
    total_score = 0

    # === 技术指标 ===
    if indicators.get("ma", True):
        ma5 = talib.SMA(close, timeperiod=5)
        ma20 = talib.SMA(close, timeperiod=20)
        if ma5[-1] > ma20[-1] and ma5[-2] <= ma20[-2]:
            signals.append("买入"); sources.append("MA"); total_score += weights.get("ma", 1)
        elif ma5[-1] < ma20[-1] and ma5[-2] >= ma20[-2]:
            signals.append("卖出"); sources.append("MA"); total_score -= weights.get("ma", 1)

    if indicators.get("macd", True):
        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        if macd[-1] > signal[-1] and macd[-2] <= signal[-2]:
            signals.append("买入"); sources.append("MACD"); total_score += weights.get("macd", 1)
        elif macd[-1] < signal[-1] and macd[-2] >= signal[-2]:
            signals.append("卖出"); sources.append("MACD"); total_score -= weights.get("macd", 1)

    if indicators.get("rsi", True):
        rsi = talib.RSI(close, timeperiod=14)
        if rsi[-1] < 30 and rsi[-2] >= 30:
            signals.append("买入"); sources.append("RSI"); total_score += weights.get("rsi", 1)
        elif rsi[-1] > 70 and rsi[-2] <= 70:
            signals.append("卖出"); sources.append("RSI"); total_score -= weights.get("rsi", 1)

    if indicators.get("boll", True):
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        if close[-1] < lower[-1] and close[-2] >= lower[-2]:
            signals.append("买入"); sources.append("BOLL"); total_score += weights.get("boll", 1)
        elif close[-1] > upper[-1] and close[-2] <= upper[-2]:
            signals.append("卖出"); sources.append("BOLL"); total_score -= weights.get("boll", 1)

    # === 数学方法 ===
    if indicators.get("fft", False):
        sig = fft_signal(close)
        if sig: signals.append(sig); sources.append("FFT")
        if sig == "买入": total_score += weights.get("fft", 1)
        if sig == "卖出": total_score -= weights.get("fft", 1)

    if indicators.get("derivative", False):
        sig = derivative_signal(close)
        if sig: signals.append(sig); sources.append("DERIV")
        if sig == "买入": total_score += weights.get("derivative", 1)
        if sig == "卖出": total_score -= weights.get("derivative", 1)

    if indicators.get("wavelet", False):
        sig = wavelet_signal(close)
        if sig: signals.append(sig); sources.append("WAVELET")
        if sig == "买入": total_score += weights.get("wavelet", 1)
        if sig == "卖出": total_score -= weights.get("wavelet", 1)

    if indicators.get("regression", False):
        sig = rolling_regression_signal(close)
        if sig: signals.append(sig); sources.append("REG")
        if sig == "买入": total_score += weights.get("regression", 1)
        if sig == "卖出": total_score -= weights.get("regression", 1)

    # === 综合信号 ===
    if not signals:
        return None, 0, sources

    if total_score > 0:
        return "买入", abs(total_score), sources
    elif total_score < 0:
        return "卖出", abs(total_score), sources
    return None, 0, sources


def check_trend(quote_ctx, code, holdings, config):
    """多周期趋势检测"""
    periods = {
        "1小时": KLType.K_60M,
        "2小时": KLType.K_60M,  # 手动取两根拼成2h
        "4小时": KLType.K_60M,  # 手动取四根拼成4h
        "日线": KLType.K_DAY
    }

    weights = config.get("weights", {})
    signals_summary = {}
    final_action = None
    final_score = 0
    used_periods = []
    all_sources = []

    for pname, kltype in periods.items():
        ret, data = quote_ctx.get_cur_kline(code, config["kline_num"], kl_type=kltype)
        if ret != RET_OK or data.empty:
            continue

        close = data["close"].values.astype(float)
        if pname == "2小时":
            close = close[::2]  # 简单取样
        elif pname == "4小时":
            close = close[::4]

        action, score, sources = detect_signals(close, config["indicators"], weights)
        if action:
            signals_summary[pname] = (action, score, sources)
            used_periods.append(pname)
            all_sources.extend(sources)

    if not signals_summary:
        return None

    # === 多周期确认 ===
    buy_count = sum(1 for a, _, _ in signals_summary.values() if a == "买入")
    sell_count = sum(1 for a, _, _ in signals_summary.values() if a == "卖出")

    if buy_count > sell_count:
        final_action = "买入"
    elif sell_count > buy_count:
        final_action = "卖出"

    if not final_action:
        return None

    # 计算总分
    final_score = sum(score for a, score, _ in signals_summary.values() if a == final_action)

    # === 持仓判断 ===
    if code in holdings:
        if final_action != "卖出":
            return None
    else:
        if final_action != "买入":
            return None

    # === 冷却控制 ===
    if not cooldown_checker(code, "多周期", final_action, config["signal"]["cooldown_minutes"]):
        return None

    # === 返回格式 ===
    color = "🔴" if final_action == "买入" else "🟢"
    sources_str = ",".join(set(all_sources))
    periods_str = ",".join(used_periods)

    return f"【{code}】 多周期一致 {final_action} {color} 强度: {final_score}\n来源: {sources_str}\n周期: {periods_str}"
