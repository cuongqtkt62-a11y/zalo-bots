"""
🎯 WINNER PICKER — Chọn token có xác suất WIN cao nhất
Deep-dive phân tích: Entry / SL / TP / R:R / Confluence

Bộ lọc CHẶT:
1. ✅ EMA bullish hoàn hảo (P > EMA34 > EMA89 > EMA200)
2. ✅ RSI 45-68 (sweet spot — không quá mua)
3. ✅ OBV đang tăng (tiền chảy vào)
4. ✅ 7d change < 50% (chưa quá nóng, tránh FOMO đỉnh)
5. ✅ Volume ≥ 1.0x trung bình
6. ✅ Có pullback về EMA → entry ngon
7. ✅ ATR-based SL/TP → R:R ≥ 1:2
"""
import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from datetime import datetime


CANDIDATES = [
    "ID/USDT:USDT",       # Score 87, BNB Chain (BSC)
    "XLM/USDT:USDT",      # Score 82
    "INJ/USDT:USDT",      # Score 64, Cosmos
    "BAT/USDT:USDT",      # Score 63
    "HYPE/USDT:USDT",     # Score 58, Layer 1 / DeFi
    "AR/USDT:USDT",       # Score 57, Infra
    "DEXE/USDT:USDT",     # Score 53, Gaming
    "DYDX/USDT:USDT",     # Score 52, DeFi Blue Chips
    "IO/USDT:USDT",       # Score 50, AI/DePIN
    "FET/USDT:USDT",      # Score 49, AI/DePIN
    "SEI/USDT:USDT",      # Layer 1 / Cosmos
    "ICP/USDT:USDT",      # Layer 1
    "WLD/USDT:USDT",      # AI/DePIN
    "DRIFT/USDT:USDT",    # Solana
    "RONIN/USDT:USDT",    # Gaming
    "AKT/USDT:USDT",      # AI/DePIN
    "TIA/USDT:USDT",      # Cosmos
]




