# backend/rag/sql_agent.py
"""
LangGraph ReAct SQL agent for querying Supabase PostgreSQL.
Adapted from Sara-Business-Intelligence's rag_pipeline.py.
"""
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent


SQL_SYSTEM_PROMPT = """You are an expert data analyst for a retail / ecommerce business.
You have access to a PostgreSQL database with the following tables:

RAW DATA TABLES:
- raw_customers: customer demographics (customer_id, name, email, age, gender, location, device_type, loyalty_status, total_spend, acquisition_date)
- raw_products: product catalog (sku, product_name, category, brand, cost_price, retail_price, profit_margin, discount_percent, average_rating)
- raw_transactions: order history (order_id, customer_id, sku, quantity, unit_price, total_amount, discount_amount, order_status, order_datetime)
- raw_transactions_with_session: transactions linked to sessions
- raw_inventory: stock levels (sku, stock_quantity, reorder_level, warehouse_location, supplier)
- raw_payments: payment details (order_id, payment_method, payment_status, transaction_fee, currency)
- raw_marketing: campaign metrics (campaign_id, channel, campaign_type, ad_spend, impressions, clicks, conversions)
- raw_campaign_performance: daily campaign performance
- raw_sessions: user sessions (session_id, customer_id, session_duration_sec, pages_viewed, device_type, traffic_source, converted_flag, revenue)
- raw_events: granular user events (event_id, session_id, customer_id, event_type, event_datetime, sku, quantity, unit_price)
- raw_web_analytics: web behavior (event_id, session_id, page_type, action, add_to_cart, referral_source)
- raw_funnel_summary: daily funnel metrics (sessions, product_views, add_to_cart, checkout_started, purchases, conversion_rate)

PIPELINE OUTPUT TABLES (JSONB snapshots):
- kpi_snapshots: KPI metrics per pipeline run (snapshot JSONB)
- forecast_snapshots: revenue/churn forecasts (snapshot JSONB)
- insight_snapshots: business insights (snapshot JSONB)
- hypothesis_snapshots: statistical test results (snapshot JSONB)
- pipeline_runs: pipeline execution metadata

IMPORTANT — DATA SOURCE PRIORITY:
Standard KPI metrics (AOV, revenue, churn rate, conversion rate, etc.) are already
pre-computed from CLEANED data and stored in kpi_snapshots. When the user asks for
a standard metric, PREFER querying the kpi_snapshots table (using JSONB operators)
over re-calculating from raw_* tables. The raw_* tables contain UNCLEANED data and
will produce different numbers than the dashboard.

Only query raw_* tables when:
- The user asks for a specific slice/filter not available in snapshots (e.g., "revenue for customers in NYC")
- The user explicitly asks for raw or unprocessed data
- The metric is not available in any snapshot table

When answering questions:
1. Write efficient PostgreSQL queries
2. Use proper JOINs when combining tables
3. Format currency values with 2 decimal places
4. Use date functions for time-based queries (e.g., DATE_TRUNC, EXTRACT)
5. Provide clear, business-focused answers
6. For JSONB snapshot tables, use jsonb operators (->>, ->, jsonb_array_elements) to extract data
7. LIMIT large result sets to avoid overwhelming output

To query KPI snapshots (preferred for standard metrics):
- Get latest snapshot: SELECT snapshot FROM kpi_snapshots ORDER BY created_at DESC LIMIT 1
- Extract a card: SELECT elem->>'value' FROM kpi_snapshots, jsonb_array_elements(snapshot->'cards') elem WHERE elem->>'id' = 'aov' ORDER BY created_at DESC LIMIT 1

For custom queries not in snapshots, use raw_* tables:
- Revenue by filter: SUM(total_amount) from raw_transactions WHERE ...
- Customer segments: GROUP BY from raw_customers WHERE ...
- Conversion rate: from raw_funnel_summary or calculated from raw_sessions

Always explain findings in business terms."""


# Module-level cache for the agent (avoid re-creating on every request)
_agent_cache: Dict[str, Any] = {}


def create_sql_agent_instance(db_url: str, llm: ChatOpenAI):
    """
    Create a LangGraph ReAct agent with SQL tools.
    Cached by db_url to avoid re-creation overhead.
    """
    cache_key = db_url
    if cache_key in _agent_cache:
        return _agent_cache[cache_key]

    db = SQLDatabase.from_uri(db_url)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SQL_SYSTEM_PROMPT,
    )

    _agent_cache[cache_key] = agent
    return agent


def run_sql_agent(
    agent,
    query: str,
    history: List = None,
    max_history: int = 20,
) -> Dict[str, Any]:
    """
    Run a query through the SQL agent with optional conversation history.
    """
    past = (history or [])[-max_history:]
    messages = past + [HumanMessage(content=query)]

    try:
        result = agent.invoke({"messages": messages})
        answer = result["messages"][-1].content

        return {
            "success": True,
            "query_type": "sql",
            "answer": answer,
            "source": "database",
        }
    except Exception as e:
        return {
            "success": False,
            "query_type": "sql",
            "answer": f"SQL agent error: {e}",
            "error": str(e),
        }
