import sys
import os
import json
import io
import tempfile
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
from utils.error_classifier import classify_error

# Set page config
st.set_page_config(
    page_title="Autonomous Debugging Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_demo_preset(preset_key: str) -> bool:
    """
    Helper to load a demo preset:
    Creates a real temporary source file on disk, populates session state, and sets demo_loaded = True.
    """
    if preset_key not in DEMO_EXAMPLES:
        st.error(f"Unknown preset key: '{preset_key}'")
        st.session_state["demo_loaded"] = False
        return False

    ex = DEMO_EXAMPLES[preset_key]
    lang = ex.get("language", "python")
    filename = ex.get("filename", "demo.py" if lang == "python" else "Main.java")
    code = ex.get("code", "")
    err_log = ex.get("error_log", "")
    test_code = ex.get("test_code", "")

    try:
        demo_dir = tempfile.mkdtemp(prefix="demo_workspace_")
        demo_file_path = os.path.join(demo_dir, filename)
        with open(demo_file_path, "w", encoding="utf-8") as f:
            f.write(code)

        st.session_state["demo_loaded"] = True
        st.session_state["demo_file_path"] = demo_file_path
        st.session_state["demo_file_name"] = filename
        st.session_state["demo_language"] = lang
        st.session_state["demo_source_code"] = code
        st.session_state["demo_error_log"] = err_log
        st.session_state["preset_test"] = test_code
        st.session_state["selected_demo_name"] = preset_key
        st.session_state["debug_mode"] = "Demo Presets"
        st.session_state["mode_radio"] = "Demo Presets"
        return True
    except Exception as e:
        st.error(f"Failed to create temporary demo source file: {str(e)}")
        st.session_state["demo_loaded"] = False
        return False

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
    [data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
        word-break: break-word !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #A0AEC0 !important;
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
    st.markdown("### 📚 Quick Demo Presets")
    
    sidebar_selected = st.selectbox(
        "Load preset single-file demo:",
        options=["Select demo..."] + list(DEMO_EXAMPLES.keys()),
        key="sidebar_demo_select"
    )
    if st.button("Load Single File Demo", type="secondary", key="sidebar_load_btn"):
        if sidebar_selected != "Select demo...":
            if load_demo_preset(sidebar_selected):
                st.success(f"Loaded '{sidebar_selected}' preset workspace!")
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
st.markdown('<div class="sub-header">Multi-Agent AI Pipeline with Error Classification Engine</div>', unsafe_allow_html=True)

# Mode Selector
if "debug_mode" not in st.session_state:
    st.session_state["debug_mode"] = "Upload Source File"

debug_mode = st.radio(
    "Select Debug Input Mode:",
    options=["Upload Source File", "Upload Project ZIP", "Demo Presets"],
    horizontal=True,
    key="debug_mode"
)

st.divider()

# Variable containers
active_project_path = None
active_temp_dir = None
active_language = "python"
active_build_system = "pytest"
source_code = ""
error_log = ""
uploaded_filename = "main.py"

if debug_mode == "Upload Source File":
    # --- REAL FILE UPLOAD MODE ---
    st.subheader("📄 Upload Source File (.py or .java)")
    st.caption("Select a standalone Python (`.py`) or Java (`.java`) source code file to classify and debug.")

    uploaded_src_file = st.file_uploader("Choose a source file", type=["py", "java"])

    if uploaded_src_file is not None:
        uploaded_filename = uploaded_src_file.name
        file_bytes = uploaded_src_file.read()
        try:
            source_code = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            source_code = file_bytes.decode("latin-1")

        # Detect Language from File Extension
        ext = os.path.splitext(uploaded_filename)[1].lower()
        if ext == ".py":
            active_language = "python"
            active_build_system = "pytest"
        elif ext == ".java":
            active_language = "java"
            active_build_system = "java-direct"
        else:
            st.error(f"Unsupported file extension '{ext}'. Only Python (.py) and Java (.java) source files are supported.")
            st.stop()

        # Display File Metadata Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Filename", uploaded_filename)
        c2.metric("Language", active_language.capitalize())
        c3.metric("File Size", f"{len(file_bytes)} bytes")
        c4.metric("Status", "Ready for Classification")

        st.markdown(f"**Source Code Preview (`{uploaded_filename}`):**")
        st.code(source_code, language=active_language)

    start_btn = st.button("🚀 Start Error Classification & Debugging", type="primary", use_container_width=True, disabled=(uploaded_src_file is None))

elif debug_mode == "Upload Project ZIP":
    # --- UPLOAD PROJECT ZIP MODE ---
    st.subheader("📦 Upload Complete Project (ZIP)")
    st.caption("Upload a `.zip` archive containing a multi-file Python or Java project.")

    uploaded_file = st.file_uploader("Choose a project ZIP file", type=["zip"])
    
    zip_bytes = None
    zip_filename = None

    if uploaded_file is not None:
        zip_bytes = uploaded_file.read()
        zip_filename = uploaded_file.name

    if zip_bytes is not None:
        temp_dir, project_root, extract_err = WorkspaceManager.extract_zip(io.BytesIO(zip_bytes))
        
        if extract_err:
            st.error(extract_err)
        else:
            active_temp_dir = temp_dir
            active_project_path = project_root
            uploaded_filename = zip_filename
            
            # Detect project
            detection_info = detect_project(project_root)
            
            if not detection_info.get("is_supported", False):
                st.error(detection_info.get("message", "Unsupported project format."))
                WorkspaceManager.cleanup(temp_dir)
                active_temp_dir = None
                active_project_path = None
            else:
                st.success("Project ZIP extracted and inspected successfully!")
                
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

    start_btn = st.button("🚀 Start Autonomous Project Debugging", type="primary", use_container_width=True, disabled=(active_project_path is None))

else:
    # --- DEMO PRESETS MODE ---
    st.subheader("📚 Demo & Preset Examples")
    st.caption("Select a built-in Python or Java demo preset to load a real temporary source file into the debugging pipeline.")
    
    preset_keys = list(DEMO_EXAMPLES.keys())
    current_preset = st.session_state.get("selected_demo_name", preset_keys[0])
    if current_preset not in preset_keys:
        current_preset = preset_keys[0]

    c_sel, c_btn = st.columns([3, 1])
    with c_sel:
        chosen_preset = st.selectbox(
            "Select Preset Example:",
            options=preset_keys,
            index=preset_keys.index(current_preset) if current_preset in preset_keys else 0,
            key="main_demo_select"
        )
    with c_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Load Single File Demo", type="primary", key="main_load_btn", use_container_width=True):
            if load_demo_preset(chosen_preset):
                st.rerun()

    demo_is_loaded = st.session_state.get("demo_loaded", False)
    demo_file_path = st.session_state.get("demo_file_path")

    # Verify that the demo temporary file actually exists on disk
    if demo_is_loaded and demo_file_path and os.path.exists(demo_file_path):
        active_language = st.session_state.get("demo_language", "python")
        uploaded_filename = st.session_state.get("demo_file_name", "demo.py")
        active_build_system = "pytest" if active_language == "python" else "java-direct"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preset Name", st.session_state.get("selected_demo_name", "Custom"))
        c2.metric("Filename", uploaded_filename)
        c3.metric("Language", active_language.capitalize())
        c4.metric("Status", "Workspace Ready ✅")

        col1, col2 = st.columns(2)
        with col1:
            source_code = st.text_area(
                f"{active_language.capitalize()} Source Code (`{uploaded_filename}`):",
                value=st.session_state.get("demo_source_code", ""),
                height=240,
                key="demo_src_text_area"
            )
            st.session_state["demo_source_code"] = source_code
            try:
                with open(demo_file_path, "w", encoding="utf-8") as f:
                    f.write(source_code)
            except Exception as e:
                st.warning(f"Could not sync edited code to disk: {e}")

        with col2:
            error_log = st.text_area(
                "Error Log / Stack Trace:",
                value=st.session_state.get("demo_error_log", ""),
                height=240,
                key="demo_err_text_area"
            )
            st.session_state["demo_error_log"] = error_log

        start_btn = st.button("🚀 Start Autonomous Debugging", type="primary", use_container_width=True, disabled=False, key="demo_start_btn")
    else:
        st.info("👈 Please select a preset example above and click **'Load Single File Demo'** to initialize the demo workspace.")
        st.session_state["demo_loaded"] = False
        start_btn = st.button("🚀 Start Autonomous Debugging", type="primary", use_container_width=True, disabled=True, key="demo_start_btn_disabled")


# --- WORKFLOW EXECUTION ---
if start_btn:
    st.divider()
    st.subheader("🔄 Error Classification & Multi-Agent Execution")
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Step 1: Resolve Active Project Path & Context based on Debug Input Mode
    if debug_mode == "Upload Source File":
        if not uploaded_src_file:
            st.error("No source file uploaded. Please upload a .py or .java file first.")
            st.stop()
        active_temp_dir = tempfile.mkdtemp(prefix="debug_workspace_")
        active_project_path = active_temp_dir
        file_path = os.path.join(active_temp_dir, uploaded_filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(source_code)

    elif debug_mode == "Demo Presets":
        demo_file_path = st.session_state.get("demo_file_path")
        if not demo_file_path or not os.path.exists(demo_file_path):
            if st.session_state.get("demo_source_code") and st.session_state.get("demo_file_name"):
                active_temp_dir = tempfile.mkdtemp(prefix="demo_workspace_")
                demo_file_path = os.path.join(active_temp_dir, st.session_state["demo_file_name"])
                with open(demo_file_path, "w", encoding="utf-8") as f:
                    f.write(st.session_state["demo_source_code"])
                st.session_state["demo_file_path"] = demo_file_path
            else:
                st.error("Demo workspace file is missing. Please click 'Load Single File Demo' again.")
                st.stop()
        
        active_project_path = os.path.dirname(demo_file_path)
        uploaded_filename = st.session_state.get("demo_file_name", "demo.py")
        active_language = st.session_state.get("demo_language", "python")
        source_code = st.session_state.get("demo_source_code", "")
        error_log = st.session_state.get("demo_error_log", "")
        active_build_system = "pytest" if active_language == "python" else "java-direct"

    elif debug_mode == "Upload Project ZIP":
        if not active_project_path or not os.path.exists(active_project_path):
            st.error("Invalid or missing project ZIP workspace. Please upload a project ZIP file first.")
            st.stop()

    # Step 2: Initial Execution Run
    status_text.text("Initial Execution: Running code & capturing execution outputs...")
    progress_bar.progress(10)

    if active_language == "java":
        init_adapter = JavaAdapter(active_project_path)
    else:
        init_adapter = PythonAdapter(active_project_path)

    if debug_mode == "Upload Project ZIP":
        init_exec = init_adapter.run_tests()
    else:
        init_exec = init_adapter.run_project()

    init_error_log = error_log if (error_log and debug_mode == "Demo Presets") else (init_exec.get("output") or init_exec.get("stderr") or "").strip()

    # Step 3: Run Error Classification Engine
    status_text.text("Running Error Classification Engine...")
    progress_bar.progress(20)

    classified_error = classify_error(
        language=active_language,
        source_code=source_code,
        execution_result=init_exec,
        error_log=init_error_log,
        test_results=init_exec
    )

    # Display Classified Error Card in UI
    st.subheader("📊 Error Classification Overview")
    
    ec1, ec2, ec3, ec4 = st.columns(4)
    ec1.metric("Category", classified_error.get("category", "UNKNOWN_ERROR"))
    ec2.metric("Error Type", classified_error.get("error_type", "None"))
    ec3.metric("Severity", classified_error.get("severity", "MEDIUM"))
    ec4.metric("Line Number", str(classified_error.get("line_number")) if classified_error.get("line_number") is not None else "N/A")

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Subtype", classified_error.get("subtype", "UNCLASSIFIED"))
    sc2.metric("Source Layer", classified_error.get("source", "unknown").capitalize())
    sc3.metric("Confidence", classified_error.get("confidence", "HIGH"))
    sc4.metric("Confirmed Error", "YES ❌" if classified_error.get("confirmed") else "NO ✅")

    if classified_error.get("evidence"):
        st.caption(f"**Evidence Snippet:** `{classified_error.get('evidence')}`")

    st.divider()

    # Step 4: Check Clean Code / No Error Condition
    if classified_error.get("category") == "NO_ERROR":
        progress_bar.progress(100)
        status_text.text("✅ Execution Completed Cleanly!")
        st.success("✓ NO ERROR DETECTED — Code executed cleanly without runtime, compilation, or test failures.")
        
        st.markdown("**Execution Output:**")
        st.code(init_exec.get("stdout") or "Program executed cleanly with no stdout output.", language="bash")
        
        st.info("Since the code executed cleanly and no confirmed error was classified, the autonomous fix-generation loop was not invoked.")

        # Cleanup workspace
        if active_temp_dir:
            WorkspaceManager.cleanup(active_temp_dir)
        st.stop()

    elif classified_error.get("category") == "POSSIBLE_ISSUE":
        st.warning(f"⚠️ Status: NO CONFIRMED ERROR — Possible issue noted: {classified_error.get('message')}")
        st.caption("The code runs without raising an exception, but static analysis detected a potential smell.")

    # Step 5: Construct Initial Execution State for 7-Agent Pipeline
    initial_state = {
        "input_mode": "single_file" if debug_mode != "Upload Project ZIP" else "project",
        "project_path": active_project_path,
        "project_name": uploaded_filename,
        "language": active_language,
        "build_system": active_build_system,
        "source_code": source_code,
        "error_log": init_error_log if init_error_log else "Execution failure",
        "execution_result": init_exec,
        "classified_error": classified_error,
        "test_code": st.session_state.get("preset_test", None),
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
        status_text.text("1/7 Code Analysis Agent inspecting code structure...")
        progress_bar.progress(30)
        
        # Execute LangGraph workflow
        final_state = debugging_app.invoke(initial_state)
        progress_bar.progress(100)
        status_text.text("✅ Autonomous Debugging Pipeline Complete!")

        st.success("Workflow Execution Finished Successfully!")

        # --- DISPLAY 7 AGENTS DETAILS ---
        st.subheader("🧩 Specialized Agent Details")

        # 0. Error Classifier
        with st.expander("📊 Error Classification Engine Details", expanded=True):
            st.json(classified_error)

        # 1. Code Analysis
        with st.expander("🔍 1. Code Analysis Agent", expanded=True):
            ca = final_state.get("code_analysis", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("File / Project", uploaded_filename)
            c2.metric("Language", final_state.get("language", active_language).capitalize())
            c3.metric("Source Files", len(ca.get("source_files", [])) or 1)
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
        st.subheader("📊 Final Debugging Report & Code Diff")

        report = final_state.get("final_report", {})
        v_status = report.get("status", "UNVERIFIED")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Verification Status", v_status)
        m2.metric("Iterations Used", report.get("iterations_used", 1))
        m3.metric("Bug Category", classified_error.get("category") or report.get("bug_category", "Unknown"))
        m4.metric("Tests Passed", f"{report.get('tests_passed', 0)} / {report.get('tests_passed', 0) + report.get('tests_failed', 0)}")

        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            st.markdown(f"#### ❌ Original File (`{uploaded_filename}`)")
            if source_code:
                st.code(source_code, language=active_language)
            else:
                st.code(final_state.get("error_log", "Execution Log"), language="text")

        with comp_col2:
            st.markdown(f"#### ✅ Fixed File (`{uploaded_filename}`)")
            if report.get("patches"):
                for p in report.get("patches"):
                    st.code(p.get("changes", ""), language=active_language)
            elif report.get("fixed_code"):
                st.code(report.get("fixed_code"), language=active_language)

        # Save session to SQLite database
        save_title = f"Fix {classified_error.get('category', 'Bug')} ({uploaded_filename})"
        save_debug_session(
            title=save_title,
            source_code=source_code if source_code else f"File: {uploaded_filename}",
            error_log=final_state.get("error_log", ""),
            bug_category=classified_error.get("category", "Bug"),
            root_cause=report.get("root_cause", ""),
            fixed_code=report.get("fixed_code", "") if not report.get("patches") else json.dumps(report.get("patches")),
            verification_status=v_status,
            iterations=report.get("iterations_used", 1),
            language=active_language.capitalize(),
            project_name=uploaded_filename
        )
        st.toast("Saved debug session to SQLite database!", icon="💾")

    except Exception as e:
        st.error(f"Error during agent pipeline execution: {str(e)}")
        st.exception(e)
    finally:
        if active_temp_dir:
            WorkspaceManager.cleanup(active_temp_dir)
