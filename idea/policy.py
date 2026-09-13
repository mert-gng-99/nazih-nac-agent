"""Nazih - exam integrity from the mobile network, with no camera in the room.

Universities and certification bodies moved exams online and were sold software
that watches the camera, the screen and the face for two hours. Students hate
it, face checking works badly in poor light and for some students, and privacy
rules in several countries make it hard to defend.

Meanwhile the biggest cheat is invisible on camera: a different person sitting
the exam from another city. And when a connection drops, nobody can tell a real
network failure from a candidate pulling the cable, so honest students are
punished for their own coverage.

Nazih uses the network instead, and the design is mostly about restraint:

*   It **streams nothing**. A few checks at random moments, and nothing recorded
    in between.
*   A **device or SIM change inside the exam window** is written down with its
    timestamp, because that is the clearest sign a session changed hands.
*   When the link breaks, it **defends the candidate as often as it accuses
    them**. Congestion and reachability say whether the network or the student
    caused it, and that is the half of the product schools ask for first.
*   Only a **person** ever decides that a student cheated. Nazih writes a report.

And it is honest about the boundary: Nazih proves the candidate is at the
declared address. It cannot prove the room is empty.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.agent import Case
from core.camara import ApiResult
from core.signals import read_signal

LEVELS = ["valid", "note", "flag", "void"]


class NazihPolicy:
    name = "nazih"
    kind = "exam_event"
    levels = LEVELS
    budget_units = 20.0

    tool_names = [
        "verify_number",
        "verify_location",
        "check_device_swap",
        "check_sim_swap",
        "check_reachability",
        "query_congestion",
        "reserve_quality",
    ]

    def system_prompt(self, case: Case) -> str:
        return (
            "You are Nazih, the integrity agent for an online exam. You handle "
            "three events: the start of a sitting, a random sample during it, and a "
            "disconnection.\n\n"
            "You never decide that a student cheated. An exam board decides; you "
            "write the report they read. Getting that boundary wrong would make "
            "this product indefensible.\n\n"
            "You stream nothing and record nothing between checks. Restraint is a "
            "feature you are selling, not a limitation to work around.\n\n"
            "How to work:\n"
            "1. At the start: confirm the line on the phone, then ask one yes/no "
            "question about the address the student themselves declared. Then "
            "reserve quality for the session, so the drop you would later have to "
            "explain does not happen in the first place.\n"
            "2. During the sitting: a device or SIM change inside the exam window "
            "is the clearest sign a session changed hands. Note the exact time.\n"
            "3. On a disconnection: find out whether the network or the student "
            "caused it. A saturated cell or an unreachable line defends the "
            "candidate. A perfectly healthy line whose session died is a question "
            "for the board.\n"
            "4. PARTIAL and UNKNOWN location answers are common indoors and are "
            "not evidence of anything. Record them as unresolved; never let them "
            "become an accusation.\n\n"
            "Your reports will be read by a nervous nineteen-year-old and by a "
            "committee. Write them so both can follow the reasoning."
        )

    def describe_case(self, case: Case) -> str:
        f = case.facts
        lines = [
            "Exam event: %s" % f.get("event", "session_start"),
            "  candidate: %s (%s)" % (f.get("candidate", "unknown"), f.get("candidate_id", "?")),
            "  exam: %s, %s hours" % (f.get("exam", "unknown"), f.get("exam_hours", "?")),
            "  address the candidate declared: %s" % f.get("declared_address", "not stated"),
            "  line: %s" % case.subject,
        ]
        if f.get("event") == "disconnect":
            lines.append("  minute of the exam when the session dropped: %s" % f.get("dropped_at_minute", "?"))
        if f.get("event") == "sample":
            lines.append("  minute of the exam: %s" % f.get("sample_at_minute", "?"))
        return "\n".join(lines)

    def interpret(self, tool: str, result: ApiResult, facts: Dict[str, Any]) -> Dict[str, Any]:
        return read_signal(tool, result)

    def next_tool(
        self, case: Case, facts: Dict[str, Any], used: List[str]
    ) -> Optional[Tuple[str, Dict[str, Any], str]]:
        event = case.facts.get("event", "session_start")
        if event == "sample":
            return self._sample(case, facts)
        if event == "disconnect":
            return self._disconnect(case, facts)
        return self._start(case, facts)

    def _start(self, case: Case, facts: Dict[str, Any]):
        if "number_verified" not in facts:
            return (
                "verify_number",
                {},
                "Confirm the line on the phone before the paper opens. One unit, "
                "and no camera has been switched on.",
            )
        if not facts.get("number_verified"):
            return None

        if "location_result" not in facts:
            return (
                "verify_location",
                {},
                "One yes/no question about the address the candidate declared "
                "themselves. No coordinates come back, so nothing is learned about "
                "where a student lives beyond what they already told us.",
            )

        if facts.get("location_outside"):
            return None  # the board needs to see this; no more spending helps

        if "qod_session_id" not in facts:
            return (
                "reserve_quality",
                {"profile": "QOS_M", "duration_s": int(case.facts.get("exam_hours", 2)) * 3600},
                "Reserve quality for the whole sitting. Preventing the drop is "
                "worth more than explaining it afterwards, and it is the part of "
                "this product students actually want.",
            )
        return None

    def _sample(self, case: Case, facts: Dict[str, Any]):
        window = int(case.facts.get("exam_hours", 2))
        if "device_swapped_in_window" not in facts:
            return (
                "check_device_swap",
                {"max_age_hours": window},
                "Look back only over the exam window (%dh). A handset change inside "
                "the sitting is the clearest sign the session changed hands; a "
                "change last month is none of our business." % window,
            )
        if facts.get("device_swapped_in_window") and "sim_swapped_in_window" not in facts:
            return (
                "check_sim_swap",
                {"max_age_hours": window},
                "The handset changed mid-exam. Check the SIM too, because both "
                "changing together is a different person sitting the paper.",
            )
        return None

    def _disconnect(self, case: Case, facts: Dict[str, Any]):
        if "reachability" not in facts:
            return (
                "check_reachability",
                {},
                "First question on any drop: can the line be reached at all. This "
                "is the call that defends honest candidates, and it costs one unit.",
            )
        if "congestion" not in facts:
            return (
                "query_congestion",
                {},
                "Ask how loaded the cell is. A saturated cell explains the drop and "
                "settles the matter in the candidate's favour.",
            )
        return None

    # -- the floor -----------------------------------------------------------

    def decide(self, case: Case, facts: Dict[str, Any]) -> Tuple[str, str, str, float]:
        event = case.facts.get("event", "session_start")
        if event == "sample":
            return self._decide_sample(case, facts)
        if event == "disconnect":
            return self._decide_disconnect(case, facts)
        return self._decide_start(case, facts)

    def _decide_start(self, case: Case, facts: Dict[str, Any]):
        f = case.facts
        candidate = f.get("candidate", "the candidate")
        address = f.get("declared_address", "the address they declared")

        if "number_verified" not in facts:
            return (
                "note",
                "Let the sitting proceed and record that no network check was possible",
                "No network evidence was available for this line, so Nazih adds "
                "nothing to this sitting either way.",
                0.35,
            )

        if not facts.get("number_verified"):
            return (
                "flag",
                "Let the sitting proceed, and put this in front of the board afterwards",
                "The network will not confirm that this line is in the phone "
                "starting the exam. That belongs in a report, but it is not grounds "
                "to throw a student out of a paper mid-sitting on a machine's word.",
                0.85,
            )

        if facts.get("location_outside"):
            return (
                "flag",
                "Refer to the board: the candidate is not at the address they declared",
                "%s declared %s, and the network places this line outside it. This "
                "is the attack the cameras never see - a paid expert sitting the "
                "paper from another city - and it is the board's decision, not ours."
                % (candidate, address),
                0.9,
            )

        if facts.get("location_uncertain"):
            return (
                "note",
                "Let the sitting proceed and record the location answer as unresolved",
                "The network answered %s, which is ordinary indoors and is not "
                "evidence of anything. It goes in the record as unresolved rather "
                "than as a suspicion against a student."
                % facts.get("location_result"),
                0.7,
            )

        reserved = " Quality is reserved for the sitting, so a drop is less likely to happen at all." if facts.get("qod_session_id") else ""
        return (
            "valid",
            "Start the exam",
            "The network confirms the line is in this phone and that the line is at "
            "the address %s declared. No camera, no screen recording, and nothing "
            "stored between checks.%s" % (candidate, reserved),
            0.92,
        )

    def _decide_sample(self, case: Case, facts: Dict[str, Any]):
        minute = case.facts.get("sample_at_minute", "mid-exam")
        if "device_swapped_in_window" not in facts:
            return (
                "note",
                "Record that the sample could not be taken",
                "No network evidence was available at this sample point.",
                0.35,
            )
        if facts.get("device_swapped_in_window") and facts.get("sim_swapped_in_window"):
            return (
                "void",
                "Recommend the board invalidate this sitting",
                "Both the handset and the SIM behind this candidate's line changed "
                "inside the exam window, at minute %s. Read together that is a "
                "session that changed hands, and it is the strongest finding this "
                "product can produce. The board still decides." % minute,
                0.92,
            )
        if facts.get("device_swapped_in_window"):
            return (
                "flag",
                "Refer to the board: the handset changed during the sitting",
                "The device behind this line changed inside the exam window while "
                "the SIM did not. A phone that died and was replaced mid-exam looks "
                "exactly like this, so it is a question for a person rather than a "
                "verdict.",
                0.82,
            )
        return (
            "valid",
            "Nothing to record from this sample",
            "Neither the handset nor the SIM changed during the exam window. The "
            "sample is taken and nothing is stored about the minutes around it.",
            0.9,
        )

    def _decide_disconnect(self, case: Case, facts: Dict[str, Any]):
        minute = case.facts.get("dropped_at_minute", "mid-exam")
        if "reachability" not in facts:
            return (
                "note",
                "Grant the candidate extra time and record the drop as unexplained",
                "No network evidence was available, so the benefit of the doubt is "
                "the only fair outcome.",
                0.4,
            )

        if facts.get("cell_saturated"):
            return (
                "note",
                "Grant extra time; the network caused this",
                "The session dropped at minute %s and the cell serving this "
                "candidate is saturated. This is the candidate's coverage failing, "
                "not the candidate cheating, and saying so is half of why a school "
                "buys this." % minute,
                0.9,
            )

        if facts.get("silent"):
            return (
                "note",
                "Grant extra time; the line itself went down",
                "The network cannot reach this line at all after the drop at minute "
                "%s. A phone that lost power or signal cannot be distinguished from "
                "one switched off deliberately, and a student should not lose a "
                "qualification on that ambiguity." % minute,
                0.78,
            )

        if facts.get("cell_crowded"):
            return (
                "note",
                "Grant extra time; the cell was congested",
                "The cell was busy when the session dropped at minute %s, which is "
                "a plausible cause the candidate had no control over." % minute,
                0.8,
            )

        return (
            "flag",
            "Refer to the board: the line was healthy when the session died",
            "The session dropped at minute %s while this line was reachable on data "
            "and its cell was not congested. The network offers no explanation, "
            "which makes it a question for the board - and note that this same "
            "check is what clears most candidates." % minute,
            0.8,
        )
