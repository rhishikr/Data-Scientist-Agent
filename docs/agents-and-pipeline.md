# Agents & Pipeline

This document explains the multi-agent system at the heart of the Data Scientist Agent: how agents work, what each one does, and how they're orchestrated.

## Overview

The pipeline consists of **7 specialized agents** that execute sequentially, each processing data and passing results to the next via a shared blackboard. Every agent uses an LLM (GPT-4.1-mini by default) to reason about its approach before executing.

```
Raw Data
   │
   ▼
┌─────────────────┐
│ 1. Cleaning     │  Validates & cleans raw CSVs
│    Agent        │  LLM decides: outlier method, cleaning strategy
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. Feature      │  Engineers features using Featuretools
│    Agent        │  LLM decides: join strategy, feature priorities
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. Hypothesis   │  Runs statistical tests (t-test, chi-squared, etc.)
│    Agent        │  LLM interprets: significant findings in business language
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. Insights     │  Generates business insights from data
│    Agent        │  LLM generates: executive narrative, priority areas
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. KPI          │  Computes key performance indicators
│    Agent        │  LLM contextualizes: KPI values with business commentary
└────────┬────────┘
         ▼
┌─────────────────┐
│ 6. Forecast     │  Trains/runs ML models (revenue, demand, churn)
│    Agent        │  LLM generates: strategic risk assessment
└────────┬────────┘
         ▼
┌─────────────────┐
│ 7. Action       │  Generates prioritized action plans
│    Agent        │  LLM generates: prescriptions with urgency/effort levels
└─────────────────┘
```

## Agent Lifecycle: Perceive → Reason → Act

Every agent extends `BaseAgent` (`backend/agents/base.py`) and implements three abstract methods:

### 1. Perceive

```python
async def perceive(self, blackboard: SharedBlackboard) -> Dict[str, Any]
```

The agent examines the blackboard and its environment. It reads outputs from upstream agents, profiles data files, and builds a summary of its inputs. No side effects — this is read-only.

**Example (CleaningAgent):** Scans raw CSV files, samples 100 rows from each, computes null percentages and data types.

### 2. Reason

```python
async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]
```

The agent calls the LLM via `ask_llm()` to decide **how** to execute. The LLM receives a summary from the perceive step and returns a JSON strategy/plan.

**Example (CleaningAgent):** The LLM examines data quality profiles and recommends `"iqr"` or `"zscore"` for outlier detection, flags high-null columns, and lists concerns.

### 3. Act

```python
async def act(self, plan: Dict[str, Any], blackboard: SharedBlackboard) -> AgentResult
```

The agent executes the actual data processing work, often by calling pipeline modules as subprocesses or direct function calls. It writes results to the blackboard and stores them in Supabase.

**Example (CleaningAgent):** Runs `pipeline/cleaning/clean_folder.py` as a subprocess, reads the cleaning report, stores cleaned datasets to Supabase.

### The `run()` method

The base class chains these three phases together:

```python
async def run(self, blackboard):
    perception = await self.perceive(blackboard)   # AgentStatus.PERCEIVING
    plan = await self.reason(perception)            # AgentStatus.REASONING
    result = await self.act(plan, blackboard)       # AgentStatus.ACTING
    return result                                   # AgentStatus.COMPLETE
```

If any phase throws an exception, the agent transitions to `AgentStatus.ERROR` and returns an `AgentResult` with `success=False`.

## The 7 Agents

### 1. CleaningAgent (`backend/agents/cleaning_agent.py`)

| | |
|---|---|
| **Wraps** | `pipeline/cleaning/clean_folder.py` (subprocess) |
| **Input** | Raw CSVs from Supabase (downloaded to temp dir) |
| **Output** | Cleaned CSVs + cleaning report |
| **LLM Decision** | Outlier detection method (IQR vs Z-score), cleaning strategy |
| **Stores to Supabase** | `cleaned_datasets` table, `cleaning_reports` table |

The perceive phase profiles each CSV (null percentages, data types). The LLM recommends a cleaning approach. The act phase runs the cleaning script and uploads results.

