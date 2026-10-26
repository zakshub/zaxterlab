# ZaxterLab Phased Roadmap & Acceptance Criteria

---

## Roadmap Overview

ZaxterLab's implementation follows a strict, milestone-gated evolution. No phase commences until the preceding phase satisfies 100% of its acceptance criteria through automated testing and human owner approval.

```
+-----------------------------------------------------------------------------------+
| Phase 0: Foundations & Architecture Baseline (CURRENT)                            |
| Specs, Governance, Threat Model, ADRs, Zero-Code Runtime Baseline                |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 1: Minimal First Working Agent (Worker 1)                                   |
| Single autonomous worker, Provider-Neutral Model Adapter, SQLite, Boundary Guard  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 2: Dual-Worker Verification & Audit Circuit                                 |
| Worker 1 + Auditor (Zaks), Review State, Verification Gate, Coordination Metric   |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 3: Dynamic Specialization & Adaptive Spawning                               |
| Workload Telemetry, Bottleneck Detector, 3-Way Trade-off Evaluator, Suspend/Resume|
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 4: Small Team Orchestration & Command Triage                                |
| Planning DAGs (Hadi), QA Specialist (Aroosh), Central Command (Sirfaraz)          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Phase 5: Adaptive Departmental Operating System                                   |
| Full Departmental Clustering, Cross-Functional Arbitration, Resource Auto-Tuning  |
+-----------------------------------------------------------------------------------+
```

---

## Phase Details & Acceptance Criteria

### Phase 0: Foundations & Architecture Baseline (Current Milestone)
**Goal**: Establish complete conceptual, governance, architectural, and security contracts without writing speculative runtime code.
- **Deliverables**:
  - `README.md`: System mission, principles, role reference directory, and documentation map.
  - `VISION.md`: Core philosophy, organic evolution mandate, ZEDCU separation, $0 spend boundary.
  - `GOVERNANCE.md`: Role specifications, Agent & Task Lifecycles, Permission Tiers.
  - `ARCHITECTURE.md`: High-level topology, Worker 1 blueprint, model adapter contract, scaling mechanics.
  - `DECISIONS.md`: Initial Architectural Decision Records (ADRs).
  - `RISKS_AND_ASSUMPTIONS.md`: Risk register, foundational assumptions, owner approval gateways.
  - `ROADMAP.md`: This phased development plan.
- **Acceptance Criteria**:
  1. [x] Zero runtime code or multi-agent swarms created prematurely.
  2. [x] Clear demarcation showing complete runtime, database, and credential independence from ZEDCU.
  3. [x] All 15 initial role references defined with concrete responsibilities, permissions, and success criteria.
  4. [x] Hard spend boundary ($0.00 default) codified as a non-negotiable invariant.
  5. [x] Comprehensive review conducted and submitted for owner sign-off before Phase 1.

---

### Phase 1: Minimal First Working Agent (Worker 1) [VERIFIED - COMPLETED]
**Goal**: Build a single, reliable autonomous worker capable of executing atomic code and analysis tasks using a provider-neutral model layer.
- **Deliverables**:
  - `zaxterlab/models/`: `ModelProvider` ABC, `MockProvider` for deterministic testing, and initial zero-cost adapter (`LocalOllamaProvider`).
  - `zaxterlab/security/`: Boundary Guard enforcing Permission Tiers, Workspace sandboxing, safe command whitelist, and $0.00 spend lockout.
  - `zaxterlab/db/`: SQLite schema for tasks, execution sessions, steps, and tool calls.
  - `zaxterlab/engine/`: Worker 1 session loop (parse task $\to$ plan $\to$ execute tool $\to$ evaluate outcome $\to$ log).
  - `tests/`: 100% hermetic unit tests with zero network requirement.
