# ZaxterLab System Architecture

---

## 1. Architectural Vision & Scope

ZaxterLab is structured as a modular, local-first, provider-neutral software system. It avoids speculative abstractions, massive dependencies, and pre-allocated multi-agent swarms.

The architecture emphasizes:
1. **Determinism over Stochasticity**: The core control plane, permission checks, state transitions, and audit trails are implemented in standard, deterministic Python code.
2. **Provider-Neutral Intelligence**: The LLM is an interchangeable reasoning engine behind a strict adapter interface, not the operating system itself.
3. **Local-First & Zero-Cost Persistence**: SQLite and structured JSON log files serve as the durable state store, requiring zero external infrastructure or cloud databases.

---

## 2. High-Level Component Topology

```
+---------------------------------------------------------------------------------+
|                                 USER / CLI                                      |
+---------------------------------------------------------------------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
|                                CONTROL PLANE                                    |
|                                                                                 |
|  +---------------------+   +---------------------+   +-----------------------+  |
|  |     Task Engine     |   |   Governance Engine |   |      Audit & QC       |  |
|  | (Queue & State Mach)|   | (Permissions & Auth)|   | (Checks & Invariants) |  |
|  +---------------------+   +---------------------+   +-----------------------+  |
+---------------------------------------------------------------------------------+
                                      |
                   +------------------+------------------+
                   |                                     |
                   v                                     v
+------------------------------------+   +------------------------------------+
|         AGENT DEFINITIONS          |   |        EXECUTION SESSIONS          |
|    (Declarative Specifications)    |   |    (Ephemeral Runtime Workers)     |
| - Identity, Role & Instructions    |   | - Session Memory & History Trace   |
| - Allowed Tools & Permission Scope |   | - Dynamic State & Step Execution   |
| - Activation & Success Metrics     |   | - Telemetry & Token Accounting     |
+------------------------------------+   +------------------------------------+
                   |                                     |
                   +------------------+------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
|                           TOOL & BOUNDARY REGISTRY                              |
| - Safe Tools (File Read, AST Parse, Test Runner)                                |
| - Boundary Guards (Tier 3 Consequential Action Interceptor)                     |
| - Zero-Spend Enforcer ($0.00 Limit Guard)                                       |
+---------------------------------------------------------------------------------+
                                      |
                   +------------------+------------------+
                   |                                     |
                   v                                     v
+------------------------------------+   +------------------------------------+
|    PROVIDER-NEUTRAL MODEL LAYER    |   |        PERSISTENCE ENGINE          |
| - Local Adapters (Ollama / vLLM)   |   | - SQLite (`zaxterlab.db`)          |
| - Free-Tier Adapters (Gemini, etc) |   | - Session Artifacts & Traces       |
| - Mock / Deterministic Test Driver |   | - Git Version Tracking             |
+------------------------------------+   +------------------------------------+
```

---

## 3. Minimal Architecture: First Working Agent (Worker 1)

In Phase 1, ZaxterLab instantiates exactly **one** working agent (utilizing the `Reem` or `Worker-1` persona specification) to handle concrete engineering and analysis tasks.

### Worker 1 Architecture Blueprint

```
                      +-----------------------------+
                      |       Input Task Spec       |
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Session Initializer       |
                      | - Load Agent Spec           |
                      | - Check Auth & Tier Limits  |
                      | - Create Session Record     |
                      +-----------------------------+
                                     |
                                     v
                         +-----------------------+
                         |     Execution Loop    | <---------------+
                         | - Format Context      |                 |
                         | - Query Model Adapter |                 |
                         | - Parse Tool Call     |                 |
                         +-----------------------+                 |
                                     |                             |
                                     v                             |
                         +-----------------------+                 |
                         |     Boundary Guard    |                 |
                         | - Tier Check          |                 |
                         | - Spend Check ($0)    |                 |
                         +-----------------------+                 |
                            /                 \                    |
                   [Permitted]               [Consequential / Error]
                          /                     \                  |
                         v                       v                 |
            +-----------------------+   +-----------------------+  |
            |     Execute Tool      |   |  Pause for Human Auth |  |
            | (Read/Write/Test)     |   |      or Abort         |  |
            +-----------------------+   +-----------------------+  |
                         |                           |             |
                         v                           v             |
            +-------------------------------------------+          |
            |            Log Step Telemetry             |          |
            +-------------------------------------------+          |
                         |                                         |
                         +--------> [Task Complete?] -- (No) ------+
                                           |
                                         (Yes)
                                           v
                              +-------------------------+
                              |   Final Verification    |
                              |   & Session Teardown    |
                              +-------------------------+
```

#### Core Components of Worker 1:
1. **Agent Definition File** (`agents/worker_1.json` or YAML):
   - Role description, system prompt, allowed tool list, max iterations, token limits.
2. **Session Engine** (`zaxterlab/engine/session.py`):
   - Ephemeral state manager. Tracks message history, current iteration count, and cumulative tokens used.
3. **Tool Registry** (`zaxterlab/tools/`):
   - Safe, minimal toolset:
     - `read_file(path, start, end)`
     - `write_file(path, content)`
     - `run_command(command)` (strictly confined to workspace; destructive commands blocked)
