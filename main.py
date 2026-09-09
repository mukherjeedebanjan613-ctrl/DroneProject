"""AeroSafeX compiler entry point: source mission to local simulation."""

from __future__ import annotations

import argparse
from pathlib import Path

from code_generator import CodeGenerator
from ir import IRGenerator
from ir_optimizer import IROptimizer
from lexer import Lexer, LexerError
from parser import Parser, ParserError
from safety_analyzer import SafetyAnalyzer
from semantic_analyzer import SemanticAnalyzer, SemanticError
from mission_visualizer import MissionVisualizer


WIDTH = 60


def heading(title: str) -> None:
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)


def pipeline_summary(completed: list[str], blocked: list[str], status: str) -> None:
    heading("AeroSafeX COMPILATION PIPELINE")
    for stage in completed:
        print(f"[✓] {stage}")
    for stage in blocked:
        print(f"[✗] {stage}")
    print("=" * WIDTH)
    print(f"MISSION STATUS: {status}")
    print("=" * WIDTH)


def resolve_source(value: str | None) -> Path:
    if value is None:
        return Path(__file__).with_name("test_missions") / "safe.aero"
    candidate = Path(value)
    if candidate.exists():
        return candidate
    return Path(__file__).parent / candidate


def compile_mission(source_path: Path) -> int:
    """Compile a mission and execute only generated code for safe missions."""
    heading("AEROSAFEX COMPILER")
    print(f"Source: {source_path.name}\n")

    try:
        source = source_path.read_text(encoding="utf-8")
        tokens = Lexer(source).tokenize()
        mission = Parser(tokens).parse()
    except FileNotFoundError:
        print(f"AeroSafeX Compilation Error: source file not found: {source_path}")
        return 1
    except LexerError as error:
        print(f"AeroSafeX Lexical Error: {error}")
        pipeline_summary(["Lexical Analysis"], ["Parsing", "AST Generation", "Semantic Analysis", "Safety Analysis", "IR Generation", "IR Optimization", "Code Generation", "Drone Simulation"], "REJECTED")
        return 1
    except ParserError as error:
        print(f"AeroSafeX Syntax Error: {error}")
        pipeline_summary(["Lexical Analysis"], ["Parsing", "AST Generation", "Semantic Analysis", "Safety Analysis", "IR Generation", "IR Optimization", "Code Generation", "Drone Simulation"], "REJECTED")
        return 1

    print("[1] LEXICAL ANALYSIS")
    print(f"    ✓ {len(tokens)} tokens generated")
    print("[2] SYNTAX ANALYSIS")
    print("    ✓ AST generated")

    try:
        symbols = SemanticAnalyzer(mission).analyze()
    except SemanticError as error:
        heading("AeroSafeX Semantic Error")
        print(f"Message: {error}")
        print("MISSION EXECUTION BLOCKED")
        pipeline_summary(["Lexical Analysis", "Parsing", "AST Generation"], ["Semantic Analysis", "Safety Analysis", "IR Generation", "IR Optimization", "Code Generation", "Drone Simulation"], "REJECTED")
        return 1

    print("[3] SEMANTIC ANALYSIS")
    print(f"    ✓ {len(symbols.waypoints)} waypoints")
    print(f"    ✓ {len(symbols.variables)} variables")
    print("    ✓ Mission sequence valid")

    safety_report = SafetyAnalyzer(mission).analyze()
    heading("AeroSafeX - SAFETY ANALYSIS")
    print(f"STATUS: {safety_report.status}")
    print(f"Route distance: {safety_report.distance:.1f}")
    print(f"Estimated battery use: {safety_report.estimated_battery_used:.1f}%")
    for issue in safety_report.issues:
        print(f"- {issue.level.value}: {issue.message}")
    if not safety_report.is_safe:
        print("\nMISSION EXECUTION BLOCKED")
        print("Simulation will NOT start.")
        pipeline_summary(["Lexical Analysis", "Parsing", "AST Generation", "Semantic Analysis"], ["Safety Analysis", "IR Generation", "IR Optimization", "Code Generation", "Drone Simulation"], "REJECTED")
        return 1

    print("    ✓ Battery: PASS")
    print("    ✓ Altitude: PASS")
    print("    ✓ Geofence: PASS")
    print("    ✓ Route: PASS")

    ir_program = IRGenerator(mission).generate()
    optimization = IROptimizer().optimize(ir_program)
    generated_code = CodeGenerator(optimization.program).generate()
    heading("[5] INTERMEDIATE REPRESENTATION")
    print(ir_program)
    heading("[6] CODE GENERATION")
    if optimization.changes:
        print("IR optimization:")
        for change in optimization.changes:
            print(f"✓ {change}")
    else:
        print("IR optimization: no redundant instructions found")
    print("✓ Python simulator code generated\n")
    print(generated_code)

    heading("AeroSafeX - DRONE SIMULATION")
    try:
        # Execute the exact Python source emitted by CodeGenerator.
        namespace: dict[str, object] = {}
        exec(generated_code, namespace)
    except (RuntimeError, ValueError) as error:
        print(f"SIMULATION FAILED: {error}")
        pipeline_summary(["Lexical Analysis", "Parsing", "AST Generation", "Semantic Analysis", "Safety Analysis", "IR Generation", "IR Optimization", "Code Generation"], ["Drone Simulation"], "FAILED")
        return 1

    print(MissionVisualizer(mission, safety_report, namespace["drone"]).render())

    pipeline_summary(["Lexical Analysis", "Parsing", "AST Generation", "Semantic Analysis", "Safety Analysis", "IR Generation", "IR Optimization", "Code Generation", "Drone Simulation"], [], "COMPLETED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile and simulate an AeroSafeX mission.")
    parser.add_argument("mission", nargs="?", help="Path to a .aero mission file")
    args = parser.parse_args()
    return compile_mission(resolve_source(args.mission))


if __name__ == "__main__":
    raise SystemExit(main())
