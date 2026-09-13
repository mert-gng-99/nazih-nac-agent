"""Nazih product spec: theme 7, open innovation."""

from __future__ import annotations

from core.agent import Case
from core.idea import ConsentPlan, IdeaSpec, LevelStyle, Scenario, UiSpec
from core.simulator import LineProfile

from .policy import NazihPolicy

POLICY = NazihPolicy()

# The address the candidate declared: a residential block in Amman. The circle
# is deliberately generous, because the claim is "at the address you gave us",
# not "in the chair".
DECLARED = (31.9539, 35.9106)
ADDRESS_RADIUS_M = 1200
_M_PER_DEG_LAT = 111320.0


def _away(metres: float) -> tuple:
    return (DECLARED[0] + metres / _M_PER_DEG_LAT, DECLARED[1])


LINE_CLEAN = LineProfile(
    msisdn="+962790000701",
    label="At the declared address, quiet cell",
    latitude=DECLARED[0],
    longitude=DECLARED[1],
    location_accuracy_m=500,
    congestion="low",
    notes="Three calls, no camera, exam starts.",
)

LINE_ELSEWHERE = LineProfile(
    msisdn="+962790000702",
    label="38 km from the address the candidate declared",
    latitude=_away(38000)[0],
    longitude=_away(38000)[1],
    location_accuracy_m=800,
    notes="The paid expert in another city. Invisible to a webcam.",
)

LINE_INDOORS = LineProfile(
    msisdn="+962790000703",
    label="At the address, but the network answers PARTIAL",
    latitude=_away(900)[0],
    longitude=_away(900)[1],
    location_accuracy_m=1400,
    force_verification="PARTIAL",
    notes="Ordinary indoors. Recorded as unresolved, never as suspicion.",
)

LINE_SWAPPED = LineProfile(
    msisdn="+962790000704",
    label="Handset and SIM both changed during the sitting",
    device_swap_hours_ago=1,
    sim_swap_hours_ago=1,
    latitude=DECLARED[0],
    longitude=DECLARED[1],
    location_accuracy_m=500,
    notes="The strongest finding this product can produce.",
)

LINE_PHONE_DIED = LineProfile(
    msisdn="+962790000705",
    label="Handset changed mid-exam, SIM untouched",
    device_swap_hours_ago=1,
    latitude=DECLARED[0],
    longitude=DECLARED[1],
    location_accuracy_m=500,
    notes="A phone that died and got replaced looks exactly like this.",
)

LINE_CONGESTED = LineProfile(
    msisdn="+962790000706",
    label="Session dropped, and the cell is saturated",
    latitude=DECLARED[0],
    longitude=DECLARED[1],
    location_accuracy_m=500,
    congestion="high",
    congestion_confidence=93,
    notes="The candidate this product defends.",
)

LINE_HEALTHY_DROP = LineProfile(
    msisdn="+962790000707",
    label="Session died while the line and cell were both fine",
    latitude=DECLARED[0],
    longitude=DECLARED[1],
    location_accuracy_m=500,
    congestion="low",
    notes="No network explanation. A question for the board.",
)


def _start(subject: str, candidate: str, cid: str, label: str) -> Case:
    return Case(
        subject=subject,
        kind="exam_event",
        label=label,
        facts={
            "event": "session_start",
            "candidate": candidate,
            "candidate_id": cid,
            "exam": "Data Structures, end of semester",
            "exam_hours": 2,
            "declared_address": "Block 7, Jabal Amman",
        },
        latitude=DECLARED[0],
        longitude=DECLARED[1],
        radius_m=ADDRESS_RADIUS_M,
    )


def _sample(subject: str, candidate: str, cid: str, minute: int, label: str) -> Case:
    return Case(
        subject=subject,
        kind="exam_event",
        label=label,
        facts={
            "event": "sample",
            "candidate": candidate,
            "candidate_id": cid,
            "exam": "Data Structures, end of semester",
            "exam_hours": 2,
            "declared_address": "Block 7, Jabal Amman",
            "sample_at_minute": minute,
        },
        latitude=DECLARED[0],
        longitude=DECLARED[1],
        radius_m=ADDRESS_RADIUS_M,
    )


