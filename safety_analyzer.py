"""Mission-level safety checks for AeroSafeX."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import hypot

from parser import Command, Condition, Mission


class SafetyLevel(Enum):
    SAFE = "SAFE"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class SafetyIssue:
    level: SafetyLevel
    message: str


@dataclass
class SafetyReport:
    issues: list[SafetyIssue] = field(default_factory=list)
    route: list[tuple[float, float]] = field(default_factory=list)
    distance: float = 0.0
    estimated_battery_used: float = 0.0

    @property
    def is_safe(self) -> bool:
        return not any(issue.level is SafetyLevel.ERROR for issue in self.issues)

    @property
    def status(self) -> str:
        return "SAFE" if self.is_safe else "UNSAFE"

    def add(self, level: SafetyLevel, message: str) -> None:
        self.issues.append(SafetyIssue(level, message))


class SafetyAnalyzer:
    """Analyze route feasibility and conflicts after semantic validation.

    Battery usage is estimated using ``BATTERY_PER_DISTANCE`` percent per
    coordinate unit. Replace this calibration constant with vehicle telemetry
    when connecting a real drone model.
    """

    BATTERY_PER_DISTANCE = 0.05

    def __init__(self, mission: Mission):
        self.mission = mission
        self.report = SafetyReport()

    def analyze(self) -> SafetyReport:
        self._analyze_route()
        self._analyze_battery()
        self._analyze_altitudes()
        self._analyze_rule_conflicts()
        return self.report

    def _analyze_route(self) -> None:
        home = self.mission.configuration.get("HOME")
        if not isinstance(home, tuple) or len(home) != 2:
            self.report.add(SafetyLevel.ERROR, "HOME coordinates are required for route analysis")
            return

        current = home
        self.report.route.append(current)
        for command in self.mission.commands:
            destination = self._command_destination(command, home)
            if destination is None:
                continue
            self._inspect_segment(current, destination)
            self.report.distance += hypot(destination[0] - current[0], destination[1] - current[1])
            self.report.route.append(destination)
            current = destination

    def _command_destination(
        self, command: Command, home: tuple[float, float]
    ) -> tuple[float, float] | None:
        if command.name == "RETURN_HOME":
            return home
        if command.name != "FLY":
            return None
        waypoint_name = command.arguments[0]
        return self.mission.waypoints.get(waypoint_name)

    def _inspect_segment(
        self, start: tuple[float, float], end: tuple[float, float]
    ) -> None:
        for zone_name, bounds in self.mission.no_fly_zones.items():
            if self._segment_intersects_rectangle(start, end, bounds):
                self.report.add(
                    SafetyLevel.ERROR,
                    f"Route segment {start} → {end} intersects no-fly zone '{zone_name}'",
                )

    @staticmethod
    def _segment_intersects_rectangle(
        start: tuple[float, float], end: tuple[float, float], bounds: tuple[float, float, float, float]
    ) -> bool:
        """Return whether a segment intersects an axis-aligned rectangle.

        Uses the Liang-Barsky clipping test, which catches crossings even when
        neither endpoint lies inside the no-fly zone.
        """
        x_min, y_min, x_max, y_max = bounds
        x_min, x_max = min(x_min, x_max), max(x_min, x_max)
        y_min, y_max = min(y_min, y_max), max(y_min, y_max)
        x0, y0 = start
        dx, dy = end[0] - x0, end[1] - y0
        lower, upper = 0.0, 1.0

        for p, q in ((-dx, x0 - x_min), (dx, x_max - x0), (-dy, y0 - y_min), (dy, y_max - y0)):
            if p == 0:
                if q < 0:
                    return False
                continue
            fraction = q / p
            if p < 0:
                if fraction > upper:
                    return False
                lower = max(lower, fraction)
            else:
                if fraction < lower:
                    return False
                upper = min(upper, fraction)
        return True

    def _analyze_battery(self) -> None:
        battery = self.mission.configuration.get("BATTERY")
        reserve = self.mission.configuration.get("RESERVE", 0)
        if battery is None:
            self.report.add(SafetyLevel.WARNING, "BATTERY is not configured; feasibility cannot be estimated")
            return

        self.report.estimated_battery_used = self.report.distance * self.BATTERY_PER_DISTANCE
        usable_battery = battery - reserve
        if self.report.estimated_battery_used > usable_battery:
            self.report.add(
                SafetyLevel.ERROR,
                f"Estimated battery use {self.report.estimated_battery_used:.1f}% exceeds "
                f"usable battery {usable_battery:.1f}%",
            )

    def _analyze_altitudes(self) -> None:
        maximum = self.mission.configuration.get("MAX_ALTITUDE")
        if maximum is None:
            self.report.add(SafetyLevel.WARNING, "MAX_ALTITUDE is not configured")
            return
        for command in self.mission.commands:
            if command.name in {"TAKEOFF", "SET_ALTITUDE", "DESCEND"}:
                self._check_altitude(command, maximum)
        for _, command in self.mission.safety_rules:
            if command.name in {"TAKEOFF", "SET_ALTITUDE", "DESCEND"}:
                self._check_altitude(command, maximum)

    def _check_altitude(self, command: Command, maximum: float) -> None:
        value = command.arguments[0]
        if isinstance(value, str):
            value = self.mission.variables.get(value)
        if isinstance(value, (int, float)) and value > maximum:
            self.report.add(SafetyLevel.ERROR, f"{command.name} altitude {value} exceeds MAX_ALTITUDE {maximum}")

    def _analyze_rule_conflicts(self) -> None:
        rules: dict[tuple[object, str, object], Command] = {}
        for condition, command in self.mission.safety_rules:
            key = self._condition_key(condition)
            previous = rules.get(key)
            if previous and (previous.name != command.name or previous.arguments != command.arguments):
                self.report.add(
                    SafetyLevel.WARNING,
                    f"Conflicting safety actions for {condition.left} {condition.operator} {condition.right}: "
                    f"{previous.name} and {command.name}",
                )
            rules[key] = command

    @staticmethod
    def _condition_key(condition: Condition) -> tuple[object, str, object]:
        return (condition.left, condition.operator, condition.right)
