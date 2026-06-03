# Apex Retail - Store Intelligence & Conversion Pipeline

This system translates raw offline retail CCTV camera streams into real-time visitor conversion funnels and store metrics. It uses **YOLOv8** object detection, **ByteTrack** spatial-temporal tracking, a **FastAPI** ingestion backend with SQLite storage, and a live interactive **Streamlit** visualization dashboard.

---

## 🚀 Quick Start (5-Command Deployment)

1. **Activate Environment & Install Dependencies**:
   ```bash
   python -m venv venv
   # On Windows: venv\Scripts\activate | On Linux/macOS: source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run Pipeline (Processes clips into event stream)**:
   ```bash
   # Process Store 1 new videos (default):
   python pipeline/run_pipeline.py --store Store1
   # Process Store 2 new videos:
   python pipeline/run_pipeline.py --store Store2
   ```

3. **Deploy Backend API Server (Docker Compose)**:
   ```bash
   docker compose up --build -d
   ```
   *The API will be live at [http://localhost:8000](http://localhost:8000).*

4. **Ingest Events Dataset**:
   ```bash
   python -c "
   import requests, json
   with open('data/events.jsonl') as f:
       events = [json.loads(line) for line in f]
   for i in range(0, len(events), 200):
       requests.post('http://localhost:8000/events/ingest', json=events[i:i+200])
   "
   ```

5. **Start Streamlit Dashboard**:
   ```bash
   streamlit run dashboard/app.py
   ```
   *Dashboard will open at [http://localhost:8501](http://localhost:8501).*

---

## 🛠️ Main Components

### 📹 1. Detection & Tracking Layer
Processes video feeds frame-by-frame:
* **Object Detection**: Class-0 (person) detections via YOLOv8.
* **Movement Tracking**: ByteTrack coordinates frame-by-frame tracking.
* **Visitor Re-ID**: Assigns persistent `visitor_id` tokens using a 5-minute spatial-temporal trajectory match.
* **Zone Classification**: Polygons partition the coordinates into `SKINCARE`, `MAKEUP`, `BILLING`, and `STAFF_ROOM`. For Store 2, the FOH screen (`zone.mp4`) is divided vertically to track skincare and makeup shelves dynamically.

### 🧠 2. FastAPI Intelligence Engine
Saves events, imports POS sales lists, and hosts endpoints:
* `POST /events/ingest`: Batch ingestion supporting custom and HackerEarth payloads (with automated normalization).
* `GET /stores/{id}/metrics`: Offline Store Conversion Rates, GMV, and abandonment metrics.
* `GET /stores/{id}/funnel`: Funnel counts showing drop-offs (Entry ➔ Zone Visit ➔ Queue ➔ Purchase).
* `GET /stores/{id}/heatmap`: Density mappings for visualization grids.
* `GET /stores/{id}/anomalies`: Active alerting (SPIKE, CONVERSION_DROP, DEAD_ZONE).
* `GET /health`: Server health checks, feed latency warnings, and database connection.

### 📊 3. Live Streamlit Dashboard
Displays premium visualization charts:
* Conversion metrics & funnels.
* Real-time anomaly banners with action prompts.
* Graphical heatmaps.
* Local Access: [http://localhost:8501](http://localhost:8501).

---

## 🧪 Running Automated Tests
Run the test suite using pytest to verify metric computations, funnels, and schema mapping compliance:
```bash
$env:PYTHONPATH="."
venv\Scripts\pytest
```
