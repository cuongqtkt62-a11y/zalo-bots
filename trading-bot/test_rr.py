import asyncio
import pandas as pd
from config import Config
from signal_scanner import SignalScanner

async def test_rr():
    symbol = "LIT/USDT:USDT"
    
    # Set tuned parameters
    Config.EMA_SQUEEZE_THRESHOLD_PCT = 3.5
    Config.DRAGON_NARROW_THRESHOLD_PCT = 1.2
    Config.SWING_LOOKBACK = 3
    Config.MIN_CONFLUENCE_SCORE = 30
    
    scanner = SignalScanner()
    try:
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        df = scanner.indicators.calculate_all(df)
        
        target_df = df.between_time('02:00', '03:10')
        print("Time | Close | StopLoss | ATR | Risk | Reward (TP1) | R:R (TP1) | Reward (TP2) | R:R (TP2)")
        print("-" * 100)
        for idx, row in target_df.iterrows():
            if idx.time().hour == 2 and idx.time().minute in (30, 45, 50):
                sub_df = df.loc[:idx]
                atr = row.get('atr', 0)
                entry = row['close']
                
                # Compute SL
                sweep_candles = sub_df.iloc[-20:]
                sweep_idx = sweep_candles[sweep_candles['sweep_low'] == True].index
                if len(sweep_idx) > 0:
                    sl_base = sub_df.loc[sweep_idx, 'low'].min()
                else:
                    sl_base = sweep_candles['low'].min()
                sl = sl_base - atr * 0.2
                
                risk = abs(entry - sl)
                reward_tp1 = atr * 1.0
                reward_tp2 = atr * 2.0
                rr_tp1 = reward_tp1 / risk if risk > 0 else 0
                rr_tp2 = reward_tp2 / risk if risk > 0 else 0
                
                print(f"{idx.time()} | {entry:.4f} | {sl:.4f} | {atr:.4f} | {risk:.4f} | {reward_tp1:.4f} | 1:{rr_tp1:.2f} | {reward_tp2:.4f} | 1:{rr_tp2:.2f}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(test_rr())
