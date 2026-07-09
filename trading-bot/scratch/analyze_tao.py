import asyncio
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from signal_scanner import SignalScanner, TradingSignal

class PatchedScanner(SignalScanner):
    def _check_confluence_setup(self, df: pd.DataFrame, symbol: str, bias: str) -> bool:
        if len(df) < 50:
            return False

        last = df.iloc[-1]
        recent = df.iloc[-20:]

        atr_pct = last.get('atr', 0) / last['close'] * 100
        if atr_pct < getattr(Config, 'MIN_ATR_PCT', 0.15):
            return False

        if pd.isna(last.get('ema_610', None)):
            return False

        sq_lb = Config.SQUEEZE_LOOKBACK_CANDLES
        has_squeeze = df['ema_squeeze'].iloc[-sq_lb:].any()
        has_narrow = df['dragon_narrow'].iloc[-sq_lb:].any()
        current_spread = last.get('ema_spread_pct', 100)

        ema_cluster_center = (last['ema_89'] + last['ema_200']) / 2
        price_distance_pct = abs(last['close'] - ema_cluster_center) / ema_cluster_center * 100
        price_distance_abs = abs(last['close'] - ema_cluster_center)
        
        # Test with 3.0 instead of 2.0
        if price_distance_pct > Config.MAX_PRICE_DISTANCE_FROM_EMA_PCT or price_distance_abs > 3.0 * last.get('atr', price_distance_abs):
            return False

        price_near_ema = (
            last.get('price_in_ema_cluster', False) or
            last.get('price_in_dragon', False) or
            last.get('touch_ema89', False) or
            last.get('touch_ema200', False)
        )

        is_strong_trend_long = (
            last['dragon_close'] > last['ema_89'] and 
            last['ema_89'] > last['ema_200']
        )
        is_strong_trend_short = (
            last['dragon_close'] < last['ema_89'] and 
            last['ema_89'] < last['ema_200']
        )

        cond1_compression = False
        confluence_score = 0
        checklist_details = []

        if has_squeeze and price_near_ema and current_spread <= Config.MAX_EMA_SPREAD_PCT:
            cond1_compression = True
            confluence_score += 25
            checklist_details.append(f"✅ Nén Sonic R: 4 EMA Hội Tụ ({current_spread:.1f}%)")
            if has_narrow:
                checklist_details.append("✅ Dragon Band thu hẹp")
                confluence_score += 5
        elif has_narrow and price_near_ema and current_spread <= Config.EMA_SQUEEZE_THRESHOLD_PCT * 1.2:
            cond1_compression = True
            confluence_score += 20
            checklist_details.append(f"⚠️ Nén Sonic R: Chỉ Dragon Band thu hẹp, EMA Spread {current_spread:.1f}%")
        elif (is_strong_trend_long or is_strong_trend_short) and price_near_ema:
            cond1_compression = True
            confluence_score += 20
            checklist_details.append(f"📈 Xu hướng Sonic R mạnh (Dragon > 89 > 200) — Pullback Setup")
        else:
            return False

        # Try to run standard parent method with modified check by monkey patching
        return True

async def test_patch():
    symbol = "TAO/USDT:USDT"
    scanner = SignalScanner()
    
    # Fetch data
    df_entry = await scanner.data_fetcher.fetch_ohlcv(symbol, Config.TIMEFRAME_ENTRY, limit=800)
    df_entry_clean = df_entry.iloc[:-1].copy()
    df_entry_indicators = scanner.indicators.calculate_all(df_entry_clean)
    bias = await scanner._get_cached_bias(symbol)
    
    # We will temporarily monkey patch the scanner method or calculate manually
    # Let's check target time 2026-06-13 05:00:00
    target_time = pd.to_datetime('2026-06-13 05:00:00')
    sub_df = df_entry_indicators.loc[:target_time]
    
    # Original check
    sig_orig = scanner._check_confluence_setup(sub_df, symbol, bias)
    print(f"Original scanner result: {sig_orig}")
    
    # Monkey patch the 2.0 to 3.0 inside signal_scanner.py method
    # To do this cleanly, we can read the file, modify 2.0 to 3.0, save it, run check, and restore it.
    # But even better, let's just inspect what the result is by writing a simulator!
    # Or we can just edit the code of signal_scanner.py and run a test script!
    
if __name__ == "__main__":
    asyncio.run(test_patch())
