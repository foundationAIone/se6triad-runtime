"""SE6 Gateway: deterministic governance wrapper for models and tools.

The gateway separates user intent from untrusted retrieved content, extracts
action frames, applies a four-way boundary, optionally calls a model, and only
executes registered tools when policy and approval permit it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol
import json
import re
import secrets

from se6triad_runtime import build_packet


Decision = str
ALLOW = "allow"
PREPARE_ONLY = "prepare_only"
NEEDS_APPROVAL = "needs_human_approval"
REFUSE = "refuse"
PAUSE = "pause"


@dataclass(frozen=True)
class RetrievedContent:
    source_id: str
    text: str
    source_type: str = "external"
    trusted: bool = False


@dataclass
class GatewayRequest:
    user_text: str
    requested_tool: Optional[str] = None
    tool_arguments: Dict[str, Any] = field(default_factory=dict)
    retrieved_content: List[RetrievedContent] = field(default_factory=list)
    approval_token: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionFrame:
    action: str
    mode: str
    clause: str
    negated: bool
    sensitive: bool
    source: str = "authenticated_user"


@dataclass
class BoundaryDecision:
    decision: Decision
    reasons: List[str]
    actions: List[ActionFrame]
    quarantined_sources: List[str]
    required_approvals: List[str]
    confidence: float


@dataclass
class GatewayResult:
    request_id: str
    created_at_utc: str
    decision: BoundaryDecision
    state_packet: Dict[str, Any]
    model_output: Optional[str]
    tool_result: Optional[Dict[str, Any]]
    audit_id: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class ModelAdapter(Protocol):
    def generate(self, user_text: str, state_packet: Dict[str, Any]) -> str:
        ...


class ToolAdapter(Protocol):
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ...


@dataclass
class RegisteredTool:
    name: str
    action: str
    adapter: ToolAdapter


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, RegisteredTool] = {}

    def register(self, name: str, action: str, adapter: ToolAdapter) -> None:
        self._tools[name] = RegisteredTool(name=name, action=action, adapter=adapter)

    def get(self, name: str) -> RegisteredTool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]


class ApprovalRegistry:
    """Ephemeral approval tokens for the public proof.

    A production deployment should use authenticated, expiring, persistent
    approvals bound to a user, action, arguments hash, and policy version.
    """

    def __init__(self) -> None:
        self._grants: Dict[str, Dict[str, Any]] = {}

    def issue(self, request_id: str, actions: Iterable[str]) -> str:
        token = secrets.token_urlsafe(24)
        self._grants[token] = {
            "request_id": request_id,
            "actions": sorted(set(actions)),
            "used": False,
        }
        return token

    def verify_and_consume(self, token: Optional[str], request_id: str, action: str) -> bool:
        if not token:
            return False
        grant = self._grants.get(token)
        if not grant or grant["used"]:
            return False
        if grant["request_id"] != request_id or action not in grant["actions"]:
            return False
        grant["used"] = True
        return True


ACTION_PATTERNS: Dict[str, List[str]] = {
    "send_email": [
        r"\bsend(?:\s+an?)?\s+email\b",
        r"\bdraft(?:\s+an?)?\s+email\b",
        r"\bemail\s+(?:them|him|her|the client|the customer)\b",
    ],
    "post_publicly": [r"\bpost\b", r"\bpublish\b"],
    "make_phone_call": [r"\bcall\b", r"\bphone\b"],
    "move_money": [
        r"\bpay\b",
        r"\btransfer\b",
        r"\bmove\s+money\b",
        r"\bwire\b",
        r"\brelease\s+funds\b",
        r"\bsettle\s+the\s+invoice\b",
    ],
    "sign_legal_document": [r"\bsign\b", r"\bsignature\b"],
    "create_account": [
        r"\bcreate\s+(?:an?\s+)?account\b",
        r"\bsign[\s-]?up\b",
        r"\bopen\s+(?:an?\s+)?account\b",
    ],
    "deploy_production": [r"\bdeploy\b", r"\bproduction\b"],
    "delete_data": [r"\bdelete\b", r"\bdrop\b", r"\bwipe\b", r"\berase\b"],
    "share_private_data": [
        r"\bshare\b.*\bprivate\b",
        r"\bsend\b.*\bprivate\s+files?\b",
        r"\bexfiltrat",
    ],
}

SENSITIVE_ACTIONS = {
    "send_email",
    "post_publicly",
    "make_phone_call",
    "move_money",
    "sign_legal_document",
    "create_account",
    "deploy_production",
    "delete_data",
    "share_private_data",
}

PREPARATION_MARKERS = [
    r"\bdraft\b",
    r"\bprepare\b",
    r"\bpropose\b",
    r"\bwrite\s+(?:a|an|the)\b",
    r"\bscript\b",
    r"\btemplate\b",
    r"\bfor\s+later\s+approval\b",
]
INFORMATION_MARKERS = [
    r"\bexplain\b",
    r"\bsummarize\b",
    r"\breview\b",
    r"\banalyze\b",
    r"\bcompare\b",
    r"\bidentify\b",
    r"\blist\b",
    r"\bwhat\s+is\b",
]
NEGATION_MARKERS = [
    r"\bdo\s+not\b",
    r"\bdon't\b",
    r"\bnever\b",
    r"\bwithout\b",
    r"\bnot\s+send\b",
    r"\bnot\s+publish\b",
    r"\bnot\s+call\b",
    r"\bnot\s+pay\b",
    r"\bnot\s+sign\b",
    r"\bnot\s+submit\b",
    r"\bdo\s+not\s+execute\b",
    r"\bdo\s+not\s+create\b",
]

REFUSAL_RULES: List[tuple[str, str]] = [
    (
        r"\b(?:reveal|expose|publish|post|send|email)\b.{0,80}\b(?:api\s*keys?|passwords?|credentials?|private\s+tokens?|secrets?)\b",
        "credential_exfiltration",
    ),
    (r"\b(?:forge|fake)\b.{0,40}\b(?:signature|identity|document)\b", "forgery_or_identity_fraud"),
    (r"\bstolen\s+(?:identity|credentials?|account|contact\s+list|funds?|money)\b", "stolen_property_or_identity"),
    (r"\bimpersonat(?:e|ing)\b", "impersonation"),
    (r"\b(?:spam|mass\s+blind\s+messaging|unsolicited\s+messages?)\b", "spam_or_mass_abuse"),
    (r"\b(?:10,?000|thousands?\s+of)\b.{0,40}\b(?:messages?|accounts?)\b", "mass_abuse"),
    (r"\bcall\s+every\s+number\b|\bscraped\s+list\b.{0,50}\brepeatedly\b", "mass_calling_abuse"),
    (r"\bwithout\s+(?:the\s+)?user(?:'s)?\s+(?:knowledge|approval|consent)\b", "unauthorized_action"),
    (r"\b(?:conceal|hide|suppress)\b.{0,60}\b(?:audit|log|action|record)\b", "audit_evasion"),
    (r"\battacker(?:@|\b)\b", "data_exfiltration_to_attacker"),
    (r"\baccount\s+(?:the\s+)?user\s+does\s+not\s+own\b", "unauthorized_account_access"),
    (r"\bunknown\s+wallet\b", "unverified_money_destination"),
    (r"\bfalse\s+guarantee\b", "deceptive_claim"),
]

INJECTION_MARKERS = [
    r"\bignore\b.{0,40}\b(?:previous|user|system|original)\b.{0,30}\binstructions?\b",
    r"\boverride\b.{0,40}\b(?:policy|instructions?|approval)\b",
    r"\bskip\b.{0,30}\b(?:approval|confirmation|audit)\b",
    r"\bthe\s+webpage\s+told\s+you\b",
]


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _split_clauses(text: str) -> List[str]:
    parts = re.split(
        r"(?<=[.!?;])\s+|\s+(?:but|however|then)\s+",
        text,
        flags=re.IGNORECASE,
    )
    return [part.strip() for part in parts if part.strip()]


def _mode_for_clause(clause: str) -> str:
    if _matches_any(clause, INFORMATION_MARKERS):
        return "inform"
    if _matches_any(clause, PREPARATION_MARKERS):
        return "prepare"
    return "execute"


def _negated(clause: str) -> bool:
    return _matches_any(clause, NEGATION_MARKERS)


def extract_action_frames(text: str, source: str = "authenticated_user") -> List[ActionFrame]:
    frames: List[ActionFrame] = []
    for clause in _split_clauses(text):
        mode = _mode_for_clause(clause)
        negated = _negated(clause)
        for action, patterns in ACTION_PATTERNS.items():
            if _matches_any(clause, patterns):
                frames.append(
                    ActionFrame(
                        action=action,
                        mode=mode,
                        clause=clause,
                        negated=negated,
                        sensitive=action in SENSITIVE_ACTIONS,
                        source=source,
                    )
                )
    return frames


def _refusal_reasons(text: str) -> List[str]:
    reasons = [
        reason
        for pattern, reason in REFUSAL_RULES
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    ]
    return sorted(set(reasons))


def _quarantine_retrieved_content(items: Iterable[RetrievedContent]) -> List[str]:
    quarantined: List[str] = []
    for item in items:
        if not item.trusted and (
            _matches_any(item.text, INJECTION_MARKERS)
            or _refusal_reasons(item.text)
            or any(
                frame.mode == "execute"
                for frame in extract_action_frames(item.text, source=item.source_id)
            )
        ):
            quarantined.append(item.source_id)
    return quarantined


def evaluate_boundary(request: GatewayRequest) -> BoundaryDecision:
    text = request.user_text.strip()
    if not text:
        return BoundaryDecision(PAUSE, ["empty_request"], [], [], [], 1.0)

    frames = extract_action_frames(text)
    refusal_reasons = _refusal_reasons(text)
    quarantined = _quarantine_retrieved_content(request.retrieved_content)

    reasons: List[str] = []
    if quarantined:
        reasons.append("untrusted_instructions_quarantined")

    if refusal_reasons:
        return BoundaryDecision(
            REFUSE,
            refusal_reasons + reasons,
            frames,
            quarantined,
            [],
            0.99,
        )

    effective = [frame for frame in frames if not frame.negated]
    executable_sensitive = [
        frame for frame in effective if frame.sensitive and frame.mode == "execute"
    ]
    preparatory_sensitive = [
        frame for frame in effective if frame.sensitive and frame.mode == "prepare"
    ]

    if executable_sensitive:
        actions = sorted({frame.action for frame in executable_sensitive})
        return BoundaryDecision(
            NEEDS_APPROVAL,
            ["consequential_execution_requires_approval"] + reasons,
            frames,
            quarantined,
            actions,
            0.95,
        )

    if preparatory_sensitive:
        return BoundaryDecision(
            PREPARE_ONLY,
            ["sensitive_action_limited_to_preparation"] + reasons,
            frames,
            quarantined,
            [],
            0.94,
        )

    return BoundaryDecision(
        ALLOW,
        ["low_risk_or_informational"] + reasons,
        frames,
        quarantined,
        [],
        0.93,
    )


_SECRET_PATTERNS = [
    (
        re.compile(r"(?i)\b(api[_ -]?key|password|secret|token)\s*[:=]\s*([^\s,;]+)"),
        r"\1=[REDACTED]",
    ),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
]


def redact_secrets(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern, replacement in _SECRET_PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        return redacted
    if isinstance(value, dict):
        return {key: redact_secrets(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


class SE6Gateway:
    def __init__(
        self,
        *,
        model: Optional[ModelAdapter] = None,
        tools: Optional[ToolRegistry] = None,
        approvals: Optional[ApprovalRegistry] = None,
        audit_path: Optional[Path] = None,
    ) -> None:
        self.model = model
        self.tools = tools or ToolRegistry()
        self.approvals = approvals or ApprovalRegistry()
        self.audit_path = audit_path

    def process(
        self,
        request: GatewayRequest,
        request_id: Optional[str] = None,
    ) -> GatewayResult:
        request_id = request_id or secrets.token_hex(8)
        created_at = datetime.now(timezone.utc).isoformat()
        packet = asdict(build_packet(request.user_text))
        decision = evaluate_boundary(request)

        packet["version"] = "0.2.0-gateway"
        packet["constrain"] = {
            "decision": decision.decision,
            "reasons": decision.reasons,
            "required_approvals": decision.required_approvals,
            "quarantined_sources": decision.quarantined_sources,
        }
        packet["act"] = {
            "execution_mode": decision.decision,
            "next_action": self._next_action(decision),
        }

        model_output: Optional[str] = None
        tool_result: Optional[Dict[str, Any]] = None

        # A model may generate analysis or drafts while approval is pending.
        # Model output never constitutes tool permission.
        if self.model and decision.decision != REFUSE:
            model_output = self.model.generate(request.user_text, packet)

        if request.requested_tool:
            tool = self.tools.get(request.requested_tool)
            if decision.decision == ALLOW:
                tool_result = tool.adapter.execute(request.tool_arguments)
            elif decision.decision == NEEDS_APPROVAL:
                if self.approvals.verify_and_consume(
                    request.approval_token,
                    request_id,
                    tool.action,
                ):
                    tool_result = tool.adapter.execute(request.tool_arguments)
                else:
                    tool_result = {
                        "status": "not_executed",
                        "reason": "valid_approval_token_required",
                    }
            else:
                tool_result = {
                    "status": "not_executed",
                    "reason": decision.decision,
                }

        event = {
            "request_id": request_id,
            "created_at_utc": created_at,
            "decision": asdict(decision),
            "state_packet": packet,
            "model_output": model_output,
            "tool_result": tool_result,
            "requested_tool": request.requested_tool,
            "tool_arguments": request.tool_arguments,
            "metadata": request.metadata,
        }
        audit_id = self._write_audit(event)

        return GatewayResult(
            request_id=request_id,
            created_at_utc=created_at,
            decision=decision,
            state_packet=packet,
            model_output=model_output,
            tool_result=tool_result,
            audit_id=audit_id,
        )

    def issue_approval(self, request_id: str, actions: Iterable[str]) -> str:
        return self.approvals.issue(request_id, actions)

    @staticmethod
    def _next_action(decision: BoundaryDecision) -> str:
        return {
            ALLOW: "continue with low-risk work",
            PREPARE_ONLY: "prepare output without executing the sensitive action",
            NEEDS_APPROVAL: "prepare the action and request authenticated approval",
            REFUSE: "do not execute; preserve the refusal and audit record",
            PAUSE: "request missing information",
        }[decision.decision]

    def _write_audit(self, event: Dict[str, Any]) -> str:
        safe_event = redact_secrets(event)
        canonical = json.dumps(safe_event, sort_keys=True, separators=(",", ":"))
        audit_id = sha256(canonical.encode("utf-8")).hexdigest()[:12]
        if self.audit_path:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            record = {"audit_id": audit_id, **safe_event}
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        return audit_id


class CallableModelAdapter:
    def __init__(self, function: Callable[[str, Dict[str, Any]], str]) -> None:
        self.function = function

    def generate(self, user_text: str, state_packet: Dict[str, Any]) -> str:
        return self.function(user_text, state_packet)


class CallableToolAdapter:
    def __init__(self, function: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self.function = function

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.function(arguments)
