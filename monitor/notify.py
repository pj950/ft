# monitor/notify.py
import logging
import requests

def send_message(messages, config):
    if not config["notify"].get("enabled", False):
        logging.info("推送未启用")
        return

    channel = config["notify"].get("channel", "wechat")

    if channel == "wechat":
        key = config["notify"]["wechat"].get("key")
        if not key:
            logging.warning("微信key未配置")
            return
        url = f"https://sctapi.ftqq.com/{key}.send"
        data = {"title": "趋势反转提醒", "desp": "\n\n".join(messages)}
        try:
            requests.post(url, data=data, timeout=5)
        except Exception as e:
            logging.error(f"微信推送失败: {e}")
