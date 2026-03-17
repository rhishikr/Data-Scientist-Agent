# Frontend Architecture

This document explains how the React frontend is structured and how to work with it.

## Tech Stack

| Technology | Purpose |
|---|---|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool and dev server |
| Tailwind CSS v4 | Utility-first styling |
| shadcn/ui (Radix UI) | Pre-built accessible UI components |
| Recharts | Chart/data visualization |
| Lucide React | Icon library |
| Sonner | Toast notifications |
| React Markdown | Render markdown in chat responses |

## Project Structure

```
frontend/src/
├── App.tsx                          # Root component + sidebar navigation
├── main.tsx                         # Entry point (wraps App with AuthProvider)
├── index.css                        # Global styles
├── components/
│   ├── ui/                          # shadcn/ui primitives (50+ components)
│   ├── LoginPage.tsx                # Password login form
│   ├── chatAssistant/
│   │   ├── ChatAssistant.tsx        # Full RAG chat interface with SSE streaming
│   │   └── Chatbot.tsx              # Simple demo chatbot (not connected to backend)
│   ├── insightsScreen/
│   │   ├── CustomerInsightsScreen.tsx  # Main insights dashboard with tabs
│   │   ├── DataExplorerScreen.tsx      # Data preview/exploration
│   │   ├── RunSelector.tsx             # Pipeline run dropdown selector
│   │   ├── charts/                     # Visualization components
│   │   │   ├── AiAnalysisPanel.tsx     # AI-generated analysis display
│   │   │   ├── HealthGauge.tsx         # Health score gauge
│   │   │   ├── InsightCard.tsx         # Individual insight card
│   │   │   ├── PrescriptionCard.tsx    # Action item card
│   │   │   ├── RevenueLineChart.tsx    # Revenue trend chart
│   │   │   ├── ChartEnlargeWrapper.tsx # Expandable chart container
│   │   │   └── ChartNarrative.tsx      # AI-generated chart description
│   │   ├── dashboard/
│   │   │   ├── DashboardWidget.tsx     # Reusable widget component
│   │   │   ├── widgetRegistry.tsx      # Widget type → renderer mapping
│   │   │   ├── data.ts                 # All data-fetching hooks
│   │   │   ├── types.ts               # TypeScript type definitions
│   │   │   ├── formatters.ts          # Number/date formatting utilities
│   │   │   └── narrativeGenerators.ts # Text generation helpers
│   │   └── sections/                  # Tab panel components
│   │       ├── OverviewTab.tsx
│   │       ├── KpiStrip.tsx
│   │       ├── AiInsightsTab.tsx
│   │       ├── RevenueSalesTab.tsx
│   │       ├── StockDemandTab.tsx
│   │       ├── CustomersTab.tsx
│   │       ├── ProductsTab.tsx
│   │       ├── MarketingTab.tsx
│   │       ├── ActionQueueTab.tsx
│   │       ├── FunnelSessionsTab.tsx
│   │       ├── RunComparisonTab.tsx
│   │       └── DiagnosisBanner.tsx
│   ├── pipelineScreen/
│   │   └── agentDecisions/            # Agent decision visualization
│   └── mockScreens/                   # Top-level screen components
│       ├── PipelineScreen.tsx         # Real-time agent pipeline execution
│       ├── LLMAssistantScreen.tsx     # Chat assistant wrapper
│       ├── SettingsScreen.tsx         # Data management + run management
│       └── ...
├── contexts/
│   └── AuthContext.tsx                # Authentication state management
├── lib/
│   └── api.ts                        # API client (apiFetch, apiFetchJson)
└── styles/                            # Additional CSS
```

## Navigation Pattern

The app uses **no client-side router** (no React Router). Instead, navigation is state-driven:

### How it works

1. `App.tsx` defines a `menuItems` array with screen IDs and icons:
   ```typescript
   const menuItems = [
     { id: "pipelines", label: "Agent Pipeline", icon: GitBranch },
     { id: "customer-insights", label: "Insights and Predictions", icon: Users },
     { id: "data-explorer", label: "Data Explorer", icon: Table2 },
     { id: "llm-assistant", label: "LLM Assistant", icon: MessageSquare },
     { id: "settings", label: "Settings", icon: Settings },
   ];
   ```

2. The `activeSection` state variable tracks which screen is visible

3. Sidebar buttons call `setActiveSection(item.id)`

4. `renderContent()` uses a `switch` statement to return the matching component:
   ```typescript
   switch (activeSection) {
     case "pipelines":        return <PipelineScreen />;
     case "customer-insights": return <CustomerInsightsScreen />;
     case "data-explorer":    return <DataExplorerScreen />;
     case "llm-assistant":    return <LLMAssistantScreen />;
     case "settings":         return <SettingsScreen />;
     default:                 return <CustomerInsightsScreen />;
   }
   ```

## Authentication Flow

Authentication uses React Context (`frontend/src/contexts/AuthContext.tsx`):

1. `main.tsx` wraps the entire app in `<AuthProvider>`
2. `App.tsx` checks `isAuthenticated` from the auth context
3. If not authenticated → renders `<LoginPage />`
4. `LoginPage` takes a password input and calls `login(password)`
5. `login()` compares against the `VITE_APP_PASSWORD` env variable
6. On success → sets `sessionStorage["authenticated"] = "true"` and updates state
7. `logout()` clears sessionStorage and resets state

