import time
import os
import uuid
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.models import DBEvent
from app.ingestion import ingest_events_batch, import_pos_csv
from app.metrics import compute_store_metrics
from app.funnel import compute_store_funnel
from app.heatmap import compute_store_heatmap
from app.anomalies import detect_store_anomalies
from app.health import run_health_check

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Store Intelligence API", version="1.0.0")

@app.on_event("startup")
def startup_populate():
    db = next(get_db())
    pos_path = "data/pos.csv"
    if os.path.exists(pos_path):
        try:
            import_pos_csv(pos_path, db)
        except Exception as e:
            print(f"Error preloading POS CSV data: {e}")
    else:
        print("Warning: data/pos.csv not found, skipping preloading.")

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    path_parts = request.url.path.split("/")
    store_id = None
    if "stores" in path_parts:
        idx = path_parts.index("stores")
        if idx + 1 < len(path_parts):
            store_id = path_parts[idx + 1]

    event_count = 0
    if request.url.path == "/events/ingest" and request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, list):
                event_count = len(body)
            elif isinstance(body, dict):
                event_count = 1
        except:
            pass

    response = await call_next(request)
    
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    print(f"[API_LOG] TraceID: {trace_id} | StoreID: {store_id} | Endpoint: {request.url.path} | "
          f"Latency: {latency_ms}ms | EventsCount: {event_count} | StatusCode: {response.status_code}")
          
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled Exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal system error occurred. Please try again later."}
    )

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {
        "message": "Welcome to the Store Intelligence API",
        "docs_url": "/docs",
        "health_url": "/health"
    }

@app.post("/events/ingest")
def events_ingest(payload: list[dict], db: Session = Depends(get_db)):
    if len(payload) > 500:
        raise HTTPException(status_code=400, detail="Batch size exceeds limit of 500 events.")
    result = ingest_events_batch(payload, db)
    return result

@app.get("/stores/{store_id}/metrics")
def store_metrics(store_id: str, db: Session = Depends(get_db)):
    metrics = compute_store_metrics(store_id, db)
    return metrics

@app.get("/stores/{store_id}/funnel")
def store_funnel(store_id: str, db: Session = Depends(get_db)):
    funnel = compute_store_funnel(store_id, db)
    return funnel

@app.get("/stores/{store_id}/heatmap")
def store_heatmap(store_id: str, db: Session = Depends(get_db)):
    heatmap = compute_store_heatmap(store_id, db)
    return heatmap

@app.get("/stores/{store_id}/anomalies")
def store_anomalies(store_id: str, db: Session = Depends(get_db)):
    anomalies = detect_store_anomalies(store_id, db)
    return anomalies

@app.get("/health")
def health_endpoint(db: Session = Depends(get_db)):
    status = run_health_check(db)
    if status["status"] == "UNHEALTHY":
        raise HTTPException(status_code=503, detail=status)
    return status
