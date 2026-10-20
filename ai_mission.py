"""Deterministic AI-style mission assistant for AeroSafeX.

The assistant turns a natural-language request into AeroSafeX DSL.  It is
intentionally conservative: generated text is still passed through the real
lexer, parser, semantic analyzer, and safety analyzer before execution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class MissionSuggestion:
    source: str
    explanation: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _number(pattern: str, text: str, default: float) -> float:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return float(match.group(1)) if match else default


def generate_mission(prompt: str) -> MissionSuggestion:
    """Generate a safe starter mission from a plain-language request.

    This local implementation is predictable and works offline. It provides
    the same contract as an LLM-backed assistant while keeping final control
    with AeroSafeX's deterministic safety pipeline.
    """
    text = prompt.strip()
    if not text:
        raise ValueError("prompt must not be empty")

    altitude = _number(r"(?:altitude|height|take[ -]?off)[^0-9]*(\d+(?:\.\d+)?)", text, 50)
    battery = _number(r"battery[^0-9]*(\d+(?:\.\d+)?)", text, 100)
    reserve = _number(r"reserve[^0-9]*(\d+(?:\.\d+)?)", text, 20)
    maximum = _number(r"(?:max(?:imum)? altitude|altitude limit)[^0-9]*(\d+(?:\.\d+)?)", text, 120)

    # Accept "A (100, 100)", "A at 100,100", and "waypoint A 100 100".
    waypoint_matches = re.findall(
        r"(?:waypoint\s+)?([A-Z])\s*(?:\(|at\s+)?\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    waypoints: list[tuple[str, float, float]] = []
    for name, x, y in waypoint_matches:
        item = (name.upper(), float(x), float(y))
        if item not in waypoints:
            waypoints.append(item)

    # If the request mentions numbered locations but gives no coordinates,
    # produce deterministic demo points and explicitly explain the assumption.
    if not waypoints:
        names = re.findall(r"(?:point|waypoint)\s*([A-Z])", text, flags=re.IGNORECASE)
        for index, name in enumerate(dict.fromkeys(n.upper() for n in names)):
            waypoints.append((name, (index + 1) * 100.0, (index + 1) * 100.0))
    if not waypoints:
        waypoints = [("A", 100.0, 100.0)]

    requested_order = re.findall(r"(?:to|visit|via)\s+([A-Z])", text, flags=re.IGNORECASE)
    order = [name.upper() for name in requested_order if name.upper() in {p[0] for p in waypoints}]
    order = list(dict.fromkeys(order)) or [p[0] for p in waypoints]

    lines = [
        "MISSION START",
        "HOME 0 0",
        f"BATTERY {battery:g}",
        f"RESERVE {reserve:g}",
        "SPEED 10",
        f"MAX_ALTITUDE {maximum:g}",
        f"SET CRUISE_ALTITUDE = {altitude:g}",
    ]
    lines.extend(f"WAYPOINT {name} {x:g} {y:g}" for name, x, y in waypoints)
    lines.extend(["TAKEOFF CRUISE_ALTITUDE"])
    lines.extend(f"FLY TO {name}" for name in order)
    lines.extend(["RETURN_HOME", "LAND", "MISSION END"])

    explanation = [
        "Converted the request into AeroSafeX mission syntax.",
        "The generated mission must pass semantic and safety analysis before simulation.",
    ]
    warnings = []
    if not waypoint_matches:
        warnings.append("No coordinates were supplied; deterministic demo coordinates were assumed.")
    if altitude > maximum:
        warnings.append("Requested altitude is above the configured limit; safety analysis will reject it.")
    return MissionSuggestion("\n".join(lines) + "\n", explanation, warnings)
