import ccxt
import pandas as pd

# 1. 配置你的本地代理地址 (请根据你实际的软件端口修改 7890)
proxies = {
    'http': 'http://127.0.0.1:33210',
    'https': 'http://127.0.0.1:33210',
}

# 2. 初始化交易所，并将代理参数传进去
exchange = ccxt.okx({
    'proxies': proxies
})

# 3. 设定参数
symbol = 'SOL/USDT'
timeframe = '1d'
limit = 100

print(f"正在通过代理从 OKX 获取 {symbol} 的最新 {timeframe} K线数据...")

# 4. 调用 API 拉取数据
ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

# 5. 数据清洗与格式化
df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=8)
df.set_index('timestamp', inplace=True)

print("\n数据拉取成功！最新的5天行情如下：")
print(df.tail())