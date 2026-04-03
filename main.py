# ============================================================
# MODULE: main
# RESPONSIBILITY: FastAPI application – routing and ASGI entry point.
# DEPENDS ON: config, news_store, defaults, llm_client, bluesky_client, fastapi, pydantic
# EXPOSES: app (ASGI)
# ============================================================

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from bluesky_client import post_article
from config import FEEDS_FILE, INTERESTS_FILE, SETTINGS_FILE, STATIC_DIR
from defaults import DEFAULT_FEEDS, DEFAULT_INTERESTS, DEFAULT_SETTINGS, init_file_if_missing
from llm_client import generate_comment
from news_store import (
    _broadcast, _cache, _clients, _fetch_all, _poller, _public_cache,
    _rescore_and_broadcast, load_feeds,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    created = any([
        init_file_if_missing(FEEDS_FILE, DEFAULT_FEEDS),
        init_file_if_missing(INTERESTS_FILE, DEFAULT_INTERESTS),
        init_file_if_missing(SETTINGS_FILE, DEFAULT_SETTINGS),
    ])
    _cache["first_run"] = created
    task = asyncio.create_task(_poller())
    yield
    task.cancel()


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sideeye",
    description="Bevakar nyheter via RSS-flöden.",
    version="0.2.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/static/index.html")


class FeedItem(BaseModel):
    name:     str
    url:      str
    category: str = "world"


@app.get("/feeds", summary="Lista konfigurerade RSS-flöden")
async def list_feeds_endpoint():
    return load_feeds()


@app.put("/feeds", summary="Uppdatera RSS-flödeslistan och hämta om alla flöden")
async def update_feeds(feeds: list[FeedItem]):
    if not feeds:
        raise HTTPException(status_code=422, detail="Minst ett flöde krävs.")
    data = {"feeds": [f.model_dump() for f in feeds]}
    with FEEDS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    new_data = await _fetch_all()
    _cache.update(new_data)
    await _broadcast(_public_cache())
    return data


@app.get("/news", summary="Hämta nyheter från cachen")
async def get_all_news(
    category: str | None = Query(None, description="Filtrera på kategori"),
):
    data = _public_cache()
    if category:
        data["articles"] = [a for a in data["articles"] if a.get("category") == category]
        data["total"] = len(data["articles"])
        if not data["articles"]:
            raise HTTPException(status_code=404, detail=f"Ingen feed med kategori '{category}' hittades.")
    return data


@app.get("/news/{feed_name}", summary="Hämta nyheter för ett specifikt flöde")
async def get_news_by_feed(feed_name: str):
    articles = [a for a in _cache["articles"] if a.get("feed_name") == feed_name]
    feeds = load_feeds()
    if not any(f["name"] == feed_name for f in feeds):
        raise HTTPException(status_code=404, detail=f"Feed '{feed_name}' hittades inte.")
    return {"total": len(articles), "articles": articles}


# ── Interests ────────────────────────────────────────────────────────────────

class InterestItem(BaseModel):
    topic: str
    score: int


class InterestsPayload(BaseModel):
    interests: list[InterestItem]


@app.get("/interests", summary="Hämta intressekonfiguration")
async def get_interests():
    with INTERESTS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


@app.put("/interests", summary="Uppdatera intressen och re-score artiklar")
async def update_interests(payload: InterestsPayload):
    for item in payload.interests:
        if not (0 <= item.score <= 10):
            raise HTTPException(
                status_code=422,
                detail=f"Score måste vara 0–10 (fick {item.score} för '{item.topic}').",
            )
    data = {"interests": [i.model_dump() for i in payload.interests]}
    with INTERESTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    await _rescore_and_broadcast()
    return data


@app.get("/stream", summary="SSE – realtidspush till klienter")
async def stream():
    q: asyncio.Queue = asyncio.Queue()
    _clients.add(q)

    async def event_generator():
        # Skicka cachad data direkt vid anslutning
        if _cache["updated_at"]:
            yield f"data: {json.dumps(_public_cache())}\n\n"
            _cache["first_run"] = False  # consumed – reset so reconnects don't re-trigger banner
        try:
            while True:
                msg = await q.get()
                yield f"data: {msg}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _clients.discard(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health", summary="Hälsokontroll")
async def health():
    return {
        "status":     "ok",
        "clients":    len(_clients),
        "updated_at": _cache.get("updated_at"),
    }


# ── AI comment ──────────────────────────────────────────────────────────────────────────

class CommentRequest(BaseModel):
    title:   str
    summary: str = ""


@app.post("/comment", summary="Generera AI-kommentar för en artikel")
async def comment(req: CommentRequest):
    if not req.title.strip():
        raise HTTPException(status_code=422, detail="title får inte vara tomt.")
    try:
        text = await generate_comment(req.title, req.summary)
    except Exception as exc:
        logger.exception("generate_comment failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    return {"comment": text}


# ── Settings ─────────────────────────────────────────────────────────────────────────────

class SettingsPayload(BaseModel):
    system_prompt: str
    temperature:   float


@app.get("/settings", summary="Hämta AI-inställningar")
async def get_settings():
    with SETTINGS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


@app.put("/settings", summary="Uppdatera AI-inställningar")
async def update_settings(payload: SettingsPayload):
    if not (0.0 <= payload.temperature <= 2.0):
        raise HTTPException(status_code=422, detail="temperature måste vara 0.0–2.0.")
    if not payload.system_prompt.strip():
        raise HTTPException(status_code=422, detail="system_prompt får inte vara tomt.")
    data = {"system_prompt": payload.system_prompt, "temperature": payload.temperature}
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


# ── Bluesky ───────────────────────────────────────────────────────────────────────────

class BlueskyPostRequest(BaseModel):
    title:   str
    link:    str
    comment: str = ""


@app.post("/bluesky/post", summary="Posta artikel till Bluesky")
async def bluesky_post(req: BlueskyPostRequest):
    if not req.title.strip() or not req.link.strip():
        raise HTTPException(status_code=422, detail="title och link krävs.")
    try:
        uri = await post_article(req.title, req.link, req.comment)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"uri": uri}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
