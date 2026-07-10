# SE6Triad: A State-Loop Runtime for Agentic LLMs

SE6Triad is a runtime pattern for turning LLM systems from simple responders into structured, state-changing agent systems.

Core loop:

```text
Observe → Reflect → Classify → Constrain → Route → Act → Audit → Learn
```

The goal is to improve:

- context compression
- model routing
- agent coordination
- tool governance
- approval safety
- audit logging
- memory updates
- cost-to-value measurement

This project is tested through **CommandCenterOS**, an avatar-led AI CEO system where user intent is routed through agents, tools, approvals, memory, and economic feedback.

## Why this exists

Current agentic LLM systems often lose state, repeat large context, call tools with weak governance, and lack a clear model for approval, audit, and economic measurement.

SE6Triad proposes that every user request should become a **state transition**, not just a response.

```text
User intent
→ structured state packet
→ agent/tool routing
→ approval boundary
→ execution
→ audit log
→ memory update
→ cost-to-value measurement
→ next state
```

## Public proof demo contents

```text
se6triad-runtime/
  README.md
  PUBLIC_POST.md
  diagrams/
    se6triad-state-loop.mmd
    ccos-runtime-flow.mmd
  docs/
    one_page_memo.md
  examples/
    ccos_attention_workflow.json
    approval_audit_model.json
    ccos_agent_runtime_map.json
    se6_state_packet_example.json
  src/
    se6triad_runtime.py
  tests/
    compression_test.py
    runtime_demo.py
  results/
    compression_result.json
    runtime_demo_result.json
```

## Run the demo

This repo uses only the Python standard library.

```bash
python tests/compression_test.py
python tests/runtime_demo.py
```

## Cost-compression proof

The first proof compares a normal repeated-context prompt against a compressed SE6Triad state packet.

Expected result:

```text
Normal context estimate: 20,669 tokens
SE6Triad state packet estimate: 1,188 tokens
Estimated reduction: 94.25%
```

This is a **context-compression proof**, not yet a full production API billing proof. The next proof is a live API A/B test using real provider `usage` fields, latency, quality ratings, and cost.

## CommandCenterOS workflow example

User command:

> Launch attention for CommandCenterOS and get early users.

SE6Triad classifies this into:

- intent: attention + lead generation
- risks: public posting, outreach, unsupported claims
- tools needed: X, LinkedIn, YouTube, landing page, email list, analytics
- agents needed: Apollo, Kama, Saraswati, Morpheus, Dionysus, Nike, Lakshmi, Themis, Mnemosyne

Workflow:

1. Apollo scans trends and target communities.
2. Kama identifies the attention hook.
3. Saraswati writes posts and scripts.
4. Morpheus creates visuals.
5. Themis checks claims and approval rules.
6. Dionysus publishes approved content.
7. Nike captures leads.
8. Lakshmi measures value.
9. Mnemosyne logs results.
10. SE6Triad updates the next campaign state.

## Approval and audit principle

```text
Prepare automatically.
Execute with permission.
Audit everything.
Measure value.
```

Sensitive actions require explicit approval:

- moving money
- signing legal documents
- publishing publicly
- making phone calls
- creating accounts
- submitting forms
- sharing private data
- using high-risk credentials

## Builder question

If SE6Triad were implemented for agentic LLM systems, where should it live first?

1. Prompt protocol
2. Agent runtime
3. Model router
4. Memory layer
5. Tool governance layer
6. Open-source framework
7. Product layer like CommandCenterOS

## Positioning

SE6Triad is not another model. It is a proposed **state-loop runtime** for agentic LLM systems.

CommandCenterOS is the reference product built on top of that runtime: an AI CEO for life and business, where the user remains the owner and every major action is governed, audited, and measured.

## Codex handoff

A Codex-ready implementation task is included in [`CODEX_TASK.md`](CODEX_TASK.md).

Use Codex to polish this into a public GitHub repository, verify the scripts, improve docs, and prepare a PR with the smoke-test workflow.

## Static proof page

A simple static public proof page is included at:

```text
web/index.html
```

It can be used as a GitHub Pages landing page for the public proof demo.

## Full smoke test

```bash
python tests/compression_test.py
python tests/runtime_demo.py
python scripts/run_public_proof.py
```
