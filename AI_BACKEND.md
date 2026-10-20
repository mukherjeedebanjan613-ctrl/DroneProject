# AeroSafeX AI/ML backend

Install dependencies and start the API:

```bash
python3 -m pip install -r requirements.txt
uvicorn api:app --reload
```

Endpoints:

- `GET /health` – backend health check
- `GET /api/sample` – sample AeroSafeX mission
- `POST /api/compile` – compile and simulate `{ "source": "..." }`
- `POST /api/ai/generate` – convert `{ "prompt": "..." }` into DSL and validate it
- `POST /api/ml/predict-battery` – predict battery usage from distance, altitude, and hover time

The same server also serves the browser interface at `http://127.0.0.1:8000/`.
Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

The AI assistant is deliberately conservative and offline. It generates a
starter mission, but the normal lexer, parser, semantic analyzer, and safety
analyzer remain authoritative. The battery model is a transparent linear
regression calibrated to simulator-style data; it is a replaceable baseline
for a future model trained on real flight telemetry.
