"""Symbol storage used during AeroSafeX semantic analysis."""

from dataclasses import dataclass, field
from typing import Any


class SymbolError(Exception):
    """Raised when an invalid symbol-table operation is attempted."""


@dataclass
class SymbolTable:
    """Stores mission configuration, variables, and waypoint declarations."""

    configuration: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    waypoints: dict[str, tuple[float, float]] = field(default_factory=dict)

    def define_configuration(self, name: str, value: Any) -> None:
        self.configuration[name] = value

    def define_variable(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def define_waypoint(self, name: str, coordinates: tuple[float, float]) -> None:
        if name in self.waypoints:
            raise SymbolError(f"Duplicate waypoint '{name}'")
        self.waypoints[name] = coordinates

    def resolve_variable(self, name: str) -> Any:
        try:
            return self.variables[name]
        except KeyError as error:
            raise SymbolError(f"Undefined variable '{name}'") from error

    def has_waypoint(self, name: str) -> bool:
        return name in self.waypoints
