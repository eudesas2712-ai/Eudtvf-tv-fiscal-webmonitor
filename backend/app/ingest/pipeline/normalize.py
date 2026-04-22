def normalize_article(art: dict) -> dict:
    # aqui você pode incluir limpeza mais agressiva, idioma, etc.
    title = (art.get("title") or "").strip()
    body = (art.get("content_text") or "").strip()
    art["title"] = title[:1024] if title else None
    art["content_text"] = body if body else None
    return art