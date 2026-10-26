# ZaxterLab Risks, Assumptions & Owner Approval Matrix

---

## 1. Technical & Operational Risk Register

| Risk ID | Description | Severity | Likelihood | Mitigation Strategy |
| :---: | :--- | :---: | :---: | :--- |
| **RSK-01** | **Accidental API / Cloud Incurred Costs**<br>Runaway autonomous loops or vendor pricing shifts triggering cloud charges. | High | Low | Programmatic `SpendGuard` set to $0.00 default. Any non-zero cost endpoint raises immediate fatal exception. Hard stop without explicit human token. |
| **RSK-02** | **Coordination Overhead Exceeding Work Value**<br>Agents spending more tokens talking to each other than executing code. | Medium | High | Track Coordination Overhead Metric (Tokens exchanged in coordination / Tokens executing tasks). Hard cap at 25%; if exceeded, system flags regression and pauses spawning. |
| **RSK-03** | **Premature Headcount Inflation**<br>Spawning agents speculatively before workload requires them. | Medium | Medium | Strict algorithmic gate in Phase 3. New agents cannot be spawned without historical evidence (queue wait time, repeated skill failures) and owner sign-off. |
| **RSK-04** | **ZEDCU State Leaks or Collisions**<br>Accidental shared access to ZEDCU databases, credentials, or runtime environment. | High | Low | Complete isolation enforced in code, file paths, databases, environment variables, and Git remotes. Verified by automated tests. |
| **RSK-05** | **Hallucinated Task Completion**<br>Agent claiming work is finished when tests are failing or not run. | High | Medium | Phase 2 independent Audit circuit (*Zaks / Vision*). A task cannot achieve `COMPLETED` status without verifiable test execution logs and independent audit sign-off. |
| **RSK-06** | **Unbounded Filesystem or Command Execution**<br>Agent executing destructive shell commands (`rm -rf`) or editing unauthorized files. | Critical | Low | Tier 3 Consequential Action Interceptor. All destructive commands, external git pushes, and file modifications outside workspace boundary are blocked. |

---

## 2. Foundational Assumptions

1. **Development Environment**:
   - Runtime operates on standard Linux with Python 3.13+ and Node 24+.
   - SQLite 3 is natively available and fully sufficient for single-node task queues and execution history.
2. **Model Availability**:
   - The initial development and testing can proceed with zero-cost adapters: hermetic in-memory mock models for unit tests, followed by local models (e.g., Ollama/llama.cpp) or free-tier APIs (e.g., Google Gemini free tier).
3. **Source of Truth**:
   - GitHub is the ultimate version-controlled source of truth.
   - All architectural decisions and governance contracts live in repository markdown files.
4. **Human Authority**:
   - Zak is the sole executive authority. No automated process may override or bypass human approval requirements.

---

## 3. Decisions & Actions Requiring Explicit Owner Approval

The following actions are classified as **Tier 3 (Consequential)** and strictly require prior affirmative approval from Zak:

| Category | Action Triggering Approval Gate | Required Artifact / Information |
| :--- | :--- | :--- |
| **Financial / Spending** | Any modification to default $0.00 spend limit, activation of paid API keys, or cloud infrastructure provisioning. | Budget limit request, expected ROI, and maximum spend cap. |
| **Organizational Evolution** | Spawning a new agent from `DRAFTED` to `ACTIVE` state, or retiring an existing agent. | Formal Spawning Proposal with telemetry evidence and 3-way trade-off analysis. |
| **Governance & Security** | Altering permission tier mappings, modifying `GOVERNANCE.md`, or elevating an agent's tool access privileges. | Full markdown diff of the governance change with security justification. |
| **Version Control & Deploy** | Committing to main, pushing git branches to remote repositories, or publishing releases. | Clean git diff summary, test pass confirmation, and release notes. |
| **Filesystem / System** | Destructive disk operations (`rm -rf`), installing system-wide packages or services. | Exact command string, target file list, and recovery plan. |

---

## 4. Open Questions & Recommendations for Owner Review

1. **Phase 1 Model Adapter Preference**:
   - *Recommendation*: For initial Phase 1 Worker 1 implementation, use `MockProvider` for 100% hermetic unit tests, paired with a pluggable adapter for either local Ollama or Google Gemini free-tier.
   - *Question for Owner*: Which zero-cost inference provider would you prefer as the primary default for live worker execution (Local Ollama or Gemini Free Tier)?

2. **Persona Archetype for Worker 1**:
   - *Recommendation*: Use `Reem` (Construction & Programming / Riri Williams) as the foundational persona for Worker 1, given that initial operational workloads will center on code generation, file modification, and unit test execution.
   - *Question for Owner*: Confirm if Reem is the preferred initial persona for Worker 1.
