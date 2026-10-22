"""Automated end-to-end tests for the AeroSafeX compiler pipeline."""

from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
import unittest

from code_generator import CodeGenerator
from ir import IRGenerator
from ir import IRInstruction, IRProgram
from ir_optimizer import IROptimizer
from lexer import Lexer
from parser import Parser
from safety_analyzer import SafetyAnalyzer
from semantic_analyzer import SemanticAnalyzer, SemanticError


MISSIONS = Path(__file__).with_name("test_missions")


def parse_mission(filename: str):
    source = (MISSIONS / filename).read_text(encoding="utf-8")
    return Parser(Lexer(source).tokenize()).parse()


class AeroSafeXCompilerTests(unittest.TestCase):
    def test_safe_mission_compiles_and_simulates(self):
        mission = parse_mission("safe.aero")
        symbols = SemanticAnalyzer(mission).analyze()
        report = SafetyAnalyzer(mission).analyze()

        self.assertTrue(report.is_safe, report.issues)
        self.assertEqual(len(symbols.waypoints), 3)

        ir_program = IRGenerator(mission).generate()
        self.assertEqual(
            [instruction.opcode for instruction in ir_program.instructions],
            ["MISSION_BEGIN", "TAKEOFF", "MOVE", "MOVE", "MOVE", "MOVE", "LAND", "MISSION_END"],
        )
        generated_code = CodeGenerator(ir_program).generate()
        namespace: dict[str, object] = {}
        with redirect_stdout(StringIO()):
            exec(generated_code, namespace)
        drone = namespace["drone"]
        self.assertFalse(drone.airborne)
        self.assertEqual(drone.position, (0, 0))
        self.assertEqual(drone.mission_status, "COMPLETED")
        self.assertEqual(drone.flight_state, "LANDED")

    def test_altitude_violation_is_rejected_semantically(self):
        with self.assertRaisesRegex(SemanticError, "exceeds MAX_ALTITUDE"):
            SemanticAnalyzer(parse_mission("altitude_violation.aero")).analyze()

    def test_geofence_violation_is_unsafe(self):
        mission = parse_mission("geofence_violation.aero")
        SemanticAnalyzer(mission).analyze()
        report = SafetyAnalyzer(mission).analyze()

        self.assertFalse(report.is_safe)
        self.assertTrue(any("intersects no-fly zone 'ZONE1'" in issue.message for issue in report.issues))

    def test_battery_violation_is_unsafe(self):
        mission = parse_mission("battery_violation.aero")
        SemanticAnalyzer(mission).analyze()
        report = SafetyAnalyzer(mission).analyze()

        self.assertFalse(report.is_safe)
        self.assertTrue(any("exceeds usable battery" in issue.message for issue in report.issues))

    def test_undefined_waypoint_is_rejected_semantically(self):
        with self.assertRaisesRegex(SemanticError, "Undefined waypoint 'UNKNOWN'"):
            SemanticAnalyzer(parse_mission("undefined_waypoint.aero")).analyze()

    def test_invalid_sequence_is_rejected_semantically(self):
        with self.assertRaisesRegex(SemanticError, "FLY requires TAKEOFF first"):
            SemanticAnalyzer(parse_mission("invalid_sequence.aero")).analyze()

    def test_ir_optimizer_removes_redundant_move(self):
        program = IRProgram([
            IRInstruction("TAKEOFF", (50,)),
            IRInstruction("MOVE", (100, 100, 50)),
            IRInstruction("MOVE", (100, 100, 50)),
            IRInstruction("LAND"),
        ])
        result = IROptimizer().optimize(program)

        self.assertEqual([item.opcode for item in result.program.instructions], ["TAKEOFF", "MOVE", "LAND"])
        self.assertEqual(len(result.changes), 1)

    def test_energy_save_mode_reduces_battery_use_without_changing_route(self):
        source = (MISSIONS / "safe.aero").read_text(encoding="utf-8").replace(
            "MAX_ALTITUDE 120", "MAX_ALTITUDE 120\nMODE ENERGY_SAVE"
        )
        mission = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer(mission).analyze()
        ir_program = IRGenerator(mission).generate()
        generated_code = CodeGenerator(ir_program).generate()
        namespace: dict[str, object] = {}
        with redirect_stdout(StringIO()):
            exec(generated_code, namespace)
        drone = namespace["drone"]
        self.assertEqual(drone.flight_mode, "ENERGY_SAVE")
        self.assertEqual(drone.position, (0, 0))
        self.assertLess(drone.battery_level, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
