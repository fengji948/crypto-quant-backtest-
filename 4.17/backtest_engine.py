import pandas as pd

# ================= 1. 策略与风控参数 =================
VOLUME_THRESHOLD = 50000      # 动能爆发阈值：单分钟成交量大于 1500 张
TRAILING_STOP_RATE = 0.005   # 追踪止盈：从最高点回撤 0.1% 
HARD_STOP_RATE = 0.01       # 硬止损：跌破买入价 0.2%
ACTIVE_PROFIT_RATE = 0.01  # 激活线：利润达到 0.15% 时才激活追踪止盈
FEE_RATE = 0.0005            # 假设单边手续费+滑点为万分之五 (0.05%)

def run_backtest(csv_file):
    print(f"📊 正在加载历史数据: {csv_file}...")
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"❌ 找不到文件 {csv_file}，请先运行上一步的下载脚本！")
        return
# 🌟 新增：计算 60 周期简单移动平均线 (代表过去1小时的趋势)
    df['sma_240'] = df['close'].rolling(window=240).mean()
    # ================= 2. 初始化状态机 =================
    in_position = False
    entry_price = 0.0
    highest_price = 0.0
    entry_time = ""
    
    # 账本：记录每一笔交易的结果
    trades = [] 
    
    print("\n🚀 启动时间机器，开始历史回测...\n")

    # ================= 3. 核心循环：模拟时间流逝 =================
    for index, row in df.iterrows():
        current_time = row['datetime']
        current_price = row['close']
        high_price = row['high']
        low_price = row['low']
        volume = row['vol']
        
        # 状态一：空仓寻找猎物
       
       # 提前提取需要判断的基础数据
        open_price = row['open']
        sma_240 = row['sma_240'] # 🌟 正确提取 240 均线值

        # 状态一：空仓寻找猎物
        if not in_position:
            # 动能爆发的四大条件：
            # 1. 成交量达标
            is_high_volume = volume > VOLUME_THRESHOLD
            # 2. 必须是阳线 (收盘价 > 开盘价)
            is_green_candle = current_price > open_price
            # 3. 实体涨幅必须超过 0.1%
            price_surge = (current_price - open_price) / open_price > 0.001
            # 4. 🌟 宏观趋势向上：价格必须在 4 小时均线之上！
            is_uptrend = pd.notna(sma_240) and current_price > sma_240
            
            # 🌟 致命修复：四个条件必须同时满足 (加上了 is_uptrend)！
            if is_high_volume and is_green_candle and price_surge and is_uptrend:
                in_position = True
                # 考虑滑点，我们的实际买入价会比收盘价稍微差一点
                entry_price = current_price * (1 + FEE_RATE) 
                highest_price = entry_price
                entry_time = current_time
                print(f"🟢 [{current_time}] 动能爆发 (量:{volume})！买入价: {entry_price:.2f}")

        # 状态二：持仓盯盘防守
        else:
            # 1. 更新历史最高价 (用这根 K 线的最高价)
            if high_price > highest_price:
                highest_price = high_price
                
            # 2. 计算防守线
            hard_stop_price = entry_price * (1 - HARD_STOP_RATE)
            
            if (highest_price - entry_price) / entry_price >= ACTIVE_PROFIT_RATE:
                trailing_stop_price = highest_price * (1 - TRAILING_STOP_RATE)
            else:
                trailing_stop_price = 0.0
                
            # 3. 判定是否触发平仓 (用这根 K 线的最低价来试探是否击穿防守线)
            # 优先判定硬止损（极端情况下暴跌）
            if low_price <= hard_stop_price:
                exit_price = hard_stop_price * (1 - FEE_RATE) # 扣除平仓手续费/滑点
                pnl_rate = (exit_price - entry_price) / entry_price
                trades.append({'入场时间': entry_time, '出场时间': current_time, '类型': '硬止损 🩸', '盈亏比': pnl_rate})
                in_position = False
                
            # 其次判定追踪止盈
            elif trailing_stop_price > 0 and low_price <= trailing_stop_price:
                exit_price = trailing_stop_price * (1 - FEE_RATE)
                pnl_rate = (exit_price - entry_price) / entry_price
                trades.append({'入场时间': entry_time, '出场时间': current_time, '类型': '追踪止盈 💰', '盈亏比': pnl_rate})
                in_position = False

                # 🌟 新增补丁：如果时间机器跑到终点时手里还有单子，按最后一刻的价格强制平仓
    if in_position:
        exit_price = current_price * (1 - FEE_RATE)
        pnl_rate = (exit_price - entry_price) / entry_price
        trades.append({'入场时间': entry_time, '出场时间': current_time, '类型': '期末清仓 ⏳', '盈亏比': pnl_rate})

    # ================= 4. 统计与结算输出 =================
    print("-" * 50)
    print("📈 回测结果报告")
    print("-" * 50)
    
    total_trades = len(trades)
    if total_trades == 0:
        print("🤷‍♂️ 在这段数据中没有触发任何交易，尝试调低 VOLUME_THRESHOLD (动能阈值)。")
        return
        
    winning_trades = [t for t in trades if t['盈亏比'] > 0]
    win_rate = len(winning_trades) / total_trades * 100
    
    # 假设初始资金 10000 U，每次全仓滚雪球（复利）
    capital = 10000.0 
    for t in trades:
        capital = capital * (1 + t['盈亏比'])
        
    print(f"总交易次数: {total_trades} 次")
    print(f"胜率: {win_rate:.2f}%")
    print(f"初始资金: 10000.00 U")
    print(f"最终资金: {capital:.2f} U")
    print(f"总盈亏率: {((capital - 10000) / 10000) * 100:.2f}%\n")
    
    print("📋 交易明细 (前 5 笔):")
    for t in trades[:5]:
        print(f"{t['入场时间']} 买入 -> {t['出场时间']} 卖出 | 结果: {t['类型']} ({t['盈亏比']*100:.2f}%)")

if __name__ == "__main__":
   run_backtest("doge_1m_data.csv")