The auth state persists within a browser session but clears when the tab is closed.

## Key Screens

### Pipeline Screen (`components/mockScreens/PipelineScreen.tsx`)

Shows the 7-agent pipeline execution in real time. When a pipeline is triggered:
- Connects to the SSE endpoint (`/api/pipeline/stream`)
- Displays each agent's status (running, complete, error)
- Shows LLM decisions made by each agent
- Shows progress percentage

### Customer Insights Screen (`components/insightsScreen/CustomerInsightsScreen.tsx`)

The main analytics dashboard with multiple tabs:
- **Overview** — KPI strip, health gauge, diagnosis banner
- **AI Insights** — LLM-generated analysis panel
- **Revenue & Sales** — Revenue line chart, forecast data
- **Stock & Demand** — Demand forecasts by SKU and location
- **Customers** — Customer segmentation, churn predictions
- **Products** — Product performance metrics
- **Marketing** — Campaign ROI, CPA metrics
- **Action Queue** — Prescription cards with status tracking
- **Funnel & Sessions** — Conversion funnel, session analytics
- **Run Comparison** — Compare KPIs between pipeline runs

Uses the `RunSelector` dropdown to switch between different pipeline runs.

### Data Explorer Screen (`components/insightsScreen/DataExplorerScreen.tsx`)

Preview cleaned and feature-engineered datasets. Shows table previews with column stats.

### LLM Assistant Screen (`components/chatAssistant/ChatAssistant.tsx`)

Full-featured chat interface backed by the RAG system:
- Streaming responses via SSE (`/api/rag/chat/stream`)
- Session management (create, switch, delete sessions)
- Markdown rendering with syntax highlighting
- Source citations with collapsible details
- Query type badges (SQL, Insight, Hybrid)
- Suggested prompts based on context
- Chat history sidebar

### Settings Screen (`components/mockScreens/SettingsScreen.tsx`)

- Generate/delete synthetic data
- Simulate business scenarios (profit, loss, seasonal spike, etc.)
- View and manage pipeline runs
- Delete individual runs

## Data Fetching

### API Client (`lib/api.ts`)

All API calls go through two utility functions:

```typescript
apiFetch(url, init?)     // Fetch with auto-injected X-API-Key header
apiFetchJson<T>(url, init?)  // Fetch + JSON parse + error handling
```

The API base URL comes from `VITE_API_URL` env variable (default: `http://127.0.0.1:8000`).

### Data Hooks (`components/insightsScreen/dashboard/data.ts`)

Custom React hooks for fetching backend data:

| Hook | Endpoint | Returns |
|---|---|---|
| `useDashboardData(runId)` | `/api/kpi/snapshot` + `/api/forecast/snapshot` | KPI cards + forecast data |
| `useInsightsData(runId)` | `/api/insights/snapshot` | Business insights |
| `useRevenueForecastSeries(runId)` | `/api/forecast/series/revenue` | Revenue timeseries |
| `useDemandForecast(runId)` | `/api/forecast/series/demand` | Demand by SKU |
| `useChurnPredictions(runId)` | `/api/forecast/series/churn` | Customer churn predictions |
| `useAiAnalysis(runId)` | `/api/insights/ai-analysis` | LLM-generated analysis text |
| `useActionPlan(runId)` | `/api/action-plan` | Prioritized prescriptions |
| `useChartNarratives(runId)` | `/api/chart-narratives` | AI-generated chart descriptions |
| `useRuns()` | `/api/runs` | All pipeline runs |
| `useCleanedData(runId)` | `/api/cleaned-data` | Cleaned dataset previews |
| `useFeaturedData(runId)` | `/api/featured-data` | Feature-engineered data |
| `useRunComparison()` | `/api/runs/compare` | Run-to-run KPI deltas |

All hooks accept an optional `runId` parameter. If omitted, they fetch the latest run's data.

### SSE Streaming

Two features use Server-Sent Events for real-time updates:
- **Pipeline execution** — `PipelineScreen` connects to `/api/pipeline/stream`
- **Chat responses** — `ChatAssistant` streams from `/api/rag/chat/stream`

## Dashboard Widget System

The insights dashboard uses a widget registry pattern:

- `DashboardWidget.tsx` — Generic wrapper that renders any widget by type
- `widgetRegistry.tsx` — Maps widget type strings to React renderer functions
- Widgets receive data props and render charts/cards/tables

## How to Add a New Screen

1. **Create the component** in `src/components/` (e.g., `MyNewScreen.tsx`)

2. **Add to the menu** in `App.tsx`:
   ```typescript
   const menuItems = [
     // ... existing items
     { id: "my-screen", label: "My Screen", icon: SomeIcon },
   ];
   ```

3. **Add the case** to `renderContent()` in `App.tsx`:
   ```typescript
   case "my-screen":
     return <MyNewScreen />;
   ```

4. **Import** the component at the top of `App.tsx`:
   ```typescript
   import { MyNewScreen } from "./components/MyNewScreen";
   ```
