import json
import logging
import os
import multiprocessing
import subprocess
from monitor.schedule_runner import run_schedule, run_once


def setup_logging(cfg):
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        filename=cfg["paths"]["log_file"],
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8"
    )
    # 同时输出到控制台
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(console)


def run_strategy(cfg):
    """运行交易策略调度"""
    if cfg["schedule"].get("enabled", True):
        run_schedule(cfg)
    else:
        run_once(cfg)


def run_web(cfg):
    """启动 Web 服务"""
    if cfg["web"].get("enabled", False):
        subprocess.run([
            "python", "web/server.py"
        ])


if __name__ == "__main__":
    with open("config.json", "r", encoding="utf-8") as f:
        CONFIG = json.load(f)

    os.makedirs("data", exist_ok=True)
    setup_logging(CONFIG)

    jobs = []

    # 策略调度
    p1 = multiprocessing.Process(target=run_strategy, args=(CONFIG,))
    jobs.append(p1)
    p1.start()

    # Web 面板
    if CONFIG["web"].get("enabled", False):
        p2 = multiprocessing.Process(target=run_web, args=(CONFIG,))
        jobs.append(p2)
        p2.start()

    for job in jobs:
        job.join()
