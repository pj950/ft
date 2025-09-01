# monitor/trend_math.py
import numpy as np
import pywt
from sklearn.linear_model import LinearRegression


def fft_signal(close, keep=5):
    """FFT重建平滑曲线并检测拐点"""
    n = len(close)
    fft_vals = np.fft.fft(close)
    fft_vals[keep:-keep] = 0
    smooth = np.fft.ifft(fft_vals).real

    if close[-1] > smooth[-1] and close[-2] <= smooth[-2]:
        return "买入"
    elif close[-1] < smooth[-1] and close[-2] >= smooth[-2]:
        return "卖出"
    return None


def derivative_signal(close):
    """一阶/二阶导数检测拐点"""
    first = np.gradient(close)
    second = np.gradient(first)

    if first[-2] < 0 and first[-1] > 0 and second[-1] > 0:
        return "买入"
    elif first[-2] > 0 and first[-1] < 0 and second[-1] < 0:
        return "卖出"
    return None


def wavelet_signal(close, wavelet="db4", level=2):
    """小波分解趋势反转检测"""
    coeffs = pywt.wavedec(close, wavelet, level=level)
    # 只保留低频部分
    coeffs[1:] = [np.zeros_like(c) for c in coeffs[1:]]
    smooth = pywt.waverec(coeffs, wavelet)

    if close[-1] > smooth[-1] and close[-2] <= smooth[-2]:
        return "买入"
    elif close[-1] < smooth[-1] and close[-2] >= smooth[-2]:
        return "卖出"
    return None


def rolling_regression_signal(close, window=20):
    """移动窗口回归斜率检测"""
    if len(close) < window + 1:
        return None
    x = np.arange(window).reshape(-1, 1)
    y_now = close[-window:]

    model_now = LinearRegression().fit(x, y_now)
    slope_now = model_now.coef_[0]

    y_prev = close[-window-1:-1]
    model_prev = LinearRegression().fit(x, y_prev)
    slope_prev = model_prev.coef_[0]

    if slope_prev <= 0 and slope_now > 0:
        return "买入"
    elif slope_prev >= 0 and slope_now < 0:
        return "卖出"
    return None
