"""
Market Bulletin — Sonic R Edition
Bản tin 7h sáng & 20h tối: Sonic R EMA status, Dragon analysis, Squeeze watchlist
"""
import html
import logging
from datetime import datetime
from market_data import MarketDataFetcher
from indicators import TechnicalIndicators
from config import Config

logger = logging.getLogger(__name__)


class MarketBulletin:
    def __init__(self, data_fetcher: MarketDataFetcher):
        self.fetcher = data_fetcher
        self.indicators = TechnicalIndicators()

    async def generate_bulletin(self) -> str:
        """Tạo bản tin thị trường Sonic R"""
        now = datetime.now()
        session = "SÁNG" if now.hour < 12 else "TỐI"
        date_str = now.strftime("%d/%m/%Y %H:%M")

        sections = []
        sections.append(
            f"{'━' * 30}\n"
            f"📰 <b>BẢN TIN SONIC R {session}</b>\n"
            f"🕐 {date_str}\n"
            f"{'━' * 30}"
        )

        # 1. Top coins
        top_section = await self._top_coins_overview()
        sections.append(top_section)

        # 2. BTC analysis
        btc_section = await self._analyze_sonic_r("BTC/USDT:USDT", "BTC")
        sections.append(btc_section)

        # 3. ETH analysis
        eth_section = await self._analyze_sonic_r("ETH/USDT:USDT", "ETH")
        sections.append(eth_section)

        # 4. Squeeze watchlist
        watchlist = await self._squeeze_watchlist()
        sections.append(watchlist)

        # 5. Sentiment
        sentiment = await self._market_sentiment()
        sections.append(sentiment)

        # 6. Nhắc nhở
        sections.append(
            f"{'─' * 30}\n"
            f"⚠️ <b>NHẮC NHỞ KỶ LUẬT</b>\n"
            f"{'─' * 30}\n"
            f"🔸 Chỉ trade khi Dragon trending (không flat)\n"
            f"🔸 R:R tối thiểu 1:3\n"
            f"🔸 Rủi ro tối đa 2%/lệnh\n"
            f"🔸 TP1 hit → dời SL về Entry\n"
            f"🔸 Tâm lý bất ổn → KHÔNG TRADE\n"
            f"{'━' * 30}\n"
            f"<i>Sonic R System 🐉</i>"
        )

        return "\n\n".join(sections)

    async def _top_coins_overview(self) -> str:
        """Top 10 coins theo volume"""
        lines = [f"{'─' * 30}", f"📊 <b>TOP COINS (24h)</b>", f"{'─' * 30}"]

        top_symbols = await self.fetcher.get_symbol_names(10)
        for sym in top_symbols:
            try:
                ticker = await self.fetcher.fetch_ticker(sym)
                if not ticker or not ticker.get('last'):
                    continue
                price = ticker['last']
                change = ticker.get('change_24h', 0) or 0
                emoji = "🟢" if change >= 0 else "🔴"
                name = sym.split('/')[0]
                lines.append(f"{emoji} <b>{name}</b>: ${price:,.2f} ({change:+.1f}%)")
            except Exception:
                continue

        return "\n".join(lines)

    async def _analyze_sonic_r(self, symbol: str, name: str) -> str:
        """Phân tích Sonic R chi tiết cho 1 coin"""
        lines = [f"{'─' * 30}", f"🐉 <b>SONIC R — {name}</b>", f"{'─' * 30}"]

        try:
            df_d1 = await self.fetcher.fetch_ohlcv(symbol, "1d", limit=200)
            df_5m = await self.fetcher.fetch_ohlcv(symbol, "5m", limit=800)

            if df_d1.empty:
                return "\n".join(lines + [f"⚠️ Không lấy được dữ liệu {name}"])

            df_d1 = self.indicators.calculate_all(df_d1)
            df_5m = self.indicators.calculate_all(df_5m) if not df_5m.empty else df_5m

            last = df_d1.iloc[-1]
            price = last['close']

            # Dragon status D1
            dragon_dir = last.get('dragon_direction', 'N/A')
            dragon_emoji = "📈" if dragon_dir == 'UP' else ("📉" if dragon_dir == 'DOWN' else "↔️")
            lines.append(f"<b>Dragon D1:</b> {dragon_emoji} {dragon_dir}")

            # EMA Order
            if last.get('full_bullish_order', False):
                lines.append("<b>EMA Order:</b> 📈 Full Bullish (P>D>89>200>610)")
            elif last.get('partial_bullish_order', False):
                lines.append("<b>EMA Order:</b> 📈 Partial Bullish")
            elif last.get('full_bearish_order', False):
                lines.append("<b>EMA Order:</b> 📉 Full Bearish")
            elif last.get('partial_bearish_order', False):
                lines.append("<b>EMA Order:</b> 📉 Partial Bearish")
            else:
                lines.append("<b>EMA Order:</b> ↔️ Tangled")

            # EMA levels
            lines.append(
                f"<b>EMA:</b> D34={last.get('dragon_close', 0):,.0f} | "
                f"89={last.get('ema_89', 0):,.0f} | "
                f"200={last.get('ema_200', 0):,.0f} | "
                f"610={last.get('ema_610', 0):,.0f}"
            )

            # Squeeze status
            spread = last.get('ema_spread_pct', 0)
            if spread < Config.EMA_SQUEEZE_THRESHOLD_PCT:
                lines.append(f"⚡ <b>EMA Squeeze:</b> {spread:.2f}% — SẮP BREAKOUT!")
            else:
                lines.append(f"<b>EMA Spread:</b> {spread:.2f}%")

            # Dragon Width
            dw = last.get('dragon_width', 0)
            if dw < Config.DRAGON_NARROW_THRESHOLD_PCT:
                lines.append(f"🔸 <b>Dragon Narrow:</b> {dw:.3f}% — Volatility cực thấp")

            # RSI
            rsi = last.get('rsi', 50)
            if rsi > 70:
                rsi_label = "⚠️ Quá mua"
            elif rsi < 30:
                rsi_label = "⚠️ Quá bán"
            elif rsi > 55:
                rsi_label = "Thiên Long"
            elif rsi < 45:
                rsi_label = "Thiên Short"
            else:
                rsi_label = "Trung tính"
            lines.append(f"<b>RSI D1:</b> {rsi:.1f} ({rsi_label})")

            # 5m Sonic R signals
            if not df_5m.empty:
                last_5m = df_5m.iloc[-1]
                signals_5m = []

                if df_5m['golden_squeeze'].iloc[-20:].any():
                    signals_5m.append("⭐ Golden Squeeze")
                if df_5m['ema_squeeze'].iloc[-20:].any():
                    signals_5m.append("⚡ EMA Squeeze")
                if df_5m['sweep_low'].iloc[-20:].any():
                    signals_5m.append("🟢 Stop Hunt (Spring)")
                if df_5m['sweep_high'].iloc[-20:].any():
                    signals_5m.append("🔴 Stop Hunt (Upthrust)")
                if df_5m['bullish_reversal_at_ema'].iloc[-10:].any():
                    signals_5m.append("🟢 Bull Reversal")
                if df_5m['bearish_reversal_at_ema'].iloc[-10:].any():
                    signals_5m.append("🔴 Bear Reversal")

                if signals_5m:
                    lines.append(f"<b>5m Signals:</b> {', '.join(signals_5m)}")

        except Exception as e:
            lines.append(f"⚠️ Lỗi phân tích: {html.escape(str(e)[:100])}")

        return "\n".join(lines)

    async def _squeeze_watchlist(self) -> str:
        """Quét coins có EMA Squeeze — sắp breakout"""
        lines = [f"{'─' * 30}", f"⚡ <b>SQUEEZE WATCHLIST — SẮP BREAKOUT</b>", f"{'─' * 30}"]

        symbols = await self.fetcher.get_symbol_names(30)
        watchlist = []

        for sym in symbols:
            try:
                df = await self.fetcher.fetch_ohlcv(sym, "4h", limit=100)
                if df.empty:
                    continue
                df = self.indicators.calculate_all(df)

                last = df.iloc[-1]
                name = sym.split('/')[0]
                signs = []

                # Golden squeeze
                if df['golden_squeeze'].iloc[-5:].any():
                    signs.append("⭐ Golden")

                # EMA squeeze
                elif df['ema_squeeze'].iloc[-5:].any():
                    signs.append("⚡ Squeeze")

                # Dragon narrow
                if last.get('dragon_width', 1) < Config.DRAGON_NARROW_THRESHOLD_PCT:
                    signs.append("🔸 Dragon Narrow")

                # Dragon breakout
                if (df['close'].iloc[-3:] > df['dragon_high'].iloc[-3:]).any():
                    signs.append("🟢 Breakout ↑")
                if (df['close'].iloc[-3:] < df['dragon_low'].iloc[-3:]).any():
                    signs.append("🔴 Breakout ↓")

                if signs:
                    ticker = await self.fetcher.fetch_ticker(sym)
                    change = ticker.get('change_24h', 0) or 0
                    spread = last.get('ema_spread_pct', 0)
                    watchlist.append(
                        f"• <b>{name}</b> ({change:+.1f}%): {', '.join(signs)} "
                        f"| Spread {spread:.1f}%"
                    )

            except Exception:
                continue

        if watchlist:
            lines.extend(watchlist[:10])
        else:
            lines.append("<i>Chưa có coin nào đang squeeze</i>")

        return "\n".join(lines)

    async def _market_sentiment(self) -> str:
        """Tâm lý thị trường"""
        lines = [f"{'─' * 30}", f"🧠 <b>TÂM LÝ THỊ TRƯỜNG</b>", f"{'─' * 30}"]

        for sym, name in [("BTC/USDT:USDT", "BTC"), ("ETH/USDT:USDT", "ETH")]:
            try:
                funding = await self.fetcher.fetch_funding_rate(sym)
                fr = funding.get('funding_rate', 0)
                if fr is not None:
                    if fr < -0.001:
                        label = "Phe Short trả phí → thuận Long"
                    elif fr > 0.001:
                        label = "Phe Long trả phí → thuận Short"
                    else:
                        label = "Trung tính"
                    lines.append(f"<b>{name} Funding:</b> {fr:.4f} ({label})")
            except Exception:
                continue

        try:
            oi = await self.fetcher.fetch_open_interest("BTC/USDT:USDT")
            if oi > 0:
                lines.append(f"<b>BTC Open Interest:</b> {oi:,.0f}")
        except Exception:
            pass

        return "\n".join(lines)
