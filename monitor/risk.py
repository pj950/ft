import logging

class RiskManager:
    def __init__(self, cfg):
        self.max_drawdown = cfg["risk"].get("max_drawdown", 0.1)   # 最大回撤 10%
        self.max_position = cfg["risk"].get("max_position", 0.2)   # 最大仓位 20%
        self.stop_loss = cfg["risk"].get("stop_loss", 0.05)        # 止损 5%
        self.take_profit = cfg["risk"].get("take_profit", 0.15)    # 止盈 15%

        # 模拟持仓信息（未来可替换成交易所/Futu API 实时持仓）
        self.positions = {}  # { "US.AAPL": {"avg_price": 150, "qty": 100, "current_price": 160} }

    def update_position(self, symbol, avg_price, qty, current_price):
        """更新持仓信息"""
        self.positions[symbol] = {
            "avg_price": avg_price,
            "qty": qty,
            "current_price": current_price
        }

    def check_risk(self, symbol, signal):
        """
        风险过滤逻辑：
        - 如果持仓亏损超过止损，强制卖出
        - 如果盈利超过止盈，强制卖出
        - 如果仓位超过最大限制，忽略买入信号
        - 未来可以加资金曲线、波动率等控制
        """
        if symbol not in self.positions:
            # 没持仓 → 风控只拦截仓位限制
            if signal == "买入":
                # 简单模拟：已有持仓占比超 max_position → 禁止买入
                # （这里需要接入资金总额，暂时用仓位数量代替）
                total_qty = sum(pos["qty"] for pos in self.positions.values())
                if total_qty > 0 and (self.positions.get(symbol, {}).get("qty", 0) / total_qty) > self.max_position:
                    logging.info(f"[风控拦截] {symbol} 仓位超限，忽略买入信号")
                    return None
            return signal

        pos = self.positions[symbol]
        avg_price = pos["avg_price"]
        qty = pos["qty"]
        current_price = pos["current_price"]

        pnl_ratio = (current_price - avg_price) / avg_price

        if pnl_ratio <= -self.stop_loss:
            logging.info(f"[风控触发止损] {symbol} - 已亏损 {pnl_ratio:.2%}，触发强制卖出")
            return "卖出"

        if pnl_ratio >= self.take_profit:
            logging.info(f"[风控触发止盈] {symbol} - 已盈利 {pnl_ratio:.2%}，触发强制卖出")
            return "卖出"

        return signal
