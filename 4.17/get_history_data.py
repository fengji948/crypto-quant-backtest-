import requests
import pandas as pd
import time

def fetch_okx_history_bulk(instId="DOGE-USDT-SWAP", bar="1m", total_candles=1440):
    url = "https://www.okx.com/api/v5/market/history-candles"
    all_data = []
    after = ""  # 用于记录上一批最后一条数据的时间戳
    
    print(f"⏳ 准备向欧易请求 {total_candles} 根 {bar} 级别的 {instId} 历史数据...")
    
    while len(all_data) < total_candles:
        params = {
            "instId": instId,
            "bar": bar,
            "limit": 100  # 遵守交易所单次 100 条的限制
        }
        if after:
            params["after"] = after
            
        try:
            response = requests.get(url, params=params)
            result = response.json()
            
            if result.get("code") == "0" and len(result["data"]) > 0:
                batch_data = result["data"]
                all_data.extend(batch_data)
                
                # 获取这批数据中最老的一根的时间戳，作为下一批的起点
                after = batch_data[-1][0] 
                print(f"✅ 已成功抓取 {len(all_data)} 根 K 线...")
                time.sleep(0.1)  # 稍微停顿，防止被交易所封锁 IP
            else:
                print("⚠️ 没有更多历史数据或接口报错。")
                break
                
        except Exception as e:
            print(f"请求异常: {e}")
            break

    # 截取我们需要的数据量
    all_data = all_data[:total_candles]
    
    # 转换为 DataFrame
    df = pd.DataFrame(all_data, columns=[
        "timestamp", "open", "high", "low", "close", 
        "vol", "volCcy", "volCcyQuote", "confirm"
    ])
    
    # 数据清洗
    df = df.astype(float)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    # 欧易默认是从最新到最老，我们需要反转成从老到新，符合时间流逝
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df[['datetime', 'open', 'high', 'low', 'close', 'vol']]

if __name__ == "__main__":
    df = fetch_okx_history_bulk(instId="DOGE-USDT-SWAP", bar="1m", total_candles=1440)
    
    if df is not None and not df.empty:
        print("\n🎉 数据拉取完毕！首尾数据时间如下：")
        print(f"起点: {df['datetime'].iloc[0]}")
        print(f"终点: {df['datetime'].iloc[-1]}")
        
        filename = "doge_1m_data.csv"
        df.to_csv(filename, index=False)
        print(f"\n📁 完整的 24 小时数据已覆盖保存至 {filename}")