### 2. FeatureAgent (`backend/agents/feature_agent.py`)

| | |
|---|---|
| **Wraps** | `pipeline/features/feature_folder.py` (subprocess) |
| **Input** | Cleaned CSVs from CleaningAgent |
| **Output** | Feature-engineered CSVs + feature report |
| **LLM Decisions** | Join strategy, high-value feature suggestions, data quality concerns |
| **Post-Act LLM** | Evaluates the quality of engineered features |
| **Stores to Supabase** | `featured_datasets` table, `feature_reports` table |

Uses Featuretools under the hood for automated feature engineering (temporal features, aggregations, etc.).

### 3. HypothesisAgent (`backend/agents/hypothesis_agent.py`)

| | |
|---|---|
| **Wraps** | `pipeline/hypothesis/runner.py` (direct import) |
| **Input** | Cleaned + featured data |
| **Output** | Statistical test results (correlations, comparisons) |
| **LLM Decisions** | Expected relationship types, alpha level |
| **Post-Act LLM** | Interprets significant findings in business language |
| **Stores to Supabase** | `hypothesis_snapshots` table |

Runs automated hypothesis tests: numeric-numeric correlations, category-numeric comparisons. Applies FDR correction for multiple testing.

### 4. InsightsAgent (`backend/agents/insights_agent.py`)

| | |
|---|---|
| **Wraps** | `pipeline/insights/runner.py` (direct import) |
| **Input** | Features + hypothesis results |
| **Output** | Business insights bundle (customer, product insights + prescriptions) |
| **LLM Decisions** | Priority areas to focus on |
| **Post-Act LLM** | Generates executive narrative ("retail doctor" diagnosis) |
| **Stores to Supabase** | `insight_snapshots` table |

Generates structured insights about customer behavior, product performance, and revenue patterns.

### 5. KPIAgent (`backend/agents/kpi_agent.py`)

| | |
|---|---|
| **Wraps** | `pipeline/kpi/runner.py` (direct import) |
| **Input** | All upstream agent outputs |
| **Output** | KPI cards (revenue, AOV, churn rate, conversion rate, etc.) |
| **LLM Decisions** | Which KPI groups to emphasize |
| **Post-Act LLM** | "Retail doctor" commentary on KPI values |
| **Stores to Supabase** | `kpi_snapshots` table |

Computes 20+ KPI metrics organized by group (revenue, customer health, inventory, marketing).

### 6. ForecastAgent (`backend/agents/forecast_agent.py`)

| | |
|---|---|
| **Wraps** | `pipeline/forecast/runner.py` (direct import) |
| **Input** | Featured data + upstream context |
| **Output** | Revenue, demand, churn, and cashflow forecasts |
| **LLM Decisions** | Key risks to monitor, forecast horizon |
| **Post-Act LLM** | Strategic risk assessment with prescribed actions |
| **Stores to Supabase** | `forecast_snapshots` table |

Uses pre-trained scikit-learn models (`.joblib` files in `backend/models/`):
- `revenue_hgbr_v1.joblib` — Revenue forecasting (HistGradientBoosting)
- `demand_hgbr_v1.joblib` — Demand forecasting
- `churn_logreg_cal_v1.joblib` — Churn prediction (calibrated logistic regression)
- `cashflow_hgbr_v1.joblib` — Cashflow forecasting

### 7. ActionAgent (`backend/agents/action_agent.py`)

| | |
|---|---|
| **Wraps** | Custom LLM-driven prescription generation |
| **Input** | All upstream agent outputs (insights, KPIs, forecasts) |
| **Output** | Prioritized action plans with urgency and effort levels |
| **LLM Decisions** | Prioritization strategy, prescription generation |
| **Stores to Supabase** | `action_plan_snapshots` table |

Aggregates all upstream results and generates actionable prescriptions. Falls back to rule-based prescriptions if LLM generation fails.

## Orchestrator (`backend/agents/orchestrator.py`)

The `PipelineOrchestrator` manages the full pipeline lifecycle:

### Factory Method

```python
orchestrator = PipelineOrchestrator.create_default(reset=True, alpha=0.05)
```

