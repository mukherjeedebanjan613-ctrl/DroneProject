"""Small, explainable optimization passes for AeroSafeX IR."""

from dataclasses import dataclass, field

from ir import IRInstruction, IRProgram


@dataclass
class OptimizationResult:
    program: IRProgram
    changes: list[str] = field(default_factory=list)


class IROptimizer:
    """Remove redundant movement and altitude instructions safely."""

    def optimize(self, program: IRProgram) -> OptimizationResult:
        optimized = IRProgram()
        changes: list[str] = []
        last_move: tuple[object, ...] | None = None
        current_altitude: object | None = None

        for instruction in program.instructions:
            if instruction.opcode == "TAKEOFF":
                current_altitude = instruction.operands[0]
                last_move = None
            elif instruction.opcode == "SET_ALTITUDE":
                if instruction.operands[0] == current_altitude:
                    changes.append(f"Removed redundant SET_ALTITUDE {instruction.operands[0]}")
                    continue
                current_altitude = instruction.operands[0]
            elif instruction.opcode == "MOVE":
                if instruction.operands == last_move:
                    changes.append(f"Removed redundant MOVE {instruction.operands}")
                    continue
                last_move = instruction.operands
            elif instruction.opcode == "LAND":
                last_move = None

            optimized.instructions.append(instruction)

        return OptimizationResult(optimized, changes)
