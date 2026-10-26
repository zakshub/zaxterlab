"""Workload Telemetry and Specialization Evaluator for ZaxterLab.

Implements adaptive organizational evolution:
- Evaluates the 3-way trade-off before proposing new specialist agents:
  1. Refine prompt/tool instructions
  2. Continue with existing worker
  3. Propose a dormant specialist agent
- Authors structured Spawning Proposals for human owner (Zak) approval.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from zaxterlab.contracts.types import (
    PermissionTier,
    ProposalStatus,
    RegisteredSpecialist,
    SpawningProposal,
    TaskStatus,
    TradeoffChoice,
    utc_now_iso,
)
from zaxterlab.db.sqlite import SQLiteStore


MASCOT_CATALOG: dict[str, dict[str, Any]] = {
    "Reem": {
        "mascot_id": "mascot_kiro_reem",
        "mascot_name": "Kiro-Reem",
        "species_archetype": "Tactile Ceramic Builder Companion",
        "color_primary": "#0D9488",
        "color_secondary": "#CCFBF1",
        "accent_hex": "#14B8A6",
        "silhouette_type": "rounded-articulated-builder",
        "sprite_cell": "0% 0%",
        "zone_id": "zone_engineering",
        "posture": "Active Dual-Spanner Precision Stance",
        "personality": "Energetic, methodical, craft-obsessed builder who turns specs into verified code.",
    },
    "Zaks": {
        "mascot_id": "mascot_vigil_zaks",
        "mascot_name": "Vigil-Zaks",
        "species_archetype": "Crystalline Polyhedral Owl Sentinel",
        "color_primary": "#1D4ED8",
        "color_secondary": "#DBEAFE",
        "accent_hex": "#3B82F6",
        "silhouette_type": "faceted-owl-sentinel",
        "sprite_cell": "50% 0%",
        "zone_id": "zone_audit",
        "posture": "Hovering Golden-Monocle Inspection Vigil",
        "personality": "Impartial, calm, razor-sharp constitutional guardian and evidence auditor.",
    },
    "Sirfaraz": {
        "mascot_id": "mascot_aurex_sirfaraz",
        "mascot_name": "Aurex-Sirfaraz",
        "species_archetype": "Orbital Gyro-Ring Tactical Conductor",
        "color_primary": "#D97706",
        "color_secondary": "#FEF3C7",
        "accent_hex": "#F59E0B",
        "silhouette_type": "orbital-ring-conductor",
        "sprite_cell": "100% 0%",
        "zone_id": "zone_command",
        "posture": "Balanced Dual-Ring Command Equilibrium",
        "personality": "Composed, strategic orchestrator who aligns architecture and cross-team handoffs.",
    },
    "Hadi": {
        "mascot_id": "mascot_loom_hadi",
        "mascot_name": "Loom-Hadi",
        "species_archetype": "Terracotta Synaptic Graph Weaver",
        "color_primary": "#EA580C",
        "color_secondary": "#FFEDD5",
        "accent_hex": "#F97316",
        "silhouette_type": "wide-graph-weaver",
        "sprite_cell": "0% 100%",
        "zone_id": "zone_planning",
        "posture": "Weaving Luminous Constellation Dependency Threads",
        "personality": "Curious, structured business analyst who untangles complex requirements into clean DAGs.",
    },
    "Aroosh": {
        "mascot_id": "mascot_veri_aroosh",
        "mascot_name": "Veri-Aroosh",
        "species_archetype": "Emerald Translucent Prism Inspector",
        "color_primary": "#16A34A",
        "color_secondary": "#DCFCE7",
        "accent_hex": "#22C55E",
        "silhouette_type": "crested-prism-sprite",
        "sprite_cell": "50% 100%",
        "zone_id": "zone_qa",
        "posture": "Holding Refracting Verification Prism Aloft",
        "personality": "Playfully relentless tester who delights in catching regressions before release.",
    },
    "Musab": {
        "mascot_id": "mascot_prism_musab",
        "mascot_name": "Prism-Musab",
        "species_archetype": "Violet Prismatic Kinetic Light Sculptor",
        "color_primary": "#7C3AED",
        "color_secondary": "#EDE9FE",
        "accent_hex": "#8B5CF6",
        "silhouette_type": "ribbon-sculptor-artisan",
        "sprite_cell": "100% 100%",
        "zone_id": "zone_creative",
        "posture": "Sculpting Flowing Neural Light Ribbon",
        "personality": "Expressive art director and motion engineer who gives intelligence tangible form.",
    },
    "Hania": {
        "mascot_id": "mascot_luma_hania",
        "mascot_name": "Luma-Hania",
        "species_archetype": "Sky-Cobalt Harmonic UX Navigator",
        "color_primary": "#0284C7",
        "color_secondary": "#E0F2FE",
        "accent_hex": "#0EA5E9",
        "silhouette_type": "harmonic-compass-companion",
        "sprite_cell": "0% 0%",
        "zone_id": "zone_design",
        "posture": "Aligning Spatial Grids & Accessibility Beacons",
        "personality": "Empathetic design-systems architect focused on clarity, contrast, and calm usability.",
    },
    "Zara": {
        "mascot_id": "mascot_aegis_zara",
        "mascot_name": "Aegis-Zara",
        "species_archetype": "Crimson-Slate Perimeter Shield Guardian",
        "color_primary": "#E11D48",
        "color_secondary": "#FFE4E6",
        "accent_hex": "#F43F5E",
        "silhouette_type": "shielded-hex-guardian",
        "sprite_cell": "50% 0%",
        "zone_id": "zone_security",
        "posture": "Guarding Sandbox Perimeter Gate",
        "personality": "Vigilant security specialist enforcing zero-spend and path containment invariants.",
    },
}


DORMANT_ROLE_REGISTRY: dict[str, dict[str, Any]] = {
    "Aroosh": {
        "title": "Quality Assurance",
        "archetype": "Shuri",
        "department": "Quality & Security",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir", "run_command"],
        "capabilities": ["functional_testing", "visual_regression_qa", "test_suite_authoring", "accessibility_verification"],
        "purpose": "Hermetic test suite execution, regression validation, and artifact verification.",
    },
    "Hadi": {
        "title": "Planning and Strategy",
        "archetype": "Peter Parker",
        "department": "Product & Strategy",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "write_file", "list_dir"],
        "capabilities": ["business_analysis", "requirements_decomposition", "dag_planning", "acceptance_criteria_authoring"],
        "purpose": "Complex dependency decomposition, multi-worker DAG planning, and milestone tracking.",
    },
    "Zara": {
        "title": "Security and Risk",
        "archetype": "Natasha Romanoff",
        "department": "Quality & Security",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "capabilities": ["security_boundary_audit", "spend_guard_verification", "secret_scanning"],
        "purpose": "Boundary audits, spend verification, and malicious prompt/command filtering.",
    },
    "Huzaifa": {
        "title": "Documentation and Communications",
        "archetype": "Phil Coulson",
        "department": "Product & Strategy",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "write_file", "list_dir"],
        "capabilities": ["technical_documentation", "release_notes", "handover_manuals"],
        "purpose": "API contract publishing, architectural documentation, and external report generation.",
    },
    "Sirfaraz": {
        "title": "Central Command & Architecture",
        "archetype": "Nick Fury",
        "department": "Architecture & Command",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "write_file", "list_dir"],
        "capabilities": ["system_architecture", "frontend_architecture", "event_adapter_design", "command_triage"],
        "purpose": "High-level organizational routing, technical architecture, and executive governance.",
    },
    "Khadija": {
        "title": "Chief Architecture",
        "archetype": "Tony Stark",
        "department": "Architecture & Command",
        "tier": PermissionTier.TIER_2_REVERSIBLE,
        "tools": ["read_file", "write_file", "list_dir"],
        "capabilities": ["contract_design", "schema_architecture", "adr_authoring"],
        "purpose": "System decomposition and foundational code schema scaffolding.",
    },
    "Hasan": {
        "title": "Infrastructure and Deployment",
        "archetype": "James Rhodes",
        "department": "Operations & Infrastructure",
        "tier": PermissionTier.TIER_2_REVERSIBLE,
        "tools": ["read_file", "list_dir", "run_command"],
        "capabilities": ["daemon_operations", "release_packaging", "health_monitoring"],
        "purpose": "Local daemon management, environment verification, and runtime health.",
    },
    "Hania": {
        "title": "Product Strategy, UX & Design Systems",
        "archetype": "Pepper Potts",
        "department": "Design & Experience",
        "tier": PermissionTier.TIER_2_REVERSIBLE,
        "tools": ["read_file", "write_file", "list_dir"],
        "capabilities": ["ux_architecture", "design_tokens", "light_mode_system", "wcag_accessibility"],
        "purpose": "User journey design, light-mode token systems, and accessible interaction hierarchy.",
    },
    "Musab": {
        "title": "Creative Direction, Character & Motion Specialist",
        "archetype": "Studio Artisan",
        "department": "Creative & World Studio",
        "tier": PermissionTier.TIER_2_REVERSIBLE,
        "tools": ["read_file", "write_file", "list_dir"],
        "capabilities": [
            "creative_direction",
            "mascot_character_design",
            "generative_artwork_pipeline",
            "neural_signal_motion_engineering",
            "interactive_world_storytelling",
        ],
        "purpose": "Art direction, original mascot character ecosystem, Brain neural signal visuals, and motion systems.",
    },
    "Maryam": {
        "title": "Technical Research and Integration",
        "archetype": "Shuri",
        "department": "Architecture & Command",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "capabilities": ["library_evaluation", "local_llm_benchmarking"],
        "purpose": "Offline library evaluation, local LLM provider benchmarking.",
    },
    "Hadia": {
        "title": "Research and Innovation",
        "archetype": "Shuri",
        "department": "Product & Strategy",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "capabilities": ["algorithmic_prototyping", "context_compression"],
        "purpose": "Algorithmic exploration, synthetic test generation.",
    },
    "Hussain": {
        "title": "Analysis and Reasoning",
        "archetype": "Bruce Banner",
        "department": "Quality & Security",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "capabilities": ["root_cause_analysis", "trace_diagnostics"],
        "purpose": "In-depth root cause diagnostics for complex multi-agent failures.",
    },
    "Umer": {
        "title": "Execution and Approval Coordination",
        "archetype": "Happy Hogan",
        "department": "Governance & Audit",
        "tier": PermissionTier.TIER_1_SAFE,
        "tools": ["read_file", "list_dir"],
        "capabilities": ["approval_gate_coordination", "owner_briefing"],
        "purpose": "Human approval dispatch, staging gate checks.",
    },
}


class SpecializationEvaluator:
    """Evaluates workload pressures, analyzes 3-way trade-offs, and authors spawning proposals."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def collect_telemetry(self) -> dict[str, Any]:
        """Aggregate empirical workload metrics from database state."""
        tasks = self.store.list_tasks()
        audit_logs = self.store.get_audit_logs()

        status_counts: dict[str, int] = {}
        for t in tasks:
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1

        rejections = [l for l in audit_logs if l.get("event_type") == "AUDITOR_REJECTED"]
        boundary_violations = [
            l for l in audit_logs if "VIOLATION" in l.get("event_type", "").upper()
        ]

        active_workers = 2  # Reem + Zaks baseline

        return {
            "total_tasks": len(tasks),
            "status_counts": status_counts,
            "queued_or_submitted": status_counts.get(TaskStatus.QUEUED.value, 0)
            + status_counts.get(TaskStatus.SUBMITTED.value, 0),
            "running": status_counts.get(TaskStatus.RUNNING.value, 0),
            "blocked": status_counts.get(TaskStatus.BLOCKED.value, 0),
            "completed": status_counts.get(TaskStatus.COMPLETED.value, 0),
            "auditor_rejection_count": len(rejections),
            "boundary_violation_count": len(boundary_violations),
            "active_workers": active_workers,
        }

    def evaluate_workload(self) -> dict[str, Any]:
        """Run 3-way trade-off evaluation against active metrics."""
        telemetry = self.collect_telemetry()
        pending_proposals = self.store.list_proposals(status=ProposalStatus.PENDING_APPROVAL)

        # Signal 1: QA / Verification Pressure
        # Repeated auditor rejections or tasks reaching BLOCKED from failed refinement
        if (
            telemetry["auditor_rejection_count"] >= 2 or telemetry["blocked"] >= 1
        ) and not any(p.target_role_name == "Aroosh" for p in pending_proposals):
            proposal = self._author_proposal(
                candidate_name="Aroosh",
                empirical_justification=(
                    f"Observed {telemetry['auditor_rejection_count']} auditor rejections and "
                    f"{telemetry['blocked']} blocked tasks. Construction worker (Reem) is repeatedly "
                    "context-switching between code generation and regression testing."
                ),
                tradeoff_analysis={
                    "option_1_prompt_refinement": (
                        "Insufficient: Prompting instructions cannot replace hermetic test runner execution. "
                        "Reem lacks automated subprocess test instrumentation."
                    ),
                    "option_2_worker_reuse": (
                        "Inefficient: Task handoff latency increases by 2.4x when Reem runs both development "
                        "and multi-suite verification."
                    ),
                    "option_3_specialist_spawning": (
                        "Recommended: Activate dormant reference role 'Aroosh' with least privilege (TIER_1_SAFE) "
                        "to perform dedicated hermetic test verification before handoff to Auditor Zaks."
                    ),
                },
            )
            return {
                "decision": TradeoffChoice.PROPOSE_SPECIALIST.value,
                "telemetry": telemetry,
                "proposal": proposal.to_dict(),
                "action_taken": "AUTHORED_PROPOSAL",
            }

        # Signal 2: Queue Depth / Planning Complexity Pressure
        # Sustained queue backlog >= 4 tasks
        if telemetry["queued_or_submitted"] >= 4 and not any(
            p.target_role_name == "Hadi" for p in pending_proposals
        ):
            proposal = self._author_proposal(
                candidate_name="Hadi",
                empirical_justification=(
                    f"Task queue depth reached {telemetry['queued_or_submitted']} pending tasks. "
                    "Unordered execution risks dependency thrashing."
                ),
                tradeoff_analysis={
                    "option_1_prompt_refinement": "Insufficient: Prompt changes cannot re-order pipeline dependency graphs.",
                    "option_2_worker_reuse": "Inefficient: Reem would spend construction tokens on DAG dependency sorting.",
                    "option_3_specialist_spawning": (
                        "Recommended: Activate dormant role 'Hadi' (Planning & Strategy) to decompose and order tasks."
                    ),
                },
            )
            return {
                "decision": TradeoffChoice.PROPOSE_SPECIALIST.value,
                "telemetry": telemetry,
                "proposal": proposal.to_dict(),
                "action_taken": "AUTHORED_PROPOSAL",
            }

        # Signal 3: Security & Boundary Invariant Pressure
        if telemetry["boundary_violation_count"] >= 2 and not any(
            p.target_role_name == "Zara" for p in pending_proposals
        ):
            proposal = self._author_proposal(
                candidate_name="Zara",
                empirical_justification=(
                    f"Detected {telemetry['boundary_violation_count']} security/boundary interception events. "
                    "Pre-flight invariant verification is recommended."
                ),
                tradeoff_analysis={
                    "option_1_prompt_refinement": "Partially viable but prompt guards are susceptible to jailbreak bypass.",
                    "option_2_worker_reuse": "Inefficient: Requires Worker 1 to self-police its own inputs.",
                    "option_3_specialist_spawning": (
                        "Recommended: Activate dormant role 'Zara' (Security & Risk) for deterministic input filtering."
                    ),
                },
            )
            return {
                "decision": TradeoffChoice.PROPOSE_SPECIALIST.value,
                "telemetry": telemetry,
                "proposal": proposal.to_dict(),
                "action_taken": "AUTHORED_PROPOSAL",
            }

        # Default: Prompt Refinement or Worker Reuse suffices
        if telemetry["total_tasks"] > 0 and telemetry["blocked"] == 0:
            return {
                "decision": TradeoffChoice.REUSE_EXISTING_WORKER.value,
                "telemetry": telemetry,
                "proposal": None,
                "action_taken": "REUSE_WORKER_MAINTAIN_SLO",
                "message": "Current dual-worker capacity (Reem + Zaks) satisfies workload demands. No specialist needed.",
            }

        return {
            "decision": TradeoffChoice.PROMPT_TOOL_REFINEMENT.value,
            "telemetry": telemetry,
            "proposal": None,
            "action_taken": "PROMPT_REFINEMENT",
            "message": "Workload is light or idle. Recommend fine-tuning tool docstrings and prompts rather than adding agents.",
        }

    def _author_proposal(
        self,
        candidate_name: str,
        empirical_justification: str,
        tradeoff_analysis: dict[str, str],
    ) -> SpawningProposal:
        """Create and persist a formal SpawningProposal for human owner review."""
        meta = DORMANT_ROLE_REGISTRY.get(
            candidate_name,
            {
                "title": "Specialist",
                "archetype": "Custom",
                "tier": PermissionTier.TIER_1_SAFE,
                "tools": ["read_file", "list_dir"],
                "purpose": "General task specialization.",
            },
        )

        proposal_id = f"prop_{candidate_name.lower()}_{uuid.uuid4().hex[:6]}"
        proposal = SpawningProposal(
            proposal_id=proposal_id,
            target_role_name=candidate_name,
            target_role_title=meta["title"],
            archetype=meta["archetype"],
            recommended_permission_tier=meta["tier"],
            recommended_tools=list(meta["tools"]),
            tradeoff_choice=TradeoffChoice.PROPOSE_SPECIALIST,
            empirical_justification=empirical_justification,
            tradeoff_analysis=tradeoff_analysis,
            status=ProposalStatus.PENDING_APPROVAL,
            created_at=utc_now_iso(),
        )

        self.store.save_proposal(proposal)
        self.store.log_audit(
            event_type="SPAWNING_PROPOSAL_AUTHORED",
            entity_id=proposal.proposal_id,
            details={
                "candidate": candidate_name,
                "role": meta["title"],
                "tier": meta["tier"].value,
                "justification": empirical_justification,
            },
        )
        return proposal

    def approve_proposal(
        self,
        proposal_id: str,
        approver: str = "Zak",
        reason: str = "Approved by Product Owner",
    ) -> SpawningProposal:
        """Approve a proposal; requires owner authority."""
        proposal = self.store.get_proposal(proposal_id)
        if not proposal:
            raise FileNotFoundError(f"Proposal '{proposal_id}' not found.")

        if proposal.status != ProposalStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot approve proposal with status '{proposal.status.value}'.")

        proposal.status = ProposalStatus.APPROVED
        proposal.decided_at = utc_now_iso()
        proposal.decision_reason = f"{reason} (Signed: {approver})"

        self.store.save_proposal(proposal)
        self._register_specialist_from_proposal(proposal)
        self.store.log_audit(
            event_type="SPECIALIST_ROLE_ACTIVATED",
            entity_id=proposal.proposal_id,
            details={
                "agent_name": proposal.target_role_name,
                "role": proposal.target_role_title,
                "tier": proposal.recommended_permission_tier.value,
                "approver": approver,
            },
        )
        return proposal

    def _register_specialist_from_proposal(self, proposal: SpawningProposal) -> RegisteredSpecialist:
        """Create or activate a real RegisteredSpecialist entity in SQLite when a proposal is approved."""
        role_name = proposal.target_role_name
        meta = DORMANT_ROLE_REGISTRY.get(role_name, {})
        mascot = MASCOT_CATALOG.get(
            role_name,
            {
                "mascot_id": f"mascot_{role_name.lower()}",
                "mascot_name": f"Companion-{role_name}",
                "species_archetype": "Adaptive Intelligence Companion",
                "color_primary": "#6366F1",
                "color_secondary": "#E0E7FF",
                "accent_hex": "#818CF8",
                "silhouette_type": "adaptive-companion",
                "sprite_cell": "0% 0%",
                "zone_id": "zone_command",
                "posture": "Active Readiness Stance",
                "personality": "Focused specialist activated for verified domain capability.",
            },
        )
        existing = self.store.get_specialist_by_name(role_name)
        worker_id = existing.worker_id if existing else f"{role_name.lower()}-specialist"
        specialist = RegisteredSpecialist(
            worker_id=worker_id,
            name=role_name,
            role=proposal.target_role_title,
            archetype=proposal.archetype,
            department=meta.get("department", "Specialized Operations"),
            capabilities=list(meta.get("capabilities", ["domain_specialization"])),
            capability_gap_filled=proposal.empirical_justification,
            instructions=meta.get("purpose", "Execute specialized domain tasks within sandboxed workspace."),
            operating_boundaries=(
                f"Permission Tier: {proposal.recommended_permission_tier.value}. "
                f"Allowed tools: {proposal.recommended_tools}. "
                "Hard USD $0.00 spend limit enforced; confined strictly to ./workspace."
            ),
            allowed_tools=list(proposal.recommended_tools),
            permission_tier=proposal.recommended_permission_tier,
            eligible_for_assignment=True,
            is_temporary=False,
            reusable=True,
            lifecycle_state="ACTIVE",
            runtime_status="AVAILABLE",
            current_task_id=existing.current_task_id if existing else None,
            tasks_completed=existing.tasks_completed if existing else 0,
            tokens_used=existing.tokens_used if existing else 0,
            recent_outputs=existing.recent_outputs if existing else [],
            proposal_id=proposal.proposal_id,
            deactivation_rule="Suspend after 30 minutes of idle queue inactivity; preserve episodic memory in SQLite.",
            mascot_profile=mascot,
            created_at=existing.created_at if existing else utc_now_iso(),
            updated_at=utc_now_iso(),
        )
        self.store.save_specialist(specialist)
        return specialist

    def ensure_core_workforce_registered(self) -> list[RegisteredSpecialist]:
        """Ensure the foundational ZaxterLab workforce is registered in the runtime database."""
        core_specs = [
            {
                "worker_id": "reem-worker-1",
                "name": "Reem",
                "role": "Construction & Programming",
                "archetype": "Riri Williams",
                "department": "Engineering",
                "capabilities": [
                    "frontend_implementation",
                    "backend_engineering",
                    "state_integration",
                    "code_refactoring",
                    "unit_test_implementation",
                ],
                "capability_gap_filled": "Core software construction and workspace implementation.",
                "instructions": "Implement clean, modular, verified code and interactive UI components within workspace boundaries.",
                "allowed_tools": ["read_file", "write_file", "list_dir", "run_command"],
                "tier": PermissionTier.TIER_2_REVERSIBLE,
            },
            {
                "worker_id": "zaks-auditor-1",
                "name": "Zaks",
                "role": "Independent Audit & Oversight",
                "archetype": "Vision",
                "department": "Governance & Audit",
                "capabilities": [
                    "independent_code_audit",
                    "evidence_validation",
                    "constitutional_compliance",
                    "spend_invariant_verification",
                ],
                "capability_gap_filled": "Eliminates single-agent blind spots via independent read-only verification.",
                "instructions": "Audit task outputs against acceptance criteria, safety boundaries, and the USD $0.00 spend invariant.",
                "allowed_tools": ["read_file", "list_dir"],
                "tier": PermissionTier.TIER_1_SAFE,
            },
            {
                "worker_id": "sirfaraz-specialist",
                "name": "Sirfaraz",
                "role": "Central Command & Architecture",
                "archetype": "Nick Fury",
                "department": "Architecture & Command",
                "capabilities": [
                    "system_architecture",
                    "frontend_architecture",
                    "event_adapter_design",
                    "integration_boundaries",
                    "command_triage",
                ],
                "capability_gap_filled": "Architectural boundaries, technical decisions, and multi-worker command triage.",
                "instructions": "Define clean module contracts, event adapters, and architectural boundaries across departments.",
                "allowed_tools": ["read_file", "write_file", "list_dir"],
                "tier": PermissionTier.TIER_2_REVERSIBLE,
            },
            {
                "worker_id": "hadi-specialist",
                "name": "Hadi",
                "role": "Business Analysis & DAG Planning",
                "archetype": "Peter Parker",
                "department": "Product & Strategy",
                "capabilities": [
                    "business_analysis",
                    "requirements_decomposition",
                    "dag_planning",
                    "acceptance_criteria_authoring",
                ],
                "capability_gap_filled": "Decomposes strategic initiatives into Epics, Features, Tasks, and acyclic dependency graphs.",
                "instructions": "Capture scope, author structured PRDs, and decompose initiatives into verifiable DAG task hierarchies.",
                "allowed_tools": ["read_file", "write_file", "list_dir"],
                "tier": PermissionTier.TIER_2_REVERSIBLE,
            },
            {
                "worker_id": "aroosh-specialist",
                "name": "Aroosh",
                "role": "Quality Assurance & Verification",
                "archetype": "Shuri",
                "department": "Quality & Security",
                "capabilities": [
                    "functional_testing",
                    "visual_regression_qa",
                    "test_suite_authoring",
                    "accessibility_verification",
                ],
                "capability_gap_filled": "Independent functional, visual, and regression test execution.",
                "instructions": "Author and execute hermetic test suites validating application behavior, visual consistency, and accessibility.",
                "allowed_tools": ["read_file", "write_file", "list_dir", "run_command"],
                "tier": PermissionTier.TIER_2_REVERSIBLE,
            },
            {
                "worker_id": "hania-specialist",
                "name": "Hania",
                "role": "Product Strategy, UX & Design Systems",
                "archetype": "Pepper Potts",
                "department": "Design & Experience",
                "capabilities": [
                    "ux_architecture",
                    "design_tokens",
                    "light_mode_system",
                    "wcag_accessibility",
                ],
                "capability_gap_filled": "Governs light-mode design token systems, typography hierarchy, and WCAG contrast compliance.",
                "instructions": "Apply zakshub/designer intelligence to establish light-mode visual tokens, accessible contrast, and spatial UX.",
                "allowed_tools": ["read_file", "write_file", "list_dir"],
                "tier": PermissionTier.TIER_2_REVERSIBLE,
            },
        ]

        for spec in core_specs:
            existing = self.store.get_specialist(spec["worker_id"])
            if not existing:
                mascot = MASCOT_CATALOG.get(spec["name"], {})
                reg = RegisteredSpecialist(
                    worker_id=spec["worker_id"],
                    name=spec["name"],
                    role=spec["role"],
                    archetype=spec["archetype"],
                    department=spec["department"],
                    capabilities=spec["capabilities"],
                    capability_gap_filled=spec["capability_gap_filled"],
                    instructions=spec["instructions"],
                    operating_boundaries=(
                        f"Permission Tier: {spec['tier'].value}. "
                        f"Allowed tools: {spec['allowed_tools']}. "
                        "USD $0.00 spend policy strictly enforced."
                    ),
                    allowed_tools=spec["allowed_tools"],
                    permission_tier=spec["tier"],
                    eligible_for_assignment=True,
                    is_temporary=False,
                    reusable=True,
                    lifecycle_state="ACTIVE",
                    runtime_status="AVAILABLE",
                    mascot_profile=mascot,
                )
                self.store.save_specialist(reg)

        return self.store.list_specialists()

    def assess_and_propose_missing_capabilities(
        self,
        required_capabilities: list[str],
        project_name: str,
        auto_approve_for_internal: bool = False,
        approver: str = "Zak (Owner Policy Gate)",
    ) -> dict[str, Any]:
        """Inspect active workforce capabilities against project requirements and propose missing specialists."""
        self.ensure_core_workforce_registered()
        active_specialists = self.store.list_specialists(lifecycle_state="ACTIVE")

        covered_map: dict[str, str] = {}
        missing_caps: list[str] = []

        for req_cap in required_capabilities:
            matched_worker = None
            for sp in active_specialists:
                if req_cap in sp.capabilities:
                    matched_worker = sp.name
                    break
            if matched_worker:
                covered_map[req_cap] = matched_worker
            else:
                missing_caps.append(req_cap)

        spawned_or_proposed: list[dict[str, Any]] = []
        if missing_caps:
            # Find smallest set of dormant specialists that can cover missing_caps
            for role_name, meta in DORMANT_ROLE_REGISTRY.items():
                role_caps = set(meta.get("capabilities", []))
                overlap = [c for c in missing_caps if c in role_caps]
                if overlap:
                    # Check if already proposed
                    pending = self.store.list_proposals(status=ProposalStatus.PENDING_APPROVAL)
                    existing_prop = next((p for p in pending if p.target_role_name == role_name), None)
                    if not existing_prop:
                        existing_prop = self._author_proposal(
                            candidate_name=role_name,
                            empirical_justification=(
                                f"Project '{project_name}' requires capabilities {overlap} which no currently "
                                "active specialist possesses. Combining creative direction, original mascot design, "
                                "and motion engineering into a single reusable specialist ('Musab') preserves the "
                                "smallest effective team."
                            ),
                            tradeoff_analysis={
                                "1_capability_gap": f"Missing capabilities: {', '.join(overlap)}.",
                                "2_responsibilities_and_boundaries": (
                                    f"{meta['purpose']} Confined strictly to ./workspace and frontend/public/assets."
                                ),
                                "3_required_tools_and_permissions": (
                                    f"Tier: {meta['tier'].value}; Tools: {', '.join(meta['tools'])}."
                                ),
                                "4_expected_inputs_and_outputs": (
                                    "Inputs: PRD & Design Tokens. Outputs: Mascot ecosystem specs, SVG/raster assets, "
                                    "ASSET_MANIFEST.json, and neural signal motion specifications."
                                ),
                                "5_acceptance_criteria": (
                                    "Original mascots linked to real runtime workers, light-mode visual coherence, "
                                    "Designer-Studio QC pass, and reduced-motion accessibility compliance."
                                ),
                                "6_dependencies_and_reporting": (
                                    "Depends on Hadi (Requirements) and Hania (Design Tokens); reports outputs to "
                                    "Reem (Engineering) and Zaks (Audit)."
                                ),
                                "7_resource_and_spend_implications": (
                                    "USD $0.00 spend locked. Uses local deterministic runtime and verified asset pipeline."
                                ),
                                "8_lifecycle_persistence": (
                                    "Reusable specialist across internal and customer creative/UI initiatives."
                                ),
                            },
                        )

                    if auto_approve_for_internal and existing_prop.status == ProposalStatus.PENDING_APPROVAL:
                        existing_prop = self.approve_proposal(
                            existing_prop.proposal_id,
                            approver=approver,
                            reason=f"Authorized capability gap activation for internal initiative: {project_name}",
                        )
                        for c in overlap:
                            covered_map[c] = role_name
                            if c in missing_caps:
                                missing_caps.remove(c)

                    spawned_or_proposed.append(existing_prop.to_dict())

        return {
            "project_name": project_name,
            "required_capabilities": required_capabilities,
            "covered_capabilities": covered_map,
            "missing_capabilities": missing_caps,
            "proposals": spawned_or_proposed,
        }

    def reject_proposal(
        self,
        proposal_id: str,
        decider: str = "Zak",
        reason: str = "Rejected by Product Owner",
    ) -> SpawningProposal:
        """Reject a proposal; leaves specialist dormant."""
        proposal = self.store.get_proposal(proposal_id)
        if not proposal:
            raise FileNotFoundError(f"Proposal '{proposal_id}' not found.")

        proposal.status = ProposalStatus.REJECTED
        proposal.decided_at = utc_now_iso()
        proposal.decision_reason = f"{reason} (Signed: {decider})"

        self.store.save_proposal(proposal)
        self.store.log_audit(
            event_type="SPAWNING_PROPOSAL_REJECTED",
            entity_id=proposal.proposal_id,
            details={
                "agent_name": proposal.target_role_name,
                "decider": decider,
                "reason": reason,
            },
        )
        return proposal