Creates the standard 7-agent pipeline with:
- A `SharedBlackboard` initialized with config and temp directory paths
- All 7 agents in execution order

### Execution Flow

1. **Create pipeline run** in Supabase (gets a `run_id`)
2. **Download raw data** from Supabase to temp directories
3. **Execute agents sequentially** — each agent runs in a background thread (via `asyncio.to_thread`) to keep the API responsive
4. **Broadcast SSE events** — `agent_started`, `agent_completed`, `pipeline_complete`
5. **Complete pipeline run** in Supabase with status and summary
6. **Rebuild RAG index** with new pipeline outputs
7. **Clean up temp directories**

### Status Callbacks

The orchestrator supports real-time updates via callbacks:

```python
orchestrator.on_status(callback_function)
```

These callbacks are used by the SSE endpoint (`/api/pipeline/stream`) to push events to connected frontends.

### Error Handling

The pipeline is **resilient** — if an agent fails, it logs the error and continues to the next agent. The overall pipeline status reflects whether any agent failed.

## SharedBlackboard (`backend/agents/blackboard.py`)

The blackboard is the central communication mechanism between agents:

```python
@dataclass
class SharedBlackboard:
    config: Dict[str, Any]          # Pipeline settings (reset, alpha, run_id)
    paths: Dict[str, str]           # Temp directory paths for each stage
    data_state: Dict[str, Any]      # Agent outputs (downstream agents read this)
    llm_decisions: List[Dict]       # Log of all LLM reasoning
    agent_results: Dict[str, AgentResult]  # Execution results per agent
    messages: List[AgentMessage]    # Inter-agent message bus
    _listeners: List[Callable]      # Event callbacks for SSE
```

Key fields that flow between agents:
- `data_state["cleaning"]` → read by FeatureAgent
- `data_state["features"]` → read by HypothesisAgent, InsightsAgent
- `data_state["hypothesis"]` → read by InsightsAgent, ForecastAgent
- `data_state["insights"]` → read by KPIAgent
- `data_state["kpi"]` → read by ForecastAgent
- All of the above → read by ActionAgent

## LLM Integration (`backend/agents/llm.py`)

All agent LLM calls go through two functions:

### `ask_llm(system_prompt, user_prompt)`

Async wrapper using LangChain's `ChatOpenAI`. Model and temperature configured via environment variables:
- Model: `RAG_LLM_MODEL` (default: `gpt-4.1-mini`)
- Temperature: `0.2` (low for deterministic reasoning)

### `parse_llm_json(raw, fallback)`

Parses JSON from LLM responses, stripping markdown code fences if present. Falls back to a default dict if parsing fails.

## How to Add a New Agent

1. **Create a new file** in `backend/agents/`, e.g., `my_agent.py`

2. **Subclass `BaseAgent`:**
   ```python
   from .base import BaseAgent, AgentResult
   from .blackboard import SharedBlackboard

   class MyAgent(BaseAgent):
       def __init__(self):
           super().__init__(
               agent_id="my_agent",
               name="My New Agent",
               description="Does something useful",
           )

       async def perceive(self, blackboard):
           # Read from blackboard.data_state
           return {"input_data": ...}

       async def reason(self, perception):
           # Call ask_llm() to decide strategy
           return {"strategy": ...}

       async def act(self, plan, blackboard):
           # Do the work, write to blackboard.data_state
           blackboard.data_state["my_agent"] = {...}
           return AgentResult(agent_id=self.agent_id, success=True)
   ```

3. **Register in the orchestrator** — add your agent to the `agents` list in `PipelineOrchestrator.create_default()` (`backend/agents/orchestrator.py`):
   ```python
   from .my_agent import MyAgent

   agents = [
       CleaningAgent(),
       FeatureAgent(),
       HypothesisAgent(),
       InsightsAgent(),
       KPIAgent(),
       ForecastAgent(),
       MyAgent(),        # Add here — order matters!
       ActionAgent(),
   ]
   ```

4. **(Optional) Store results to Supabase** — use `run_id = blackboard.config.get("run_id")` and call the appropriate `store_*` function from `db/store.py`.
