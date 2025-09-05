import time
import logging
import schedule
from futu import *
from .trend import check_trend_single_period, aggregate_multiperiod, decide_priority
from .holdings import get_holdings
from .notify import notify
from .utils import cooldown_checker, is_market_open

def _scan_once(quote_ctx, cfg):
    holdings = get_holdings()
    watchlist = cfg.get("watchlist", [])
    messages_high = []
    messages_mid = []

    for code in watchlist:
        period_results = []
        for p in cfg["periods"]:
            res = check_trend_single_period(quote_ctx, code, p, cfg)
            if res:
                period_results.append(res)

        final_action, score, used_periods, sources = aggregate_multiperiod(
            period_results, cfg["indicators"].get("confirm_level", 2)
        )
        if not final_action:
            continue

        # 持仓方向过滤：无仓只提示买入，有仓只提示卖出
        holding = (code in holdings)
        if holding and final_action != "卖出":
            continue
        if (not holding) and final_action != "买入":
            continue

        # 冷却
        if not cooldown_checker(code, "多周期", final_action, cfg["signal"]["cooldown_minutes"], cfg["paths"]["signal_csv"]):
            continue

        priority = decide_priority(score, used_periods, cfg)
        color = "🔴" if final_action == "买入" else "🟢"
        msg = (
            f"【{code}】 多周期{final_action} {color} 强度: {score}\n"
            f"周期: {','.join(sorted(used_periods))}\n"
            f"来源: {','.join(sorted(sources))}\n"
            f"优先级: {priority}"
        )

        if priority == "高":
            messages_high.append(msg)
        elif priority == "中":
            messages_mid.append(msg)

    # 推送策略：高优先级→通知通道；中优先级→日志；低优先级→忽略
    if messages_high:
        notify(messages_high, cfg)
    for m in messages_mid:
        logging.info("[中优先级] " + m)

def run_once(cfg):
    quote_ctx = OpenQuoteContext(host=cfg["futu"]["host"], port=cfg["futu"]["port"])
    try:
        _scan_once(quote_ctx, cfg)
    finally:
        quote_ctx.close()

def run_schedule(cfg):
    interval = int(cfg["schedule"].get("interval_minutes", 5))
    logging.info(f"定时任务启动，每 {interval} 分钟执行一次。")

    def job():
        if cfg["schedule"].get("market_open_check", True):
            if not is_market_open():
                logging.info("休市，跳过本轮。")
                return
        run_once(cfg)

    schedule.every(interval).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
