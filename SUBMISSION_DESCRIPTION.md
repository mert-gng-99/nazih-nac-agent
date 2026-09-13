## Nazih - Exam integrity from the network, with no camera in the room

Online exams are policed by software that watches a student's camera and screen for two hours, and it still misses the biggest cheat: someone else sitting the paper from another city. Nazih uses the mobile network instead. It streams nothing, samples a few checks, and defends honest candidates whose connection drops as often as it catches anyone.

### The problem

Two hours of webcam recording finds a face in a room and never asks which room. Nazih asks the network, streams nothing, and clears more students than it flags.

### What the prototype actually does

Nazih is a working web application with an operator console, a REST API, and
a live WebSocket feed of the agent's reasoning. Open it, click a scenario, and
you watch the agent choose CAMARA calls one at a time and then justify its
decision with the network answers behind it.

It runs in three modes. `simulator` needs no credentials and answers every
CAMARA call in the real CAMARA response shape, which is how the organisers
recommend demonstrating and how the test suite stays deterministic. `live`
calls the Nokia Network-as-Code gateway with your own key. `hybrid` uses live
where credentials allow and falls back per call. Every answer is tagged with
its source in the UI, so a simulated result can never pass itself off as a real
network answer.

### The AI agent layer

The agent is a planner over a CAMARA tool registry, not a script with an LLM
bolted on. Each tool in the registry carries its price, its typical latency and
how much it reveals about a person, and the planner is judged on choosing well:

1. The planner proposes one call, with a stated reason.
2. The runtime, never the model, checks it against the tool allowlist, the
   consent ledger and the remaining budget.
3. The CAMARA answer is recorded with full provenance and turned into a fact.
4. Repeat until the planner submits a decision, or the budget runs out.

The planner is Google AI Studio (Gemini) through **Pydantic AI**'s typed,
structured-output path. It is enabled by setting `AGENT_PROVIDER=gemini`
alongside a `GEMINI_API_KEY`. A model turn may only propose a next CAMARA check
or a decision; it cannot execute a network call itself. The runtime remains the
only executor of consent, the tool allowlist, argument filtering and budget.

Gemini is opt-in on both counts deliberately: a key sitting in the environment
should not be enough to start spending on a model. Otherwise a deterministic
policy planner implementing the same escalation ladder takes over, so the
prototype is demonstrable offline and CI has something stable to assert. If a
configured model cannot complete a turn, the finished case is explicitly
labelled `policy-fallback` with a bounded error reason. It is never presented
as a successful Gemini-planned decision.

**The guardrail is the part worth looking at.** The policy computes a floor for
every case from the facts alone. If the model proposes something less cautious
than the floor, the floor wins and the disagreement is written into the
decision record. A language model should choose which checks to buy; it should
not be able to clear a case the evidence says to escalate. There is a test for
exactly this.

### Results from the shipped scenarios

7 scenarios ship with the prototype, and all 7 reach the
outcome they claim. The demo and the test suite assert the same thing, so a
scenario drifting from the pitch is a build failure.

- Outcome levels reached: `valid`, `note`, `flag`, `void`
- CAMARA calls per case: 2 to 3 (average 2.3)
- Total spend across all scenarios: 41 units, against 133 if
  every available check were called on every case, a saving of 69.2%

| Scenario | Outcome | CAMARA calls | Spend |
| --- | --- | --- | --- |
| A sitting starts normally | `valid` | 3 | 11 |
| The candidate is 38 km from the address they declared | `flag` | 2 | 3 |
| The network answers PARTIAL at the address | `note` | 3 | 11 |
| Handset and SIM both changed mid-exam | `void` | 2 | 6 |
| Handset changed, SIM untouched | `flag` | 2 | 6 |
| The session dropped and the cell is saturated | `note` | 2 | 2 |
| The session died while the line was perfectly healthy | `flag` | 2 | 2 |

The cheapest case, *The candidate is 38 km from the address they declared*, resolves in 2 call(s). The
most expensive, *A sitting starts normally*, earns 3. That gap is the product:
an agent that calls everything on everyone is safe, useless and unaffordable.

### CAMARA APIs on Nokia Network as Code

`number-verification`, `location-verification`, `device-swap`, `sim-swap`, `device-status`, `congestion-insights`, `quality-on-demand`

| CAMARA API | What the agent asks it | Cost | Reveals |
| --- | --- | --- | --- |
| `number-verification` | Confirm the line on the phone | 1 | boolean |
| `location-verification` | Is the line inside this area | 2 | boolean |
| `device-swap` | Has the handset changed recently | 3 | boolean |
| `sim-swap` | Has the SIM changed recently | 3 | boolean |
| `device-status` | Can the line be reached | 1 | enum |
| `congestion-insights` | How loaded is the serving cell | 1 | enum |
| `quality-on-demand` | Reserve network quality for this line | 8 | mutates |

### Consent

CAMARA identity, location and geofencing APIs are only lawful with the consent
of the line owner, so consent is enforced in the transport path rather than
described in a policy document. An ungranted call raises before a request is
built.

Consent is taken at exam registration, per sitting, as a condition the student
sees in full, from the candidate, who owns the line and declares their own
exam address. Checks run inside the exam window only. Nothing is recorded
between checks and no location is ever retrieved, only verified. A candidate
who declines sits the exam under the institution's existing arrangement.
Consent to network checks must not be the only way to sit a paper.

You can prove this in the running app: press **Withdraw consent**, run the same
case again, and watch the agent get refused at the transport layer with zero
CAMARA calls made.

### What this does not do

- Nazih proves the candidate is at the declared address. It does not prove the room is empty, so a helper sitting beside them is invisible to it. For a final medical board a school should still add a short live human check.
- What it removes is the cheapest and most common attack, the paid expert somewhere else entirely - and two hours of bedroom recording for every weekly quiz and language test that never needed it.
- A device change mid-exam has an innocent explanation often enough that Nazih refers it rather than voiding on it. Some real handovers will therefore only ever be flagged.
- No decision here is final. Every output is a report for an exam board, and a product that automated that judgement would deserve the criticism proctoring software already gets.

### Who pays

- Universities, certification bodies and training providers paying per sitting
- Three buyers inside one school: the privacy officer wants less data, the finance office wants a lower price than proctoring, the students want the camera gone
- Mobile operators, who earn per API call

### Verification

Run `pytest -q` in the repository. The suite covers the CAMARA transport and
its provenance, the consent gate, budget enforcement, the tool allowlist, the
guardrail floor overruling an over-confident model, the LLM planner loop
against a scripted model, the full HTTP surface, and every shipped scenario.
