# monitor/schedule_runner.py
import time
import logging
import schedule
from futu import *
from .trend import check_trend
from .notify import send_message
from .holdings import get_holdings

def detect_reversal_for_market(config, market):
    quote_ctx = OpenQuoteContext(host=config["futu_ip"], port=config["futu_port"])
    holdings = get_holdings()
    signals = []

    for code in config["watchlist"]:
        if not code.startswith(market + "."):
            continue
        daily = check_trend(quote_ctx, code, KLType.K_DAY, "日线", holdings, config)
        if daily: signals.append(daily)
        hourly = check_trend(quote_ctx, code, KLType.K_60M, "1小时线", holdings, config)
        if hourly: signals.append(hourly)

    quote_ctx.close()
    if signals:
        logging.info(f"{market} 信号:\n" + "\n".join(signals))
        send_message(signals, config)

def run_schedule(config):
    for market, conf in config["schedule"].get("markets", {}).items():
        if conf.get("enabled", False):
            interval = conf.get("interval_minutes", 5)
            schedule.every(interval).minutes.do(detect_reversal_for_market, config=config, market=market)
            logging.info(f"调度: {market} 每 {interval} 分钟运行一次")
    while True:
        schedule.run_pending()
        time.sleep(1)

def run_once(config):
    for market in ["HK", "US", "CN"]:
        detect_reversal_for_market(config, market)
