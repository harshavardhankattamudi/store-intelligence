# Engineering Choices and Tradeoffs

This document details key tradeoffs made during design of the Store Intelligence system.

## 1. Object Detection Model Tradeoffs
- **Option Considered**: YOLOv8n, YOLOv8x, RT-DETR.
- **AI Recommendation**: YOLOv8n.
- **Selection**: YOLOv8n.
- **Rationale**: Retail edge servers typically operate without high-end dedicated GPUs. YOLOv8 Nano runs at >30fps on basic CPU nodes, saving hardware costs while maintaining high counts accuracy.

## 2. Event Schema Design
- **Selection**: JSON schema matching standard logging format.
- **Rationale**: Included `is_staff` and `confidence` parameters at the event level to decouple the model predictions from backend analytics computation, enabling rapid upgrades to model weights without modifying endpoint code.

## 3. Database Engine
- **Option Considered**: SQLite, PostgreSQL.
- **Selection**: SQLite.
- **Rationale**: Ideal for embedded store server architectures where data persistence runs locally. It does not require separate server provisioning, enabling quick setup during docker compose execution.
