# monitor/trend.py

import numpy as np
import talib
from futu import *
import logging

from .trend_math import (
    fft_signal,
    derivative_signal,
    wavelet_signal,
    rolling_regression_signal,
    hybrid_fft_wavelet_signal,  # 新增混合检测
)

<<<<<<< HEAD
# ---------- 小工具 ----------

def _series_ok(arr, min_len=50):
    """长度与 NaN 检查"""
    if arr is None:
        return False
    if len(arr) < min_len:
        return False
    if np.isnan(arr).any():
        return False
    return True

def _volume_spike(turnover, threshold):
    """
    成交额突变：最近一根 / 过去20根均值 >= threshold
    返回 (是否突变, 倍数)
    """
    if turnover is None or len(turnover) < 20:
        return False, 0.0
    base = np.nanmean(turnover[-20:-1])
    if base <= 0 or np.isnan(base):
        return False, 0.0
    factor = float(turnover[-1]) / float(base)
    return (factor >= threshold), factor

def _apply_period_downsample(close, turnover, period_label):
    """
    用 60m K 线下采样为 2h / 4h
    """
    if period_label == "2h":
        return close[::2], (turnover[::2] if turnover is not None else None)
    if period_label == "4h":
        return close[::4], (turnover[::4] if turnover is not None else None)
    return close, turnover

# ---------- 指标投票 ----------

def _indicator_votes(close, indicators_cfg, weights):
    """
    返回：
      votes_buy, votes_sell, sources, detail_by_indicator
    其中 detail_by_indicator: { "MACD": "买入/卖出/None", ... }
    """
    votes_buy = 0
    votes_sell = 0
    sources = []
    detail = {}

    # ---- 传统指标 ----
    if indicators_cfg.get("ma", True):
        # 需要至少20长度
        if _series_ok(close, min_len=25):
            ma5 = talib.SMA(close, timeperiod=5)
            ma20 = talib.SMA(close, timeperiod=20)
            w = weights.get("ma", 1)
            if not (np.isnan(ma5[-2:]).any() or np.isnan(ma20[-2:]).any()):
                if ma5[-1] > ma20[-1] and ma5[-2] <= ma20[-2]:
                    votes_buy += w; sources.append("MA"); detail["MA"] = "买入"
                elif ma5[-1] < ma20[-1] and ma5[-2] >= ma20[-2]:
                    votes_sell += w; sources.append("MA"); detail["MA"] = "卖出"
                else:
                    detail["MA"] = None
        else:
            detail["MA"] = None

    if indicators_cfg.get("macd", True):
        if _series_ok(close, min_len=35):
            macd, sig, _ = talib.MACD(close, 12, 26, 9)
            w = weights.get("macd", 1)
            if not (np.isnan(macd[-2:]).any() or np.isnan(sig[-2:]).any()):
                if macd[-1] > sig[-1] and macd[-2] <= sig[-2]:
                    votes_buy += w; sources.append("MACD"); detail["MACD"] = "买入"
                elif macd[-1] < sig[-1] and macd[-2] >= sig[-2]:
                    votes_sell += w; sources.append("MACD"); detail["MACD"] = "卖出"
                else:
                    detail["MACD"] = None
        else:
            detail["MACD"] = None

    if indicators_cfg.get("rsi", True):
        if _series_ok(close, min_len=20):
            rsi = talib.RSI(close, timeperiod=14)
            w = weights.get("rsi", 1)
            if not np.isnan(rsi[-2:]).any():
                # 过低/过高阈值也可做成配置
                if rsi[-1] < 30 <= rsi[-2]:
                    votes_buy += w; sources.append("RSI"); detail["RSI"] = "买入"
                elif rsi[-1] > 70 >= rsi[-2]:
                    votes_sell += w; sources.append("RSI"); detail["RSI"] = "卖出"
                else:
                    detail["RSI"] = None
        else:
            detail["RSI"] = None

    if indicators_cfg.get("boll", True):
        if _series_ok(close, min_len=25):
            up, mid, low = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
            w = weights.get("boll", 1)
            if not (np.isnan(up[-2:]).any() or np.isnan(low[-2:]).any()):
                # 下轨跌破→反弹（买）、上轨突破→回落（卖）
                if close[-1] > low[-1] and close[-2] <= low[-2]:
                    votes_buy += w; sources.append("BOLL"); detail["BOLL"] = "买入"
                elif close[-1] < up[-1] and close[-2] >= up[-2]:
                    votes_sell += w; sources.append("BOLL"); detail["BOLL"] = "卖出"
                else:
                    detail["BOLL"] = None
        else:
            detail["BOLL"] = None

    # ---- 数学方法 ----
    if indicators_cfg.get("fft", True):
        sig = fft_signal(close)
        w = weights.get("fft", 1)
        if sig == "买入":
            votes_buy += w; sources.append("FFT"); detail["FFT"] = "买入"
        elif sig == "卖出":
            votes_sell += w; sources.append("FFT"); detail["FFT"] = "卖出"
        else:
            detail["FFT"] = None

    if indicators_cfg.get("derivative", True):
        sig = derivative_signal(close)
        w = weights.get("derivative", 1)
        if sig == "买入":
            votes_buy += w; sources.append("DERIV"); detail["DERIV"] = "买入"
        elif sig == "卖出":
            votes_sell += w; sources.append("DERIV"); detail["DERIV"] = "卖出"
        else:
            detail["DERIV"] = None

    if indicators_cfg.get("wavelet", True):
        sig = wavelet_signal(close)
        w = weights.get("wavelet", 1)
        if sig == "买入":
            votes_buy += w; sources.append("WAVELET"); detail["WAVELET"] = "买入"
        elif sig == "卖出":
            votes_sell += w; sources.append("WAVELET"); detail["WAVELET"] = "卖出"
        else:
            detail["WAVELET"] = None

    # 混合：FFT + 小波
    if indicators_cfg.get("hybrid", True):
        sig = hybrid_fft_wavelet_signal(close)
        w = weights.get("hybrid", weights.get("wavelet", 1))  # 若未显式配置，沿用 wavelet 的权重
        if sig == "买入":
            votes_buy += w; sources.append("HYBRID"); detail["HYBRID"] = "买入"
        elif sig == "卖出":
            votes_sell += w; sources.append("HYBRID"); detail["HYBRID"] = "卖出"
        else:
            detail["HYBRID"] = None

    if indicators_cfg.get("regression", True):
        sig = rolling_regression_signal(close)
        w = weights.get("regression", 1)
        if sig == "买入":
            votes_buy += w; sources.append("REG"); detail["REG"] = "买入"
        elif sig == "卖出":
            votes_sell += w; sources.append("REG"); detail["REG"] = "卖出"
        else:
            detail["REG"] = None

    return votes_buy, votes_sell, sources, detail

