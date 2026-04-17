import ccxt
import pandas as pd
import numpy as np

# ================= 1. 获取真实数据 =================
proxies = {
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808',
}
exchange = ccxt.okx({'proxies': proxies})

symbol = 'SOL/USDT'
timeframe = '1d'
limit = 365  # 我们多拉一点数据，拉取过去  天的，回测效果更明显

print(f"正在拉取 {symbol} 真实历史数据...")
ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=8)
df.set_index('timestamp', inplace=True)

# ================= 2. 核心策略逻辑 (双均线) =================
print("正在执行双均线策略回测计算...")

# 计算 5日均线 和 20日均线
df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()

# 剔除最开始没有足够天数计算 MA20 的空数据行 (NaN)
df.dropna(inplace=True)

# 产生信号：MA5 大于 MA20 时做多 (1)，否则空仓 (0)
df['Signal'] = np.where(df['MA5'] > df['MA20'], 1, 0)

# 计算交易动作：相比昨天，信号变化了说明发生了买卖
# 买入为 1，卖出为 -1，不动为 0
df['Position'] = df['Signal'].diff()

# ================= 3. 结算与摩擦成本计算 =================
fee_rate = 0.001  # 设定单边手续费为千分之一 (0.1%)

# 市场本身的单日涨跌幅
df['Market_Return'] = df['Close'].pct_change()

# 策略的单日涨跌幅：只有在持有(昨天的Signal为1)时，才能吃到今天的涨跌幅
df['Strategy_Return'] = df['Signal'].shift(1) * df['Market_Return']

# 扣除手续费：只要发生交易 (Position != 0 或者 Position != NaN)，就减去摩擦成本
df.loc[df['Position'].notna() & (df['Position'] != 0), 'Strategy_Return'] -= fee_rate

# 计算累计净值 (把每天的收益率累乘起来)
# 填充 NaN 为 0，避免计算报错
df['Market_Return'] = df['Market_Return'].fillna(0)
df['Strategy_Return'] = df['Strategy_Return'].fillna(0)

df['Cumulative_Market'] = (1 + df['Market_Return']).cumprod()
df['Cumulative_Strategy'] = (1 + df['Strategy_Return']).cumprod()

# ================= 4. 输出结果 =================
print("-" * 30)
print(f"回测标的: {symbol}")
print(f"回测天数: {len(df)} 天")
print(f"市场基准最终净值 (一直死拿): {df['Cumulative_Market'].iloc[-1]:.4f}")
print(f"策略回测最终净值 (按均线做T): {df['Cumulative_Strategy'].iloc[-1]:.4f}")
print("-" * 30)

import matplotlib.pyplot as plt

print("正在生成收益率对比曲线图，请稍候...")

# 1. 设置画布大小和分辨率
plt.figure(figsize=(12, 6), dpi=100)

# 2. 绘制市场基准净值曲线（蓝色、虚线），代表“死拿”的收益
plt.plot(df.index, df['Cumulative_Market'], label='Market Benchmark (Buy & Hold)', color='#1f77b4', linestyle='--', linewidth=1.5)

# 3. 绘制策略回测净值曲线（红色、实线），代表“双均线做T”的收益
plt.plot(df.index, df['Cumulative_Strategy'], label='Dual MA Strategy', color='#d62728', linewidth=2)

# 4. 细节美化：添加标题、坐标轴标签、图例和网格
plt.title('SOL/USDT Backtest: Dual Moving Average vs Market', fontsize=16, fontweight='bold')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Cumulative Net Value (Initial = 1.0)', fontsize=12)
plt.legend(loc='upper left', fontsize=12) # 将图例放在左上角
plt.grid(True, linestyle=':', alpha=0.6)  # 添加虚线网格，方便对齐看数据

# 5. 自动调整日期标签的显示角度，防止重叠
plt.gcf().autofmt_xdate()

# 6. 弹出并显示图像！
plt.show()