import asyncio
import sys
import argparse
import ccxt.async_support as ccxt
from config import Config

async def execute_trade(live_mode=False):
    # Initialize CCXT exchange using credentials from config/dotenv
    exchange = ccxt.binance({
        'apiKey': Config.BINANCE_API_KEY,
        'secret': Config.BINANCE_API_SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    
    symbol = "WLD/USDT"
    print(f"============================================================")
    print(f"🚀 THIẾT LẬP LỆNH LONG WLD/USDT FUTURES")
    print(f"📊 CHẾ ĐỘ: {'🔥 LIVE (THỰC TẾ)' if live_mode else '📝 DRY-RUN (MÔ PHỎNG)'}")
    print(f"============================================================")
    
    try:
        # 1. Load markets
        await exchange.load_markets()
        
        # Verify symbol
        if symbol not in exchange.markets:
            # Try WLD/USDT:USDT
            symbol = "WLD/USDT:USDT"
            if symbol not in exchange.markets:
                print("❌ Lỗi: Không tìm thấy symbol WLD trên sàn Binance Futures.")
                return
                
        # 2. Fetch current ticker price
        ticker = await exchange.fetch_ticker(symbol)
        price = ticker['last']
        print(f"   • Giá hiện tại WLD: ${price:.4f}")
        
        # 3. Check account balance
        balance = await exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {}).get('free', 0.0)
        total_usdt = balance.get('USDT', {}).get('total', 0.0)
        print(f"   • Số dư khả dụng (Free USDT): ${usdt_balance:.2f} (Tổng: ${total_usdt:.2f})")
        
        # In dry-run mode, default to Config capital. In live mode, use the minimum of config or actual
        capital = Config.ACCOUNT_BALANCE
        if live_mode:
            capital = min(Config.ACCOUNT_BALANCE, total_usdt) if total_usdt > 0 else Config.ACCOUNT_BALANCE
            
        risk_usd = capital * (Config.MAX_RISK_PERCENT / 100) # $20 * 2% = $0.40
        
        # SL and TPs based on recent analysis (Stop Loss at 0.5223, current price ~0.5314)
        # We can also calculate it dynamically: current price - 1.5 * ATR (approx 0.00706)
        # Let's fetch 5m OHLCV to calculate actual ATR 5m
        ohlcv = await exchange.fetch_ohlcv(symbol, '5m', limit=50)
        df = pd_df = None
        atr_5m = 0.00706  # fallback
        try:
            import pandas as pd
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_5m = tr.rolling(window=14).mean().iloc[-1]
        except Exception:
            pass
            
        sl_level = price - (1.5 * atr_5m)
        # Format levels nicely
        sl_level = round(sl_level, 4)
        
        # Ensure SL is at least 1% below price
        if sl_level >= price * 0.995:
            sl_level = round(price * 0.985, 4)
            
        tp1 = round(price + (1.0 * atr_5m), 4)
        tp2 = round(price + (2.0 * atr_5m), 4)
        tp3 = round(price + (3.5 * atr_5m), 4)
        
        risk_per_token = price - sl_level
        if risk_per_token <= 0:
            print("❌ Lỗi: Khoảng cách Stop Loss không hợp lý.")
            return
            
        pos_size = risk_usd / risk_per_token
        pos_usd = pos_size * price
        leverage = pos_usd / capital if capital > 0 else 1.0
        
        # Round position size to Binance's WLD lot size
        pos_size_rounded = float(exchange.amount_to_precision(symbol, pos_size))
        pos_usd_rounded = pos_size_rounded * price
        
        # Round prices to precision
        sl_level = float(exchange.price_to_precision(symbol, sl_level))
        tp1 = float(exchange.price_to_precision(symbol, tp1))
        tp2 = float(exchange.price_to_precision(symbol, tp2))
        tp3 = float(exchange.price_to_precision(symbol, tp3))
        
        print(f"\n📊 THÔNG SỐ LỆNH ĐỀ XUẤT:")
        print(f"   • Hướng: LONG (MUA)")
        print(f"   • Vốn tính toán: ${capital:.2f} | Rủi ro: {Config.MAX_RISK_PERCENT}% (${risk_usd:.2f})")
        print(f"   • Đòn bẩy tính toán: {leverage:.1f}x (Sẽ set sàn ở {max(1, round(leverage))}x)")
        print(f"   • Khối lượng WLD: {pos_size_rounded} WLD (~${pos_usd_rounded:.2f})")
        print(f"   • Entry: Market Price (~${price:.4f})")
        print(f"   • Stop Loss (Cứng): ${sl_level:.4f} (-{((price-sl_level)/price*100):.2f}%)")
        print(f"   • Take Profit 1 (40%): ${tp1:.4f}")
        print(f"   • Take Profit 2 (30%): ${tp2:.4f}")
        print(f"   • Take Profit 3 (30%): ${tp3:.4f}")
        
        if pos_size_rounded <= 0:
            print("❌ Lỗi: Khối lượng tính toán quá nhỏ so với quy định sàn.")
            return
            
        if not live_mode:
            print("\n💡 Chạy lệnh này với flag `--live` để thực hiện giao dịch thực tế trên Binance.")
            return
            
        # LIVE MODE EXECUTION
        if total_usdt < 1.0:
            print("❌ Lỗi: Số dư USDT trong ví Futures không đủ để giao dịch.")
            return
            
        # 1. Set leverage
        leverage_to_set = max(1, min(int(round(leverage)), Config.MAX_LEVERAGE))
        # Ensure leverage is within allowed limits
        leverage_to_set = min(leverage_to_set, 20) # cap at 20x for safety
        print(f"\n⚙️ 1. Thiết lập đòn bẩy: {leverage_to_set}x...")
        try:
            await exchange.set_leverage(leverage_to_set, symbol)
            print("   ✅ Đã set đòn bẩy thành công.")
        except Exception as e:
            print(f"   ⚠️ Lỗi set đòn bẩy (có thể đã set trước đó): {e}")
            
        # 2. Place Market Order
        print(f"⚙️ 2. Gửi lệnh Market Buy: {pos_size_rounded} WLD...")
        order = await exchange.create_market_buy_order(symbol, pos_size_rounded)
        entry_price = order.get('price') or price
        print(f"   ✅ Khớp lệnh LONG thành công tại giá: ${entry_price:.4f} (Order ID: {order.get('id')})")
        
        # Calculate levels relative to actual entry price
        sl_level = round(entry_price - (entry_price - sl_level), 4)
        tp1 = round(entry_price + (tp1 - price), 4)
        tp2 = round(entry_price + (tp2 - price), 4)
        tp3 = round(entry_price + (tp3 - price), 4)
        
        # 3. Place Stop Loss Order (reduceOnly=True)
        print(f"⚙️ 3. Thiết lập lệnh Stop Loss tại ${sl_level:.4f}...")
        sl_params = {
            'stopPrice': sl_level,
            'reduceOnly': True,
            'workingType': 'MARK_PRICE'
        }
        sl_order = await exchange.create_order(
            symbol=symbol,
            type='STOP_MARKET',
            side='sell',
            amount=pos_size_rounded,
            params=sl_params
        )
        print(f"   ✅ Đã đặt lệnh Stop Loss (ID: {sl_order.get('id')})")
        
        # 4. Place Take Profit Orders (Split TP)
        # TP1: 40%
        tp1_qty = float(exchange.amount_to_precision(symbol, pos_size_rounded * 0.4))
        # TP2: 30%
        tp2_qty = float(exchange.amount_to_precision(symbol, pos_size_rounded * 0.3))
        # TP3: 30%
        tp3_qty = float(exchange.amount_to_precision(symbol, pos_size_rounded - tp1_qty - tp2_qty))
        
        print(f"⚙️ 4. Thiết lập các lệnh Take Profit...")
        
        # TP1 Order (Limit or Take Profit Market)
        if tp1_qty > 0:
            tp1_order = await exchange.create_order(
                symbol=symbol,
                type='LIMIT',
                side='sell',
                amount=tp1_qty,
                price=tp1,
                params={'reduceOnly': True}
            )
            print(f"   ✅ Đã đặt Limit TP1 (40%): {tp1_qty} WLD tại ${tp1:.4f} (ID: {tp1_order.get('id')})")
            
        # TP2 Order
        if tp2_qty > 0:
            tp2_order = await exchange.create_order(
                symbol=symbol,
                type='LIMIT',
                side='sell',
                amount=tp2_qty,
                price=tp2,
                params={'reduceOnly': True}
            )
            print(f"   ✅ Đã đặt Limit TP2 (30%): {tp2_qty} WLD tại ${tp2:.4f} (ID: {tp2_order.get('id')})")
            
        # TP3 Order
        if tp3_qty > 0:
            tp3_order = await exchange.create_order(
                symbol=symbol,
                type='LIMIT',
                side='sell',
                amount=tp3_qty,
                price=tp3,
                params={'reduceOnly': True}
            )
            print(f"   ✅ Đã đặt Limit TP3 (30%): {tp3_qty} WLD tại ${tp3:.4f} (ID: {tp3_order.get('id')})")
            
        print(f"\n🎉 HOÀN TẤT THIẾT LẬP LỆNH LONG WLD!")
        
    except Exception as e:
        print(f"❌ Lỗi thực thi lệnh: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await exchange.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Thực hiện lệnh thực tế trên sàn')
    args = parser.parse_args()
    
    asyncio.run(execute_trade(live_mode=args.live))