4. **Boundary Interceptor** (`zaxterlab/security/guard.py`):
   - Validates every action against the Permission Tier matrix.
   - Throws `ConsequentialActionHalt` if an operation requires human owner sign-off.
5. **Persistence Handler** (`zaxterlab/db/`):
   - Stores session records, task inputs, step executions, tool inputs/outputs, and final artifacts into SQLite.

---

## 4. Provider-Neutral Model Interface

To guarantee that ZaxterLab never suffers vendor lock-in or unexpected cost, LLM interaction is isolated behind an abstract base class (`ModelProvider`):

```python
class ModelProvider(ABC):
    """Abstract interface for all model execution backends."""

    @abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a text/chat completion request."""
        pass

    @abstractmethod
    def get_token_usage(self) -> TokenUsage:
        """Return cumulative token usage and cost calculation."""
        pass

    @abstractmethod
    def get_cost_estimate(self, request: CompletionRequest) -> float:
        """Calculate estimated cost. Must equal 0.0 for free/local tiers."""
        pass
```

### Supported Provider Drivers:
- **`MockProvider`**: Deterministic test adapter returning canned or scripted responses for hermetic unit testing without network or GPU.
- **`LocalOllamaProvider`**: Direct HTTP connection to local Ollama/llama.cpp inference running on localhost. Zero dollar spend.
- **`FreeTierGeminiProvider`**: Adapter leveraging official Google Gemini free-tier developer keys within strict rate limits.
- **`CloudProvider` (Guarded)**: Optional paid API adapter locked behind cryptographic owner approval. Default disabled.

---

## 5. Organizational Scaling Mechanics

ZaxterLab explicitly forbids creating agents speculatively. Instead, the system implements an algorithmic **Specialization Evaluator**.

### The Growth Trigger Pipeline

```
+---------------------------------------------------------------------------------+
| 1. MONITORING & TELEMETRY                                                       |
| - Rolling window of completed, failed, and queued tasks                         |
| - Metrics: Queue wait time, task completion duration, iteration count, failure %|
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| 2. BOTTLENECK IDENTIFICATION                                                    |
| Condition A: Sustained Queue Saturation (Queue depth > Threshold for X hours)   |
| Condition B: Repeated Skill Failure (Specific tool domain fails > Y% of runs)   |
| Condition C: Context Window Thrashing (Agent losing focus on multi-modal tasks) |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| 3. THREE-WAY TRADE-OFF EVALUATION                                               |
|                                                                                 |
|   Option A: Prompt / Workflow Refinement                                        |
|   - Can improved instructions or tool ergonomics resolve the bottleneck?        |
|                                                                                 |
|   Option B: Existing Agent Reuse                                                |
|   - Can an existing active/suspended worker be reassigned to this queue?        |
|                                                                                 |
|   Option C: Propose New Specialist                                              |
|   - Is there a clear, distinct domain boundary justifying a new agent spec?     |
+---------------------------------------------------------------------------------+
                                       |
                         (If Option C wins evaluation)
                                       v
+---------------------------------------------------------------------------------+
| 4. PROPOSAL ARTIFACT GENERATION                                                 |
| Author structured Spawning Proposal:                                            |
| - Target Role (e.g. Aroosh for QA or Hasan for DevOps)                          |
| - Evidence: Historical task IDs, failure metrics, queue latencies               |
| - Projected coordination overhead vs. throughput gain                           |
| - Success criteria and qualification test suite                                 |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
| 5. OWNER GATEWAY (HUMAN SIGN-OFF)                                               |
| The owner reviews the Spawning Proposal. If approved, agent moves from          |
| DRAFTED -> QUALIFIED -> ACTIVE.                                                 |
+---------------------------------------------------------------------------------+
```

---

## 6. Suspension and Resumption Mechanics

Idle agents consume unnecessary system resources and cognitive context. ZaxterLab implements clean lifecycle serialization:

- **Suspension Protocol**:
  1. Detect idle status (no assigned tasks for $K$ execution cycles).
  2. Serialize active working memory and episodic context to SQLite (`agent_state` table).
  3. Release in-memory data structures and model provider sessions.
  4. Transition status: `ACTIVE` $\to$ `SUSPENDED`.
  5. Log suspension event with timestamp and memory checksum.

- **Resumption Protocol**:
  1. New task arrives matching the suspended agent's qualification signature.
  2. Instantiate fresh execution session.
  3. Rehydrate historical state and lessons-learned summaries from SQLite.
  4. Transition status: `SUSPENDED` $\to$ `ACTIVE`.
  5. Resume execution with warm context.

---

## 7. Metrics & Observability Architecture

The system persists structured telemetry on every operation:
- **Task Outcomes**: Success / Failure / Aborted / Blocked.
- **Execution Cost**: Input tokens, output tokens, cached tokens, and estimated cost (enforcing $0.00).
- **Coordination Overhead**: Ratio of inter-agent messages / coordination cycles to actual task execution steps. If coordination overhead exceeds 25%, the system flags organizational inefficiency.
- **Audit Findings**: Number of review objections, hallucinations detected, and security halts triggered.