class WinnerPicker:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })

    async def close(self):
        await self.exchange.close()

    async def fetch_ohlcv(self, symbol, timeframe, limit=200):
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except:
            return None

    def calc_ema(self, s, p):
        return s.ewm(span=p, adjust=False).mean()

    def analyze_deep(self, df_5m, df_1h, df_4h, df_1d, symbol):
        """
        Phân tích sâu — trả về dict với entry/SL/TP/R:R + win probability
        """
        if df_4h is None or len(df_4h) < 60:
            return None
        if df_1h is None or len(df_1h) < 50:
            return None

        close_4h = df_4h['close']
        high_4h = df_4h['high']
        low_4h = df_4h['low']
        vol_4h = df_4h['volume']
        price = close_4h.iloc[-1]

        result = {
            'symbol': symbol.split('/')[0],
            'price': price,
            'win_score': 0,      # 0-100, cao = win xác suất cao
            'reasons': [],
            'warnings': [],
            'verdict': '',
        }

        # ═══════════════════════════════════════
        # 1. EMA ALIGNMENT CHECK (4H)
        # ═══════════════════════════════════════
        ema34 = self.calc_ema(close_4h, 34)
        ema89 = self.calc_ema(close_4h, 89)
        ema200 = self.calc_ema(close_4h, 200)
        ema610 = self.calc_ema(close_4h, 610) if len(close_4h) >= 610 else None

        ema34_now = ema34.iloc[-1]
        ema89_now = ema89.iloc[-1]
        ema200_now = ema200.iloc[-1]

        # Perfect bullish stack
        if price > ema34_now > ema89_now > ema200_now:
            result['win_score'] += 20
            result['reasons'].append("✅ EMA bullish hoàn hảo (P > 34 > 89 > 200)")
            
            # Bonus: EMA610 cũng dưới
            if ema610 is not None and ema200_now > ema610.iloc[-1]:
                result['win_score'] += 5
                result['reasons'].append("✅ EMA610 cũng bullish")
        elif price > ema34_now > ema89_now:
            result['win_score'] += 10
            result['reasons'].append("🟡 EMA gần bullish (P > 34 > 89)")
        else:
            result['win_score'] -= 10
            result['warnings'].append("❌ EMA CHƯA bullish — KHÔNG nên vào")
            result['verdict'] = "❌ BỎ QUA"
            return result

        # EMA slope — đang tăng tốc?
        ema34_slope = (ema34.iloc[-1] - ema34.iloc[-3]) / ema34.iloc[-3] * 100
        if ema34_slope > 0.5:
            result['win_score'] += 5
            result['reasons'].append(f"📈 EMA34 đang dốc lên (+{ema34_slope:.2f}%)")

        # ═══════════════════════════════════════
        # 2. RSI SWEET SPOT
        # ═══════════════════════════════════════
        delta = close_4h.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        if 50 <= rsi <= 60:
            result['win_score'] += 15
            result['reasons'].append(f"✅ RSI {rsi:.0f} — PERFECT entry zone")
        elif 60 < rsi <= 68:
            result['win_score'] += 10
            result['reasons'].append(f"✅ RSI {rsi:.0f} — Momentum tốt")
        elif 45 <= rsi < 50:
            result['win_score'] += 8
            result['reasons'].append(f"🟡 RSI {rsi:.0f} — Vùng support")
        elif rsi > 75:
            result['win_score'] -= 15
            result['warnings'].append(f"🚨 RSI {rsi:.0f} — QUÁ MUA! Nguy hiểm")
        elif rsi > 68:
            result['win_score'] -= 5
            result['warnings'].append(f"⚠️ RSI {rsi:.0f} — Gần quá mua")
        else:
            result['warnings'].append(f"📉 RSI {rsi:.0f} — Yếu")

        result['rsi'] = rsi

        # ═══════════════════════════════════════
        # 3. VOLUME CONFIRMATION
        # ═══════════════════════════════════════
        vol_avg_20 = vol_4h.rolling(20).mean().iloc[-1]
        vol_recent = vol_4h.tail(3).mean()
        vol_surge = vol_recent / vol_avg_20 if vol_avg_20 > 0 else 1

        if vol_surge > 2.5:
            result['win_score'] += 12
            result['reasons'].append(f"🔥🔥 Volume SURGE {vol_surge:.1f}x — Tiền đổ vào mạnh")
        elif vol_surge > 1.5:
            result['win_score'] += 8
            result['reasons'].append(f"🔥 Volume tăng {vol_surge:.1f}x")
        elif vol_surge > 1.0:
            result['win_score'] += 4
            result['reasons'].append(f"📊 Volume OK {vol_surge:.1f}x")
        else:
            result['win_score'] -= 3
            result['warnings'].append(f"📉 Volume yếu {vol_surge:.1f}x — thiếu xác nhận")

        result['vol_surge'] = vol_surge

        # ═══════════════════════════════════════
        # 4. OBV TREND — Dòng tiền thực
        # ═══════════════════════════════════════
        obv = (np.sign(close_4h.diff()) * vol_4h).cumsum()
        obv_ema10 = self.calc_ema(obv, 10).iloc[-1]
        obv_ema30 = self.calc_ema(obv, 30).iloc[-1]

        if obv_ema10 > obv_ema30:
            obv_strength = (obv_ema10 - obv_ema30) / abs(obv_ema30) * 100 if obv_ema30 != 0 else 0
            result['win_score'] += 10
            result['reasons'].append(f"💰 OBV tăng — Tiền THỰC chảy vào")
        else:
            result['win_score'] -= 5
            result['warnings'].append("📉 OBV giảm — Dòng tiền yếu")

        # ═══════════════════════════════════════
        # 5. OVEREXTENSION CHECK
        # ═══════════════════════════════════════
        change_7d = (price / close_4h.iloc[-42] - 1) * 100 if len(close_4h) >= 42 else 0
        change_3d = (price / close_4h.iloc[-18] - 1) * 100 if len(close_4h) >= 18 else 0
        change_24h = (price / close_4h.iloc[-6] - 1) * 100 if len(close_4h) >= 6 else 0

        if change_7d > 60:
            result['win_score'] -= 15
            result['warnings'].append(f"🚨 Đã tăng {change_7d:.0f}% 7d — QUÁ NÓNG, dễ dump")
        elif change_7d > 40:
            result['win_score'] -= 8
            result['warnings'].append(f"⚠️ Đã tăng {change_7d:.0f}% 7d — Cẩn thận")
        elif 10 < change_7d <= 30:
            result['win_score'] += 5
            result['reasons'].append(f"📈 Momentum tốt +{change_7d:.0f}% 7d (chưa nóng)")
        elif 0 < change_7d <= 10:
            result['win_score'] += 3

        result['change_24h'] = change_24h
        result['change_3d'] = change_3d
        result['change_7d'] = change_7d

        # ═══════════════════════════════════════
        # 6. PULLBACK TO EMA — Entry đẹp?
        # ═══════════════════════════════════════
        dist_to_ema34 = (price - ema34_now) / ema34_now * 100
        dist_to_ema89 = (price - ema89_now) / ema89_now * 100

        if 0 <= dist_to_ema34 <= 1.5:
            result['win_score'] += 12
            result['reasons'].append(f"🎯 Giá sát EMA34 ({dist_to_ema34:.1f}%) — ENTRY NGON!")
        elif 0 <= dist_to_ema34 <= 3:
            result['win_score'] += 6
            result['reasons'].append(f"📍 Giá gần EMA34 ({dist_to_ema34:.1f}%)")
        elif dist_to_ema34 > 8:
            result['win_score'] -= 5
            result['warnings'].append(f"⚠️ Giá xa EMA34 ({dist_to_ema34:.1f}%) — có thể pullback")

        # ═══════════════════════════════════════
        # 7. ATR-BASED ENTRY / SL / TP
        # ═══════════════════════════════════════
        atr_series = pd.DataFrame()
        tr = pd.concat([
            high_4h - low_4h,
            abs(high_4h - close_4h.shift(1)),
            abs(low_4h - close_4h.shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = atr / price * 100

        # Entry = giá hiện tại (market) hoặc limit tại EMA34
        entry = price
        entry_limit = ema34_now  # Limit order tại EMA34

        # SL dưới EMA89 hoặc 1.5x ATR
        sl_atr = entry - 1.5 * atr
        sl_ema = ema89_now * 0.995  # Dưới EMA89 0.5%
        sl = max(sl_atr, sl_ema)  # Chọn SL gần hơn (risk ít hơn)

        # Nếu SL > entry (impossible trade)
        if sl >= entry:
            sl = entry - 2 * atr

        risk = entry - sl
        
        # TP phân tầng
        tp1 = entry + 1.5 * atr  # TP1: 1.5x ATR
        tp2 = entry + 2.5 * atr  # TP2: 2.5x ATR
        tp3 = entry + 4.0 * atr  # TP3: 4x ATR (trailing)

        rr1 = (tp1 - entry) / risk if risk > 0 else 0
        rr2 = (tp2 - entry) / risk if risk > 0 else 0
        rr3 = (tp3 - entry) / risk if risk > 0 else 0

        # R:R phải >= 1:2
        if rr2 >= 2.0:
            result['win_score'] += 8
            result['reasons'].append(f"✅ R:R tốt — TP2 = 1:{rr2:.1f}")
        elif rr1 >= 1.5:
            result['win_score'] += 4

        result['entry'] = entry
        result['entry_limit'] = entry_limit
        result['sl'] = sl
        result['tp1'] = tp1
        result['tp2'] = tp2
        result['tp3'] = tp3
        result['rr1'] = rr1
        result['rr2'] = rr2
        result['rr3'] = rr3
        result['atr'] = atr
        result['atr_pct'] = atr_pct
        result['risk_pct'] = (entry - sl) / entry * 100

        # ═══════════════════════════════════════
        # 8. 1H TIMEFRAME CONFIRMATION
        # ═══════════════════════════════════════
        if df_1h is not None and len(df_1h) >= 90:
            close_1h = df_1h['close']
            ema34_1h = self.calc_ema(close_1h, 34).iloc[-1]
            ema89_1h = self.calc_ema(close_1h, 89).iloc[-1]
            
            if price > ema34_1h > ema89_1h:
                result['win_score'] += 8
                result['reasons'].append("✅ 1H cũng bullish (P > 34 > 89) — Multi-TF confirm")
            else:
                result['win_score'] -= 3
                result['warnings'].append("🟡 1H chưa align (P > 34 > 89) — chờ confirm")

        # ═══════════════════════════════════════
        # 9. ACCUMULATION PATTERN
        # ═══════════════════════════════════════
        recent_range = (close_4h.tail(12).max() - close_4h.tail(12).min()) / close_4h.tail(12).mean() * 100
        if recent_range < 6 and vol_surge > 1.0:
            result['win_score'] += 8
            result['reasons'].append(f"🏦 Tích lũy (range {recent_range:.1f}%) + Vol OK → Sắp bùng")
        elif recent_range < 8:
            result['win_score'] += 4
            result['reasons'].append(f"📦 Range hẹp {recent_range:.1f}%")

        # ═══════════════════════════════════════
        # 10. BREAKOUT PROXIMITY
        # ═══════════════════════════════════════
        high_20d = high_4h.tail(120).max()  # 20 ngày
        if price >= high_20d * 0.97:
            result['win_score'] += 8
            result['reasons'].append("🚀 Sát đỉnh 20 ngày — Breakout potential!")

        # ═══════════════════════════════════════
        # VERDICT
        # ═══════════════════════════════════════
        score = result['win_score']
        if score >= 70:
            result['verdict'] = "🏆 STRONG BUY — Win rate rất cao"
            result['grade'] = "A+"
        elif score >= 55:
            result['verdict'] = "✅ BUY — Win rate cao"
            result['grade'] = "A"
        elif score >= 40:
            result['verdict'] = "🟡 WATCH — Chờ pullback entry"
            result['grade'] = "B"
        elif score >= 25:
            result['verdict'] = "⏳ HOLD — Chưa đủ điều kiện"
            result['grade'] = "C"
        else:
            result['verdict'] = "❌ BỎ QUA"
            result['grade'] = "D"

        return result

    async def pick_winners(self):
        print("=" * 70)
        print("🎯 WINNER PICKER — Chọn token WIN RATE cao nhất")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        await self.exchange.load_markets()
        results = []

        for i, sym in enumerate(CANDIDATES, 1):
            print(f"  Phân tích {i}/{len(CANDIDATES)}: {sym.split('/')[0]}...")
            try:
                df_5m, df_1h, df_4h, df_1d = await asyncio.gather(
                    self.fetch_ohlcv(sym, '5m', 200),
                    self.fetch_ohlcv(sym, '1h', 300),
                    self.fetch_ohlcv(sym, '4h', 800),
                    self.fetch_ohlcv(sym, '1d', 150),
                )
                analysis = self.analyze_deep(df_5m, df_1h, df_4h, df_1d, sym)
                if analysis:
                    results.append(analysis)
            except Exception as e:
                print(f"    ❌ Lỗi: {e}")

            if i % 3 == 0:
                await asyncio.sleep(0.3)

        # Sort by win_score
        results.sort(key=lambda x: x['win_score'], reverse=True)

        # Print report
        self.print_report(results)
        return results

    def print_report(self, results):
        print("\n" + "=" * 70)
        print("🏆 KẾT QUẢ CHỌN TOKEN WIN — BẢNG XẾP HẠNG")
        print("=" * 70)

        # Winners (grade A+ and A)
        winners = [r for r in results if r.get('grade', 'D') in ('A+', 'A')]
        watchlist = [r for r in results if r.get('grade', 'D') == 'B']
        rejects = [r for r in results if r.get('grade', 'D') in ('C', 'D')]

        if winners:
            print(f"\n{'🏆 TOKEN NÊN LONG NGAY':=^70}")
            for i, r in enumerate(winners, 1):
                self._print_token_detail(r, i)

        if watchlist:
            print(f"\n{'👀 WATCH LIST — CHỜ PULLBACK':=^70}")
            for i, r in enumerate(watchlist, 1):
                self._print_token_brief(r, i)

        if rejects:
            print(f"\n{'❌ BỎ QUA — CHƯA ĐỦ ĐIỀU KIỆN':=^70}")
            for r in rejects:
                print(f"  ❌ {r['symbol']:<10} Score: {r['win_score']:<4} | {r['verdict']}")
                if r['warnings']:
                    for w in r['warnings'][:2]:
                        print(f"     {w}")

        # Final summary
        print("\n" + "=" * 70)
        print("📋 TÓM TẮT NHANH")
        print("=" * 70)
        if winners:
            print("\n💰 LONG NGAY (ưu tiên từ trên xuống):")
            for i, r in enumerate(winners, 1):
                risk_usd = 20 * 0.02  # $20 vốn, 2% risk
                print(
                    f"  {i}. {r['grade']} {r['symbol']:<10} "
                    f"Entry: ${r['entry']:.4f} | SL: ${r['sl']:.4f} (-{r['risk_pct']:.1f}%) | "
                    f"TP1: ${r['tp1']:.4f} | TP2: ${r['tp2']:.4f} | R:R 1:{r['rr2']:.1f}"
                )

    def _print_token_detail(self, r, idx):
        print(f"\n{'─' * 60}")
        print(f"  #{idx} {r['grade']} {r['symbol']} — Win Score: {r['win_score']} | {r['verdict']}")
        print(f"{'─' * 60}")
        print(f"  💲 Giá hiện tại: ${r['price']:.4f}")
        print(f"  📊 RSI: {r.get('rsi', 0):.0f} | Vol: {r.get('vol_surge', 0):.1f}x")
        print(f"  📈 24h: {r['change_24h']:+.1f}% | 3d: {r['change_3d']:+.1f}% | 7d: {r['change_7d']:+.1f}%")

        print(f"\n  🎯 ENTRY PLAN:")
        print(f"     📍 Entry (Market): ${r['entry']:.4f}")
        print(f"     📍 Entry (Limit tại EMA34): ${r['entry_limit']:.4f}")
        print(f"     🛑 Stop Loss: ${r['sl']:.4f} (-{r['risk_pct']:.1f}%)")
        print(f"     ✅ TP1 (40%): ${r['tp1']:.4f} | R:R 1:{r['rr1']:.1f}")
        print(f"     ✅ TP2 (30%): ${r['tp2']:.4f} | R:R 1:{r['rr2']:.1f}")
        print(f"     ✅ TP3 (30%): ${r['tp3']:.4f} | R:R 1:{r['rr3']:.1f}")

        # Risk calc for $20 account
        risk_pct = 2  # 2% risk
        risk_usd = 20 * risk_pct / 100
        risk_per_token = r['entry'] - r['sl']
        if risk_per_token > 0:
            position_size = risk_usd / risk_per_token
            position_usd = position_size * r['entry']
            leverage = position_usd / 20
            profit_tp1 = position_size * (r['tp1'] - r['entry'])
            profit_tp2 = position_size * (r['tp2'] - r['entry'])

            print(f"\n  💰 VỐN $20 — Risk 2% (${risk_usd:.2f}):")
            print(f"     📏 Size: {position_size:.2f} token (${position_usd:.1f})")
            print(f"     🔧 Leverage: ~{leverage:.0f}x")
            print(f"     💵 Profit TP1: +${profit_tp1:.2f}")
            print(f"     💵 Profit TP2: +${profit_tp2:.2f}")

        print(f"\n  ✅ LÝ DO VÀO LỆNH:")
        for reason in r['reasons']:
            print(f"     {reason}")
        if r['warnings']:
            print(f"  ⚠️ CẢNH BÁO:")
            for w in r['warnings']:
                print(f"     {w}")

    def _print_token_brief(self, r, idx):
        print(f"\n  #{idx} {r['symbol']:<10} Score: {r['win_score']:<4} | RSI: {r.get('rsi',0):.0f} | "
              f"Vol: {r.get('vol_surge',0):.1f}x | {r['verdict']}")
        print(f"     Entry: ${r['entry']:.4f} → SL: ${r['sl']:.4f} | TP2: ${r['tp2']:.4f} | R:R 1:{r['rr2']:.1f}")
        if r['reasons']:
            print(f"     {r['reasons'][0]}")
        if r['warnings']:
            print(f"     {r['warnings'][0]}")


async def main():
    picker = WinnerPicker()
    try:
        results = await picker.pick_winners()

        # Send to Telegram
        try:
            from telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()

            winners = [r for r in results if r.get('grade', 'D') in ('A+', 'A')]
            if winners:
                msg = "🏆 <b>TOKEN CHỌN LONG — Win Rate Cao</b>\n\n"
                for i, r in enumerate(winners, 1):
                    msg += (
                        f"<b>{i}. {r['grade']} {r['symbol']}</b> — Score {r['win_score']}\n"
                        f"   💲 Entry: <code>${r['entry']:.4f}</code>\n"
                        f"   🛑 SL: <code>${r['sl']:.4f}</code> (-{r['risk_pct']:.1f}%)\n"
                        f"   ✅ TP1: <code>${r['tp1']:.4f}</code> (1:{r['rr1']:.1f})\n"
                        f"   ✅ TP2: <code>${r['tp2']:.4f}</code> (1:{r['rr2']:.1f})\n"
                        f"   📊 RSI: {r.get('rsi',0):.0f} | Vol: {r.get('vol_surge',0):.1f}x\n\n"
                    )
                msg += f"<i>⏰ {datetime.now().strftime('%H:%M %d/%m')}</i>"
                await notifier.send_status(msg)
                print("\n📱 Đã gửi lên Telegram!")
        except Exception as e:
            print(f"⚠️ Telegram: {e}")

    finally:
        await picker.close()


if __name__ == "__main__":
    asyncio.run(main())
