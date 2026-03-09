import httpx

async def execute(text, to_language, from_language=None):
    """Translate text between languages. Tries MyMemory free API as standalone fallback."""
    src = from_language or "autodetect"
    lang_map = {
        "english": "en", "russian": "ru", "spanish": "es", "french": "fr",
        "german": "de", "italian": "it", "portuguese": "pt", "chinese": "zh",
        "japanese": "ja", "korean": "ko", "arabic": "ar", "hindi": "hi",
        "dutch": "nl", "polish": "pl", "turkish": "tr", "swedish": "sv",
        "czech": "cs", "ukrainian": "uk",
    }
    src_code = lang_map.get(src.lower(), src.lower()[:2]) if src != "autodetect" else "autodetect"
    tgt_code = lang_map.get(to_language.lower(), to_language.lower()[:2])
    langpair = f"{src_code}|{tgt_code}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": text[:500], "langpair": langpair},
            )
            data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        if translated:
            return {"translated": translated, "from": src, "to": to_language, "source": "mymemory"}
        return {"error": f"Translation failed: {data.get('responseStatus', 'unknown')}"}
    except Exception as e:
        return {"error": f"Translation error: {e}. For better results, use through pipeline with LLM."}
