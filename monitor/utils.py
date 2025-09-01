# monitor/utils.py
import os
import csv
import time
import functools
import logging

SIGNAL_FILE = "data/signals.csv"

def retry(n=3, delay=2):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(n):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.error(f"{func.__name__} 失败 {i+1}/{n}: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


def cooldown_checker(stock, period, signal, cooldown_minutes):
    """检查是否需要推送（冷却控制）"""
    now = int(time.time())
    cooldown_sec = cooldown_minutes * 60

    if not os.path.exists("data"):
        os.makedirs("data")

    if not os.path.exists(SIGNAL_FILE):
        with open(SIGNAL_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["stock", "period", "signal", "timestamp"])

    with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if row["stock"] == stock and row["period"] == period and row["signal"] == signal:
            if now - int(row["timestamp"]) < cooldown_sec:
                logging.info(f"信号冷却中，跳过: {stock}-{period}-{signal}")
                return False  # 不推送

    # 保存新信号
    with open(SIGNAL_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([stock, period, signal, now])

    return True
