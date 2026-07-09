import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    ) as session:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        async with session.get(url) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            rates = data.get("rates", {})
            print("XAU rate:", rates.get("XAU"))
            if rates.get("XAU"):
                print("Gold Price per oz (1 / XAU):", 1.0 / rates.get("XAU"))

if __name__ == "__main__":
    asyncio.run(main())
