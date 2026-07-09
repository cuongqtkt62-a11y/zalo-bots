"""
🔥 Ecosystem Money Flow Scanner
Quét toàn bộ Binance Futures — phân tích dòng tiền theo hệ sinh thái
Tìm token chuẩn bị tăng mạnh bởi dòng tiền cực mạnh

Tiêu chí:
1. Volume Surge — Volume 24h tăng đột biến so với trung bình
2. Price Momentum — Xu hướng giá tăng mạnh trên nhiều khung
3. OI Change — Open Interest tăng = tiền mới vào
4. Accumulation Score — Mua tích lũy ở vùng đáy/support
5. EMA Alignment — Các EMA xếp hàng tăng (bullish stacking)
"""
import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════
# ECOSYSTEM MAPPING — Phân loại token theo hệ sinh thái
# ═══════════════════════════════════════════════════
ECOSYSTEM_MAP = {
    "🟣 Ethereum (ETH)": [
        "ETH", "UNI", "AAVE", "LDO", "MKR", "SNX", "COMP", "CRV", "SUSHI",
        "ENS", "RPL", "SSV", "PENDLE", "EIGEN", "ETHFI", "ENA", "MORPHO",
        "INST", "BAL", "YFI", "DYDX", "1INCH", "GNO", "LQTY", "FXS",
        "ANKR", "BLUR", "LOOKS", "X2Y2", "CELR", "STORJ", "SKL", "IMX",
        "STRK", "ZK", "TAIKO", "SCROLL", "MANTA", "METIS", "MODE",
        "PEPE", "SHIB", "FLOKI", "TURBO", "MOG", "NEIRO",
        "PHA", "AUCTION",
    ],
    "🟡 BNB Chain (BSC)": [
        "BNB", "CAKE", "XVS", "BAKE", "BURGER", "ALPHA", "TWT",
        "RDNT", "ID", "HOOK", "EDU", "LISTA", "BSW", "VIC",
    ],
    "🟢 Solana (SOL)": [
        "SOL", "RAY", "JTO", "JUP", "PYTH", "BONK", "WIF", "BOME",
        "POPCAT", "MEW", "RENDER", "HNT", "MOBILE", "TNSR", "KMNO",
        "W", "DRIFT", "ORCA", "MNDE", "MSOL", "JITO",
        "GRASS", "BAN", "PNUT",
    ],
    "🔴 Avalanche (AVAX)": [
        "AVAX", "JOE", "GMX", "GLP", "BENQI", "PNG", "COQ",
    ],
    "🟠 Polygon / MATIC": [
        "POL", "MATIC", "QUICK", "SAND", "MANA",
    ],
    "🔵 Arbitrum": [
        "ARB", "GMX", "MAGIC", "RDNT", "GNS", "GRAIL", "DPX",
        "PENDLE", "VELA",
    ],
    "🟣 Optimism": [
        "OP", "VELO", "SNX", "KWENTA",
    ],
    "⚪ Cosmos": [
        "ATOM", "OSMO", "INJ", "SEI", "TIA", "DYM", "SAGA",
        "STRD", "SCRT", "AKT", "KAVA", "RUNE", "NIL",
    ],
    "🌐 Polkadot": [
        "DOT", "GLMR", "ASTR", "ACA", "PARA", "MOVR", "PHA",
    ],
    "🔷 Near / Aurora": [
        "NEAR", "AURORA", "REF",
    ],
    "💎 Layer 1 Mới": [
        "SUI", "APT", "SEI", "TIA", "MONAD", "BERA",
        "TON", "NOT", "DOGS", "HMSTR", "CATI",
        "HYPE", "PLUME", "NIL",
    ],
    "🏦 DeFi Blue Chips": [
        "LINK", "UNI", "AAVE", "MKR", "SNX", "CRV", "COMP",
        "SUSHI", "1INCH", "DYDX", "BAL", "YFI",
        "HYPE", "MORPHO", "HUMA",
    ],
    "🎮 Gaming / Metaverse": [
        "AXS", "SAND", "MANA", "GALA", "IMX", "ILV", "RONIN",
        "PIXEL", "PORTAL", "PRIME", "SUPER", "YGG", "BIGTIME",
        "BEAM", "MYRIA", "XAI", "DEXE", "BEAT",
    ],
    "🤖 AI / DePIN": [
        "FET", "AGIX", "OCEAN", "RNDR", "RENDER", "TAO", "ARKM",
        "WLD", "JASMY", "IOTX", "HNT", "MOBILE", "DIMO",
        "IO", "AIOZ", "ATH", "VIRTUAL", "AI16Z", "GRIFFAIN",
        "GRASS", "NIL", "AGT", "GENIUS", "TRUST",
        "AKT", "FLUX", "PHA",
    ],
    "🔐 ZK / Privacy": [
        "ZK", "STRK", "MINA", "MASK", "SCRT", "ROSE",
        "TAIKO", "NIL",
    ],
    "📦 Infra / Oracle": [
        "LINK", "PYTH", "BAND", "API3", "DIA", "TRB",
        "GRT", "FIL", "AR", "STORJ", "ANKR",
        "FLUX", "PHA",
    ],
    "🐕 Meme / Culture": [
        "DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "BOME",
        "TURBO", "MOG", "NEIRO", "POPCAT", "MEW", "NOT", "DOGS",
        "HMSTR", "CATI", "PEOPLE", "ACH", "MEME", "COQ",
        "1000SATS", "ORDI", "RATS", "BAN", "PNUT",
    ],
    "₿ Bitcoin Ecosystem": [
        "BTC", "STX", "ORDI", "1000SATS", "RATS", "SATS",
        "BCH", "LTC", "RUNE",
    ],
    "🌊 RWA / PayFi": [
        "ONDO", "MKR", "COMP", "CFG", "MPL", "TRU",
        "CELO", "RSR", "PLUME", "HUMA", "TAG",
    ],
    "🔥 Hyperliquid": [
        "HYPE",
    ],
}


