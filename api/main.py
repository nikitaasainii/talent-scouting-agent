import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agents.orchestrator import run_pipeline
from schemas.output_schema import FinalShortlist

app = FastAPI(
    title="Talent Scout AI Agent",
    description="AI-powered recruitment pipeline using GitHub + LLM",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class JDRequest(BaseModel):
    raw_jd: str

class HealthResponse(BaseModel):
    status: str
    message: str

@app.get("/", response_model=HealthResponse)
def root():
    return {"status": "ok", "message": "Talent Scout AI Agent is running"}

@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "message": "All systems operational"}

@app.post("/scout", response_model=FinalShortlist)
def scout(request: JDRequest):
    if not request.raw_jd.strip():
        raise HTTPException(status_code=400, detail="JD cannot be empty")
    if len(request.raw_jd) < 50:
        raise HTTPException(status_code=400, detail="JD too short — provide a detailed job description")
    try:
        shortlist = run_pipeline(request.raw_jd)
        return shortlist
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)