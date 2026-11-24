from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, cases, chat, compare, documents, drafts, forms, guidance, me, services
from app.config import get_settings
from app.data.guidance import load_guidance
from app.data.loader import load_catalog
from app.db.store import MemoryStore, SupabaseStore
from app.graph.checkpoint import make_checkpointer
from app.graph.graph import build_graph
from app.llm.client import LLM
from app.ocr.pipeline import load_doc_types
from app.pdf.forms import load_forms


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.catalog = load_catalog(settings.data_dir)
    app.state.guidance = load_guidance(settings.data_dir, app.state.catalog.allowlist)
    app.state.llm = LLM()
    checkpointer = make_checkpointer(settings.database_url)
    app.state.checkpointer = checkpointer
    app.state.graph = build_graph(checkpointer.saver)
    app.state.doc_types = load_doc_types(settings.data_dir)
    app.state.forms = load_forms(settings.data_dir, app.state.catalog.allowlist)
    app.state.store = (
        SupabaseStore(settings.supabase_url, settings.supabase_secret_key)
        if settings.supabase_url and settings.supabase_secret_key
        else MemoryStore()
    )
    app.state.verifier = auth.TokenVerifier(settings.supabase_url) if settings.supabase_url else None
    yield
    checkpointer.close()


app = FastAPI(title="Sahaay API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat.router)
app.include_router(services.router)
app.include_router(compare.router)
app.include_router(documents.router)
app.include_router(me.router)
app.include_router(cases.router)
app.include_router(drafts.router)
app.include_router(forms.router)
app.include_router(guidance.router)


@app.get("/health")
def health() -> dict[str, str]:
    llm = getattr(app.state, "llm", None)
    return {"status": "ok", "llm": "live" if llm and llm.live else "stub"}


@app.get("/me")
def me(user: auth.CurrentUser) -> dict[str, object]:
    return {"user_id": user.id, "is_anonymous": user.is_anonymous}
