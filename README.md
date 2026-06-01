# Store Intelligence System

Apex Retail Analytics System translating raw video feeds into store metrics.

## Quick Start (5 Commands)

1. Build & start containerized backend:
```bash
docker compose up --build -d
```

2. Run detection pipeline against input videos:
```bash
python pipeline/run_pipeline.py
```

3. Post generated event stream batch to API:
```bash
python -c "
import requests, json
with open('data/events.jsonl') as f:
    events = [json.loads(line) for line in f]
for i in range(0, len(events), 500):
    requests.post('http://localhost:8000/events/ingest', json=events[i:i+500])
"
```

4. Launch live metrics visualization dashboard:
```bash
streamlit run dashboard/app.py
```
*Note: Dashboard runs locally at http://localhost:8501*


5. Verify metrics and funnel endpoints return successful responses:
```bash
curl http://localhost:8000/stores/ST1008/metrics
curl http://localhost:8000/health
```

## Running Verification Tests
```bash
pytest tests/
```
