# ZaxterLab — Operations & Owner Manual

**System Version:** 0.3.0-phase3  
**Status Assessment Date:** October 26, 2026  
**Primary Executive Authority:** Product Owner (Zak)  
**Authorized Spend:** **$0.00 USD (Hard Invariant)**

---

## 1. Quick Start

### Starting the Local Platform Daemon
```bash
# Option A: Direct CLI Entrypoint
python3 -m zaxterlab --host 127.0.0.1 --port 8000

# Option B: Managed Daemon Script
./scripts/run_daemon.sh start
./scripts/run_daemon.sh status
./scripts/run_daemon.sh stop
```

### Accessing the Web Dashboard
Open your local web browser to:
```
http://127.0.0.1:8000
```
The interface provides:
- **Operations Core:** Live Three.js 3D neural visualization with real-time state changes (`READ`, `PLAN`, `TOOL_CALL`, `EVALUATE`, `LOG`).
- **Completion Dashboard:** Honest, test-verified progress gauges, pillar statuses, and evidence summaries.
- **Workload Manager:** Task queue, dependency DAG graphs, execution controls, and step traces.
- **Role Roster:** Active specialist team, pending spawning proposals awaiting owner review, and dormant reference roles.
- **Workspace Files:** Sandboxed filesystem browser confined to `/root/zakxterlab/workspace`.
- **Audit Trail:** Immutable SQLite log of all task submissions, executions, auditor reviews, and specialist activations.

---

## 2. Dynamic Specialist Evolution & Approval Workflow

ZaxterLab does not spawn agents arbitrarily. It follows an empirical 3-way trade-off:
1. **Prompt/Tool Refinement:** Used for light backlogs and minor syntax errors.
2. **Worker 1 Reuse:** Used for normal construction workloads within Reem's domain.
3. **Specialist Spawning:** Only proposed when sustained workload pressure is detected.

### When a Specialist is Proposed
When the `SpecializationEvaluator` detects pressure (e.g. repeated test failures or backlog $\ge 4$):
1. A structured `SpawningProposal` is authored and persisted in SQLite.
2. The proposal appears in the **Role Roster** web interface under **"Pending Spawning Proposals (Owner Review Required)"**.
3. **You (Product Owner) have full decision authority:**
   - Click **"Approve & Activate Role"** to activate the specialist.
   - Click **"Reject"** to keep the role dormant.
4. Once approved, the specialist is immediately active and available for task assignments in multi-worker DAG pipelines.

---

## 3. Multi-Worker DAG Task Orchestration

### Defining Task Dependencies
Tasks can depend on other tasks:
```json
{
  "title": "Build Integration Tests",
  "description": "Write automated test suite in tests/test_calc.py",
  "assigned_specialist": "Aroosh",
  "depends_on": ["task_calc_module_01"],
  "max_retries": 2
}
```

### Pipeline Execution
- Dispatched via `POST /api/pipeline/run` or via the web UI.
- Validates the dependency graph using Kahn's topological sort algorithm. Cyclic dependencies are strictly rejected.
- If an upstream task fails, downstream dependent tasks transition safely to `BLOCKED_BY_UPSTREAM`.
- Recoverable errors trigger automatic retries up to `max_retries` with failure feedback injected into subsequent attempts.

---

## 4. Zero-Cost Offline Inference Adapters

ZaxterLab operates with a hard-locked budget of **$0.00 USD**.

### Supported Inference Modes
1. **Deterministic Mock Provider:** Included by default for automated hermetic unit tests.
2. **Local Ollama Provider (`LocalOllamaProvider`):**
   - Connects to local offline models running at `http://127.0.0.1:11434` (e.g. `qwen2.5-coder:7b`).
   - Automatically rejects any non-local external hostnames.
   - Gracefully falls back to mock inference if the local Ollama daemon is not running.

---

## 5. Verification & Testing

Run the hermetic test suite across all subsystems:
```bash
python3 -m unittest discover -s tests -v
```
All **54 tests** run hermetically in under 10 seconds without network access or billing.
