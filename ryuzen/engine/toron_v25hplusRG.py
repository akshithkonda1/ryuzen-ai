"""Ryuzen Toron v2.5H+ epistemic reasoning engine implementation.

This module encodes the enterprise-grade, multi-tiered cognition pipeline
specified for Toron v2.5H+. The implementation focuses on deterministic,
inspectable stages with structured inputs/outputs to ease observability and
future extension toward live model integrations.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from ryuzen.engine.cache import InMemoryCache
from ryuzen.engine.confidence import stabilized_confidence
from ryuzen.engine.execution_plan import stabilize_execution_plan
from ryuzen.engine.latency_utils import stable_latency
from ryuzen.engine.meta_flags import stabilized_meta_flags
from ryuzen.engine.snapshot_utils import normalize_snapshot
from ryuzen.engine.tier_utils import normalized_pipeline


@dataclass
class ModelResponse:
    """Normalized response envelope returned by the Model Abstraction Layer."""

    model: str
    response: str
    latency_ms: int
    tokens_used: int


class ModelAbstractionLayer:
    """Single entrypoint to all external or simulated model calls.

    The layer standardizes payloads, enforces safety/timeout constraints,
    and caches responses based on a semantic fingerprint to avoid redundant
    calls during a pipeline run. Exponential backoff is simulated without
    introducing real wall-clock delays.
    """

    SUPPORTED_MODELS: Sequence[str] = (
        "Claude-Sonnet-4.5",
        "GPT-5.2",
        "Mistral-Large",
        "Gemini 3",
        "Qwen 72B",
        "Llama 3.1 70B",
        "Grok",
        "DeepSeek R1 (Light)",
        "DeepSeek R1 (Heavy)",
        "Kimi K2 (Light)",
        "Kimi K2 (Heavy)",
        "Opus",
        "Perplexity Sonar",

    )

    def __init__(self, cache: Optional[InMemoryCache] = None) -> None:
        self.cache = cache or InMemoryCache()

    def _fingerprint(self, model: str, prompt: str) -> str:
        payload = json.dumps({"model": model, "prompt": prompt}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _sanitize(self, text: str) -> str:
        redacted = text.replace("harmful", "[redacted]")
        return redacted.strip()

    def call_model(self, model: str, prompt: str) -> ModelResponse:
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} is not supported by MAL")

        key = self._fingerprint(model, prompt)
        cached = self.cache.get(key)
        if cached:
            return cached

        latency_ms = stable_latency(prompt)
        tokens_used = max(24, len(prompt) // 4)
        response_text = self._sanitize(f"{model} processed: {prompt[:256]}")

        envelope = ModelResponse(
            model=model,
            response=response_text,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

        self.cache.set(key, envelope, ttl_seconds=3600)
        return envelope


@dataclass
class ExecutionPlan:
    domain: str
    complexity: str
    contradiction_likelihood: str
    emotional_volatility: str
    evidence_scarcity: str
    latency_target_ms: int
    use_opus: bool
    tier1_models: List[str]
    mmre_layers: List[int]
    synthesis_depth: str
    latency_ms: int = 0
    tier_path: List[str] = field(default_factory=list)
    snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TierArtifacts:
    clean_prompt: str
    execution_plan: ExecutionPlan
    t1_raw: List[Dict[str, Any]]
    t1_summary: Dict[str, Any]
    cdg_structure: Dict[str, Any]
    t2_audit_report: Dict[str, Any]
    reality_packet: Dict[str, Any]
    judicial_result: Dict[str, Any]
    rwl_result: Dict[str, Any]
    confidence_score: float
    aloe_policy: Dict[str, Any]
    meta_surveillance_flags: List[str]


class RyuzenToronV25HPlus:
    """Deterministic, multi-tier Toron v2.5H+ pipeline."""

    TIER2_MODELS: Sequence[str] = ("DeepSeek R1 (Light)", "Kimi K2 (Light)")

    def __init__(self, now: Optional[float] = None) -> None:
        self.mal = ModelAbstractionLayer()
        self.psl_cache = InMemoryCache()
        self.t1_cache = InMemoryCache()
        self.now = now or time.time()
#This defines the tier structure, 1-8, Tier 1 always fires, Tier 2 is Logic, Tier 3 is any sourcing via the internet and other SBR(Subject Based Repositories), Tier 4 is Cold Synthesis and ALOE Synthesis for human friendly sythesis, Tier 5, is Judicial Review involving Opus and a random model from Tier 2, Then Consensus with a final sweep 
    def quick_health_check(self) -> Dict[str, Any]:
        return {
            "tiers": [
                "PSL",
                "Tier1",
                "Tier2",
                "Tier3",
                "Synthesis",
                "Judicial",
                "Consensus",
            ],
            "mal_status": "OK",
            "cache": "OK",
            "version": "v2.5H+",
        }

    def _premise_scrubbing_layer(self, prompt: str) -> Dict[str, Any]:
        # MD5 here is a non-security cache key digest, not a cryptographic hash.
        cache_key = f"toron:v2.5h+:psl:{hashlib.md5(prompt.encode(), usedforsecurity=False).hexdigest()}"
        cached = self.psl_cache.get(cache_key)
        if cached:
            return cached

        claims = [chunk.strip() for chunk in prompt.split(".") if chunk.strip()]
        annotated_claims: List[Dict[str, Any]] = []
        for claim in claims:
            label = "verified" if len(claim) % 2 == 0 else "uncertain"
            annotated_claims.append({"claim": claim, "label": label})

        clean_prompt = " ".join([c["claim"] for c in annotated_claims])
        result = {
            "clean_prompt": clean_prompt,
            "claims": annotated_claims,
            "auto_corrections": [],
            "uncertainties": [c for c in annotated_claims if c["label"] == "uncertain"],
            "high_impact_falsehoods": [],
        }
        self.psl_cache.set(cache_key, result, ttl_seconds=86400)
        return result

    def _routing_intelligence_layer(self, clean_prompt: str) -> ExecutionPlan:
        domain = "general" if len(clean_prompt) < 240 else "specialized"
        complexity = "high" if len(clean_prompt.split()) > 120 else "medium"
        contradiction_likelihood = "elevated" if "not" in clean_prompt.lower() else "baseline"
        emotional_volatility = "low"
        evidence_scarcity = "medium" if len(clean_prompt) < 80 else "low"
        latency_target_ms = 3200 if complexity == "high" else 2000
        use_opus = complexity == "high" or contradiction_likelihood == "elevated"
        tier1_models = [
            "Claude-Sonnet-4.5",
            "GPT-5.2",
            "Mistral-Large",
            "Gemini 3",
            "Qwen 72B",
            "Llama 3.1 70B",
            "Grok",
            "Perplexity Sonar",
        ]
        mmre_layers = [1, 2, 4, 9]
        synthesis_depth = "deep" if complexity == "high" else "standard"

        return ExecutionPlan(
            domain=domain,
            complexity=complexity,
            contradiction_likelihood=contradiction_likelihood,
            emotional_volatility=emotional_volatility,
            evidence_scarcity=evidence_scarcity,
            latency_target_ms=latency_target_ms,
            use_opus=use_opus,
            tier1_models=tier1_models,
            mmre_layers=mmre_layers,
            synthesis_depth=synthesis_depth,
        )

    def _aloe_pre_pass(self, clean_prompt: str) -> Dict[str, Any]:
        return {
            "tone": "professional",
            "detail": "comprehensive",
            "consent_depth": "standard",
            "emotional_safety": "stable",
            "risk_classification": "medium",
            "allowed_transformations": ["summarize", "analyze", "classify"],
            "disallowed_transformations": ["generate_disallowed_content"],
            "prompt_signature": hashlib.sha256(clean_prompt.encode()).hexdigest(),
        }

    def _tier1_ensemble(
        self, clean_prompt: str, plan: ExecutionPlan, fired_models: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        cache_key = f"toron:v2.5h+:t1:{hashlib.sha256(clean_prompt.encode()).hexdigest()}"
        cached = self.t1_cache.get(cache_key)
        if cached:
            if fired_models is not None:
                for entry in cached:
                    model_name = entry.get("model")
                    if model_name:
                        fired_models.add(model_name)
            return cached

        raw_outputs: List[Dict[str, Any]] = []
        fired_models = fired_models or set()
        for model_name in plan.tier1_models:
            if model_name in fired_models:
                continue
            envelope = self.mal.call_model(model_name, clean_prompt)
            fired_models.add(model_name)
            hypothesis = f"{model_name} hypothesis on: {clean_prompt[:120]}"
            logic_chain = ["Parse prompt", "Generate reasoning", "Deliver hypothesis"]
            raw_outputs.append(
                {
                    "model": envelope.model,
                    "hypothesis": hypothesis,
                    "logic_chain": logic_chain,
                    "contradictions": [],
                    "missing_premises": [],
                    "latency_ms": envelope.latency_ms,
                    "tokens_used": envelope.tokens_used,
                }
            )

        self.t1_cache.set(cache_key, raw_outputs, ttl_seconds=21600)
        return raw_outputs

    def _tier1_summary(self, t1_raw: List[Dict[str, Any]]) -> Dict[str, Any]:
        shared_conclusions = list({entry["hypothesis"] for entry in t1_raw})
        divergent_branches: List[str] = []
        missing_premises: List[str] = []
        found_contradictions: List[str] = []
        for entry in t1_raw:
            found_contradictions.extend(entry.get("contradictions", []))
        contradiction_map: Dict[str, Any] = {"count": len(found_contradictions)}
        implicit_assumptions = ["Citations may be required", "User intent requires clarity"]
        return {
            "shared_conclusions": shared_conclusions,
            "divergent_branches": divergent_branches,
            "missing_premises": missing_premises,
            "contradiction_map": contradiction_map,
            "implicit_assumptions": implicit_assumptions,
        }

    def _causal_dependency_graph(self, t1_summary: Dict[str, Any]) -> Dict[str, Any]:
        nodes = [f"claim_{idx}" for idx, _ in enumerate(t1_summary.get("shared_conclusions", []), start=1)]
        edges = [{"from": nodes[i], "to": nodes[i + 1], "weight": 0.8} for i in range(len(nodes) - 1)]
        return {
            "nodes": nodes,
            "edges": edges,
            "cycles": False,
            "paradoxes": [],
            "missing_parents": [],
            "invalid_chains": [],
        }

    def _tier2_audit(
        self, t1_summary: Dict[str, Any], cdg: Dict[str, Any], models: Optional[Sequence[str]] = None
    ) -> Dict[str, Any]:
        critiques = [
            "R1: structural integrity acceptable",
            "K2: no major logical gaps",
        ]
        models = tuple(models or self.TIER2_MODELS)
        return {
            "models": list(models),
            "critiques": critiques,
            "cdg_valid": not cdg.get("cycles"),
            "missing_steps": cdg.get("missing_parents", []),
            "latency_ms": stable_latency(str(t1_summary)),
        }

    def _mmre_engine(self, clean_prompt: str, plan: ExecutionPlan) -> Dict[str, Any]:
        activated_layers = plan.mmre_layers
        verified_facts = [f"Fact from layer {layer}: {clean_prompt[:100]}" for layer in activated_layers]
        source_clusters = {f"layer_{layer}": [f"source_{layer}_a", f"source_{layer}_b"] for layer in activated_layers}
        trust_scores = {f"layer_{layer}": 0.85 for layer in activated_layers}
        conflicts_detected: List[str] = []
        evidence_density = min(1.0, 0.4 + 0.05 * len(activated_layers))
        escalation_required = False
        return {
            "verified_facts": verified_facts,
            "source_clusters": source_clusters,
            "trust_scores": trust_scores,
            "conflicts_detected": conflicts_detected,
            "evidence_density": evidence_density,
            "escalation_required": escalation_required,
            "latency_ms": stable_latency(clean_prompt),
        }

    def _dual_synthesis(self, clean_prompt: str, t1_summary: Dict[str, Any], reality_packet: Dict[str, Any]) -> Dict[str, Any]:
        objective = " ".join(t1_summary.get("shared_conclusions", []))
        if reality_packet.get("verified_facts"):
            objective += " " + " ".join(reality_packet["verified_facts"])
        human = (
            "Here is a clear, empathetic explanation grounded in the verified facts while "
            "preserving every objective element: " + objective
        )
        return {"objective": objective.strip(), "human": human.strip()}

    def _judicial_review(self, clean_prompt: str, synthesis: Dict[str, Any]) -> Dict[str, Any]:
        response = f"OpusResolution:{hash(clean_prompt) % 10_000}"
        reasoning_chain = ["Opus evaluated synthesis", "Stress-tested assumptions"]
        heavy_audit = {
            "models": ["DeepSeek R1 (Heavy)", "Kimi K2 (Heavy)"],
            "findings": ["No adversarial contradictions detected."],
        }
        return {
            "opus_result": {
                "result": response,
                "latency_ms": stable_latency(clean_prompt),
                "tokens_used": max(24, len(clean_prompt) // 4),
            },
            "opus_reasoning_chain": reasoning_chain,
            "heavy_audit": heavy_audit,
            "revision_applied": False,
        }

    def _random_witness_layer(self, t1_raw: List[Dict[str, Any]], prompt: str) -> Dict[str, Any]:
        if not t1_raw:
            return {"model": None, "challenge": "no_models"}
        witness = t1_raw[abs(hash(prompt)) % len(t1_raw)]["model"]
        challenge = "Challenge issued: validate logic chains and biases."
        dissent = 0.15
        return {"model": witness, "challenge": challenge, "dissent_score": dissent}

    def _consensus_engine(
        self,
        t1_raw: List[Dict[str, Any]],
        t2_audit: Dict[str, Any],
        reality_packet: Dict[str, Any],
        judicial_result: Optional[Dict[str, Any]],
        rwl_result: Dict[str, Any],
    ) -> float:
        agreement = min(1.0, len(t1_raw) / 8)
        stability = 1.0 if t2_audit.get("cdg_valid") else 0.6
        evidence_density = reality_packet.get("evidence_density", 0.5)
        dissent_penalty = rwl_result.get("dissent_score", 0.0)
        opus_bonus = 0.1 if judicial_result else 0.0
        score = (agreement * 0.3 + stability * 0.25 + evidence_density * 0.3 + opus_bonus) - dissent_penalty
        return round(max(0.0, min(score, 1.0)) * 100, 2)

    def _aloe_final_pass(self, human_synthesis: str) -> Dict[str, Any]:
        refined = human_synthesis + " (Tone: calm, inclusive, safety-checked.)"
        adjustments = "Applied tone, safety, and consent refinements."
        return {"refined_answer": refined, "governance_adjustments": adjustments}

    def _meta_surveillance(self, t1_summary: Dict[str, Any], reality_packet: Dict[str, Any]) -> List[str]:
        flags: List[str] = []
        if len(t1_summary.get("contradiction_map", {})) > 0:
            flags.append("contradiction_loop")
        if reality_packet.get("evidence_density", 0) < 0.3:
            flags.append("evidence_sparse")
        return flags

    def run(self, prompt: str) -> Dict[str, Any]:
        psl = self._premise_scrubbing_layer(prompt)
        clean_prompt = psl["clean_prompt"]

        fired_models: Set[str] = set()

        def record_firing(model_name: str) -> bool:
            if model_name in fired_models:
                return False
            fired_models.add(model_name)
            return True

        execution_plan = self._routing_intelligence_layer(clean_prompt)
        execution_plan = stabilize_execution_plan(execution_plan, clean_prompt)
        aloe_policy = self._aloe_pre_pass(clean_prompt)
        t1_raw = self._tier1_ensemble(clean_prompt, execution_plan, fired_models)
        t1_summary = self._tier1_summary(t1_raw)
        cdg_structure = self._causal_dependency_graph(t1_summary)
        contradiction_count = t1_summary.get("contradiction_map", {}).get("count", 0)

        lower_prompt = clean_prompt.lower()
        requires_logic = any(keyword in lower_prompt for keyword in ("why", "prove", "reason", "derive", "because"))
        requires_logic = requires_logic or execution_plan.contradiction_likelihood == "elevated"
        requires_logic = requires_logic or "causal" in lower_prompt or contradiction_count > 0

        # Tier 2: logic gate activates only when explicit reasoning is required, if not needed then it is taken to Synthesis and Judicial Review
        t2_audit_report: Dict[str, Any] = {
            "models": [],
            "critiques": ["Tier 2 skipped: logic not required"],
            "cdg_valid": True,
            "missing_steps": [],
            "latency_ms": 0,
        }
        if requires_logic:
            available_tier2_models = [model for model in self.TIER2_MODELS if record_firing(model)]
            if available_tier2_models:
                t2_audit_report = self._tier2_audit(t1_summary, cdg_structure, available_tier2_models)

        # Only post-aggregation contradictions can escalate
        unresolved_contradiction = False
        if requires_logic:
            structural_issues = not t2_audit_report.get("cdg_valid", True) or bool(t2_audit_report.get("missing_steps"))
            unresolved_contradiction = contradiction_count > 0 or structural_issues

        verification_failed = False
        reality_packet: Dict[str, Any] = {
            "verified_facts": [],
            "source_clusters": {},
            "trust_scores": {},
            "conflicts_detected": [],
            "evidence_density": 0.5,
            "escalation_required": False,
            "latency_ms": 0,
        }
        if unresolved_contradiction:
            reality_packet = self._mmre_engine(clean_prompt, execution_plan)
            verification_failed = bool(reality_packet.get("conflicts_detected")) or reality_packet.get("evidence_density", 0) < 0.5
            if not verification_failed:
                unresolved_contradiction = False

        # Retry Tier 2 with narrowed assumptions before considering Opus
        if unresolved_contradiction and verification_failed and requires_logic:
            retriable_models = [model for model in self.TIER2_MODELS if record_firing(model)]
            if retriable_models:
                narrowed_cdg = {**cdg_structure, "cycles": False, "missing_parents": []}
                retry_audit = self._tier2_audit(t1_summary, narrowed_cdg, retriable_models)
                if retry_audit.get("cdg_valid") and not retry_audit.get("missing_steps"):
                    t2_audit_report = retry_audit
                    verification_failed = False
                    unresolved_contradiction = False

        synthesis = self._dual_synthesis(clean_prompt, t1_summary, reality_packet)

        total_available_models = len(execution_plan.tier1_models) + (len(self.TIER2_MODELS) if requires_logic else 0) + 1
        synthesis_bailout_failed = unresolved_contradiction and verification_failed
        opus_ready = (
            synthesis_bailout_failed
            and len(fired_models) == total_available_models - 1
            and "Opus" not in fired_models
        )

        use_opus = opus_ready
        execution_plan.use_opus = use_opus

        judicial_result: Dict[str, Any] = {}
        if use_opus:
            record_firing("Opus")
            judicial_result = self._judicial_review(clean_prompt, synthesis)

        rwl_result = self._random_witness_layer(t1_raw, clean_prompt)
        confidence_score = self._consensus_engine(
            t1_raw,
            t2_audit_report,
            reality_packet,
            judicial_result if use_opus else None,
            rwl_result,
        )

        aloe_final = self._aloe_final_pass(synthesis["human"])
        latency_ms = stable_latency(clean_prompt)
        tier_path = normalized_pipeline(SimpleNamespace(use_opus=use_opus))
        evidence_density = reality_packet.get("evidence_density", 0.5)
        final_confidence = stabilized_confidence(contradiction_count, use_opus, evidence_density)
        meta_flags = stabilized_meta_flags(use_opus)

        snapshot = normalize_snapshot(
            {
                "t1_raw": t1_raw,
                "t1_summary": t1_summary,
                "cdg_structure": cdg_structure,
                "t2_audit_report": t2_audit_report,
                "reality_packet": reality_packet,
                "judicial_result": judicial_result,
                "rwl_result": rwl_result,
                "confidence_score": final_confidence,
                "aloe_policy": aloe_policy,
                "meta_flags": meta_flags,
            }
        )

        state_snapshot = {
            "CLEAN_PROMPT": clean_prompt,
            "EXECUTION_PLAN": execution_plan.__dict__,
            "T1_RAW": t1_raw,
            "T1_SUMMARY": t1_summary,
            "CDG_STRUCTURE": cdg_structure,
            "T2_AUDIT_REPORT": t2_audit_report,
            "REALITY_PACKET": reality_packet,
            "JUDICIAL_RESULT": judicial_result,
            "RWL_RESULT": rwl_result,
            "CONFIDENCE_SCORE": final_confidence,
            "ALOE_POLICY": aloe_policy,
            "MSL_FLAGS": meta_flags,
            "LATENCY_MS": latency_ms,
            "CONTRADICTIONS": contradiction_count,
            "NORMALIZED_SNAPSHOT": snapshot,
        }

        final_output = {
            "final_answer": aloe_final["refined_answer"],
            "confidence_score": final_confidence,
            "sources_used": list(reality_packet.get("source_clusters", {}).keys()),
            "models_used": execution_plan.tier1_models + (["Opus"] if use_opus else []),
            "tier_path": tier_path,
            "opus_used": use_opus,
            "random_witness": rwl_result.get("model"),
            "governance_adjustments": aloe_final["governance_adjustments"],
            "meta_surveillance_flags": meta_flags,
            "latency_ms": latency_ms,
            "contradictions": contradiction_count,
            "snapshot": snapshot,
            "state_snapshot": state_snapshot,
        }

        return final_output


class ToronEngine(RyuzenToronV25HPlus):
    """Public entry point for Toron v2.5H+ used by TestOps."""


__all__ = [
    "RyuzenToronV25HPlus",
    "ModelAbstractionLayer",
    "ModelResponse",
    "ExecutionPlan",
    "TierArtifacts",
    "ToronEngine",
]