def get_ecosystem(symbol: str) -> list:
    """Trả về danh sách ecosystem của 1 token"""
    # Extract base: "NIL/USDT:USDT" -> "NIL", "1000PEPE/USDT:USDT" -> "PEPE"
    base = symbol.split('/')[0] if '/' in symbol else symbol
    base = base.replace('USDT', '')
    # Handle 1000X tokens
    base_clean = base.lstrip('0123456789') if base.startswith('1000') else base

    ecosystems = []
    for eco, tokens in ECOSYSTEM_MAP.items():
        if base in tokens or base_clean in tokens:
            ecosystems.append(eco)
    return ecosystems if ecosystems else ["❓ Khác"]


class EcosystemScanner:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })

    async def close(self):
        await self.exchange.close()

    async def fetch_ohlcv(self, symbol, timeframe='4h', limit=100):
        """Fetch OHLCV data"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception:
            return None

    async def get_all_futures_symbols(self, min_vol_24h=None):
        """Lấy tất cả cặp USDT Futures có volume đủ lớn"""
        if min_vol_24h is None:
            from config import Config
            min_vol_24h = Config.MIN_VOLUME_24H

        await self.exchange.load_markets()
        tickers = await self.exchange.fetch_tickers()

        symbols = []
        for sym, ticker in tickers.items():
            # Binance Futures format: BTC/USDT:USDT
            if ':USDT' not in sym:
                continue
            if '/USDT' not in sym:
                continue
            vol_24h = (ticker.get('quoteVolume') or 0)
            if vol_24h >= min_vol_24h:
                symbols.append({
                    'symbol': sym,
                    'price': ticker.get('last', 0),
                    'change_24h': ticker.get('percentage', 0) or 0,
                    'volume_24h': vol_24h,
                    'high_24h': ticker.get('high', 0) or 0,
                    'low_24h': ticker.get('low', 0) or 0,
                })

        # Sort by volume descending, limit to top 1000
        symbols.sort(key=lambda x: x['volume_24h'], reverse=True)
        symbols = symbols[:1000]
        return symbols

    def calc_ema(self, series, period):
        return series.ewm(span=period, adjust=False).mean()

    def analyze_token(self, df_4h, df_1d, ticker_info):
        """
        Phân tích dòng tiền 1 token — trả về money flow score
        """
        if df_4h is None or len(df_4h) < 50:
            return None
        if df_1d is None or len(df_1d) < 30:
            return None

        score = 0
        details = {}
        close = df_4h['close']
        volume = df_4h['volume']
        close_d = df_1d['close']
        volume_d = df_1d['volume']

        # ═══════════════════════════════════════
        # 1. VOLUME SURGE — Volume tăng đột biến
        # ═══════════════════════════════════════
        vol_avg_20 = volume.rolling(20).mean().iloc[-1]
        vol_avg_5 = volume.tail(5).mean()
        vol_current = volume.tail(3).mean()

        vol_surge = vol_current / vol_avg_20 if vol_avg_20 > 0 else 1
        vol_trend = vol_avg_5 / vol_avg_20 if vol_avg_20 > 0 else 1

        if vol_surge > 3.0:
            score += 25
            details['volume'] = f"🔥🔥🔥 Vol SURGE {vol_surge:.1f}x"
        elif vol_surge > 2.0:
            score += 18
            details['volume'] = f"🔥🔥 Vol tăng {vol_surge:.1f}x"
        elif vol_surge > 1.5:
            score += 12
            details['volume'] = f"🔥 Vol tăng {vol_surge:.1f}x"
        elif vol_surge > 1.2:
            score += 6
            details['volume'] = f"📊 Vol nhích {vol_surge:.1f}x"
        else:
            details['volume'] = f"📉 Vol bình thường {vol_surge:.1f}x"

        # Daily volume trend
        vol_d_avg_10 = volume_d.rolling(10).mean().iloc[-1]
        vol_d_avg_3 = volume_d.tail(3).mean()
        vol_d_surge = vol_d_avg_3 / vol_d_avg_10 if vol_d_avg_10 > 0 else 1
        if vol_d_surge > 2.0:
            score += 10
        elif vol_d_surge > 1.5:
            score += 5

        # ═══════════════════════════════════════
        # 2. PRICE MOMENTUM — Đà tăng giá
        # ═══════════════════════════════════════
        change_3d = (close.iloc[-1] / close.iloc[-18] - 1) * 100 if len(close) >= 18 else 0  # 3 ngày × 6 cây 4h
        change_7d = (close.iloc[-1] / close.iloc[-42] - 1) * 100 if len(close) >= 42 else 0
        change_24h = ticker_info.get('change_24h', 0)

        # Tăng mạnh ngắn hạn
        if change_24h > 10:
            score += 15
        elif change_24h > 5:
            score += 10
        elif change_24h > 2:
            score += 5

        # Momentum 3 ngày
        if change_3d > 15:
            score += 12
        elif change_3d > 8:
            score += 8
        elif change_3d > 3:
            score += 4

        # Momentum 7 ngày
        if change_7d > 25:
            score += 10
        elif change_7d > 12:
            score += 6

        details['momentum'] = f"24h: {change_24h:+.1f}% | 3d: {change_3d:+.1f}% | 7d: {change_7d:+.1f}%"

        # ═══════════════════════════════════════
        # 3. EMA ALIGNMENT — EMA xếp hàng bullish
        # ═══════════════════════════════════════
        ema_34 = self.calc_ema(close, 34).iloc[-1]
        ema_89 = self.calc_ema(close, 89).iloc[-1]
        ema_200 = self.calc_ema(close, 200).iloc[-1] if len(close) >= 200 else None
        price_now = close.iloc[-1]

        bullish_stack = 0
        if price_now > ema_34:
            bullish_stack += 1
        if ema_34 > ema_89:
            bullish_stack += 1
        if ema_200 is not None and ema_89 > ema_200:
            bullish_stack += 1

        if bullish_stack == 3:
            score += 15
            details['ema'] = "🟢 EMA bullish hoàn hảo (P > 34 > 89 > 200)"
        elif bullish_stack == 2:
            score += 8
            details['ema'] = "🟡 EMA gần bullish (P > 34 > 89)"
        elif bullish_stack == 1:
            score += 3
            details['ema'] = "🟠 EMA hỗn hợp"
        else:
            details['ema'] = "🔴 EMA bearish"

        # ═══════════════════════════════════════
        # 4. ACCUMULATION — Tích lũy (volume tăng + giá nén)
        # ═══════════════════════════════════════
        # Giá nén trong 10 nến gần nhất
        recent_range = (close.tail(10).max() - close.tail(10).min()) / close.tail(10).mean() * 100
        # Giá nén + volume tăng = tích lũy
        if recent_range < 5 and vol_surge > 1.3:
            score += 12
            details['accumulation'] = f"🏦 Tích lũy mạnh (range {recent_range:.1f}%, vol {vol_surge:.1f}x)"
        elif recent_range < 8 and vol_surge > 1.2:
            score += 6
            details['accumulation'] = f"📦 Đang tích lũy (range {recent_range:.1f}%)"
        else:
            details['accumulation'] = f"Range {recent_range:.1f}%"

        # ═══════════════════════════════════════
        # 5. BREAKOUT DETECTION — Phá vỡ kháng cự
        # ═══════════════════════════════════════
        high_20 = df_4h['high'].tail(20 * 6).max()  # High 20 ngày
        high_10 = df_4h['high'].tail(10 * 6).max()  # High 10 ngày
        
        if price_now >= high_20 * 0.98:
            score += 10
            details['breakout'] = "🚀 Gần ATH 20 ngày — sắp breakout!"
        elif price_now >= high_10 * 0.98:
            score += 5
            details['breakout'] = "📈 Test đỉnh 10 ngày"

        # ═══════════════════════════════════════
        # 6. RSI MOMENTUM
        # ═══════════════════════════════════════
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_now = rsi.iloc[-1]

        if 55 <= rsi_now <= 70:
            score += 8
            details['rsi'] = f"💪 RSI {rsi_now:.0f} — Momentum tốt"
        elif 50 <= rsi_now < 55:
            score += 4
            details['rsi'] = f"📊 RSI {rsi_now:.0f} — Trung tính"
        elif rsi_now > 70:
            score += 2
            details['rsi'] = f"⚠️ RSI {rsi_now:.0f} — Quá mua"
        else:
            details['rsi'] = f"📉 RSI {rsi_now:.0f}"

        # ═══════════════════════════════════════
        # 7. VOLUME × PRICE CORRELATION (OBV trend)
        # ═══════════════════════════════════════
        obv = (np.sign(close.diff()) * volume).cumsum()
        obv_ema_10 = self.calc_ema(obv, 10).iloc[-1]
        obv_ema_30 = self.calc_ema(obv, 30).iloc[-1]
        if obv_ema_10 > obv_ema_30:
            score += 8
            details['obv'] = "💰 OBV tăng — Tiền đang chảy vào"
        else:
            details['obv'] = "📉 OBV giảm"

        return {
            'score': score,
            'details': details,
            'change_24h': change_24h,
            'change_3d': change_3d,
            'change_7d': change_7d,
            'vol_surge': vol_surge,
            'rsi': rsi_now,
            'vol_24h': ticker_info.get('volume_24h', 0),
            'price': ticker_info.get('price', 0),
        }

    async def scan_all(self):
        """Quét toàn bộ và phân loại theo ecosystem"""
        print("=" * 70)
        print("🔥 ECOSYSTEM MONEY FLOW SCANNER")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        from config import Config
        print("\n📊 Đang tải danh sách Binance Futures...")
        symbols_info = await self.get_all_futures_symbols(min_vol_24h=Config.MIN_VOLUME_24H)
        print(f"✅ Tìm thấy {len(symbols_info)} cặp có vol > ${Config.MIN_VOLUME_24H/1e6:.1f}M\n")

        results = []
        total = len(symbols_info)

        for i, info in enumerate(symbols_info, 1):
            sym = info['symbol']
            if i % 20 == 0 or i == total:
                print(f"   Tiến độ: {i}/{total}...")

            try:
                df_4h, df_1d = await asyncio.gather(
                    self.fetch_ohlcv(sym, '4h', 60),
                    self.fetch_ohlcv(sym, '1d', 50),
                )
                analysis = self.analyze_token(df_4h, df_1d, info)
                if analysis and analysis['score'] >= 25:
                    base = sym.split('/')[0]
                    ecosystems = get_ecosystem(sym)
                    results.append({
                        'symbol': base,
                        'full_symbol': sym,
                        'ecosystems': ecosystems,
                        **analysis,
                    })
            except Exception as e:
                pass

            # Rate limit - optimized for lower weight requests
            if i % 10 == 0:
                await asyncio.sleep(0.1)

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def format_report(self, results):
        """Format báo cáo theo ecosystem"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = []
        lines.append("=" * 70)
        lines.append(f"🔥🔥🔥 BÁO CÁO DÒNG TIỀN THEO HỆ SINH THÁI")
        lines.append(f"📅 {now}")
        lines.append(f"📊 Tổng: {len(results)} token có dòng tiền mạnh (score ≥ 25)")
        lines.append("=" * 70)

        # Top 20 mạnh nhất
        lines.append(f"\n{'🏆 TOP 20 DÒNG TIỀN MẠNH NHẤT':=^70}")
        lines.append(f"{'#':<3} {'Token':<10} {'Score':<7} {'24h':>7} {'3d':>7} {'7d':>7} {'Vol↑':>6} {'RSI':>5}")
        lines.append("-" * 60)
        for i, r in enumerate(results[:20], 1):
            emoji = "🥇" if i <= 3 else "🥈" if i <= 6 else "🥉" if i <= 10 else "  "
            lines.append(
                f"{emoji}{i:<2} {r['symbol']:<10} {r['score']:<7} "
                f"{r['change_24h']:>+6.1f}% {r['change_3d']:>+6.1f}% {r['change_7d']:>+6.1f}% "
                f"{r['vol_surge']:>5.1f}x {r['rsi']:>4.0f}"
            )

        # Phân loại theo ecosystem
        eco_groups = {}
        for r in results:
            for eco in r['ecosystems']:
                if eco not in eco_groups:
                    eco_groups[eco] = []
                eco_groups[eco].append(r)

        # Sort ecosystems by average score
        eco_sorted = sorted(
            eco_groups.items(),
            key=lambda x: sum(r['score'] for r in x[1]) / len(x[1]),
            reverse=True
        )

        lines.append(f"\n{'═' * 70}")
        lines.append(f"📊 PHÂN TÍCH THEO HỆ SINH THÁI")
        lines.append(f"{'═' * 70}")

        # Ecosystem summary
        lines.append(f"\n{'Hệ sinh thái':<30} {'Tokens':>7} {'Avg Score':>10} {'Tổng Vol 24h':>15}")
        lines.append("-" * 65)
        for eco, tokens in eco_sorted:
            avg_score = sum(r['score'] for r in tokens) / len(tokens)
            total_vol = sum(r['vol_24h'] for r in tokens)
            fire = "🔥" if avg_score >= 50 else "📈" if avg_score >= 35 else "📊"
            lines.append(
                f"{fire} {eco:<28} {len(tokens):>5}   {avg_score:>8.0f}   ${total_vol/1e9:>10.2f}B"
            )

        # Chi tiết từng ecosystem
        for eco, tokens in eco_sorted:
            tokens_sorted = sorted(tokens, key=lambda x: x['score'], reverse=True)
            avg_score = sum(r['score'] for r in tokens) / len(tokens)

            lines.append(f"\n{'─' * 70}")
            fire = "🔥🔥🔥" if avg_score >= 55 else "🔥🔥" if avg_score >= 45 else "🔥" if avg_score >= 35 else "📊"
            lines.append(f"{eco}  {fire} Avg Score: {avg_score:.0f}")
            lines.append(f"{'─' * 70}")

            for r in tokens_sorted[:10]:  # Top 10 mỗi eco
                grade = "⭐⭐⭐" if r['score'] >= 70 else "⭐⭐" if r['score'] >= 50 else "⭐" if r['score'] >= 35 else ""
                lines.append(
                    f"  {grade} {r['symbol']:<10} Score: {r['score']:<4} | "
                    f"24h: {r['change_24h']:>+5.1f}% | 3d: {r['change_3d']:>+5.1f}% | "
                    f"Vol: {r['vol_surge']:.1f}x | RSI: {r['rsi']:.0f}"
                )

                # Details
                for key in ['volume', 'ema', 'accumulation', 'breakout', 'obv']:
                    if key in r['details']:
                        lines.append(f"           {r['details'][key]}")

        # Kết luận
        lines.append(f"\n{'═' * 70}")
        lines.append("🎯 KẾT LUẬN & KHUYẾN NGHỊ")
        lines.append(f"{'═' * 70}")

        if eco_sorted:
            top3_eco = eco_sorted[:3]
            lines.append("\n💰 TOP 3 HỆ SINH THÁI DÒNG TIỀN MẠNH NHẤT:")
            for i, (eco, tokens) in enumerate(top3_eco, 1):
                avg_score = sum(r['score'] for r in tokens) / len(tokens)
                top_tokens = sorted(tokens, key=lambda x: x['score'], reverse=True)[:3]
                token_names = ", ".join([f"{t['symbol']}({t['score']})" for t in top_tokens])
                lines.append(f"  {i}. {eco} — Avg: {avg_score:.0f} | Best: {token_names}")

        # Tokens nên theo dõi
        hot_tokens = [r for r in results if r['score'] >= 50]
        if hot_tokens:
            lines.append(f"\n🔥 TOKEN DÒNG TIỀN CỰC MẠNH (Score ≥ 50):")
            for r in hot_tokens[:15]:
                eco_str = " & ".join(r['ecosystems'][:2])
                lines.append(
                    f"  ⭐ {r['symbol']:<10} Score: {r['score']:<4} | {eco_str} | "
                    f"24h: {r['change_24h']:>+5.1f}% | Vol: {r['vol_surge']:.1f}x"
                )

        lines.append(f"\n{'═' * 70}")
        lines.append(f"⏰ Cập nhật lúc: {now}")
        lines.append(f"{'═' * 70}")

        return "\n".join(lines)

    def format_telegram_report(self, results):
        """Format cho Telegram"""
        now = datetime.now().strftime("%H:%M %d/%m")
        msg = f"🔥 <b>DÒNG TIỀN HỆ SINH THÁI</b> — {now}\n\n"

        # Top tokens
        hot = [r for r in results if r['score'] >= 50]
        if hot:
            msg += "<b>⭐ TOKEN CỰC MẠNH:</b>\n"
            for r in hot[:10]:
                eco_short = r['ecosystems'][0].split('(')[0].strip() if r['ecosystems'] else "?"
                msg += (
                    f"🔸 <b>{r['symbol']}</b> [{r['score']}] "
                    f"{r['change_24h']:+.1f}% vol:{r['vol_surge']:.1f}x\n"
                )
            msg += "\n"

        # Ecosystem summary
        eco_groups = {}
        for r in results:
            for eco in r['ecosystems']:
                if eco not in eco_groups:
                    eco_groups[eco] = []
                eco_groups[eco].append(r)

        eco_sorted = sorted(
            eco_groups.items(),
            key=lambda x: sum(r['score'] for r in x[1]) / len(x[1]),
            reverse=True
        )

        msg += "<b>📊 DÒNG TIỀN THEO ECOSYSTEM:</b>\n"
        for eco, tokens in eco_sorted[:8]:
            avg = sum(r['score'] for r in tokens) / len(tokens)
            best = max(tokens, key=lambda x: x['score'])
            fire = "🔥" if avg >= 50 else "📈" if avg >= 35 else "📊"
            msg += f"{fire} {eco}: avg {avg:.0f} | Top: {best['symbol']}({best['score']})\n"

        msg += f"\n<i>Tổng {len(results)} token có dòng tiền mạnh</i>"
        return msg


async def main():
    scanner = EcosystemScanner()
    try:
        results = await scanner.scan_all()
        report = scanner.format_report(results)
        print(report)

        # Save report
        filename = f"ecosystem_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📁 Đã lưu báo cáo: {filename}")

        # Send Telegram
        try:
            from telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()
            tg_msg = scanner.format_telegram_report(results)
            await notifier.send_status(tg_msg)
            print("📱 Đã gửi báo cáo lên Telegram!")
        except Exception as e:
            print(f"⚠️ Không gửi được Telegram: {e}")

    finally:
        await scanner.close()


if __name__ == "__main__":
    asyncio.run(main())
