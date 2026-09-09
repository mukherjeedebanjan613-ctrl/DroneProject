"""Intermediate representation for validated AeroSafeX missions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from parser import Mission


@dataclass(frozen=True)
class IRInstruction:
    opcode: str
    operands: tuple[Any, ...] = ()

    def __str__(self) -> str:
        values = " ".join(map(str, self.operands))
        return f"{self.opcode} {values}".rstrip()


@dataclass
class IRProgram:
    instructions: list[IRInstruction] = field(default_factory=list)

    def emit(self, opcode: str, *operands: Any) -> None:
        self.instructions.append(IRInstruction(opcode, operands))

    def __str__(self) -> str:
        return "\n".join(str(instruction) for instruction in self.instructions)


class IRGenerator:
    """Lower an AeroSafeX AST into coordinate-based drone instructions."""

    def __init__(self, mission: Mission):
        self.mission = mission
        self.program = IRProgram()
        self.altitude: int | float = 0

    def generate(self) -> IRProgram:
        self.program.emit("MISSION_BEGIN", self.mission.configuration.get("BATTERY", 100.0))
        for command in self.mission.commands:
            self._lower_command(command.name, command.arguments)
        self.program.emit("MISSION_END")
        return self.program

    def _resolve_value(self, value: Any) -> Any:
        if isinstance(value, str) and value in self.mission.variables:
            return self.mission.variables[value]
        return value

    def _lower_command(self, name: str, arguments: list[Any]) -> None:
        if name == "TAKEOFF":
            self.altitude = self._resolve_value(arguments[0])
            self.program.emit("TAKEOFF", self.altitude)
        elif name == "FLY":
            waypoint_name = arguments[0]
            x, y = self.mission.waypoints[waypoint_name]
            self.program.emit("MOVE", x, y, self.altitude)
        elif name == "RETURN_HOME":
            x, y = self.mission.configuration["HOME"]
            self.program.emit("MOVE", x, y, self.altitude)
        elif name == "SET_ALTITUDE":
            self.altitude = self._resolve_value(arguments[0])
            self.program.emit("SET_ALTITUDE", self.altitude)
        elif name == "DESCEND":
            self.altitude = self._resolve_value(arguments[0])
            self.program.emit("SET_ALTITUDE", self.altitude)
        elif name == "HOVER":
            self.program.emit("HOVER", self._resolve_value(arguments[0]))
        elif name == "LAND":
            self.program.emit("LAND")
        elif name == "AVOID":
            self.program.emit("AVOID")
