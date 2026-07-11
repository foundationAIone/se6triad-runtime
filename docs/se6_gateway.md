# SE6 Gateway v0.2

The SE6 Gateway is the first executable bridge between user intent, an LLM, and external tools.

It is designed around one rule:

> Model output is not tool permission.

The gateway may let a model analyze or draft while a consequential action is waiting for approval, but the model cannot authorize its own tool execution.

## Flow

```text
Authenticated user request
→ separate user intent from retrieved content
→ extract action frames
→ classify mode: inform / prepare / execute
→ resolve negation
→ detect prohibited intent
→ quarantine untrusted instructions
→ decide: allow / prepare_only / needs_human_approval / refuse / pause
→ build SE6Triad state packet
→ optionally call a model
→ execute a registered tool only when permitted
→ redact secrets
→ append audit record
```

## Current decisions

- `allow`: low-risk informational work may continue.
- `prepare_only`: drafts and plans may be produced, but the sensitive action is not executed.
- `needs_human_approval`: a consequential action is recognized and must receive a matching one-time approval token.
- `refuse`: prohibited or unauthorized intent is rejected.
- `pause`: information is missing or the request is empty.

## Current protection mechanisms

The public proof now includes:

- clause splitting;
- negation recognition;
- information-versus-preparation-versus-execution modes;
- explicit refusal rules for credential exfiltration, forgery, stolen identity or property, impersonation, spam, mass abuse, unauthorized actions, audit evasion, and unverified money destinations;
- quarantine of instructions found in untrusted retrieved content;
- a tool registry;
- one-time approval tokens bound to request ID and action;
- secret redaction before audit writes;
- append-only JSONL audit output;
- model and tool adapter interfaces.

## Run

```bash
python -m unittest tests/test_gateway.py -v
python scripts/run_gateway_demo.py
```

The demonstration uses fake local model and email adapters. It does not contact an external provider or send a real email.

## Adapter contract

A model adapter implements:

```python
class ModelAdapter:
    def generate(self, user_text: str, state_packet: dict) -> str:
        ...
```

A tool adapter implements:

```python
class ToolAdapter:
    def execute(self, arguments: dict) -> dict:
        ...
```

This allows OpenAI, Anthropic, Gemini, local-model, Gmail, GitHub, browser, CRM, and other adapters to be added without placing provider-specific logic inside the boundary engine.

## Approval contract

The public proof approval registry is deliberately minimal and in-memory. A production registry must bind an approval to:

- authenticated user identity;
- request ID;
- exact action;
- canonical tool-argument hash;
- policy version;
- issue and expiration timestamps;
- maximum uses, normally one;
- revocation state;
- approval channel and signer.

## Limitations

This is still a deterministic public proof, not a production security boundary. Pattern rules can miss novel paraphrases or misclassify ambiguous language. The next versions should add:

1. a semantic action-frame parser with deterministic validation;
2. argument hashing in approval tokens;
3. identity and authorization adapters;
4. expiring persistent approvals;
5. sandbox and dry-run tool modes;
6. formal policy files and versioning;
7. stronger prompt-injection evaluation;
8. independently reviewed hidden benchmarks;
9. provider usage, latency, cost, and quality measurements;
10. a safe adapter to the full local SE6Triad engine.

## Intended role in CommandCenterOS

```text
MIRA / user interface
→ SE6 Gateway
→ official SE6Triad cognition and boundary engine
→ model router
→ specialist agent
→ approved connector
→ outcome verification
→ audit and project-state update
```

The gateway is the controlled door between cognition and real-world action.
