from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from pipeline.customer_insights import run_customer_insights
from chat.customer_chat import answer_customer_question

app = FastAPI(title="AI Data Scientist Backend (MVP)")

# Allow React dev server to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/customer-insights")
def customer_insights(days: int = Query(30, ge=7, le=365)):
    return run_customer_insights(days=days)

@app.post("/api/customer-insights/chat")
def customer_chat(payload: dict):
    """
    payload = { "message": "...", "days": 30 }
    """
    return answer_customer_question(payload)
