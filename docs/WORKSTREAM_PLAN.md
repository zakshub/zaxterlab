# ZaxterLab Workstream Execution Plan

---

## 1. Workstream Overview

To deliver a coordinated, robust product without disconnected prototypes, work is partitioned into three strictly delineated workstreams:

```
+-----------------------------------------------------------------------------------+
|                        WORKSTREAM C: COORDINATION & INTEGRATION                   |
| - Single API Contract (`docs/API_CONTRACT.md`)                                    |
| - Continuous Verification, Security Boundary Checks, Zero-Spend Invariant         |
+-----------------------------------------------------------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v                                                   v
+----------------------------------+   +----------------------------------+
|   WORKSTREAM A: FRONTEND AGENT   |   |   WORKSTREAM B: BACKEND AGENT    |
| - Dedicated `frontend/` workspace|   | - Minimal stdlib Python HTTP API |
| - React + TypeScript + Three.js  |   | - Task CRUD, Execution Engine    |
| - 3D Neural Network (Event-driven|   | - Session Controls (Suspend/     |
| - Typed Data Models & Adapters   |   |   Resume/Terminate)              |
| - Dual Mode: Demo vs. Live Backend|   | - Workspace & Audit Endpoints    |
| - Explicit Demo Labeling         |   | - Zero-Spend Enforcer ($0.00)    |
+----------------------------------+   +----------------------------------+
```

---

## 2. Workstream A — Frontend Agent

- **Location**: `/root/zakxterlab/frontend`
- **Stack**: React 18/19, TypeScript, Vite, Three.js for 3D Neural Network visualization, TailwindCSS design tokens.
- **Key Modules**:
  1. `src/types/api.ts`: TypeScript contracts mirroring `docs/API_CONTRACT.md`.
  2. `src/services/apiClient.ts`: Pluggable client adapter interface.
  3. `src/services/mockAdapter.ts`: Deterministic demo adapter labeled **DEMO — SIMULATED EVENTS**.
  4. `src/services/liveAdapter.ts`: Real backend HTTP client communicating with `/api`.
  5. `src/components/NeuralNetwork3D.tsx`: Three.js interactive 3D particle/synapse visualizer responding to event pipeline (Read, Plan, Tool Call, Evaluate, Log, Suspend, Resume).
  6. `src/components/Navigation.tsx`: Left navigation (Home, Tasks, Sessions, Agents, Workspace, Logs, Settings).
  7. `src/components/WorkerStatus.tsx`: Real-time status cards (Worker persona, spend boundary badge, pipeline stage indicator).
  8. `src/components/Timeline.tsx`: Live step trace cards with expand/collapse details.
  9. `src/components/WorkspaceBrowser.tsx`: Safe workspace file tree and content viewer.
  10. `src/components/SessionControls.tsx`: Suspend, Resume, and Terminate action buttons.

---

## 3. Workstream B — Backend Agent

- **Location**: `/root/zakxterlab/zaxterlab/api`
- **Stack**: Python 3 standard library `http.server` (zero additional dependencies, offline-first).
- **Key Modules**:
  1. `zaxterlab/api/server.py`: Deterministic REST API server binding to `127.0.0.1:8000` (or configurable port).
  2. `zaxterlab/api/handlers.py`: JSON request router mapping endpoints to `SQLiteStore`, `Worker1Engine`, and `ToolRegistry`.
  3. `tests/test_api_server.py`: Automated integration test suite validating all HTTP endpoints, spend guard enforcement over HTTP, and workspace sandboxing over HTTP.

---

## 4. Workstream C — Coordination, Integration & Verification

- **Lead**: Principal Engineer & Technical Coordinator.
- **Checklist**:
  1. Verify backend API starts cleanly and passes all HTTP integration tests.
  2. Verify frontend builds cleanly with TypeScript (`tsc --noEmit` and Vite build).
  3. Verify frontend in Demo Mode displays explicit demo banner.
  4. Verify frontend switched to Live Mode connects to backend API and displays real tasks, sessions, and files.
  5. Verify UI actions (Create Task, Execute, Suspend, Resume, Terminate) execute against real SQLite database and reflect deterministic state transitions.
  6. Confirm that spend boundary remains rigidly at $0.00 across all UI and API interactions.
