import asyncio
import websockets
import json

async def listen_market_trades():
    # 欧易公共 WebSocket 地址
    url = "wss://ws.okx.com:8443/ws/v5/public"
    
    # 订阅参数：监听 DOGE-USDT 永续合约的实时交易 (trades)
    subscribe_msg = {
        "op": "subscribe",
        "args": [{"channel": "trades", "instId": "DOGE-USDT-SWAP"}]
    }

    try:
        async with websockets.connect(url) as ws:
            print("🔗 正在连接 OKX WebSocket 服务器...")
            
            # 发送订阅请求
            await ws.send(json.dumps(subscribe_msg))
            print("✅ 订阅请求已发送，等待数据推送...\n")
            
            # 持续接收数据流
            while True:
                response = await ws.recv()
                data = json.loads(response)
                
                # 过滤出包含真实成交的数据包
                if "data" in data:
                    for trade in data["data"]:
                        side = trade["side"]       # 方向：buy 或 sell
                        price = trade["px"]        # 成交价格
                        sz = trade["sz"]           # 成交数量（张）
                        time_str = trade["ts"]     # 时间戳
                        
                        # 简单加个颜色区分买卖，方便肉眼看（Buy为绿，Sell为红）
                        if side == "buy":
                            print(f"🟢 [买入] 价格: {price} | 数量: {sz}张")
                        else:
                            print(f"🔴 [卖出] 价格: {price} | 数量: {sz}张")
                            
    except Exception as e:
        print(f"WebSocket 发生异常: {e}")

if __name__ == "__main__":
    # 运行异步事件循环
    asyncio.run(listen_market_trades())