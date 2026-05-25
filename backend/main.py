# Intelligent Research Assistant - Backend Entry Point
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag.rag_api import router as rag_router
from api.research import router as research_router
from api.models import router as models_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Intelligent Research Assistant",
    description="RAG + Multi-Agent Research System",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag_router)
app.include_router(research_router)
app.include_router(models_router)

# شو هو BaseModel؟
# تخيّل نموذج تعبئة — يحدد شو البيانات المطلوبة ونوعها
class ResearchRequest(BaseModel):
    topic: str
    max_sources: int = 5  # قيمة افتراضية

class ResearchResponse(BaseModel):
    topic: str
    status: str
    message: str

# GET endpoints
@app.get("/")
def root():
    return {"status": "running", "message": "Intelligent Research Assistant API"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# POST endpoint - يقبل طلب بحث
@app.post("/research", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    # هاد مؤقت — رح نربطه بالـagents لاحقاً
    return ResearchResponse(
        topic=request.topic,
        status="received",
        message=f"Research request for '{request.topic}' received. Processing {request.max_sources} sources."
    )