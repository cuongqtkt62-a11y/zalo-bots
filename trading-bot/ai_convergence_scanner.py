"""
🤖 AI + CRYPTO CONVERGENCE SCANNER
Quét toàn bộ hệ sinh thái AI/DePIN/Compute/AI Agents trên Binance Futures
Phân tích dòng tiền + Win Score cho narrative chính 2026-2027

Phân loại:
1. 🧠 AI Intelligence & Agents (FET, TAO, WLD, ARKM, VIRTUAL...)
2. 🖥️ Decentralized Compute / GPU (RENDER, AKT, IO, FLUX...)
3. 📡 DePIN Infrastructure (HNT, IOTX, DIMO, MOBILE...)
4. 🔗 AI Data & Oracles (GRT, OCEAN, LINK, PYTH...)
5. 🤖 AI Agent Frameworks (VIRTUAL, AI16Z, GRIFFAIN...)
"""
import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from datetime import datetime

# ═══════════════════════════════════════════════════
# AI + CRYPTO CONVERGENCE TOKEN MAP
# ═══════════════════════════════════════════════════
AI_CRYPTO_MAP = {
    "🧠 AI Intelligence & Agents": {
        "tokens": [
            "FET/USDT:USDT",      # Fetch.ai / ASI Alliance
            "TAO/USDT:USDT",      # Bittensor
            "WLD/USDT:USDT",      # Worldcoin (Sam Altman)
            "ARKM/USDT:USDT",     # Arkham Intelligence
            "VIRTUAL/USDT:USDT",  # Virtuals Protocol
            "NEAR/USDT:USDT",     # NEAR Protocol (L1 + AI Infra)
        ],
        "description": "AI models, intelligence networks, agent marketplaces",
        "catalyst": "Anthropic IPO → xác nhận giá trị AI → hưởng lợi narrative",
    },
    "🖥️ Decentralized Compute / GPU": {
        "tokens": [
            "RENDER/USDT:USDT",   # Render Network
            "AKT/USDT:USDT",      # Akash Network
            "IO/USDT:USDT",       # io.net
            "FLUX/USDT:USDT",     # Flux
            "ATH/USDT:USDT",      # Aethir
        ],
        "description": "GPU marketplace, compute rental, AI training infra",
        "catalyst": "GPU shortage + Anthropic/OpenAI tăng nhu cầu compute → demand tăng",
    },
    "📡 DePIN Infrastructure": {
        "tokens": [
            "HNT/USDT:USDT",      # Helium
            "IOTX/USDT:USDT",     # IoTeX
            "MOBILE/USDT:USDT",   # Helium Mobile
            "GRASS/USDT:USDT",    # Grass (data scraping network)
        ],
        "description": "Physical infrastructure networks, IoT, wireless",
        "catalyst": "Real-world data cho AI training → giá trị thực",
    },
    "🔗 AI Data & Oracles": {
        "tokens": [
            "GRT/USDT:USDT",      # The Graph
            "LINK/USDT:USDT",     # Chainlink
            "PYTH/USDT:USDT",     # Pyth Network
            "FIL/USDT:USDT",      # Filecoin (storage)
            "AR/USDT:USDT",       # Arweave (permanent storage)
        ],
        "description": "Data indexing, oracle feeds, storage cho AI models",
        "catalyst": "AI agents cần data on-chain → GRT, LINK volume tăng",
    },
    "🤖 AI Agent Frameworks": {
        "tokens": [
            "VIRTUAL/USDT:USDT",  # Virtuals Protocol
            "JASMY/USDT:USDT",    # JasmyCoin (IoT + data)
            "PHA/USDT:USDT",      # Phala Network (confidential computing)
            "AIOZ/USDT:USDT",     # AIOZ Network
            "NIL/USDT:USDT",      # Nil Foundation (ZK + AI)
        ],
        "description": "Agent launchpads, frameworks, confidential AI",
        "catalyst": "Autonomous agents economy → demand cho execution layers",
    },
}


