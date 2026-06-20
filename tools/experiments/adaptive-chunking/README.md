# Adaptive Chunking Evaluation

Offline experiment harness for comparing baseline chunks with simple adaptive/structure-aware chunks.

This is intentionally read-only with respect to SecondBrain production data:

- It does not write to PostgreSQL.
- It does not call LightRAG.
- It does not update NAS state.

## Run

```powershell
python tools/experiments/adaptive-chunking/run_evaluation.py `
  --config tools/experiments/adaptive-chunking/config.sensor.json
```

Reports are written to:

```text
docs/experiments/artifacts/adaptive-chunking/
```

The Admin UI can read generated JSON/Markdown reports from that folder.

