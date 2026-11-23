from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, services
from app.config import get_settings
from app.data.loader import load_catalog
from app.graph.graph import build_graph
from app.llm.client import LLM


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.catalog = load_catalog(settings.data_dir)
    app.state.llm = LLM()
    app.state.graph = build_graph()
    app.state.verifier = auth.TokenVerifier(settings.supabase_url) if settings.supabase_url else None
    yield


app = FastAPI(title="Sahaay API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat.router)
app.include_router(services.router)


@app.get("/health")
def health() -> dict[str, str]:
    llm = getattr(app.state, "llm", None)
    return {"status": "ok", "llm": "live" if llm and llm.live else "stub"}


@app.get("/me")
def me(user: auth.CurrentUser) -> dict[str, object]:
    return {"user_id": user.id, "is_anonymous": user.is_anonymous}
