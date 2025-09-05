import logging
import requests

def notify(messages, config):
    if not config["notify"].get("enabled", False):
        logging.info("[通知] 已关闭")
        return

    channel = config["notify"].get("channel", "log")
    text = "\n".join(messages)

    if channel == "wecom":
        webhook = config["notify"]["wecom"].get("webhook", "")
        if not webhook:
            logging.warning("[通知] 企业微信 webhook 未配置")
            return
        try:
            r = requests.post(webhook, json={"msgtype":"text", "text":{"content": text}}, timeout=8)
            logging.info(f"[通知-企业微信] {r.status_code}")
        except Exception as e:
            logging.error(f"[通知失败-企业微信] {e}")

    elif channel == "serverchan":
        key = config["notify"]["serverchan"].get("key", "")
        if not key:
            logging.warning("[通知] Server酱 key 未配置")
            return
        url = f"https://sctapi.ftqq.com/{key}.send"
        try:
            r = requests.post(url, data={"title":"趋势提醒", "desp": text}, timeout=8)
            logging.info(f"[通知-Server酱] {r.status_code}")
        except Exception as e:
            logging.error(f"[通知失败-Server酱] {e}")

    else:
        logging.info(f"[通知-日志]\n{text}")
