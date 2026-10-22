"""Semantic validation for AeroSafeX missions."""

from parser import Command, Mission
from symbol_table import SymbolError, SymbolTable


class SemanticError(Exception):
    """Raised when a syntactically correct mission is unsafe or invalid."""


class SemanticAnalyzer:
    """Validate mission references, configuration, and command ordering."""

    def __init__(self, mission: Mission):
        self.mission = mission
        self.symbols = SymbolTable()

    def analyze(self) -> SymbolTable:
        self._define_symbols()
        self._validate_configuration()
        self._validate_commands()
        self._validate_safety_rules()
        return self.symbols

    def _define_symbols(self) -> None:
        for name, value in self.mission.configuration.items():
            self.symbols.define_configuration(name, value)
        for name, value in self.mission.variables.items():
            self.symbols.define_variable(name, value)
        for name, coordinates in self.mission.waypoint_declarations:
            try:
                self.symbols.define_waypoint(name, coordinates)
            except SymbolError as error:
                raise SemanticError(str(error)) from error

    def _validate_configuration(self) -> None:
        battery = self.symbols.configuration.get("BATTERY")
        reserve = self.symbols.configuration.get("RESERVE")
        if battery is not None and battery < 0:
            raise SemanticError("BATTERY cannot be negative")
        if reserve is not None and reserve < 0:
            raise SemanticError("RESERVE cannot be negative")
        if battery is not None and reserve is not None and reserve > battery:
            raise SemanticError("RESERVE cannot exceed BATTERY")

        maximum = self.symbols.configuration.get("MAX_ALTITUDE")
        if maximum is not None and maximum <= 0:
            raise SemanticError("MAX_ALTITUDE must be greater than zero")

        mode = self.symbols.configuration.get("MODE", "NORMAL")
        if mode not in {"NORMAL", "ENERGY_SAVE"}:
            raise SemanticError("MODE must be NORMAL or ENERGY_SAVE")

    def _validate_commands(self) -> None:
        airborne = False
        for command in self.mission.commands:
            if command.name == "TAKEOFF":
                if airborne:
                    raise SemanticError("TAKEOFF cannot be issued while airborne")
                self._validate_altitude(command.arguments[0], "TAKEOFF")
                airborne = True
            elif command.name == "LAND":
                if not airborne:
                    raise SemanticError("LAND requires the drone to be airborne")
                airborne = False
            elif command.name == "FLY":
                if not airborne:
                    raise SemanticError("FLY requires TAKEOFF first")
                waypoint = command.arguments[0]
                if not self.symbols.has_waypoint(waypoint):
                    raise SemanticError(f"Undefined waypoint '{waypoint}'")
            elif command.name in {"MOVE", "SET_ALTITUDE", "HOVER", "RETURN_HOME"} and not airborne:
                raise SemanticError(f"{command.name} requires TAKEOFF first")
            elif command.name in {"SET_ALTITUDE", "DESCEND"}:
                self._validate_altitude(command.arguments[0], command.name)

        if airborne:
            raise SemanticError("Mission ends while drone is airborne; add LAND")

    def _validate_safety_rules(self) -> None:
        for _, command in self.mission.safety_rules:
            if command.name in {"TAKEOFF", "SET_ALTITUDE", "DESCEND"}:
                self._validate_altitude(command.arguments[0], command.name)

    def _validate_altitude(self, value: object, command_name: str) -> None:
        if isinstance(value, str):
            try:
                value = self.symbols.resolve_variable(value)
            except SymbolError as error:
                raise SemanticError(str(error)) from error
        if not isinstance(value, (int, float)):
            raise SemanticError(f"{command_name} altitude must be a number")
        if value < 0:
            raise SemanticError(f"{command_name} altitude cannot be negative")

        maximum = self.symbols.configuration.get("MAX_ALTITUDE")
        if maximum is not None and value > maximum:
            raise SemanticError(
                f"{command_name} altitude {value} exceeds MAX_ALTITUDE {maximum}"
            )
