import sys
import os
import json
import io
import zipfile
import streamlit as st

# Add project root directory to python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from demo_examples import DEMO_EXAMPLES, DEMO_PROJECT_PRESETS
from utils.llm import is_gemini_available, get_api_key
from database.database import save_debug_session, get_all_sessions, init_db
from orchestration.graph import debugging_app
from utils.workspace import WorkspaceManager
from language_adapters.detector import detect_project
from language_adapters.python.adapter import PythonAdapter
from language_adapters.java.adapter import JavaAdapter

# Set page config
st.set_page_config(
    page_title="Autonomous Debugging Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich dark modern aesthetic
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4A00E0 0%, #8E2DE2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #A0AEC0;
        margin-bottom: 25px;
    }
    .agent-card {
        border-radius: 10px;
        padding: 15px;
        background-color: #1A202C;
        border: 1px solid #2D3748;
        margin-bottom: 12px;
    }
    .status-badge-success {
        background-color: #276749;
        color: #9AE6B4;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
    }
    .status-badge-fail {
        background-color: #9B2C2C;
        color: #FEB2B2;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
init_db()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/bug.png", width=64)
    st.markdown("### 🤖 Agent Configuration")
    
    gemini_active = is_gemini_available()
    if gemini_active:
        st.success("🟢 Gemini API Key Active")
    else:
        st.warning("🟠 Mock Mode (No Gemini Key)")
        st.caption("Add `GEMINI_API_KEY` to `.env` to enable full LLM generation.")

    st.divider()
    st.markdown("### 📚 Demo Presets")
    
    preset_mode = st.radio("Preset type:", ["Single File", "ZIP Project"])

    if preset_mode == "Single File":
        selected_demo = st.selectbox(
            "Load single-file example:",
            options=["Select preset..."] + list(DEMO_EXAMPLES.keys())
        )

        if st.button("Load Selected Single File", type="secondary"):
            if selected_demo in DEMO_EXAMPLES:
                ex = DEMO_EXAMPLES[selected_demo]
                st.session_state["code_input"] = ex["code"]
                st.session_state["error_input"] = ex["error_log"]
                st.session_state["test_input"] = ex.get("test_code", "")
                st.session_state["debug_mode"] = "Single File"
                st.rerun()

    else:
        selected_proj = st.selectbox(
            "Load project ZIP preset:",
            options=["Select project preset..."] + list(DEMO_PROJECT_PRESETS.keys())
        )

        if st.button("Load Selected Project ZIP", type="secondary"):
            if selected_proj in DEMO_PROJECT_PRESETS:
                p_spec = DEMO_PROJECT_PRESETS[selected_proj]
                # Build in-memory zip
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for path, text in p_spec["files"].items():
                        zf.writestr(path, text)
                buf.seek(0)
                
                st.session_state["uploaded_preset_bytes"] = buf.getvalue()
                st.session_state["uploaded_preset_name"] = p_spec["filename"]
                st.session_state["debug_mode"] = "Upload Project"
                st.rerun()

    st.divider()
    st.markdown("### 📜 Session History")
    sessions = get_all_sessions()
    if sessions:
        for s in sessions[:5]:
            status_icon = "✅" if s["verification_status"] == "VERIFIED" else "❌"
            lang = s.get("language", "Python")
            st.caption(f"{status_icon} **{s['title']}** [{lang}] ({s['timestamp']})")
    else:
        st.caption("No saved debug sessions yet.")


# --- MAIN UI ---
st.markdown('<div class="main-header">Autonomous Software Debugging Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Agent AI Pipeline: Analyze → Reason → Fix → Test → Verify</div>', unsafe_allow_html=True)

# Input Mode Selector
if "debug_mode" not in st.session_state:
    st.session_state["debug_mode"] = "Single File"

debug_mode = st.radio(
    "Select Debug Input Mode:",
    options=["Single File", "Upload Project"],
    horizontal=True,
    index=0 if st.session_state.get("debug_mode") == "Single File" else 1,
    key="mode_radio"
)
st.session_state["debug_mode"] = debug_mode

st.divider()

# Variable containers
active_project_path = None
active_temp_dir = None
active_language = "python"
active_build_system = "pytest"
detection_info = None

if debug_mode == "Single File":
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Python Source Code")
        source_code = st.text_area(
            "Enter buggy Python code:",
            value=st.session_state.get("code_input", DEMO_EXAMPLES["ZeroDivisionError (Empty List)"]["code"]),
            height=240,
            key="source_editor"
        )

    with col2:
        st.subheader("2. Stack Trace / Error Log")
        error_log = st.text_area(
            "Paste error log or stack trace:",
            value=st.session_state.get("error_input", DEMO_EXAMPLES["ZeroDivisionError (Empty List)"]["error_log"]),
            height=240,
            key="error_editor"
        )

    start_btn = st.button("🚀 Start Autonomous Debugging", type="primary", use_container_width=True)

else:
    # --- UPLOAD PROJECT MODE ---
    st.subheader("📦 Upload Complete Project (ZIP)")
    st.caption("Upload a `.zip` archive containing a Python or Java project.")

    uploaded_file = st.file_uploader("Choose a project ZIP file", type=["zip"])
    
    zip_bytes = None
    zip_filename = None

    if uploaded_file is not None:
        zip_bytes = uploaded_file.read()
        zip_filename = uploaded_file.name
    elif "uploaded_preset_bytes" in st.session_state:
        zip_bytes = st.session_state["uploaded_preset_bytes"]
        zip_filename = st.session_state.get("uploaded_preset_name", "preset_project.zip")
        st.info(f"Loaded demo project preset: `{zip_filename}`")

    if zip_bytes is not None:
        temp_dir, project_root, extract_err = WorkspaceManager.extract_zip(io.BytesIO(zip_bytes))
        
        if extract_err:
            st.error(extract_err)
        else:
            active_temp_dir = temp_dir
            active_project_path = project_root
            
            # Detect project
            detection_info = detect_project(project_root)
            
            if not detection_info.get("is_supported", False):
                st.error(detection_info.get("message", "Unsupported project format."))
                WorkspaceManager.cleanup(temp_dir)
                active_temp_dir = None
                active_project_path = None
            else:
                st.success("Project ZIP extracted and inspected successfully!")
                
                # Project Overview Card
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Project Name", zip_filename)
                
                detected_lang = detection_info.get("language")
                if detected_lang == "multiple":
                    st.warning("⚠️ Multiple languages detected in project.")
                    selected_lang = st.radio("Select target language to debug:", ["Python", "Java"], horizontal=True)
                    active_language = selected_lang.lower()
                    active_build_system = "pytest" if active_language == "python" else "maven"
                else:
                    active_language = detected_lang
                    active_build_system = detection_info.get("build_system", "unknown")

                c2.metric("Detected Language", active_language.capitalize())
                c3.metric("Build/Test System", active_build_system)
                c4.metric("Total Files", detection_info.get("files_count", 0))

                st.markdown(f"**Test Files Detected:** `{detection_info.get('test_files_count', 0)}`")
                if detection_info.get("dependency_files"):
                    st.markdown(f"**Manifest Files:** `{', '.join(detection_info.get('dependency_files'))}`")

    start_btn = st.button("🚀 Start Autonomous Project Debugging", type="primary", use_container_width=True, disabled=(active_project_path is None))


# --- WORKFLOW EXECUTION ---
if start_btn:
    if debug_mode == "Single File" and not source_code.strip():
        st.error("Please provide Python source code to debug.")
    elif debug_mode == "Upload Project" and not active_project_path:
        st.error("Please upload a valid project ZIP archive first.")
    else:
        st.divider()
        st.subheader("🔄 Multi-Agent Workflow Execution")
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Initialize execution state
        if debug_mode == "Single File":
            initial_state = {
                "input_mode": "single_file",
                "source_code": source_code,
                "error_log": error_log,
                "test_code": st.session_state.get("test_input", None),
                "code_analysis": None,
                "bug_investigation": None,
                "root_cause": None,
                "candidate_fix": None,
                "test_results": None,
                "verification_result": None,
                "iteration_count": 0,
                "max_iterations": 3,
                "history": [],
                "final_report": None,
                "is_mock_mode": not gemini_active,
                "language": "python",
                "project_name": "Single File"
            }
        else:
            # First execution run to collect initial errors from project if error_log is empty
            if active_language == "java":
                init_adapter = JavaAdapter(active_project_path)
            else:
                init_adapter = PythonAdapter(active_project_path)

            init_exec = init_adapter.run_tests()
            init_error_log = init_exec.get("output") or init_exec.get("stderr") or "Build/Test failure"

            initial_state = {
                "input_mode": "project",
                "project_path": active_project_path,
                "project_name": zip_filename,
                "language": active_language,
                "build_system": active_build_system,
                "source_code": "",
                "error_log": init_error_log,
                "execution_result": init_exec,
                "test_code": None,
                "code_analysis": None,
                "bug_investigation": None,
                "root_cause": None,
                "candidate_fix": None,
                "test_results": None,
                "verification_result": None,
                "iteration_count": 0,
                "max_iterations": 3,
                "history": [],
                "final_report": None,
                "is_mock_mode": not gemini_active
            }

        try:
            status_text.text("1/7 Code Analysis Agent inspecting project structure...")
            progress_bar.progress(15)
            
            # Execute LangGraph workflow
            final_state = debugging_app.invoke(initial_state)
            progress_bar.progress(100)
            status_text.text("✅ Autonomous Debugging Pipeline Complete!")

            st.success("Workflow Execution Finished Successfully!")

            # --- DISPLAY 7 AGENTS DETAILS ---
            st.subheader("🧩 Specialized Agent Details")

            # 1. Code Analysis
            with st.expander("🔍 1. Code Analysis Agent", expanded=True):
                ca = final_state.get("code_analysis", {})
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Mode", "Project" if ca.get("is_project") else "Single File")
                c2.metric("Language", final_state.get("language", "python").capitalize())
                c3.metric("Source Files", len(ca.get("source_files", [])))
                c4.metric("Test Files", len(ca.get("test_files", [])))
                st.markdown(f"**Summary:** {ca.get('summary')}")
                st.json(ca)

            # 2. Bug Investigation
            with st.expander("📍 2. Bug Investigation Agent", expanded=True):
                bi = final_state.get("bug_investigation", {})
                st.markdown(f"**Suspected Location:** `{bi.get('suspected_location')}`")
                st.markdown(f"**Suspicious Code Snippet:** `{bi.get('suspicious_code')}`")
                st.markdown(f"**Reason:** {bi.get('reason')}")
                st.json(bi)

            # 3. Root Cause
            with st.expander("🧠 3. Root Cause Agent", expanded=True):
                rc = final_state.get("root_cause", {})
                st.info(f"**Bug Category:** `{rc.get('bug_category')}`")
                st.markdown(f"**Root Cause:** {rc.get('root_cause')}")
                st.markdown(f"**Explanation:** {rc.get('explanation')}")
                st.markdown(f"**Recommended Strategy:** {rc.get('recommended_fix_strategy')}")

            # 4. Fix Generation
            with st.expander("🛠️ 4. Fix Generation Agent", expanded=True):
                cf = final_state.get("candidate_fix", {})
                st.markdown(f"**Fix Strategy Explanation:** {cf.get('explanation')}")
                if cf.get("patches"):
                    for p in cf.get("patches"):
                        st.markdown(f"**Patch File:** `{p.get('file')}`")
                        st.code(p.get("changes", ""), language=active_language)
                else:
                    st.code(cf.get("fixed_code", ""), language=active_language)

            # 5. Testing Agent
            with st.expander("🧪 5. Testing Agent Execution", expanded=True):
                tr = final_state.get("test_results", {})
                tc1, tc2, tc3 = st.columns(3)
                tc1.metric("Tests Executed", tr.get("tests_run", 0))
                tc2.metric("Passed", tr.get("passed", 0))
                tc3.metric("Failed", tr.get("failed", 0))
                st.code(tr.get("output", ""), language="bash")

            # 6. Verification Agent
            with st.expander("🎯 6. Verification Agent", expanded=True):
                vr = final_state.get("verification_result", {})
                v_status = vr.get("status", "UNVERIFIED")
                if v_status == "VERIFIED":
                    st.success(f"Status: {v_status} — {vr.get('reason')}")
                else:
                    st.error(f"Status: {v_status} — {vr.get('reason')}")

            # 7. Supervisor Agent Overview
            with st.expander("👑 7. Supervisor Agent Overview", expanded=True):
                sup = final_state.get("final_report", {})
                st.json(sup)

            # --- FINAL REPORT SUMMARY CARD ---
            st.divider()
            st.subheader("📊 Final Debugging Report")

            report = final_state.get("final_report", {})
            v_status = report.get("status", "UNVERIFIED")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Verification Status", v_status)
            m2.metric("Iterations Used", report.get("iterations_used", 1))
            m3.metric("Bug Category", report.get("bug_category", "Unknown"))
            m4.metric("Tests Passed", f"{report.get('tests_passed', 0)} / {report.get('tests_passed', 0) + report.get('tests_failed', 0)}")

            comp_col1, comp_col2 = st.columns(2)
            with comp_col1:
                st.markdown("#### ❌ Initial Bug Context")
                if debug_mode == "Single File":
                    st.code(source_code, language="python")
                else:
                    st.code(final_state.get("error_log", "Execution Log"), language="text")

            with comp_col2:
                st.markdown("#### ✅ Candidate Fix / Patches")
                if report.get("patches"):
                    for p in report.get("patches"):
                        st.markdown(f"**{p.get('file')}**")
                        st.code(p.get("changes", ""), language=active_language)
                else:
                    st.code(report.get("fixed_code", ""), language=active_language)

            # Save session to SQLite database
            save_title = f"Fix {report.get('bug_category', 'Bug')} ({final_state.get('project_name', 'Project')})"
            save_debug_session(
                title=save_title,
                source_code=source_code if debug_mode == "Single File" else f"Project: {final_state.get('project_name')}",
                error_log=final_state.get("error_log", ""),
                bug_category=report.get("bug_category", ""),
                root_cause=report.get("root_cause", ""),
                fixed_code=report.get("fixed_code", "") if not report.get("patches") else json.dumps(report.get("patches")),
                verification_status=v_status,
                iterations=report.get("iterations_used", 1),
                language=active_language.capitalize(),
                project_name=final_state.get("project_name", "Single File")
            )
            st.toast("Saved session to SQLite database!", icon="💾")

        except Exception as e:
            st.error(f"Error during agent pipeline execution: {str(e)}")
            st.exception(e)
        finally:
            if active_temp_dir:
                WorkspaceManager.cleanup(active_temp_dir)