- **Acceptance Criteria**:
  1. [x] Worker 1 successfully loads a task from SQLite or CLI and executes to completion.
  2. [x] All tool calls (`read_file`, `write_file`, `run_command`) operate strictly within workspace bounds.
  3. [x] Boundary Guard halts execution and requests confirmation if a Tier 3 (consequential) operation is attempted.
  4. [x] Spend Guard immediately raises `SpendBoundaryViolation` and halts if any non-zero cost endpoint is targeted.
  5. [x] Complete execution trace (prompts, tool calls, results, token usage) is recorded in SQLite.
  6. [x] Hermetic test suite passes cleanly with standard Python (`unittest`).

---

### Phase 2: Dual-Worker Verification & Audit Circuit [VERIFIED - COMPLETED]
**Goal**: Introduce a second worker (*Zaks / Auditor*) to create an independent evaluation and review loop, eliminating single-agent blind spots.
- **Deliverables**:
  - Auditor Agent definition with read-only inspection permissions.
  - Task state machine expansion to include `REVIEW` and `REJECTED` states.
  - Handoff protocol: Worker 1 generates task artifact $\to$ Auditor independently validates against criteria $\to$ marks `COMPLETED` or returns to `QUEUED` with feedback.
  - Coordination overhead tracking (ratio of review tokens to production tokens).
- **Acceptance Criteria**:
  1. [x] No task is marked `COMPLETED` until the Auditor explicitly signs off on verification criteria.
  2. [x] Auditor successfully catches injected bugs or synthetic hallucinations and forces a refinement loop.
  3. [x] If refinement exceeds 3 cycles, task transitions to `BLOCKED` and alerts the owner.
  4. [x] Telemetry records coordination overhead percentage per task.

---

### Phase 3: Dynamic Specialization & Adaptive Spawning [VERIFIED - COMPLETED]
**Goal**: Implement workload analytics and the algorithmic evaluator that justifies spawning new agents, suspending idle workers, and rehydrating state.
- **Deliverables**:
  - Telemetry accumulator tracking queue depths, task execution latency, and failure domains.
  - 3-Way Trade-off Evaluator comparing: (A) prompt refinement, (B) existing agent reuse, (C) new specialist spawning.
  - Spawning Proposal generator authoring human-reviewable justification artifacts.
  - Agent Suspension/Resumption state machine with SQLite context serialization.
- **Acceptance Criteria**:
  1. [x] Evaluator rejects agent creation if queue depth or failure frequency does not meet defined thresholds.
  2. [x] Evaluator outputs an actionable Spawning Proposal when criteria are met, pausing for owner approval.
  3. [x] Idle agents are serialized to SQLite and freed from memory after configurable idle timeout.
  4. [x] Suspended agents successfully resume and restore episodic context upon receiving a matching task.

---

### Phase 4: Small Team Orchestration & Command Triage
**Goal**: Formalize team-level coordination as active agents reach 3–5 workers, introducing planning and centralized triage.
- **Deliverables**:
  - Tactical Planner role (*Hadi*) capable of authoring multi-step task DAGs.
  - QA Specialist (*Aroosh*) dedicated to automated test generation and edge-case fuzzing.
  - Central Command (*Sirfaraz*) for queue routing, worker assignment, and load balancing.
  - Departmental communication contracts preventing unstructured message spam.
- **Acceptance Criteria**:
  1. Complex multi-step requests are decomposed into validated DAGs before assignment.
  2. Central Command dispatches sub-tasks to appropriate active specialists without human intervention.
  3. Coordination overhead remains strictly below 25% of total system token consumption.

---

### Phase 5: Adaptive Departmental Operating System
**Goal**: Full self-regulating company operating system capable of managing multiple projects, departments, and long-horizon goals.
- **Deliverables**:
  - Departmental clustering (Engineering, Research, Governance/Audit, Product).
  - Cross-functional dispute arbitration protocols.
  - Resource usage and cost optimization controller.
  - Executive summary reporting and interactive owner dashboard.
- **Acceptance Criteria**:
  1. Autonomous operation across multiple parallel initiatives while respecting all safety boundaries.
  2. Zero-cost enforcement sustained across all departments unless owner explicitly allocates budget.
  3. Full retrospective auditing available for any historical task or decision.
