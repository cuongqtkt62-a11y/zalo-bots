import asyncio
import aiohttp
import urllib.parse

async def translate_text(text: str, target_lang: str = "vi") -> str:
    if not text:
        return ""
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Google Translate response structure: [[["translated_text", "original_text", ...]]]
                    translated = "".join(item[0] for item in data[0] if item[0])
                    return translated
                else:
                    return text
    except Exception as e:
        print("Translation error:", e)
        return text

async def main():
    test_sentences = [
        "Zelensky proposes face-to-face talks in open letter to Putin",
        "Xi Jinping to meet Kim Jong Un in rare visit to North Korea",
        "Bernstein sees food inflation driving UK grocer earnings upside; names top picks"
    ]
    for s in test_sentences:
        res = await translate_text(s)
        print(f"Original: {s}")
        print(f"Translated: {res}\n")

asyncio.run(main())
