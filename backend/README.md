# Backend — How to Run (Terminal Commands)

This backend supports two ways to start the server:

1. `python app.py`
2. `uvicorn app:app --reload --port 8000`

Both run the backend, but **Uvicorn is the standard FastAPI server** and is what reliably exposes the interactive API docs (Swagger).

---

## 0) Navigate to the backend folder

### Windows (PowerShell)

```powershell
cd .\backend
```
