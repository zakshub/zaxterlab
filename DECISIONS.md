# ZaxterLab Architectural Decision Records (ADRs)

---

## ADR-001: Strict Runtime and Storage Independence from ZEDCU

### Status
Accepted

### Context
ZEDCU is an established project within the ecosystem that features its own multi-agent orchestration, cloud infrastructure, task queues, and configuration. ZaxterLab requires a clean slate to explore an adaptive, organic company operating system without inheriting legacy technical debt, database schemas, or deployment dependencies from ZEDCU.

### Decision
ZaxterLab will maintain 100% codebase, runtime, database, task history, and credential independence from ZEDCU.
- No shared database tables, queues, or Redis/Temporal instances.
- No shared environment secrets or deployment scripts.
- Marvel-inspired role naming conventions (Sirfaraz, Khadija, etc.) and organizational archetypes are reused as conceptual templates only.

### Consequences
- **Positive**: Complete architectural freedom; zero risk of breaking ZEDCU operations; isolated failure domains.
- **Trade-off**: Core abstractions (task queues, database adapters) must be implemented natively in ZaxterLab rather than imported from ZEDCU.

---

## ADR-002: Organic Headcount Evolution vs. Pre-Instantiated Multi-Agent Topology

### Status
Accepted

### Context
Standard multi-agent frameworks often initialize large ensembles (5 to 20 agents) before validating basic task execution. This causes excessive token usage, opaque inter-agent communication loops, difficult debugging, and unjustified coordination overhead.

### Decision
ZaxterLab mandates an organic evolutionary growth model:
1. Start with **Worker 1** (a single generalist worker).
2. Expand to a **Worker 1 + Auditor** pairing in Phase 2 to introduce independent verification.
3. Spawn specialized workers (e.g. Planner, QA, DevOps) in subsequent phases only when quantified telemetry (sustained queue backlog, distinct skill boundaries, or context saturation) justifies the addition.

### Consequences
- **Positive**: Predictable behavior, easily debugged single-step traces, minimal token waste, and justified system expansion.
- **Trade-off**: Requires building an analytical evaluator to measure workload and generate formal spawning proposals.

---

## ADR-003: Provider-Neutral Model Abstraction Layer

### Status
Accepted

### Context
Coupling the agent framework directly to a single LLM provider (e.g., OpenAI, Google, Anthropic) risks vendor lock-in, API deprecation disruptions, and accidental financial expenditure.

### Decision
All model interactions must pass through an abstract base class (`ModelProvider`) supporting:
- Hermetic `MockProvider` for deterministic offline testing.
- Local inference adapters (`LocalOllamaProvider`, `llama.cpp`).
- Free-tier cloud adapters (`FreeTierGeminiProvider`).
- Strict zero-spend cost estimation guards.

### Consequences
- **Positive**: Zero cost default can be strictly enforced; unit tests run offline without API keys; easy switching between local and remote models.
- **Trade-off**: Advanced provider-specific proprietary features (e.g., proprietary tool syntax) must be normalized by adapter layers.

---

## ADR-004: Local-First SQLite Persistence Engine

### Status
Accepted

### Context
The operating system requires persistent tracking of agent definitions, task queues, step execution traces, and audit logs. Relying on cloud databases (PostgreSQL, DynamoDB) introduces operational friction, external dependencies, and potential hosting costs.

### Decision
ZaxterLab will use SQLite as its primary persistence engine, augmented by structured JSONL logs for raw execution traces.
- Standard Python `sqlite3` library (zero extra dependencies).
- Single-file database with WAL (Write-Ahead Logging) mode enabled.
- Automatic schema migrations managed within the codebase.

### Consequences
- **Positive**: Zero external dependencies; instant local setup; hermetic testing via in-memory SQLite (`:memory:`); simple backup and inspection.
- **Trade-off**: Concurrency is limited compared to distributed databases; sufficient for organic worker scale, but requires connection serialization under high write concurrency.

---

## ADR-005: Separation of Declarative Agent Definitions from Ephemeral Execution Sessions

### Status
Accepted

### Context
In monolithic agent designs, agent identity, system prompts, memory traces, and execution state are often tangled in single long-lived objects. This prevents clean suspension, makes telemetry difficult, and leads to memory leaks.

### Decision
ZaxterLab strictly separates:
1. **Agent Definition**: Immutable, declarative configuration files defining identity, domain, system prompt, allowed tools, and security boundaries.
2. **Execution Session**: Short-lived, stateful runtime instance created to fulfill a specific task. Upon task completion or idle timeout, session memory is flushed or persisted to SQLite, and runtime memory is freed.

### Consequences
- **Positive**: Agents can be safely suspended and resumed without state corruption; memory footprint remains near zero when idle.
- **Trade-off**: State persistence and rehydration logic must be tested to ensure continuity across task lifecycles.

---

## ADR-006: Hard Zero-Authorized Spend Boundary ($0.00 Default)

### Status
Accepted

### Context
Automated agents with network or API tool access can inadvertently rack up significant cloud and inference costs if runaway loops occur.

### Decision
The default authorized budget for ZaxterLab is permanently set to **USD $0.00**.
- A dedicated `BoundaryGuard` checks every outbound tool call and model request.
- Any request with a calculated cost $> 0$ triggers an immediate `SpendBoundaryViolation` halt.
- Spending can only be unlocked through a cryptographically verified or explicitly logged approval token from the human owner (Zak).

### Consequences
- **Positive**: 100% financial safety guaranteed by code invariants; no surprise bills.
- **Trade-off**: Requires careful management of free-tier rate limits and local inference availability.
