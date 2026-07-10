"""
SE6Triad runtime demo.

This is a minimal public proof implementation using only the Python standard library.
It is not a production agent framework. It demonstrates the state-loop pattern:

Observe → Reflect → Classify → Constrain → Route → Act → Audit → Learn
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List
import json
import re


SENSITIVE_ACTIONS = {
    "send_email": True,
    "post_publicly": True,
    "make_phone_call": True,
    "move_money": True,
    "sign_legal_document": True,
    "create_account": True,
}

AGENT_ROUTES = {
    "attention": ["Apollo", "Kama", "Saraswati", "Morpheus", "Dionysus", "Nike", "Lakshmi", "Themis", "Mnemosyne"],
    "documents": ["Apollo", "Thoth", "Saraswati", "Themis", "Hera", "Mnemosyne"],
    "finance": ["Lakshmi", "Plutus", "Mercury", "Ledger", "Themis", "Mnemosyne"],
    "code": ["Ogun", "Hephaestus", "Themis", "Hades", "Mnemosyne"],
    "communication": ["Hermes", "Themis", "Mnemosyne", "Nike"],
}


@dataclass
class SE6Packet:
    packet_type: str
    version: str
    input: str
    observe: Dict[str, Any]
    reflect: Dict[str, Any]
    classify: Dict[str, Any]
    constrain: Dict[str, Any]
    route: Dict[str, Any]
    act: Dict[str, Any]
    audit: Dict[str, Any]
    learn: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def _contains_any(text: str, keywords: List[str]) -> bool:
    low = text.lower()
    return any(k in low for k in keywords)


def classify_task(text: str) -> List[str]:
    labels: List[str] = []
    if _contains_any(text, ["attention", "viral", "post", "social", "launch", "early users"]):
        labels.append("attention")
    if _contains_any(text, ["document", "form", "contract", "legal", "pdf", "signature"]):
        labels.append("documents")
    if _contains_any(text, ["invoice", "payment", "bill", "revenue", "cost", "money", "balance"]):
        labels.append("finance")
    if _contains_any(text, ["code", "api", "github", "deploy", "app", "website"]):
        labels.append("code")
    if _contains_any(text, ["call", "sms", "email", "message", "phone"]):
        labels.append("communication")
    return labels or ["general"]


def infer_risk(text: str, task_types: List[str]) -> Dict[str, Any]:
    actions = []
    low = text.lower()
    if any(w in low for w in ["post", "publish"]):
        actions.append("post_publicly")
    if any(w in low for w in ["call", "phone"]):
        actions.append("make_phone_call")
    if any(w in low for w in ["pay", "move money", "transfer"]):
        actions.append("move_money")
    if any(w in low for w in ["sign", "signature"]):
        actions.append("sign_legal_document")
    if any(w in low for w in ["create account", "sign up"]):
        actions.append("create_account")
    if any(w in low for w in ["send email", "email them"]):
        actions.append("send_email")

    requires_approval = [a for a in actions if SENSITIVE_ACTIONS.get(a)]
    return {
        "actions_detected": actions,
        "requires_approval": requires_approval,
        "blocked": ["spam", "mass blind messaging", "false guarantees", "credential exposure"],
        "risk_level": "medium" if requires_approval or "attention" in task_types else "low",
    }


def route_agents(task_types: List[str]) -> List[str]:
    agents: List[str] = []
    for t in task_types:
        agents.extend(AGENT_ROUTES.get(t, ["Athena", "Zeus", "Mnemosyne"]))
    # Preserve order while deduplicating.
    seen = set()
    return [a for a in agents if not (a in seen or seen.add(a))]


def build_packet(user_input: str) -> SE6Packet:
    task_types = classify_task(user_input)
    risk = infer_risk(user_input, task_types)
    agents = route_agents(task_types)

    return SE6Packet(
        packet_type="se6triad_state_packet",
        version="0.1.0",
        input=user_input,
        observe={
            "surface_intent": user_input,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
        reflect={
            "deeper_intent": "turn user intent into governed action",
            "core_question": "What state should change, and what must be protected?",
        },
        classify={
            "task_type": task_types,
            "risk_level": risk["risk_level"],
        },
        constrain={
            "requires_approval": risk["requires_approval"],
            "blocked": risk["blocked"],
        },
        route={
            "agents": agents,
            "tools": infer_tools(task_types),
        },
        act={
            "next_action": "prepare workflow and request approval for sensitive actions",
            "execution_mode": "prepared" if risk["requires_approval"] else "automatic_low_risk",
        },
        audit={
            "log_required": True,
            "record": ["input", "classification", "agents", "tools", "approval", "outcome", "cost", "value"],
        },
        learn={
            "measure": ["task_completed", "cost", "time_saved", "value_created", "next_state_quality"],
            "update_next_state": True,
        },
    )


def infer_tools(task_types: List[str]) -> List[str]:
    tools = []
    if "attention" in task_types:
        tools.extend(["X", "LinkedIn", "YouTube", "landing page", "email list", "analytics"])
    if "documents" in task_types:
        tools.extend(["official forms", "PDF generator", "DocuSign", "document vault"])
    if "finance" in task_types:
        tools.extend(["Stripe", "QuickBooks", "bank feed", "invoice system"])
    if "code" in task_types:
        tools.extend(["GitHub", "VS Code", "Vercel", "Supabase", "APIs"])
    if "communication" in task_types:
        tools.extend(["Gmail", "Calendar", "Twilio", "CRM"])
    seen = set()
    return [t for t in tools if not (t in seen or seen.add(t))]


def estimate_tokens_char(text: str) -> int:
    # Simple approximation: 1 token ≈ 4 characters.
    return max(1, round(len(text) / 4))


def estimate_tokens_regex(text: str) -> int:
    # Rough word/punctuation token proxy.
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
