import requests
import time
import hmac
import base64
import json

# ================= 填入你的模拟盘 API 信息 =================
API_KEY = "811f149c-c07f-4708-a9a0-1bfdf30c58d7"
SECRET_KEY = "9BC6B1B93FB7A9D4A200611127F20523"
PASSPHRASE = "15835379424qQ!" # <--- 注意！这个必须你自己填
# =========================================================

def get_timestamp():
    # OKX API 要求的 ISO 8601 UTC 时间戳格式
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())

def sign_request(timestamp, method, request_path, body):
    # HMAC SHA256 签名算法
    message = str(timestamp) + str(method) + str(request_path) + str(body)
    mac = hmac.new(bytes(SECRET_KEY, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()
    return base64.b64encode(d).decode('utf-8')

def place_demo_market_order():
    url = "https://www.okx.com"
    endpoint = "/api/v5/trade/order"
    
    # 订单参数：DOGE-USDT 永续合约，全仓，买入，市价，1张
    body_dict = {
        "instId": "DOGE-USDT-SWAP", 
        "tdMode": "cross",          
        "side": "buy",              
        "ordType": "market",        
        "sz": "1"                   
    }
    body_str = json.dumps(body_dict)
    
    timestamp = get_timestamp()
    sign = sign_request(timestamp, "POST", endpoint, body_str)
    
    # 请求头，必须包含 x-simulated-trading 字段
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "x-simulated-trading": "1"  
    }
    
    try:
        print(f"正在发送下单请求...")
        response = requests.post(url + endpoint, headers=headers, data=body_str)
        result = response.json()
        
        # 解析返回结果
        if result.get("code") == "0":
            print(f"✅ 下单成功！订单ID: {result['data'][0]['ordId']}")
        else:
            print(f"❌ 下单失败！错误代码: {result.get('code')}")
            print(f"错误信息: {result.get('msg')}")
            
    except Exception as e:
        print(f"请求发生异常: {e}")

if __name__ == "__main__":
    place_demo_market_order()