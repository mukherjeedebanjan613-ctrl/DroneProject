"""Dependency-free ASCII map for AeroSafeX mission demonstrations."""

from __future__ import annotations

from parser import Mission
from safety_analyzer import SafetyReport


class MissionVisualizer:
    """Render home, waypoints, route, zones, and execution status in text."""

    WIDTH = 62
    HEIGHT = 20

    def __init__(self, mission: Mission, report: SafetyReport, drone: object | None = None):
        self.mission = mission
        self.report = report
        self.drone = drone

    def render(self) -> str:
        points = list(self.report.route)
        for x1, y1, x2, y2 in self.mission.no_fly_zones.values():
            points.extend(((x1, y1), (x2, y2)))
        if not points:
            return "Mission map unavailable: no route coordinates."

        min_x, max_x, min_y, max_y = self._bounds(points)
        grid = [[" " for _ in range(self.WIDTH)] for _ in range(self.HEIGHT)]
        for bounds in self.mission.no_fly_zones.values():
            self._draw_zone(grid, bounds, min_x, max_x, min_y, max_y)
        for start, end in zip(self.report.route, self.report.route[1:]):
            self._draw_line(grid, start, end, min_x, max_x, min_y, max_y)

        home = self.mission.configuration.get("HOME")
        if home:
            self._place(grid, home, "H", min_x, max_x, min_y, max_y)
        for name, point in self.mission.waypoints.items():
            self._place(grid, point, name[0].upper(), min_x, max_x, min_y, max_y)
        if self.drone is not None and getattr(self.drone, "position", None) != home:
            self._place(grid, self.drone.position, "D", min_x, max_x, min_y, max_y)

        status = getattr(self.drone, "mission_status", self.report.status)
        battery = getattr(self.drone, "battery_level", None)
        battery_text = f"{battery:.1f}%" if isinstance(battery, (int, float)) else "n/a"
        return "\n".join(
            [
                "=" * self.WIDTH,
                "AEROSAFEX 2D MISSION MAP",
                "=" * self.WIDTH,
                *["".join(row).rstrip() for row in grid],
                "Legend: H=HOME  A/B/C=WAYPOINTS  #=NO-FLY ZONE  ·=ROUTE  D=DRONE",
                f"Route distance: {self.report.distance:.1f} m | Battery remaining: {battery_text} | Status: {status}",
            ]
        )

    @staticmethod
    def _bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
        xs, ys = zip(*points)
        pad_x = max(1.0, (max(xs) - min(xs)) * 0.08)
        pad_y = max(1.0, (max(ys) - min(ys)) * 0.12)
        return min(xs) - pad_x, max(xs) + pad_x, min(ys) - pad_y, max(ys) + pad_y

    def _cell(self, point, min_x, max_x, min_y, max_y) -> tuple[int, int]:
        x, y = point
        column = round((x - min_x) / (max_x - min_x) * (self.WIDTH - 1))
        row = round((max_y - y) / (max_y - min_y) * (self.HEIGHT - 1))
        return max(0, min(self.WIDTH - 1, column)), max(0, min(self.HEIGHT - 1, row))

    def _place(self, grid, point, marker, min_x, max_x, min_y, max_y) -> None:
        column, row = self._cell(point, min_x, max_x, min_y, max_y)
        grid[row][column] = marker

    def _draw_zone(self, grid, bounds, min_x, max_x, min_y, max_y) -> None:
        x1, y1, x2, y2 = bounds
        left, top = self._cell((min(x1, x2), max(y1, y2)), min_x, max_x, min_y, max_y)
        right, bottom = self._cell((max(x1, x2), min(y1, y2)), min_x, max_x, min_y, max_y)
        for row in range(top, bottom + 1):
            for column in range(left, right + 1):
                grid[row][column] = "#"

    def _draw_line(self, grid, start, end, min_x, max_x, min_y, max_y) -> None:
        x0, y0 = self._cell(start, min_x, max_x, min_y, max_y)
        x1, y1 = self._cell(end, min_x, max_x, min_y, max_y)
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            column = round(x0 + (x1 - x0) * step / steps)
            row = round(y0 + (y1 - y0) * step / steps)
            if grid[row][column] == " ":
                grid[row][column] = "·"
