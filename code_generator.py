"""Generate executable Python simulator commands from AeroSafeX IR."""

from ir import IRProgram


class CodeGenerator:
    """Translate platform-neutral IR instructions into simulator API calls."""

    def __init__(self, program: IRProgram):
        self.program = program

    def generate(self) -> str:
        initial_battery = self._initial_battery()
        lines = [
            "from drone_simulator import DroneSimulator",
            "",
            f"drone = DroneSimulator(initial_battery={initial_battery!r}, animation_steps=8, step_delay=0.08)",
            "drone.start_mission()",
        ]
        for instruction in self.program.instructions:
            lines.extend(self._generate_instruction(instruction.opcode, instruction.operands))
        lines.append("drone.complete_mission()")
        lines.append("print(drone.summary())")
        return "\n".join(lines) + "\n"

    def _initial_battery(self) -> object:
        for instruction in self.program.instructions:
            if instruction.opcode == "MISSION_BEGIN" and instruction.operands:
                return instruction.operands[0]
        return 100.0

    @staticmethod
    def _generate_instruction(opcode: str, operands: tuple[object, ...]) -> list[str]:
        if opcode in {"MISSION_BEGIN", "MISSION_END"}:
            return []
        if opcode == "TAKEOFF":
            return [f"drone.takeoff({operands[0]!r})"]
        if opcode == "MOVE":
            return [f"drone.move_to({operands[0]!r}, {operands[1]!r}, {operands[2]!r})"]
        if opcode == "SET_ALTITUDE":
            return [f"drone.set_altitude({operands[0]!r})"]
        if opcode == "HOVER":
            return [f"drone.hover({operands[0]!r})"]
        if opcode == "LAND":
            return ["drone.land()"]
        if opcode == "AVOID":
            return ["drone.avoid()"]
        raise ValueError(f"Unsupported IR opcode: {opcode}")
