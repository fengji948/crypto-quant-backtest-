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

# --- 策略核心参数 ---
SYMBOL = "BTC-USDT-SWAP"
TIME_WINDOW = 3.0       
VOLUME_THRESHOLD = 50   # 触发开仓阈值：3秒内涌入50张买单（可随时调小以便测试触发）
ORDER_SIZE = "1"        # 交易张数

# --- 风控参数 (核心！) ---
TRAILING_STOP_RATE = 0.001  # 追踪止盈：从最高点回撤 0.1% (千分之一) 即刻平仓
HARD_STOP_RATE = 0.002      # 硬止损：跌破买入价的 0.2% (千分之二) 认赔割肉
ACTIVE_PROFIT_RATE = 0.002  # 🌟 新增：利润达到 0.2% 时，才激活追踪止盈
# ================= REST API 执行模块 =================
def get_timestamp():
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())

def sign_request(timestamp, method, request_path, body):
    message = str(timestamp) + str(method) + str(request_path) + str(body)
    mac = hmac.new(bytes(SECRET_KEY, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    return base64.b64encode(mac.digest()).decode('utf-8')

def place_order(side):
    url = "https://www.okx.com"
    endpoint = "/api/v5/trade/order"
    
    body_dict = {
        "instId": SYMBOL, 
        "tdMode": "cross",          
        "side": side,               # "buy" 为开多，"sell" 为平多
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
        response = requests.post(url + endpoint, headers=headers, data=body_str)
        result = response.json()
        if result.get("code") == "0":
            print(f"✅ [{'买入开多' if side=='buy' else '卖出平多'}] 成功！订单ID: {result['data'][0]['ordId']}")
            return True
        else:
            print(f"❌ 下单失败！: {result}")
            return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False

# ================= WebSocket 侦听与策略大脑 =================
async def strategy_run():
    url = "wss://ws.okx.com:8443/ws/v5/public"
    subscribe_msg = {
        "op": "subscribe",
        "args": [{"channel": "trades", "instId": SYMBOL}]
    }

    recent_buys = []
    
    # 状态机变量
    in_position = False
    entry_price = 0.0
    highest_price = 0.0

    try:
        async with websockets.connect(url) as ws:
            print(f"🔗 系统启动！正在监控 {SYMBOL} ...")
            await ws.send(json.dumps(subscribe_msg))
            
            while True:
                response = await ws.recv()
                data = json.loads(response)
                
                if "data" in data:
                    current_time = time.time()
                    
                    for trade in data["data"]:
                        side = trade["side"]       
                        sz = float(trade["sz"])
                        price = float(trade["px"]) # 获取实时成交价
                        
                        # ================= 状态一：空仓等待买入 =================
                        if not in_position:
                            if side == "buy":
                                recent_buys.append((current_time, sz))
                            
                            recent_buys = [b for b in recent_buys if current_time - b[0] <= TIME_WINDOW]
                            total_buy_volume = sum([b[1] for b in recent_buys])
                            
                            if total_buy_volume >= VOLUME_THRESHOLD:
                                print(f"\n⚡ 发现异动！{TIME_WINDOW}秒内涌入 {total_buy_volume} 张买单！")
                                print("🚀 执行市价抢筹 (Buy)...")
                                
                                if place_order("buy"):
                                    in_position = True
                                    entry_price = price
                                    highest_price = price
                                    print(f"🎯 进场参考价格: {entry_price}")
                                    print("🛡️ 开启移动追踪止盈与硬止损风控...\n")
                                    # 清空队列防止连环触发
                                    recent_buys = [] 
                                else:
                                    print("⚠️ 开仓失败，继续监控...")
                                    recent_buys = []
                                    await asyncio.sleep(2)

                        # ================= 状态二：持仓监控平仓 =================
                        # ================= 状态二：持仓监控平仓 =================
                        else:
                            # 1. 不断更新历史最高价
                            if price > highest_price:
                                highest_price = price
                            
                            # 🌟 2. 核心逻辑升级：计算当前的实时利润率
                            current_profit_rate = (price - entry_price) / entry_price
                            
                            # 3. 计算止损/止盈线
                            hard_stop_price = entry_price * (1 - HARD_STOP_RATE)
                            
                            # 只有当最高利润曾经达到过“激活线”，才计算追踪止盈线；否则追踪止盈线为 0（不生效）
                            if (highest_price - entry_price) / entry_price >= ACTIVE_PROFIT_RATE:
                                trailing_stop_price = highest_price * (1 - TRAILING_STOP_RATE)
                            else:
                                trailing_stop_price = 0.0 
                            
                            # 4. 判定是否触发平仓
                            if trailing_stop_price > 0 and price <= trailing_stop_price:
                                print(f"\n📉 触发追踪止盈！最高价: {highest_price}, 现价回撤至: {price}")
                                print(f"💰 最终保底盈利！")
                                place_order("sell")
                                return 
                                
                            elif price <= hard_stop_price:
                                print(f"\n🩸 触发硬止损！进场价: {entry_price}, 现价跌至: {price}")
                                print("🪓 执行市价割肉 (Sell)...")
                                place_order("sell")
                                return

    except Exception as e:
        print(f"系统异常: {e}")

if __name__ == "__main__":
    asyncio.run(strategy_run())