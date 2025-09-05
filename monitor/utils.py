import csv
import os
import time
import logging
from datetime import datetime
from dateutil import tz

SIGNAL_FILE_DEFAULT = "data/signals.csv"

def ensure_signal_csv(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["code", "period", "action", "ts"])

def cooldown_checker(code, period, action, cooldown_minutes, path=SIGNAL_FILE_DEFAULT):
    ensure_signal_csv(path)
    now = int(time.time())
    cool = cooldown_minutes * 60

    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        for r in rows:
            if r["code"] == code and r["period"] == period and r["action"] == action:
                if now - int(r["ts"]) < cool:
                    logging.info(f"[冷却中] 跳过 {code}-{period}-{action}")
                    return False

    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([code, period, action, now])
    return True

def local_now(tzname="Asia/Shanghai"):
    return datetime.now(tz.gettz(tzname))

def is_market_open(now=None):
    """
    简易开盘判断：工作日 + 典型时段（港股/美股）。如需精准节假日，建议接入交易日历API。
    港股: 09:30-12:00, 13:00-16:00 HKT
    美股: 09:30-16:00 ET
    """
    now = now or local_now()
    wd = now.weekday()  # 0=Mon ... 6=Sun
    if wd >= 5:
        return False

    # HKT
    hkt = now.astimezone(tz.gettz("Asia/Hong_Kong"))
    hkt_ok = ((hkt.hour > 9 or (hkt.hour == 9 and hkt.minute >= 30)) and (hkt.hour < 12)) or \
             ((hkt.hour >= 13) and (hkt.hour < 16))
    # ET
    et = now.astimezone(tz.gettz("America/New_York"))
    et_ok = ((et.hour > 9 or (et.hour == 9 and et.minute >= 30)) and (et.hour < 16))

    return hkt_ok or et_ok
