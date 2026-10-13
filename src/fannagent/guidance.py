"""Pinned research guidance for offline experiments, independent of a concrete backend."""

from __future__ import annotations

import json
from importlib.resources import files

from .errors import AgentError
from .store import canonical, digest

PROTOCOL_VERSION = 1
MAX_PRIMER_BYTES = 8192
MODES = {"baseline", "protocol_only", "guided"}
PROTOCOL = """Research experiment protocol v1:
Use fannagent-tool experiment 'JSON' to register a plan before count, descriptors, probe,
audit, labels, development_evaluate, or calibrate. Orientation tools and validate remain free.
Start with {"action":"start","plan":{"client_key":"unique-key",
"purpose":"investigation","hypothesis":"testable claim","why_now":"reason",
"basis":{"kind":"exploratory","principle_ids":[],"evidence_refs":[]},
"comparison":"what to compare","measurements":"what to measure",
"expected_observation":"expected result","challenging_observation":"contrary result",
"decision_if_supported":"next decision","decision_if_challenged":"alternative decision"}}.
Basis kind is literature, measurement, or exploratory. Literature uses IDs from the pinned
primer; measurement requires permitted development evidence. Do not invent citations.
Purpose is investigation, candidate_evaluation, or calibration. One experiment may span turns
and many measurements. Only one is open; measurements attach to it automatically.
Finish with {"action":"finish","client_key":"unique-key","conclusion":{
"assessment":"supported","observations":"concise findings","evidence_refs":["$latest"],
"decision":"what changes next"}}. Assessment is supported, challenged, or inconclusive.
Use returned event IDs or development artifact hashes as evidence. $latest selects the last
recorded observation. get accepts experiment_id or client_key; list returns bounded summaries.
State short scientific justifications, not private chain-of-thought. Record contrary findings.
Distinguish host measurements from Python-derived interpretation. A citation suggests a test;
it never proves that a rule works here. Choose your own experiments; no fixed sequence is required.
Finish an experiment containing accepted calibration for the exact policy before submit.
Keep calibration aggregates and final-test boundaries intact. Checkpoint recovery can still
freeze an eligible fallback if spending ends before your conclusion.
"""


def configured_mode(config):
    return config.research.mode if config.research else "baseline"


def render_primer(manifest, profile, capabilities):
    lines = [manifest["introduction"]]
    for principle in manifest["principles"]:
        lines.append(f"{principle['id']} ({principle['classification']}): {principle['claim']}")
        for citation in principle.get("citations", []):
            source = manifest["sources"][citation["source_id"]]
            lines.append(f"Source: {source['title']}, {citation['sections']}: {source['url']}")
        lines.append("Limit: " + principle["limit"])
        lines.append("Investigation: " + principle["investigation"])
    supported = set(capabilities.runtime_features)
    runtime = {
        name: feature for name, feature in profile.runtime_features.items() if name in supported
    }
    groups = sorted({feature.group for feature in runtime.values()})
    lines.append(
        "Backend applicability: use only available observations in the selected profile. "
        f"Available runtime collection groups: {', '.join(groups) or 'none'}. "
        "Read the feature registry for populations, scope, availability and collection cost. "
        "An offline membership reconstruction is not a live filter or queue-validity signal. "
        "Do not assume that every signal used by a paper is supported by this backend."
    )
    lines.extend([manifest["example"], manifest["interpretation"]])
    text = "\n\n".join(lines)
    if len(text.encode()) > MAX_PRIMER_BYTES:
        raise AgentError("research primer exceeds the 8 KiB text bound")
    return text


def read_guidance(store):
    state = store.get("research_guidance")
    if state is None:
        return {"mode": "baseline", "research_protocol_version": None}
    if state.get("research_protocol_version") != PROTOCOL_VERSION or state.get("mode") not in MODES:
        raise AgentError("unsupported research protocol; use a compatible agent package")
    if state["mode"] != "baseline":
        snapshot = store.read(state["snapshot"])
        if (
            snapshot["mode"] != state["mode"]
            or digest(snapshot["manifest"]) != state["primer_hash"]
        ):
            raise AgentError("research guidance identity changed")
    return state


def prepare_guidance(config, store, backend):
    mode = configured_mode(config)
    existing = store.get("research_guidance")
    if existing:
        state = read_guidance(store)
        if state["mode"] != mode:
            raise AgentError("research mode is immutable; use a new run")
        return state
    if mode == "baseline":
        return read_guidance(store)
    if store.get("trajectory"):
        raise AgentError("cannot add research guidance to an existing conversation; use a new run")
    manifest = (
        json.loads(files("fannagent").joinpath("assets/research_primer_v1.json").read_text())
        if mode == "guided"
        else {"version": 1, "sources": {}, "principles": []}
    )
    primer = (
        render_primer(manifest, backend.runtime_profile, backend.describe_capabilities())
        if mode == "guided"
        else ""
    )
    snapshot = {
        "view": "private_research_snapshot",
        "mode": mode,
        "manifest": manifest,
        "primer": primer,
        "protocol": PROTOCOL,
    }
    private = store.put("research_snapshot", snapshot)
    public = store.put(
        "research_guidance",
        {**snapshot, "view": "development_research_guidance"},
        scope="development",
    )
    state = {
        "mode": mode,
        "research_protocol_version": PROTOCOL_VERSION,
        "primer_hash": digest(manifest),
        "snapshot": private,
        "artifact": public,
    }
    store.set("research_guidance", state)
    return state


def system_guidance(store):
    state = read_guidance(store)
    if state["mode"] == "baseline":
        return ""
    snapshot = store.read(state["snapshot"])
    return "\n" + snapshot["protocol"] + "\n" + snapshot["primer"]


def principle_ids(store, classification=None):
    state = read_guidance(store)
    if state["mode"] != "guided":
        return set()
    return {
        p["id"]
        for p in store.read(state["snapshot"])["manifest"]["principles"]
        if classification is None or p["classification"] == classification
    }


def pin_prompt(store, system):
    state = read_guidance(store)
    if state["mode"] == "baseline":
        return {}
    fingerprint = digest(system)
    if state.get("system_prompt_hash") and state["system_prompt_hash"] != fingerprint:
        raise AgentError("saved research system prompt identity changed")
    if not state.get("system_prompt_hash"):
        store.set("research_guidance", {**state, "system_prompt_hash": fingerprint})
    return {
        "research_protocol_version": PROTOCOL_VERSION,
        "research_mode": state["mode"],
        "research_primer_hash": state["primer_hash"],
        "research_system_prompt_hash": fingerprint,
    }


def check_initial_bound(model_config, system, context):
    # BudgetedModel remains authoritative, including provider formatting/tool overhead.
    if model_config.model != "scripted" and (
        len(canonical({"system": system, "context": context})) > model_config.input_token_bound
    ):
        raise AgentError(
            "research startup context exceeds configured input bound; use a new "
            "configuration with a verified larger bound"
        )
