# monitor/trend.py
import numpy as np
import talib
from futu import *
from .utils import cooldown_checker
from .trend_math import fft_signal, derivative_signal, wavelet_signal, rolling_regression_signal


def check_trend(quote_ctx, code, kl_type, period_name, holdings, config):
    """检测趋势反转信号（技术指标 + 数学方法）"""
    ret, data = quote_ctx.get_cur_kline(code, config["kline_num"], kl_type=kl_type)
    if ret != RET_OK or data.empty:
        return None

    close = data["close"].values.astype(float)
    if len(close) < 50:
        return None

    signals = []
    sources = []

    # === 技术指标 ===
    if config["indicators"].get("ma", True):
        ma5 = talib.SMA(close, timeperiod=5)
        ma20 = talib.SMA(close, timeperiod=20)
        if ma5[-1] > ma20[-1] and ma5[-2] <= ma20[-2]:
            signals.append("买入"); sources.append("MA")
        elif ma5[-1] < ma20[-1] and ma5[-2] >= ma20[-2]:
            signals.append("卖出"); sources.append("MA")

    if config["indicators"].get("macd", True):
        macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        if macd[-1] > signal[-1] and macd[-2] <= signal[-2]:
            signals.append("买入"); sources.append("MACD")
        elif macd[-1] < signal[-1] and macd[-2] >= signal[-2]:
            signals.append("卖出"); sources.append("MACD")

    if config["indicators"].get("rsi", True):
        rsi = talib.RSI(close, timeperiod=14)
        if rsi[-1] < 30 and rsi[-2] >= 30:
            signals.append("买入"); sources.append("RSI")
        elif rsi[-1] > 70 and rsi[-2] <= 70:
            signals.append("卖出"); sources.append("RSI")

    if config["indicators"].get("boll", True):
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        if close[-1] < lower[-1] and close[-2] >= lower[-2]:
            signals.append("买入"); sources.append("BOLL")
        elif close[-1] > upper[-1] and close[-2] <= upper[-2]:
            signals.append("卖出"); sources.append("BOLL")

    # === 数学方法 ===
    if config["indicators"].get("fft", False):
        sig = fft_signal(close)
        if sig: signals.append(sig); sources.append("FFT")

    if config["indicators"].get("derivative", False):
        sig = derivative_signal(close)
        if sig: signals.append(sig); sources.append("DERIV")

    if config["indicators"].get("wavelet", False):
        sig = wavelet_signal(close)
        if sig: signals.append(sig); sources.append("WAVELET")

    if config["indicators"].get("regression", False):
        sig = rolling_regression_signal(close)
        if sig: signals.append(sig); sources.append("REG")

    if not signals:
        return None

    # === 多指标确认 ===
    buy_count = signals.count("买入")
    sell_count = signals.count("卖出")
    confirm_level = config["indicators"].get("confirm_level", 2)

    action = None
    if buy_count >= confirm_level and buy_count > sell_count:
        action = "买入"
    elif sell_count >= confirm_level and sell_count > buy_count:
        action = "卖出"

    if not action:
        return None

    # === 持仓判断 ===
    if code in holdings:
        if action != "卖出":
            return None
    else:
        if action != "买入":
            return None

    # === 冷却控制 ===
    if not cooldown_checker(code, period_name, action, config["signal"]["cooldown_minutes"]):
        return None

    # === 返回格式化结果 ===
    source_str = ",".join(sources)
    return f"【{code}】 {period_name} 出现 {action} 信号 (来源: {source_str})"
