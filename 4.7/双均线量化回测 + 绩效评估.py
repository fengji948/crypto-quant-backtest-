import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ================= 1. 获取真实数据 =================
# 使用你测试成功的 v2rayN SOCKS5 端口 10808
proxies = {
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808',
}
exchange = ccxt.okx({'proxies': proxies})

symbol = 'SOL/USDT'
timeframe = '1d'
limit = 365  # 拉取过去一年的数据

print(f"正在拉取 {symbol} 真实历史数据...")
ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=8)
df.set_index('timestamp', inplace=True)

# ================= 2. 核心策略逻辑 (双均线) =================
print("正在执行双均线策略回测计算...")

df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()
df.dropna(inplace=True)

# 产生信号：MA5 大于 MA20 时做多 (1)，否则空仓 (0)
df['Signal'] = np.where(df['MA5'] > df['MA20'], 1, 0)
# 计算交易动作：买入为 1，卖出为 -1，不动为 0
df['Position'] = df['Signal'].diff()

# ================= 3. 结算与摩擦成本计算 =================
fee_rate = 0.001  # 千分之一手续费

df['Market_Return'] = df['Close'].pct_change()
df['Strategy_Return'] = df['Signal'].shift(1) * df['Market_Return']

# 扣除手续费
df.loc[df['Position'].notna() & (df['Position'] != 0), 'Strategy_Return'] -= fee_rate

df['Market_Return'] = df['Market_Return'].fillna(0)
df['Strategy_Return'] = df['Strategy_Return'].fillna(0)

df['Cumulative_Market'] = (1 + df['Market_Return']).cumprod()
df['Cumulative_Strategy'] = (1 + df['Strategy_Return']).cumprod()

# ================= 4. 计算并打印量化评估指标 =================
print("\n" + "="*15 + " 策略绩效体检报告 " + "="*15)

# 1. 累计收益率与年化收益率
total_days = len(df)
cumulative_return = df['Cumulative_Strategy'].iloc[-1] - 1
annualized_return = (1 + cumulative_return) ** (365 / total_days) - 1
print(f"策略累计收益率: {cumulative_return * 100:.2f}%")
print(f"市场死拿收益率: {(df['Cumulative_Market'].iloc[-1] - 1) * 100:.2f}%")
print(f"策略年化收益率: {annualized_return * 100:.2f}%")

# 2. 最大回撤 (Maximum Drawdown)
df['Rolling_Max'] = df['Cumulative_Strategy'].cummax()
df['Drawdown'] = (df['Cumulative_Strategy'] - df['Rolling_Max']) / df['Rolling_Max']
max_drawdown = df['Drawdown'].min()
print(f"最大回撤: {max_drawdown * 100:.2f}%")

# 3. 夏普比率 (Sharpe Ratio)
daily_return_mean = df['Strategy_Return'].mean()
daily_return_std = df['Strategy_Return'].std()
sharpe_ratio = (daily_return_mean / daily_return_std) * np.sqrt(365) if daily_return_std != 0 else 0
print(f"夏普比率: {sharpe_ratio:.2f}")

# 4. 胜率与盈亏比

buy_prices = df[df['Position'] == 1]['Close'].values
sell_prices = df[df['Position'] == -1]['Close'].values

if len(buy_prices) > len(sell_prices):
    buy_prices = buy_prices[:len(sell_prices)]
# 1. 找到完整的交易对数量（取买卖次数的最小值）
min_trades = min(len(buy_prices), len(sell_prices))

# 2. 截取相同长度的数组
# 注意：如果是因为期初“未买先卖”导致卖出多一次，应该剔除第一个卖出信号
if len(sell_prices) > len(buy_prices):
    buy_prices_aligned = buy_prices[:]
    sell_prices_aligned = sell_prices[-min_trades:] # 抛弃最早的那个无效卖出
elif len(buy_prices) > len(sell_prices):
    buy_prices_aligned = buy_prices[:min_trades]    # 抛弃最后那个还没卖出的买入
    sell_prices_aligned = sell_prices[:]
else:
    buy_prices_aligned = buy_prices
    sell_prices_aligned = sell_prices

# 3. 使用对齐后的数组计算单次交易收益率
trade_returns = (sell_prices_aligned * (1 - fee_rate)) / (buy_prices_aligned * (1 + fee_rate)) - 1

win_trades = trade_returns[trade_returns > 0]
lose_trades = trade_returns[trade_returns <= 0]
total_trades = len(trade_returns)

if total_trades > 0:
    win_rate = len(win_trades) / total_trades
    print(f"总完整交易次数: {total_trades} 次")
    print(f"胜率: {win_rate * 100:.2f}%")
    if len(lose_trades) > 0:
        pnl_ratio = win_trades.mean() / abs(lose_trades.mean())
        print(f"盈亏比: {pnl_ratio:.2f}")
else:
    print("总交易次数: 0 次")

print("="*48 + "\n")

# ================= 5. 画图可视化 =================
print("正在生成收益率对比曲线图...")
plt.figure(figsize=(12, 6), dpi=100)
plt.plot(df.index, df['Cumulative_Market'], label='Market Benchmark', color='#1f77b4', linestyle='--')
plt.plot(df.index, df['Cumulative_Strategy'], label='Dual MA Strategy', color='#d62728', linewidth=2)
plt.title('SOL/USDT Backtest: Dual Moving Average vs Market', fontsize=16, fontweight='bold')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Cumulative Net Value (Initial = 1.0)', fontsize=12)
plt.legend(loc='upper left', fontsize=12)
plt.grid(True, linestyle=':', alpha=0.6)
plt.gcf().autofmt_xdate()
plt.show()