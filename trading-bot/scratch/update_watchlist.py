import asyncio
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_convergence_scanner import AIDePINScanner, AI_CRYPTO_MAP

async def update_watchlist():
    print("=== Scanning AI & DePIN Tokens to Update Watchlist ===")
    scanner = AIDePINScanner()
    try:
        all_results = await scanner.scan_all()
        
        # Flatten results for top ranking
        flat = []
        for cat, data in all_results.items():
            for r in data['results']:
                r['category'] = cat
                flat.append(r)
        flat.sort(key=lambda x: x['win_score'], reverse=True)
        
        # Build markdown content
        now_str = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        
        # Determine narrative warning based on scores
        avg_score = sum(r['win_score'] for r in flat) / len(flat) if flat else 0
        
        warning_type = "[!WARNING]" if avg_score < 35 else "[!IMPORTANT]"
        warning_emoji = "⚠️" if avg_score < 35 else "🚀"
        warning_title = "CẢNH BÁO SECTOR AI/DEPIN:" if avg_score < 35 else "CƠ HỘI SECTOR AI/DEPIN BẮT ĐẦU NÓNG LÊN:"
        
        buys = [r for r in flat if r.get('grade', 'D') in ('A+', 'A')]
        watches = [r for r in flat if r.get('grade', 'D') == 'B']
        skips = [r for r in flat if r.get('grade', 'D') in ('C', 'D')]
        
        if avg_score < 25:
            warning_body = f"Toàn bộ nhóm sector AI/DePIN đang chịu áp lực xả hoặc đi ngang chán nản. Hơn {len(skips)/len(flat)*100:.0f}% danh sách có Grade D. Cần kiên nhẫn tích lũy Spot."
        elif avg_score < 45:
            warning_body = f"Thị trường đang hồi phục sau đợt quét thanh khoản vĩ mô. Có {len(buys)} cơ hội mua được Grade A/A+. Ưu tiên các dòng tiền dẫn đầu."
        else:
            warning_body = f"Narrative AI đang cực kỳ bùng nổ! Hơn {len(buys)/len(flat)*100:.0f}% danh sách có Grade A/A+. Cơ hội bứt phá diện rộng."
            
        md = []
        md.append(f"# 🤖🔗 AI + CRYPTO CONVERGENCE — Watchlist & Phân Tích\n")
        md.append(f"> **📅 Cập nhật real-time: {now_str}**  ")
        md.append(f"> Scan {len(flat)} tokens | 5 categories | Binance Futures\n")
        md.append(f"---\n")
        
        md.append(f"## 📊 Tổng Quan Narrative\n")
        md.append(f"> {warning_type}")
        md.append(f"> **{warning_emoji} {warning_title}**")
        md.append(f"> {warning_body}\n")
        
        # Category diagram
        md.append(f"### 5 Sub-Narratives\n")
        md.append(f"```mermaid")
        md.append(f"graph TD")
        md.append(f"    A[\"🤖 AI + Crypto<br/>Convergence\"] --> B[\"🧠 AI Intelligence<br/>WLD, NEAR, FET, ARKM\"]")
        md.append(f"    A --> C[\"🖥️ Decentralized Compute<br/>RENDER, AKT, IO, ATH\"]")
        md.append(f"    A --> D[\"📡 DePIN Infra<br/>GRASS, IOTX\"]")
        md.append(f"    A --> E[\"🔗 Data & Oracles<br/>LINK, PYTH, FIL\"]")
        md.append(f"    A --> F[\"🤖 Agent Frameworks<br/>VIRTUAL, NIL, JASMY\"]")
        md.append(f"```\n")
        md.append(f"---\n")
        
        # TOP RANKING TABLE
        md.append(f"## 🏆 XẾP HẠNG TỔNG HỢP — {len(flat)} Tokens\n")
        md.append(f"| # | Token | Win Score | Grade | RSI | Vol↑ | 24h | 7d | EMA H4 | Category |")
        md.append(f"|---|---|---|---|---|---|---|---|---|---|")
        
        for i, r in enumerate(flat, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            category_short = r['category'].split(" ", 2)[-1] if " " in r['category'] else r['category']
            md.append(f"| {emoji}{i} | **{r['symbol']}** | **{r['win_score']}** | {r.get('grade','D')} | {r['rsi']:.0f} | {r['vol_surge']:.1f}x | {r['change_24h']:+.1f}% | {r['change_7d']:+.1f}% | {r.get('ema_status','')} | {category_short} |")
            
        md.append(f"\n---\n")
        
        # DETAILED CATEGORIES
        md.append(f"## 🟢 ĐÁNH GIÁ CHI TIẾT TỪNG NHÓM\n")
        for cat, data in all_results.items():
            results = data['results']
            if not results:
                continue
            cat_avg = sum(r['win_score'] for r in results) / len(results)
            md.append(f"### {cat} (Avg Score: {cat_avg:.1f})")
            md.append(f"*Description: {data['description']}*")
            md.append(f"*Catalyst: {data['catalyst']}*\n")
            
            for r in results[:4]: # Show top 4 in each category
                md.append(f"#### {r['symbol']} — Verdict: **{r['verdict']}** (Score: {r['win_score']})")
                md.append(f"- **Giá hiện tại:** ${r['price']:.4f} | RSI Daily: {r['rsi']:.0f} | Vol Surge: {r['vol_surge']:.1f}x")
                md.append(f"- **Biến động:** 24h: {r['change_24h']:+.1f}% | 7d: {r['change_7d']:+.1f}% | EMA Status: {r.get('ema_status','')}")
                if r['win_score'] >= 35:
                    md.append(f"- **Khuyến nghị giao dịch:** Entry: ${r['entry']:.4f} | Stop Loss: ${r['sl']:.4f} (-{r['risk_pct']:.1f}%) | TP1: ${r['tp1']:.4f} | TP2: ${r['tp2']:.4f}")
                md.append("")
                
        md.append(f"---\n")
        
        # CURRENT STRATEGY
        md.append(f"## 🎯 Chiến Lược Phân Bổ Hiện Tại\n")
        md.append(f"| Hành động | Chi tiết |")
        md.append(f"|---|---|")
        
        if buys:
            buy_names = ", ".join([r['symbol'] for r in buys])
            md.append(f"| 🟢 **MÚC NGAY Spot** | Nhóm Grade A/A+ có tín hiệu dòng tiền đảo chiều mạnh: **{buy_names}** |")
        else:
            md.append(f"| 🟢 **MÚC Spot** | Không có coin Grade A+. Rải vốn gom dần các coin Grade B tích lũy đáy. |")
            
        if watches:
            watch_names = ", ".join([r['symbol'] for r in watches[:5]])
            md.append(f"| ⏳ **Theo dõi (Grade B)** | Theo dõi cấu trúc H4 tạo đáy của: **{watch_names}** |")
            
        md.append(f"| ❌ **Hạn chế Futures** | Chỉ đánh Futures khi có setup nén Sonic R + Stop Hunt quét râu rũ bỏ chuẩn chỉ H5 |")
        md.append(f"| 💵 **Tỷ lệ Tiền mặt** | Giữ tối thiểu 20-30% USDT dự phòng phòng thủ. |")
        
        md.append(f"\n---\n")
        md.append(f"## 🔧 Cách Quét Lại\n")
        md.append(f"Script scanner chuyên biệt lưu tại:\n")
        md.append(f"`trading-telegram-bot-v3/ai_convergence_scanner.py`\n")
        md.append(f"Chạy thủ công:\n")
        md.append(f"```bash\n")
        md.append(f"cd \"Trading System/trading-telegram-bot-v3\"\n")
        md.append(f"source venv/bin/activate\n")
        md.append(f"python ai_convergence_scanner.py\n")
        md.append(f"```\n")
        md.append(f"Hoặc nói **\"Múc\"** hoặc **\"Cập nhật\"** để AI cập nhật file này tự động.\n")
        
        output_path = "/Users/mac/Desktop/USP- Cường/Trading System/ai_crypto_convergence_watchlist.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(md))
        print(f"✅ Successfully wrote updated watchlist to {output_path}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await scanner.close()

if __name__ == "__main__":
    asyncio.run(update_watchlist())
