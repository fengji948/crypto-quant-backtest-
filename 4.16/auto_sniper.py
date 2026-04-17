import asyncio
import websockets
import json
import requests
import time
import hmac
import base64

# ================= 填入你的模拟盘 API 信息 =================
API_KEY = "811f149c-c07f-4708-a9a0-1bfdf30c58d7"
SECRET_KEY = "9BC6B1B93FB7A9D4A200611127F20523"
PASSPHRASE = "15835379424qQ!"
# =========================================================

# --- 策略参数 ---
SYMBOL = "BTC-USDT-SWAP"
TIME_WINDOW = 3.0       # 统计时间窗口（秒）
VOLUME_THRESHOLD = 100 # 触发阈值：3秒内买入量超过多少张触发（测试时可以改小点容易触发）
ORDER_SIZE = "1"        # 触发后买入多少张

# --- 1. 执行模块：下单手 (REST API) ---
def get_timestamp():
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())

def sign_request(timestamp, method, request_path, body):
    message = str(timestamp) + str(method) + str(request_path) + str(body)
    mac = hmac.new(bytes(SECRET_KEY, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    return base64.b64encode(mac.digest()).decode('utf-8')

def place_market_buy_order():
    url = "https://www.okx.com"
    endpoint = "/api/v5/trade/order"
    
    body_dict = {
        "instId": SYMBOL, 
        "tdMode": "cross",          
        "side": "buy",              
        "ordType": "market",    
        "sz": ORDER_SIZE                   
    }
    body_str = json.dumps(body_dict)
    timestamp = get_timestamp()
    sign = sign_request(timestamp, "POST", endpoint, body_str)
    
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "x-simulated-trading": "1"  
    }
    
    try:
        print(f"\n🚀 动能爆发！正在极速发送市价买单...")
        start_time = time.time()
        response = requests.post(url + endpoint, headers=headers, data=body_str)
        result = response.json()
        end_time = time.time()
        
        if result.get("code") == "0":
            print(f"✅ 下单成功！订单ID: {result['data'][0]['ordId']} (耗时: {round((end_time-start_time)*1000)} 毫秒)")
        else:
            print(f"❌ 下单失败！: {result}")
    except Exception as e:
        print(f"请求异常: {e}")

# --- 2. 侦听模块：数据眼与大脑 (WebSocket) ---
async def strategy_run():
    url = "wss://ws.okx.com:8443/ws/v5/public"
    subscribe_msg = {
        "op": "subscribe",
        "args": [{"channel": "trades", "instId": SYMBOL}]
    }

    # 用于存放近期买单的列表：格式为 [(时间戳, 数量), (时间戳, 数量)...]
    recent_buys = []

    try:
        async with websockets.connect(url) as ws:
            print(f"🔗 策略已启动！正在监控 {SYMBOL} 盘口动能...")
            print(f"📊 触发条件：{TIME_WINDOW} 秒内买入量激增超过 {VOLUME_THRESHOLD} 张")
            await ws.send(json.dumps(subscribe_msg))
            
            while True:
                response = await ws.recv()
                data = json.loads(response)
                
                if "data" in data:
                    current_time = time.time()
                    
                    for trade in data["data"]:
                        side = trade["side"]       
                        sz = float(trade["sz"])           
                        
                        # 只要主动买单
                        if side == "buy":
                            recent_buys.append((current_time, sz))
                    
                    # 核心逻辑：清理过期数据（把3秒前的数据踢出去）
                    recent_buys = [b for b in recent_buys if current_time - b[0] <= TIME_WINDOW]
                    
                    # 计算这3秒内的总买入量
                    total_buy_volume = sum([b[1] for b in recent_buys])
                    
                    # 动态打印当前动能（可选，让你知道程序在干嘛）
                    # print(f"当前 {TIME_WINDOW}s 累计买单量: {total_buy_volume} 张", end='\r')
                    
                    # 触发判定！
                    if total_buy_volume >= VOLUME_THRESHOLD:
                        print(f"\n⚡ 警告！检测到 {total_buy_volume} 张大额买单涌入！")
                        # 开枪下单！
                        place_market_buy_order()
                        
                        print("\n🏁 策略执行完毕，安全退出程序。")
                        return # 触发一次后立刻退出，防止连续开单

    except Exception as e:
        print(f"系统异常: {e}")

if __name__ == "__main__":
    asyncio.run(strategy_run())