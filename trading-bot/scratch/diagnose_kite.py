import asyncio
import pandas as pd
from config import Config
from signal_scanner import SignalScanner

async def diagnose():
    print("Diagnosing KITE/USDT:USDT...")
    scanner = SignalScanner()
    try:
        symbol = "KITE/USDT:USDT"
        df = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
        if df.empty:
            print("❌ Failed to fetch data")
            return
            
        df = scanner.indicators.calculate_all(df)
        recent = df.iloc[-100:]
        
        print("Timestamp | Close | Cond1 (Compress) | Reversal | SweepLow | Both | Score | R:R")
        print("-" * 100)
        
        for i in range(20, len(recent)):
            idx = recent.index[i]
            row = recent.iloc[i]
            sub_df = df.loc[:idx]
            
            # Condition 1: Compression
            has_squeeze = sub_df['ema_squeeze'].iloc[-15:].any()
            has_narrow = sub_df['dragon_narrow'].iloc[-15:].any()
            price_near_ema = (
                row.get('price_in_ema_cluster', False) or
                row.get('price_in_dragon', False) or
                row.get('touch_ema89', False) or
                row.get('touch_ema200', False)
            )
            cond1 = (has_squeeze or has_narrow) and price_near_ema
            
            reversal = row.get('bullish_reversal_at_ema', False)
            sweep = row.get('sweep_low', False)
            
            reversal_with_sweep_series = sub_df['bullish_reversal_at_ema'] & sub_df['sweep_low']
            has_reversal_with_sweep = reversal_with_sweep_series.iloc[-3:].any()
            
            # Calculate potential signal properties
            atr = row.get('atr', 0)
            entry_price = row['close']
            
            # SL calculation
            sweep_candles = sub_df.iloc[-20:]
            sweep_idx = sweep_candles[sweep_candles['sweep_low'] == True].index
            if len(sweep_idx) > 0:
                sl_base = sub_df.loc[sweep_idx, 'low'].min()
            else:
                sl_base = sweep_candles['low'].min()
            stop_loss = sl_base - atr * 0.2
            
            risk = abs(entry_price - stop_loss)
            min_risk = atr * 1.0
            if risk < min_risk:
                stop_loss = entry_price - atr * 1.2
                risk = abs(entry_price - stop_loss)
                
            tp2 = entry_price + Config.TP2_ATR_MULT * atr
            reward = abs(tp2 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confluence score
            confluence_score = 0
            confluence_score += 25 if has_squeeze else 0
            confluence_score += 5 if has_narrow else 0
            confluence_score += 20 if reversal else 0
            recent_rejections = sub_df.iloc[-3:]
            if (recent_rejections['lower_wick_ratio'] >= 0.6).any():
                confluence_score += 20
            if (recent_rejections['volume_ratio'] >= 1.5).any():
                confluence_score += 10
            confluence_score += 20 if sweep else 0
            
            # Print if there is any interesting setup or any matching candle
            is_interesting = cond1 or reversal or sweep or has_reversal_with_sweep
            
            # Let's print rows where there's a sweep or reversal to inspect details
            if reversal or sweep:
                print(f"{idx} | {entry_price:.5f} | Cond1: {cond1} | Rev: {reversal} | Sweep: {sweep} | Both: {reversal and sweep} | Score: {confluence_score} | R:R: 1:{risk_reward:.2f}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scanner.data_fetcher.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
