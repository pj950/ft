import numpy as np
import pywt
from scipy.fft import fft, ifft
from sklearn.linear_model import LinearRegression

def fft_signal(close, keep=5, label="fft"):
    if len(close) < keep * 4:
        return None
    F = fft(close)
    F[keep:-keep] = 0
    smooth = ifft(F).real

    sig = None
    if close[-1] > smooth[-1] and close[-2] <= smooth[-2]:
        sig = "买入"
    elif close[-1] < smooth[-1] and close[-2] >= smooth[-2]:
        sig = "卖出"

    if sig:
        return {"signal": sig, "method": label}
    return None

def derivative_signal(close):
    if len(close) < 5: return None
    d1 = np.gradient(close)
    d2 = np.gradient(d1)
    if d1[-2] < 0 and d1[-1] > 0 and d2[-1] > 0:
        return "买入"
    if d1[-2] > 0 and d1[-1] < 0 and d2[-1] < 0:
        return "卖出"
    return None

def wavelet_signal(close, wavelet="db4", level=2):
    if len(close) < 32: return None
    coeffs = pywt.wavedec(close, wavelet, level=level)
    coeffs[1:] = [np.zeros_like(c) for c in coeffs[1:]]
    smooth = pywt.waverec(coeffs, wavelet)
    smooth = smooth[:len(close)]
    if close[-1] > smooth[-1] and close[-2] <= smooth[-2]:
        return "买入"
    if close[-1] < smooth[-1] and close[-2] >= smooth[-2]:
        return "卖出"
    return None

def rolling_regression_signal(close, window=20):
    if len(close) < window + 1: return None
    X = np.arange(window).reshape(-1,1)
    y_now = close[-window:]
    y_prev = close[-window-1:-1]
    slope_now = LinearRegression().fit(X, y_now).coef_[0]
    slope_prev = LinearRegression().fit(X, y_prev).coef_[0]
    if slope_prev <= 0 and slope_now > 0:
        return "买入"
    if slope_prev >= 0 and slope_now < 0:
        return "卖出"
    return None

def hybrid_fft_wavelet_signal(close, keep=5, wavelet="db4", level=2):
    """
    混合 FFT + 小波检测
    1. FFT 平滑去噪
    2. 小波提取趋势
    3. 检测拐点
    """
    if len(close) < max(32, keep * 4):
        return None

    # Step1: FFT 平滑
    F = fft(close)
    F[keep:-keep] = 0
    smooth_fft = ifft(F).real

    # Step2: 小波低频趋势
    coeffs = pywt.wavedec(smooth_fft, wavelet, level=level)
    coeffs[1:] = [np.zeros_like(c) for c in coeffs[1:]]
    smooth = pywt.waverec(coeffs, wavelet)
    smooth = smooth[:len(close)]

    # Step3: 信号判断
    if close[-1] > smooth[-1] and close[-2] <= smooth[-2]:
        return "买入"
    if close[-1] < smooth[-1] and close[-2] >= smooth[-2]:
        return "卖出"
    return None