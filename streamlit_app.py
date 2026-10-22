"""Streamlit browser interface for the AeroSafeX compiler."""

from pathlib import Path

import streamlit as st

from compiler_service import compile_source


DEFAULT_SOURCE = (Path(__file__).parent / "test_missions" / "safe.aero").read_text(encoding="utf-8")

st.set_page_config(page_title="AeroSafeX", page_icon="🚁", layout="wide")
st.title("🚁 AeroSafeX")
st.caption("Safety-aware drone mission compiler and simulator")
st.info("Add `MODE ENERGY_SAVE` to a mission to use slower, more efficient movement while preserving the validated route and altitude.")

source = st.text_area("Mission source (.aero)", value=DEFAULT_SOURCE, height=420)
if st.button("Compile and simulate", type="primary"):
    result = compile_source(source)
    st.session_state["result"] = result

result = st.session_state.get("result")
if not result:
    st.info("Enter a mission and select Compile and simulate.")
    st.stop()

if result["status"] != "COMPLETED":
    st.error(f"{result['stage']} analysis rejected the mission: {result['error']}")
    for issue in result.get("issues", []):
        st.warning(f"{issue['level']}: {issue['message']}")
    st.stop()

st.success("Mission completed successfully")
drone = result["drone"]
metrics = st.columns(5)
metrics[0].metric("Status", drone["mission_status"])
metrics[1].metric("Flight state", drone["flight_state"])
metrics[2].metric("Final position", str(drone["position"]))
metrics[3].metric("Battery", f"{drone['battery']:.1f}%")
metrics[4].metric("Route distance", f"{result['distance']:.1f}")

left, right = st.columns(2)
with left:
    st.subheader("Route")
    route = result.get("route", [])
    if route:
        st.line_chart({"x": [point[0] for point in route], "y": [point[1] for point in route]})
    st.subheader("Telemetry")
    st.dataframe(
        [{"x": p[0], "y": p[1], "altitude": p[2], "battery": p[3]} for p in drone["trace"]],
        use_container_width=True,
    )
with right:
    st.subheader("Compiler pipeline")
    st.write("✅ Lexical analysis")
    st.write("✅ Parsing and AST")
    st.write("✅ Semantic analysis")
    st.write("✅ Safety analysis")
    st.write("✅ IR generation and optimization")
    st.write("✅ Code generation")
    st.write("✅ Drone simulation")
    st.subheader("Intermediate representation")
    st.code(result["ir"], language="text")
    if result["optimizations"]:
        st.subheader("Optimizations")
        for change in result["optimizations"]:
            st.write(f"- {change}")
    st.subheader("Generated simulator code")
    st.code(result["generated_code"], language="python")
