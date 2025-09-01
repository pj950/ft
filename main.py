# main.py
import json
import logging
from monitor.schedule_runner import run_schedule, run_once

with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

logging.basicConfig(
    filename="logs/trend_monitor.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

if __name__ == "__main__":
    if CONFIG["schedule"].get("enabled", True):
        run_schedule(CONFIG)
    else:
        run_once(CONFIG)
