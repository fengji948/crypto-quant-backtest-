import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# ================= 1. 配置区域 =================

# --- 欧易API配置 (替换为你自己的) ---
# 如果只是测试信号，可以先不填，下单函数会被跳过
API_KEY = '你的API_KEY'
SECRET_KEY = '你的SECRET_KEY'
PASSPHRASE = '你的PASSPHRASE'

# --- 策略参数 ---
SYMBOL = 'SOL/USDT'       # 交易对
TIMEFRAME = '1d'          # K线周期 (例如: 1d, 4h, 1h, 15m)
MA_FAST = 5               # 快线周期
MA_SLOW = 20              # 慢线周期
AMOUNT = 0.1              # 每次交易数量 (SOL)

# --- 代理设置 (如果在国内需要) ---
proxies = {
    'http': 'http://127.0.0.1:33210',
    'https': 'http://127.0.0.1:33210',
}

# ================= 2. 初始化交易所对象 =================
def init_exchange():
    exchange_config = {
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'password': PASSPHRASE,
        'enableRateLimit': True,  # 启用速率限制，防止请求过快被 ban
        # 'proxies': proxies,     # 如果不需要代理，注释掉这一行
    }
    
    # 只有当API Key不为空时才添加密钥配置
    if API_KEY and SECRET_KEY and PASSPHRASE:
        exchange = ccxt.okx(exchange_config)
        print("✅ 已连接欧易实盘账户")
    else:
        # 没有密钥时，使用只读模式（只能看行情，不能交易）
        exchange = ccxt.okx()
        print("⚠️ 未配置API Key，运行在【模拟信号模式】，不会真实下单")

    return exchange

# ================= 3. 核心策略逻辑函数 =================
def fetch_and_calculate(exchange):
    """获取数据并计算均线"""
    try:
        # 获取K线数据，limit多取一点确保计算准确
        # 注意：最后一条数据通常是未完成的当前K线
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=50)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # 计算均线
        df['MA_Fast'] = df['Close'].rolling(window=MA_FAST).mean()
        df['MA_Slow'] = df['Close'].rolling(window=MA_SLOW).mean()
        
        # 去掉NaN
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"获取数据出错: {e}")
        return None

def execute_trade(exchange, signal_type):
    """执行交易下单"""
    if not (API_KEY and SECRET_KEY and PASSPHRASE):
        return # 没密钥直接返回

    try:
        if signal_type == 'buy':
            print(f"🚀 执行买入操作: {AMOUNT} {SYMBOL}")
            # 市价买入
            order = exchange.create_market_buy_order(SYMBOL, AMOUNT)
            print(f"订单详情: {order['id']}")
            
        elif signal_type == 'sell':
            print(f"💸 执行卖出操作: {AMOUNT} {SYMBOL}")
            # 市价卖出
            order = exchange.create_market_sell_order(SYMBOL, AMOUNT)
            print(f"订单详情: {order['id']}")
            
    except Exception as e:
        print(f"❌ 下单失败: {e}")

# ================= 4. 主循环 (实时监控) =================
def run_bot():
    exchange = init_exchange()
    
    # 记录上一次的信号状态，避免重复发送
    last_signal = None 
    
    print(f"\n▶️ 开始监控 {SYMBOL} ({TIMEFRAME})...")
    print("等待均线交叉信号...\n")

    while True:
        # 1. 获取数据
        df = fetch_and_calculate(exchange)
        if df is None or len(df) < 2:
            time.sleep(10)
            continue

        # 2. 获取最新两根K线的数据 (倒数第2根是刚完成的，倒数第1根是正在走的)
        # 策略逻辑：基于【已完成K线】判断信号，避免未完成K线导致的信号反复跳跃
        last_candle = df.iloc[-2] # 刚完成的K线
        prev_candle = df.iloc[-3] # 再前一根

        # 当前价格 (用于展示)
        current_price = df.iloc[-1]['Close']

        # 3. 判断金叉和死叉
        # 金叉条件：昨天快线>慢线，前天快线<=慢线
        is_golden_cross = (last_candle['MA_Fast'] > last_candle['MA_Slow']) and \
                          (prev_candle['MA_Fast'] <= prev_candle['MA_Slow'])
        
        # 死叉条件：昨天快线<慢线，前天快线>=慢线
        is_death_cross = (last_candle['MA_Fast'] < last_candle['MA_Slow']) and \
                         (prev_candle['MA_Fast'] >= prev_candle['MA_Slow'])

        # 4. 打印实时状态
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{now}] 价格: {current_price:.2f} | MA{MA_FAST}: {last_candle['MA_Fast']:.2f} | MA{MA_SLOW}: {last_candle['MA_Slow']:.2f}", end='')

        # 5. 触发交易逻辑
        if is_golden_cross:
            print(" -> ⚡️发现【金叉】信号！")
            if last_signal != 'buy':
                execute_trade(exchange, 'buy')
                last_signal = 'buy'
        elif is_death_cross:
            print(" -> ⚡️发现【死叉】信号！")
            if last_signal != 'sell':
                execute_trade(exchange, 'sell')
                last_signal = 'sell'
        else:
            print(" -> 无信号")

        # 6. 轮询间隔
        # 如果是1d周期，不需要太频繁，每10-30分钟查一次即可
        # 如果是1m周期，建议设置短一点，如5-10秒
        time.sleep(600) # 休眠10分钟

# 启动
if __name__ == '__main__':
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n程序已手动停止")
