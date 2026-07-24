"""
Market Data Fetcher — Sonic R Edition
Async CCXT cho tốc độ quét nhanh hơn, limit=800 cho EMA 610 warmup
"""
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from config import Config
import logging

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': Config.BINANCE_API_KEY,
            'secret': Config.BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
            'timeout': 5000,
            'maxRetries': 1,
        })
        self._all_symbols_cache = None

    async def close(self):
        """Đóng kết nối exchange"""
        await self.exchange.close()

    async def fetch_all_futures_symbols(self, min_volume_usd: float = 0.0) -> list:
        """Lấy TẤT CẢ cặp USDT Futures, lọc theo volume 24h."""
        try:
            await self.exchange.load_markets()
            tickers = await self.exchange.fetch_tickers()

            symbols = []
            for symbol, ticker in tickers.items():
                if '/USDT' not in symbol:
                    continue
                base = symbol.split('/')[0]
                if base in ('USDC', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'USDD'):
                    continue
                vol_24h = ticker.get('quoteVolume', 0) or 0
                if vol_24h >= min_volume_usd:
                    symbols.append({
                        'symbol': symbol,
                        'volume_24h': vol_24h,
                        'price': ticker.get('last', 0),
                        'change_24h': ticker.get('percentage', 0),
                    })

            symbols.sort(key=lambda x: x['volume_24h'], reverse=True)
            logger.info(f"📊 Tìm thấy {len(symbols)} cặp USDT Futures có vol > ${min_volume_usd/1e6:.0f}M")
            self._all_symbols_cache = symbols
            return symbols

        except Exception as e:
            logger.error(f"Lỗi lấy danh sách symbols: {e}")
            return []

    async def get_symbol_names(self, max_symbols: int = None) -> list:
        """Trả về danh sách tên symbol"""
        if not self._all_symbols_cache:
            await self.fetch_all_futures_symbols(Config.MIN_VOLUME_24H)
        symbols = [s['symbol'] for s in (self._all_symbols_cache or [])]
        if max_symbols:
            symbols = symbols[:max_symbols]
            
        # Đảm bảo các đồng coin ưu tiên luôn nằm trong danh sách được quét
        priority_symbols = ["AKT/USDT:USDT", "HUMA/USDT:USDT", "EIGEN/USDT:USDT"]
        for ps in priority_symbols:
            if ps not in symbols:
                symbols.append(ps)
                
        return symbols

    async def _fetch_yahoo_ohlcv(self, ticker: str, timeframe: str, limit: int = 800) -> pd.DataFrame:
        import aiohttp
        
        if timeframe == '5m':
            interval, range_str = '5m', '5d'
        elif timeframe == '15m':
            interval, range_str = '15m', '15d'
        elif timeframe == '1h':
            interval, range_str = '60m', '60d'
        elif timeframe == '4h':
            interval, range_str = '60m', '60d'
        elif timeframe == '1d':
            interval, range_str = '1d', '2y'
        else:
            interval, range_str = '1d', '2y'
            
        try:
            async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_str}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'chart' in data and data['chart']['result'] and 'timestamp' in data['chart']['result'][0]:
                            res = data['chart']['result'][0]
                            timestamps = res['timestamp']
                            quote = res['indicators']['quote'][0]
                            
                            df = pd.DataFrame({
                                'timestamp': pd.to_datetime(timestamps, unit='s'),
                                'open': quote['open'],
                                'high': quote['high'],
                                'low': quote['low'],
                                'close': quote['close'],
                                'volume': quote['volume']
                            })
                            # Tránh lỗi forward fill NaN
                            df.ffill(inplace=True)
                            df.set_index('timestamp', inplace=True)
                            
                            if timeframe == '4h':
                                df = df.resample('4H').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
                            
                            return df.tail(limit)
        except Exception as e:
            logger.error(f"Lỗi lấy dữ liệu Yahoo {ticker} {timeframe}: {e}")
            
        return pd.DataFrame()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 800) -> pd.DataFrame:
        """Lấy dữ liệu OHLCV — limit=800 cho EMA 610 warmup"""
        if symbol == "XAU/USDT:USDT":
            return await self._fetch_yahoo_ohlcv("GC=F", timeframe, limit)  # Gold Futures (sát giá XAU/USD thật)

        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Lỗi lấy dữ liệu {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    async def fetch_funding_rate(self, symbol: str) -> dict:
        """Lấy Funding Rate"""
        try:
            funding = await self.exchange.fetch_funding_rate(symbol)
            return {
                'funding_rate': funding.get('fundingRate', 0),
                'next_funding_time': funding.get('fundingDatetime', ''),
                'mark_price': funding.get('markPrice', 0),
            }
        except Exception as e:
            logger.warning(f"Không lấy được Funding Rate cho {symbol}: {e}")
            return {'funding_rate': 0, 'next_funding_time': '', 'mark_price': 0}

    async def fetch_open_interest(self, symbol: str) -> float:
        """Lấy Open Interest"""
        try:
            binance_symbol = symbol.split(':')[0].replace('/', '')
            oi_data = await self.exchange.fapiPublicGetOpenInterest({'symbol': binance_symbol})
            return float(oi_data.get('openInterest', 0))
        except Exception as e:
            logger.warning(f"Không lấy được OI cho {symbol}: {e}")
            return 0.0

    async def fetch_ticker(self, symbol: str) -> dict:
        """Lấy giá hiện tại"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                'last': ticker.get('last', 0),
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'volume_24h': ticker.get('quoteVolume', 0),
                'change_24h': ticker.get('percentage', 0),
            }
        except Exception as e:
            logger.error(f"Lỗi lấy ticker {symbol}: {e}")
            return {}

    async def fetch_open_interest_change_pct(self, symbol: str, period: str = "5m", limit: int = 6) -> float:
        """Lấy phần trăm thay đổi Open Interest trong khoảng thời gian gần đây"""
        try:
            binance_symbol = symbol.split(':')[0].replace('/', '')
            params = {
                'symbol': binance_symbol,
                'period': period,
                'limit': limit
            }
            data = await self.exchange.fapiPublicGetOpenInterestHist(params)
            if len(data) >= 2:
                first_oi = float(data[0].get('sumOpenInterest', 0))
                last_oi = float(data[-1].get('sumOpenInterest', 0))
                if first_oi > 0:
                    return (last_oi - first_oi) / first_oi * 100
            return 0.0
        except Exception as e:
            logger.warning(f"Không lấy được lịch sử OI cho {symbol}: {e}")
            return 0.0