class AIDePINScanner:
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

    def analyze_deep(self, df_1h, df_4h, df_1d, symbol, ticker):
        """Phân tích sâu — Win Score + Entry/SL/TP"""
        if df_4h is None or len(df_4h) < 50:
            return None

        close = df_4h['close']
        high = df_4h['high']
        low = df_4h['low']
        vol = df_4h['volume']
        price = close.iloc[-1]

        result = {
            'symbol': symbol.split('/')[0],
            'full_symbol': symbol,
            'price': price,
            'win_score': 0,
            'flow_score': 0,  # Dòng tiền score
            'reasons': [],
            'warnings': [],
        }

        # ═══ 1. EMA ALIGNMENT (4H) ═══
        ema34 = self.calc_ema(close, 34)
        ema89 = self.calc_ema(close, 89)
        ema200 = self.calc_ema(close, 200) if len(close) >= 200 else None
        ema34_now = ema34.iloc[-1]
        ema89_now = ema89.iloc[-1]

        if ema200 is not None:
            ema200_now = ema200.iloc[-1]
            if price > ema34_now > ema89_now > ema200_now:
                result['win_score'] += 20
                result['ema_status'] = "🟢 Bullish hoàn hảo"
                result['reasons'].append("✅ EMA bullish (P > 34 > 89 > 200)")
            elif price > ema34_now > ema89_now:
                result['win_score'] += 10
                result['ema_status'] = "🟡 Gần bullish"
                result['reasons'].append("🟡 EMA gần bullish (P > 34 > 89)")
            elif price > ema34_now:
                result['win_score'] += 3
                result['ema_status'] = "🟠 Hỗn hợp"
            else:
                result['win_score'] -= 5
                result['ema_status'] = "🔴 Bearish"
                result['warnings'].append("❌ EMA bearish")
        else:
            if price > ema34_now > ema89_now:
                result['win_score'] += 10
                result['ema_status'] = "🟡 Gần bullish"
            else:
                result['ema_status'] = "🟠 N/A"

        # ═══ 2. RSI ═══
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        result['rsi'] = rsi

        if 50 <= rsi <= 60:
            result['win_score'] += 15
            result['reasons'].append(f"✅ RSI {rsi:.0f} — PERFECT zone")
        elif 60 < rsi <= 68:
            result['win_score'] += 10
            result['reasons'].append(f"✅ RSI {rsi:.0f} — Momentum tốt")
        elif 45 <= rsi < 50:
            result['win_score'] += 8
        elif rsi > 75:
            result['win_score'] -= 10
            result['warnings'].append(f"🚨 RSI {rsi:.0f} — QUÁ MUA")
        elif rsi > 68:
            result['win_score'] -= 3
            result['warnings'].append(f"⚠️ RSI {rsi:.0f} — Gần quá mua")

        # ═══ 3. VOLUME SURGE ═══
        vol_avg_20 = vol.rolling(20).mean().iloc[-1]
        vol_recent = vol.tail(3).mean()
        vol_surge = vol_recent / vol_avg_20 if vol_avg_20 > 0 else 1
        result['vol_surge'] = vol_surge

        if vol_surge > 3.0:
            result['win_score'] += 15
            result['flow_score'] += 25
            result['reasons'].append(f"🔥🔥🔥 Vol SURGE {vol_surge:.1f}x")
        elif vol_surge > 2.0:
            result['win_score'] += 10
            result['flow_score'] += 18
            result['reasons'].append(f"🔥🔥 Vol tăng {vol_surge:.1f}x")
        elif vol_surge > 1.5:
            result['win_score'] += 7
            result['flow_score'] += 12
            result['reasons'].append(f"🔥 Vol tăng {vol_surge:.1f}x")
        elif vol_surge > 1.2:
            result['win_score'] += 4
            result['flow_score'] += 6
        else:
            result['warnings'].append(f"📉 Vol yếu {vol_surge:.1f}x")

        # ═══ 4. OBV ═══
        obv = (np.sign(close.diff()) * vol).cumsum()
        obv_10 = self.calc_ema(obv, 10).iloc[-1]
        obv_30 = self.calc_ema(obv, 30).iloc[-1]
        if obv_10 > obv_30:
            result['win_score'] += 10
            result['flow_score'] += 10
            result['obv'] = "💰 Tăng"
            result['reasons'].append("💰 OBV tăng — Tiền thực chảy vào")
        else:
            result['obv'] = "📉 Giảm"
            result['warnings'].append("📉 OBV giảm")

        # ═══ 5. MOMENTUM ═══
        change_24h = ticker.get('percentage', 0) or 0
        change_3d = (price / close.iloc[-18] - 1) * 100 if len(close) >= 18 else 0
        change_7d = (price / close.iloc[-42] - 1) * 100 if len(close) >= 42 else 0
        result['change_24h'] = change_24h
        result['change_3d'] = change_3d
        result['change_7d'] = change_7d

        if 10 < change_7d <= 30:
            result['win_score'] += 5
        elif change_7d > 50:
            result['win_score'] -= 10
            result['warnings'].append(f"🚨 +{change_7d:.0f}% 7d — Quá nóng!")

        # ═══ 6. PULLBACK TO EMA ═══
        dist_ema34 = (price - ema34_now) / ema34_now * 100
        result['dist_ema34'] = dist_ema34
        if 0 <= dist_ema34 <= 2:
            result['win_score'] += 12
            result['reasons'].append(f"🎯 Sát EMA34 ({dist_ema34:.1f}%) — Entry ngon!")
        elif 0 <= dist_ema34 <= 4:
            result['win_score'] += 6
        elif dist_ema34 > 10:
            result['win_score'] -= 5
            result['warnings'].append(f"⚠️ Xa EMA34 ({dist_ema34:.1f}%)")

        # ═══ 7. MULTI-TF CONFIRM (1H) ═══
        if df_1h is not None and len(df_1h) >= 90:
            close_1h = df_1h['close']
            ema34_1h = self.calc_ema(close_1h, 34).iloc[-1]
            ema89_1h = self.calc_ema(close_1h, 89).iloc[-1]
            if price > ema34_1h > ema89_1h:
                result['win_score'] += 8
                result['reasons'].append("✅ 1H cũng bullish — Multi-TF ✓")

        # ═══ 8. BREAKOUT PROXIMITY ═══
        high_20d = high.tail(120).max()
        if price >= high_20d * 0.97:
            result['win_score'] += 8
            result['reasons'].append("🚀 Sát đỉnh 20 ngày!")

        # ═══ 9. ACCUMULATION ═══
        recent_range = (close.tail(12).max() - close.tail(12).min()) / close.tail(12).mean() * 100
        if recent_range < 6 and vol_surge > 1.0:
            result['win_score'] += 8
            result['reasons'].append(f"🏦 Tích lũy (range {recent_range:.1f}%) + vol OK")

        # ═══ 10. ATR ENTRY/SL/TP ═══
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]

        entry = price
        sl = max(entry - 1.5 * atr, ema89_now * 0.995) if price > ema89_now else entry - 2 * atr
        if sl >= entry:
            sl = entry - 2 * atr
        tp1 = entry + 1.5 * atr
        tp2 = entry + 2.5 * atr
        tp3 = entry + 4.0 * atr
        risk = entry - sl

        result['entry'] = entry
        result['entry_limit'] = ema34_now
        result['sl'] = sl
        result['tp1'] = tp1
        result['tp2'] = tp2
        result['tp3'] = tp3
        result['rr2'] = (tp2 - entry) / risk if risk > 0 else 0
        result['risk_pct'] = (entry - sl) / entry * 100
        result['vol_24h'] = ticker.get('quoteVolume', 0) or 0

        # VERDICT
        score = result['win_score']
        if score >= 65:
            result['verdict'] = "🏆 STRONG BUY"
            result['grade'] = "A+"
        elif score >= 50:
            result['verdict'] = "✅ BUY"
            result['grade'] = "A"
        elif score >= 35:
            result['verdict'] = "👀 WATCH"
            result['grade'] = "B"
        elif score >= 20:
            result['verdict'] = "⏳ HOLD"
            result['grade'] = "C"
        else:
            result['verdict'] = "❌ SKIP"
            result['grade'] = "D"

        return result

    async def scan_all(self):
        print("=" * 70)
        print("🤖 AI + CRYPTO CONVERGENCE SCANNER")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        await self.exchange.load_markets()
        tickers = await self.exchange.fetch_tickers()

        all_results = {}
        total_tokens = sum(len(cat['tokens']) for cat in AI_CRYPTO_MAP.values())
        scanned = 0

        for category, info in AI_CRYPTO_MAP.items():
            cat_results = []
            for sym in info['tokens']:
                scanned += 1
                base = sym.split('/')[0]
                print(f"  [{scanned}/{total_tokens}] {base}...")

                if sym not in tickers:
                    print(f"    ⚠️ {base} không có trên Binance Futures")
                    continue

                try:
                    df_1h, df_4h, df_1d = await asyncio.gather(
                        self.fetch_ohlcv(sym, '1h', 300),
                        self.fetch_ohlcv(sym, '4h', 300),
                        self.fetch_ohlcv(sym, '1d', 150),
                    )
                    analysis = self.analyze_deep(df_1h, df_4h, df_1d, sym, tickers[sym])
                    if analysis:
                        cat_results.append(analysis)
                except Exception as e:
                    print(f"    ❌ Lỗi: {e}")

                if scanned % 3 == 0:
                    await asyncio.sleep(0.3)

            cat_results.sort(key=lambda x: x['win_score'], reverse=True)
            all_results[category] = {
                'results': cat_results,
                'description': info['description'],
                'catalyst': info['catalyst'],
            }

        self.print_report(all_results)
        return all_results

    def print_report(self, all_results):
        print("\n" + "═" * 70)
        print("🤖🔗 BÁO CÁO AI + CRYPTO CONVERGENCE")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("═" * 70)

        # Flatten all for top ranking
        flat = []
        for cat, data in all_results.items():
            for r in data['results']:
                r['category'] = cat
                flat.append(r)
        flat.sort(key=lambda x: x['win_score'], reverse=True)

        # TOP RANKING
        print(f"\n{'🏆 TOP RANKING — AI + CRYPTO':=^70}")
        print(f"{'#':<3} {'Token':<10} {'Score':<7} {'Grade':<5} {'RSI':<5} "
              f"{'Vol↑':<6} {'24h':<8} {'7d':<8} {'EMA':<20}")
        print("-" * 70)
        for i, r in enumerate(flat, 1):
            emoji = "🥇" if i <= 3 else "🥈" if i <= 6 else "🥉" if i <= 9 else "  "
            print(f"{emoji}{i:<2} {r['symbol']:<10} {r['win_score']:<7} {r.get('grade',''):<5} "
                  f"{r['rsi']:<5.0f} {r['vol_surge']:<5.1f}x "
                  f"{r['change_24h']:>+6.1f}% {r['change_7d']:>+6.1f}% "
                  f"{r.get('ema_status','')}")

        # PER CATEGORY
        for cat, data in all_results.items():
            results = data['results']
            if not results:
                continue

            avg_score = sum(r['win_score'] for r in results) / len(results)
            print(f"\n{'─' * 70}")
            fire = "🔥🔥🔥" if avg_score >= 50 else "🔥🔥" if avg_score >= 35 else "🔥" if avg_score >= 20 else "📊"
            print(f"{cat}  {fire} Avg Score: {avg_score:.0f}")
            print(f"  📝 {data['description']}")
            print(f"  🎯 Catalyst: {data['catalyst']}")
            print(f"{'─' * 70}")

            for r in results:
                grade_emoji = "⭐⭐⭐" if r['win_score'] >= 60 else "⭐⭐" if r['win_score'] >= 40 else "⭐" if r['win_score'] >= 25 else ""
                print(f"\n  {grade_emoji} {r['symbol']:<10} Win Score: {r['win_score']} | {r['verdict']}")
                print(f"     💲 ${r['price']:.4f} | RSI: {r['rsi']:.0f} | Vol: {r['vol_surge']:.1f}x | {r.get('ema_status','')}")
                print(f"     📈 24h: {r['change_24h']:+.1f}% | 3d: {r['change_3d']:+.1f}% | 7d: {r['change_7d']:+.1f}%")
                print(f"     OBV: {r.get('obv','')} | Vol24h: ${r['vol_24h']/1e6:.0f}M")

                if r['win_score'] >= 35:
                    print(f"     📍 Entry: ${r['entry']:.4f} | Limit: ${r['entry_limit']:.4f}")
                    print(f"     🛑 SL: ${r['sl']:.4f} (-{r['risk_pct']:.1f}%)")
                    print(f"     ✅ TP1: ${r['tp1']:.4f} | TP2: ${r['tp2']:.4f} | R:R 1:{r['rr2']:.1f}")

                if r['reasons']:
                    for reason in r['reasons'][:4]:
                        print(f"     {reason}")
                if r['warnings']:
                    for w in r['warnings'][:2]:
                        print(f"     {w}")

        # SUMMARY
        print("\n" + "═" * 70)
        print("📋 TÓM TẮT NHANH")
        print("═" * 70)

        buys = [r for r in flat if r.get('grade', 'D') in ('A+', 'A')]
        watches = [r for r in flat if r.get('grade', 'D') == 'B']

        if buys:
            print("\n💰 NÊN LONG (Grade A+/A):")
            for i, r in enumerate(buys, 1):
                print(f"  {i}. {r['grade']} {r['symbol']:<8} [{r['category'].split()[0]}] "
                      f"Score {r['win_score']} | Entry ${r['entry']:.4f} | "
                      f"SL ${r['sl']:.4f} (-{r['risk_pct']:.1f}%) | R:R 1:{r['rr2']:.1f}")

        if watches:
            print("\n👀 WATCHLIST (Grade B):")
            for i, r in enumerate(watches, 1):
                print(f"  {i}. {r['symbol']:<8} [{r['category'].split()[0]}] "
                      f"Score {r['win_score']} | RSI {r['rsi']:.0f} | Vol {r['vol_surge']:.1f}x")

        # Category ranking
        print("\n📊 XẾP HẠNG CATEGORY:")
        cat_scores = []
        for cat, data in all_results.items():
            if data['results']:
                avg = sum(r['win_score'] for r in data['results']) / len(data['results'])
                cat_scores.append((cat, avg, len(data['results'])))
        cat_scores.sort(key=lambda x: x[1], reverse=True)
        for i, (cat, avg, cnt) in enumerate(cat_scores, 1):
            fire = "🔥" if avg >= 35 else "📊"
            print(f"  {i}. {fire} {cat} — Avg: {avg:.0f} ({cnt} tokens)")

        print(f"\n{'═' * 70}")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═' * 70}")

    def generate_html_report(self, all_results):
        # Flatten all for top ranking
        flat = []
        for cat, data in all_results.items():
            for r in data['results']:
                r['category'] = cat
                flat.append(r)
        flat.sort(key=lambda x: x['win_score'], reverse=True)

        buys = [r for r in flat if r.get('grade', 'D') in ('A+', 'A')]
        watches = [r for r in flat if r.get('grade', 'D') == 'B']

        html = "🤖 <b>BÁO CÁO AI + CRYPTO CONVERGENCE</b> 🤖\n"
        html += f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>\n"
        html += "━━━━━━━━━━━━━━━━━━━━\n\n"

        if buys:
            html += "💰 <b>TOP COIN NÊN LONG (Grade A)</b>\n"
            for i, r in enumerate(buys, 1):
                cat_emoji = r['category'].split()[0]
                html += (f"<b>{i}. {r['symbol']}</b> {cat_emoji} | Score: {r['win_score']}\n"
                         f"▶️ Entry: {r['entry']:.4f}\n"
                         f"🛑 SL: {r['sl']:.4f} (-{r['risk_pct']:.1f}%)\n"
                         f"🎯 R:R 1:{r['rr2']:.1f} | RSI: {r['rsi']:.0f}\n\n")

        if watches:
            html += "👀 <b>WATCHLIST (Grade B)</b>\n"
            for i, r in enumerate(watches, 1):
                cat_emoji = r['category'].split()[0]
                html += f"<b>{i}. {r['symbol']}</b> {cat_emoji} | Score: {r['win_score']} | Vol: {r['vol_surge']:.1f}x\n"
            html += "\n"

        html += "📊 <b>XẾP HẠNG CATEGORY</b>\n"
        cat_scores = []
        for cat, data in all_results.items():
            if data['results']:
                avg = sum(r['win_score'] for r in data['results']) / len(data['results'])
                cat_scores.append((cat, avg, len(data['results'])))
        cat_scores.sort(key=lambda x: x[1], reverse=True)
        
        for i, (cat, avg, cnt) in enumerate(cat_scores, 1):
            fire = "🔥" if avg >= 35 else "📊"
            html += f"{i}. {fire} {cat}\n   └ Avg: {avg:.0f} ({cnt} tokens)\n"

        html += "\n💡 <i>Narrative AI + Crypto đang cực hot trước thềm Anthropic IPO!</i>"
        return html



async def main():
    scanner = AIDePINScanner()
    try:
        results = await scanner.scan_all()
    finally:
        await scanner.close()


if __name__ == "__main__":
    asyncio.run(main())
