# Nazih

> Exam integrity from the network, with no camera in the room

**MENA Ignite Hackathon - GSMA Open Gateway - Theme 7: Open Innovation**

Two hours of webcam recording finds a face in a room and never asks which room. Nazih asks the network, streams nothing, and clears more students than it flags.

Online exams are policed by software that watches a student's camera and screen for two hours, and it still misses the biggest cheat: someone else sitting the paper from another city. Nazih uses the mobile network instead. It streams nothing, samples a few checks, and defends honest candidates whose connection drops as often as it catches anyone.

---

## Quick start

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000. You need no credentials, because the app starts in
`simulator` mode and every answer is tagged with its source.

Full instructions, including the Gemini planner and the live Nokia gateway, are
in **INSTRUCTIONS.md**. The design is in **ARCHITECTURE.md**.

## What it is

An AI agent that decides *which* CAMARA network check is worth making for a
given case, spends against a budget, refuses calls it has no consent for, and
explains every decision with the network answers behind it.

- **7 scenarios** ship with it, all reaching the outcome they claim
- **7 CAMARA APIs** on the Nokia Network-as-Code platform
- **69.2% cheaper** than calling every available check on every case
- **2 to 3 calls** per case, depending on what the case deserves

## Scenarios

- A sitting starts normally. Line confirmed, candidate at the declared address, quality reserved (expects `valid`)
- The candidate is 38 km from the address they declared. The attack a webcam cannot see (expects `flag`)
- The network answers PARTIAL at the address. Ordinary indoor uncertainty, recorded as unresolved (expects `note`)
- Handset and SIM both changed mid-exam. Random sample at minute 54 (expects `void`)
- Handset changed, SIM untouched. Random sample at minute 41 (expects `flag`)
- The session dropped and the cell is saturated. Minute 73 of a two-hour paper (expects `note`)
- The session died while the line was perfectly healthy. Reachable on data, cell uncongested, minute 88 (expects `flag`)

## CAMARA APIs used

| CAMARA API | What the agent asks it | Cost | Reveals |
| --- | --- | --- | --- |
| `number-verification` | Confirm the line on the phone | 1 | boolean |
| `location-verification` | Is the line inside this area | 2 | boolean |
| `device-swap` | Has the handset changed recently | 3 | boolean |
| `sim-swap` | Has the SIM changed recently | 3 | boolean |
| `device-status` | Can the line be reached | 1 | enum |
| `congestion-insights` | How loaded is the serving cell | 1 | enum |
| `quality-on-demand` | Reserve network quality for this line | 8 | mutates |

## The agent

```
planner proposes one call  ->  runtime checks allowlist, consent, budget
      ^                                        |
      |                                        v
  answer becomes a fact   <-   CAMARA call recorded with provenance
      |
      +--> planner submits a decision  ->  policy floor applied  ->  ledger
```

The planner is Google AI Studio (Gemini) through Pydantic AI when
`AGENT_PROVIDER=gemini` and a `GEMINI_API_KEY` are both set, and a deterministic
policy ladder otherwise. Pydantic AI returns a typed proposal only; the runtime
still holds the budget, allowlist and consent gate, and the policy holds a floor
the model cannot talk its way under.

## Tests

```bash
pytest -q
```

## What this does not do

- Nazih proves the candidate is at the declared address. It does not prove the room is empty, so a helper sitting beside them is invisible to it. For a final medical board a school should still add a short live human check.
- What it removes is the cheapest and most common attack, the paid expert somewhere else entirely - and two hours of bedroom recording for every weekly quiz and language test that never needed it.
- A device change mid-exam has an innocent explanation often enough that Nazih refers it rather than voiding on it. Some real handovers will therefore only ever be flagged.
- No decision here is final. Every output is a report for an exam board, and a product that automated that judgement would deserve the criticism proctoring software already gets.

## Layout

```
main.py            uvicorn entry point
app_spec.py        re-exports this product's spec
core/              shared platform: CAMARA client, agent, consent, ledger, UI
  camara.py        the eleven CAMARA API families, live + simulator
  simulator.py     deterministic network simulator
  agent.py         the agent loop, budget, guardrail
  tools.py         CAMARA tool registry with cost and reveal metadata
  consent.py       consent ledger enforced in the transport path
  ledger.py        SQLite decision ledger
  signals.py       CAMARA answers -> named facts
  server.py        FastAPI app
  webui.py         the operator console
idea/              this product: policy, scenarios, demo lines, copy
tests/             pytest suite
```

## Licence

MIT. See LICENSE.
