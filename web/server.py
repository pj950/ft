from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
import uvicorn
import json

app = FastAPI()

# 存储最新行情和信号（全局变量，实际可用Redis/DB）
latest_data = {"prices": [], "signal": None}

@app.get("/")
def index():
    return FileResponse("web/static/index.html")

@app.get("/data")
def get_data():
    return latest_data

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await websocket.send_json(latest_data)
        await websocket.receive_text()  # 保持连接心跳

def update_data(prices, signal):
    """在 main/trend 调用这个方法更新面板"""
    latest_data["prices"] = prices
    latest_data["signal"] = signal

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
