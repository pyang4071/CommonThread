import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.engine import engine
from app.routers import admin, archetypes, book_types, books, genres, recommendations, search, series, tones, tropes, users
from app.routers.dislikes import router as dislikes_router
from app.routers.user_tags import router as user_tags_router
from app.routers.ratings import ratings_router, router as ratings_books_router
from app.routers.reading_status import router as reading_status_books_router, shelf_router
from app.services.embedding import _get_description_model, _get_genome_model

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm both FastEmbed models at startup so the first request doesn't
    # hang waiting for ~570 MB of model weights to download/load.
    logger.info("Pre-warming embedding models…")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _get_genome_model)
    await loop.run_in_executor(None, _get_description_model)
    logger.info("Embedding models ready.")
    yield
    await engine.dispose()


app = FastAPI(
    title="CommonThread",
    description="Book recommendation engine powered by tropes and character archetypes",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(books.router, prefix=API_PREFIX)
app.include_router(book_types.router, prefix=API_PREFIX)
app.include_router(genres.router, prefix=API_PREFIX)
app.include_router(tropes.router, prefix=API_PREFIX)
app.include_router(archetypes.router, prefix=API_PREFIX)
app.include_router(recommendations.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(series.router, prefix=API_PREFIX)
app.include_router(tones.router, prefix=API_PREFIX)
app.include_router(ratings_books_router, prefix=API_PREFIX)
app.include_router(ratings_router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(reading_status_books_router, prefix=API_PREFIX)
app.include_router(shelf_router, prefix=API_PREFIX)
app.include_router(dislikes_router, prefix=API_PREFIX)
app.include_router(user_tags_router, prefix=API_PREFIX)


@app.get("/health")
async def health():
    genome_ready = _get_genome_model.cache_info().currsize > 0
    desc_ready = _get_description_model.cache_info().currsize > 0
    return {
        "status": "ok",
        "models": {
            "genome": "ready" if genome_ready else "loading",
            "description": "ready" if desc_ready else "loading",
        },
    }
