"""FastAPI backend for the AeroSafeX web interface and AI/ML features."""

from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
except ImportError as error:  # pragma: no cover - exercised when dependencies are absent
    raise RuntimeError("FastAPI backend requires: pip install -r requirements.txt") from error

from ai_mission import generate_mission
from compiler_service import compile_source
from ml_battery import model


class CompileRequest(BaseModel):
    source: str = Field(min_length=1)


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1)


class BatteryRequest(BaseModel):
    distance: float = Field(ge=0)
    altitude: float = Field(ge=0)
    hover_seconds: float = Field(default=0, ge=0)
    battery: float = Field(default=100, ge=0)


app = FastAPI(title="AeroSafeX AI Backend", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "AeroSafeX AI backend"}


@app.get("/api/sample")
def sample() -> dict[str, str]:
    from pathlib import Path
    path = Path(__file__).parent / "test_missions" / "safe.aero"
    return {"source": path.read_text(encoding="utf-8")}


@app.post("/api/compile")
def compile_mission(request: CompileRequest) -> dict[str, Any]:
    return compile_source(request.source)


@app.post("/api/ai/generate")
def ai_generate(request: PromptRequest) -> dict[str, Any]:
    try:
        suggestion = generate_mission(request.prompt)
        validation = compile_source(suggestion.source)
        return {"source": suggestion.source, "explanation": suggestion.explanation,
                "warnings": suggestion.warnings, "validation": validation}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/ml/predict-battery")
def predict_battery(request: BatteryRequest) -> dict[str, Any]:
    prediction = model.predict(request.distance, request.altitude, request.hover_seconds, request.battery)
    return {"predicted_use": round(prediction.predicted_use, 2),
            "remaining_battery": round(prediction.remaining_battery, 2),
            "confidence": prediction.confidence}


# Serve the browser UI from the same origin as the API. API routes are
# declared first, so /api/* continues to be handled by FastAPI endpoints.
from pathlib import Path
app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="web")