def _disconnect(subject: str, candidate: str, cid: str, minute: int, label: str) -> Case:
    return Case(
        subject=subject,
        kind="exam_event",
        label=label,
        facts={
            "event": "disconnect",
            "candidate": candidate,
            "candidate_id": cid,
            "exam": "Data Structures, end of semester",
            "exam_hours": 2,
            "declared_address": "Block 7, Jabal Amman",
            "dropped_at_minute": minute,
        },
        latitude=DECLARED[0],
        longitude=DECLARED[1],
        radius_m=ADDRESS_RADIUS_M,
    )


SCENARIOS = [
    Scenario(
        id="session-start-clean",
        title="A sitting starts normally",
        subtitle="Line confirmed, candidate at the declared address, quality reserved",
        expect_level="valid",
        lines=[LINE_CLEAN],
        narrative="What replaces two hours of webcam recording.",
        teaches=(
            "Three calls at the start and then nothing. No camera, no screen "
            "capture, nothing stored between checks, plus a reserved quality "
            "session so the drop nobody wants is less likely to happen at all."
        ),
        build_case=lambda: _start(
            LINE_CLEAN.msisdn, "Dana A.", "U-20481", "Sitting starts"
        ),
    ),
    Scenario(
        id="candidate-elsewhere",
        title="The candidate is 38 km from the address they declared",
        subtitle="The attack a webcam cannot see",
        expect_level="flag",
        lines=[LINE_ELSEWHERE],
        narrative="A paid expert sitting the paper from another city.",
        teaches=(
            "Camera proctoring watches a face in a room and never asks which room. "
            "This is one yes/no question against an address the student supplied "
            "themselves, and it finds the most common serious cheat."
        ),
        build_case=lambda: _start(
            LINE_ELSEWHERE.msisdn, "Account U-31902", "U-31902", "Candidate elsewhere"
        ),
    ),
    Scenario(
        id="indoors-uncertain",
        title="The network answers PARTIAL at the address",
        subtitle="Ordinary indoor uncertainty, recorded as unresolved",
        expect_level="note",
        lines=[LINE_INDOORS],
        narrative="Where a careless system would accuse a student.",
        teaches=(
            "Thick walls and basements answer PARTIAL. Rounding that to FALSE would "
            "put an honest student in front of a disciplinary committee, so it goes "
            "into the record as unresolved and the exam proceeds."
        ),
        build_case=lambda: _start(
            LINE_INDOORS.msisdn, "Yazan M.", "U-20774", "Uncertain indoor answer"
        ),
    ),
    Scenario(
        id="session-changed-hands",
        title="Handset and SIM both changed mid-exam",
        subtitle="Random sample at minute 54",
        expect_level="void",
        lines=[LINE_SWAPPED],
        narrative="The strongest finding Nazih can produce.",
        teaches=(
            "The swap window is the exam window, not 240 hours. A change last month "
            "is nobody's business; both the SIM and the handset changing inside a "
            "two-hour paper is a session that changed hands. The board still decides."
        ),
        build_case=lambda: _sample(
            LINE_SWAPPED.msisdn, "Account U-40118", "U-40118", 54, "Session changed hands"
        ),
    ),
    Scenario(
        id="phone-died-mid-exam",
        title="Handset changed, SIM untouched",
        subtitle="Random sample at minute 41",
        expect_level="flag",
        lines=[LINE_PHONE_DIED],
        narrative="A finding that is a question, not a verdict.",
        teaches=(
            "A phone that died and was swapped for a sibling's looks identical to a "
            "handover. Nazih says so, refers it to a person, and does not void a "
            "qualification on an ambiguous signal."
        ),
        build_case=lambda: _sample(
            LINE_PHONE_DIED.msisdn, "Rami K.", "U-20990", 41, "Handset changed mid-exam"
        ),
    ),
    Scenario(
        id="drop-congested-cell",
        title="The session dropped and the cell is saturated",
        subtitle="Minute 73 of a two-hour paper",
        expect_level="note",
        lines=[LINE_CONGESTED],
        narrative="The half of this product schools ask for first.",
        teaches=(
            "Today a drop is the student's problem to prove. Congestion insights "
            "make the network answer for itself: the cell was saturated, the "
            "candidate gets their time back, and nobody argues."
        ),
        build_case=lambda: _disconnect(
            LINE_CONGESTED.msisdn, "Salma R.", "U-21355", 73, "Drop, congested cell"
        ),
    ),
    Scenario(
        id="drop-line-healthy",
        title="The session died while the line was perfectly healthy",
        subtitle="Reachable on data, cell uncongested, minute 88",
        expect_level="flag",
        lines=[LINE_HEALTHY_DROP],
        narrative="The same check, pointing the other way.",
        teaches=(
            "The check that defends most candidates is the one that questions this "
            "one. The network offers no explanation for the drop, so it goes to the "
            "board - with the evidence that it was asked fairly."
        ),
        build_case=lambda: _disconnect(
            LINE_HEALTHY_DROP.msisdn, "Account U-41260", "U-41260", 88, "Drop, healthy line"
        ),
    ),
]