# ---------- 单周期检测 ----------

def check_trend_single_period(quote_ctx, code, period_label, cfg):
    """
    返回：
      {
        "period": "1h/2h/4h/1d",
        "action": "买入/卖出",
        "score": int,
        "sources": [指示器...],
        "detail": { indicator: "买入/卖出/None", ... }
      }
    或 None
    """
    # 选择基础K线类型（2h/4h 用 60m 下采样）
    kl_type = {
        "1h": KLType.K_60M,
        "2h": KLType.K_60M,
        "4h": KLType.K_60M,
        "1d": KLType.K_DAY
    }[period_label]

    ret, df = quote_ctx.get_cur_kline(code, cfg["kline_num"], kl_type=kl_type)
    if ret != RET_OK or df is None or df.empty:
        logging.warning(f"[{code} {period_label}] 拉取K线失败")
        return None

    # 成交额与收盘价
    turnover = None
    if "turnover" in df.columns:
        turnover = df["turnover"].astype(float).values
    elif "turnover" in df:
        turnover = df["turnover"].astype(float).values

    close = df["close"].astype(float).values

    # 基础校验
    if not _series_ok(close, min_len=50):
        return None

    # 下采样到 2h/4h
    close, turnover = _apply_period_downsample(close, turnover, period_label)

    # 过滤成交额/价格
    if turnover is not None and turnover[-1] < cfg["filters"]["min_turnover"]:
        return None
    if close[-1] < cfg["filters"]["min_price"]:
        return None

    # 指标投票
    buy, sell, sources, detail = _indicator_votes(close, cfg["indicators"], cfg["weights"])

    # 成交额突变加分
    bonus = 0
    if turnover is not None:
        spike, factor = _volume_spike(turnover, cfg["signal"]["volume_spike_threshold"])
        if spike:
            bonus = int(factor * cfg["weights"].get("volume_spike_bonus_per_x", 5))
            sources.append("VOLUME_SPIKE")

    # 方向与评分：仅统计占优方向（避免 5:4 这类“势均力敌”抬高分）
    if buy > sell:
        base = buy
        action = "买入"
    elif sell > buy:
        base = sell
        action = "卖出"
    else:
        return None

    score = base + bonus

    return {
        "period": period_label,
        "action": action,
        "score": score,
        "sources": sources,
        "detail": detail,
    }

# ---------- 多周期汇总 ----------

def aggregate_multiperiod(results, confirm_level):
    """
    多周期确认：
      - 至少 confirm_level 个周期同向
    返回：
      final_action, total_score, used_periods_set, sources_list, sources_by_period
    """
    if not results:
        return None, 0, set(), [], {}

    buy = sum(1 for r in results if r["action"] == "买入")
    sell = sum(1 for r in results if r["action"] == "卖出")

    if buy >= confirm_level and buy > sell:
        final = "买入"
    elif sell >= confirm_level and sell > buy:
        final = "卖出"
    else:
        return None, 0, set(), [], {}

    # 汇总
    used_periods = [r["period"] for r in results if r["action"] == final]
    total_score = sum(r["score"] for r in results if r["action"] == final)

    sources = set()
    sources_by_period = {}
    for r in results:
        if r["action"] == final:
            sources.update(r["sources"])
            sources_by_period[r["period"]] = r.get("detail", {})

    return final, total_score, set(used_periods), list(sources), sources_by_period

# ---------- 优先级 ----------

def decide_priority(score, used_periods, cfg):
    """
    “高/中/低”：
      - 高：分数 >= priority_high_score 且 覆盖≥2个周期
      - 中：分数 >= priority_mid_score
      - 否则：低
    """
    if score >= cfg["signal"]["priority_high_score"] and len(used_periods) >= 2:
        return "高"
    if score >= cfg["signal"]["priority_mid_score"]:
        return "中"
    return "低"
=======
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
>>>>>>> 9bb94dd4d8f2ce286f91219188f2e78c9646b30c