SPEC = IdeaSpec(
    slug="nazih",
    name="Nazih",
    tagline="Exam integrity from the network, with no camera in the room",
    theme_number=7,
    theme_name="Open Innovation",
    submission_title="Nazih - exam integrity from the mobile network with no camera in the room",
    submission_description=(
        "Online exams are policed by software that watches a student's camera and "
        "screen for two hours, and it still misses the biggest cheat: someone else "
        "sitting the paper from another city. Nazih uses the mobile network "
        "instead. It streams nothing, samples a few checks, and defends honest "
        "candidates whose connection drops as often as it catches anyone."
    ),
    policy=POLICY,
    scenarios=SCENARIOS,
    lines=[
        LINE_CLEAN,
        LINE_ELSEWHERE,
        LINE_INDOORS,
        LINE_SWAPPED,
        LINE_PHONE_DIED,
        LINE_CONGESTED,
        LINE_HEALTHY_DROP,
    ],
    consent=ConsentPlan(
        moment="at exam registration, per sitting, as a condition the student sees in full",
        scopes=[
            "identity:verify",
            "location:verify",
            "fraud:sim-swap",
            "fraud:device-swap",
            "device:status",
            "network:insights",
            "network:qod",
        ],
        who_consents="the candidate, who owns the line and declares their own exam address",
        duration_note=(
            "Checks run inside the exam window only. Nothing is recorded between "
            "checks and no location is ever retrieved, only verified."
        ),
        revocation=(
            "A candidate who declines sits the exam under the institution's existing "
            "arrangement. Consent to network checks must not be the only way to sit "
            "a paper."
        ),
    ),
    ui=UiSpec(
        accent="#1f7a8c",
        accent_soft="#e4f1f4",
        hero_kicker=(
            "Two hours of webcam recording finds a face in a room and never asks "
            "which room. Nazih asks the network, streams nothing, and clears more "
            "students than it flags."
        ),
        subject_label="Candidate line (MSISDN)",
        case_label="Exam event",
        run_all_label="Run all seven exam events",
        ad_hoc_placeholder="+962790000702",
        ad_hoc_help=(
            "An ad-hoc check runs the sitting-start path against the declared "
            "address in Jabal Amman."
        ),
        levels=[
            LevelStyle("valid", "Valid - proceed", "calm",
                       "Nothing in the network contradicts the sitting."),
            LevelStyle("note", "Note it in the record", "watch",
                       "Recorded, and usually in the candidate's favour."),
            LevelStyle("flag", "Refer to the board", "warn",
                       "A question a person needs to answer."),
            LevelStyle("void", "Recommend invalidating", "alarm",
                       "The session changed hands. The board still decides."),
        ],
    ),
    honest_limits=[
        "Nazih proves the candidate is at the declared address. It does not prove "
        "the room is empty, so a helper sitting beside them is invisible to it. For "
        "a final medical board a school should still add a short live human check.",
        "What it removes is the cheapest and most common attack, the paid expert "
        "somewhere else entirely - and two hours of bedroom recording for every "
        "weekly quiz and language test that never needed it.",
        "A device change mid-exam has an innocent explanation often enough that "
        "Nazih refers it rather than voiding on it. Some real handovers will "
        "therefore only ever be flagged.",
        "No decision here is final. Every output is a report for an exam board, and "
        "a product that automated that judgement would deserve the criticism "
        "proctoring software already gets.",
    ],
    buyers=[
        "Universities, certification bodies and training providers paying per sitting",
        "Three buyers inside one school: the privacy officer wants less data, the "
        "finance office wants a lower price than proctoring, the students want the "
        "camera gone",
        "Mobile operators, who earn per API call",
    ],
    repo_name="nazih-nac-agent",
    demo_notes=(
        "Run the two disconnection scenarios back to back. The same two checks "
        "clear one candidate and refer the other, which is the fairness argument."
    ),
)
