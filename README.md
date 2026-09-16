# Autonomous Software Debugging Agent (Multi-Language & ZIP Project Support)

An agentic AI system built in Python using **LangGraph**, **Streamlit**, **Language Adapters (Python & Java)**, **PyTest**, **Maven/Gradle**, **SQLite**, and **Google Gemini API** that autonomously analyzes buggy single-file code or complete software projects, investigates stack traces/compilation errors, identifies root causes, generates targeted patches, executes automated unit test suites in an isolated sandbox, and verifies solutions.

---

## 1. Supported Languages & Input Modes

### Supported Languages
- **Python**: `.py`, `requirements.txt`, `pyproject.toml`, `setup.py` (via `pytest` runner or entry file fallback)
- **Java**: `.java`, `pom.xml`, `build.gradle`, `build.gradle.kts` (via Maven `mvn`/`mvnw`, Gradle `gradle`/`gradlew`, or direct `javac`/`java`)

### Input Modes
1. **Single File**: Paste Python source code & error log directly in the Streamlit editor.
2. **ZIP Project Upload**: Upload a full `.zip` project archive containing multi-file Python or Java code bases.

---

## 2. High-Level Architecture & Workflow

```
User
  │
  ▼
Streamlit Upload UI (Single File / ZIP Upload)
  │
  ▼
Workspace Manager (Safe ZIP Extraction & Path Traversal Guard)
  │
  ▼
Project Detector (Language, Build System, Source/Test Dirs)
  │
  ▼
Language Adapter (PythonAdapter / JavaAdapter)
  │
  ▼
LangGraph Orchestration Engine (7-Agent Workflow)
  ├── 1. Code Analysis Agent
  ├── 2. Bug Investigation Agent
  ├── 3. Root Cause Agent
  ├── 4. Fix Generation Agent
  ├── 5. Testing Agent (Executes Adapter build/tests)
  ├── 6. Verification Agent (Evaluates test/build results)
  └── 7. Supervisor Agent (Retry loop control & report compiling)
  │
  ▼
Final Report & SQLite Session History
```

---

## 3. The 7 Specialized Agents

| # | Agent Name | Location | Responsibility |
|---|------------|----------|----------------|
| 1 | **Supervisor Agent** | `agents/supervisor/` | Manages state, iteration loop bounds (max 3 retries), and compiles final reports. |
| 2 | **Code Analysis Agent** | `agents/code_analysis/` | Parses single-file AST or analyzes multi-file project structure & manifests. |
| 3 | **Bug Investigation Agent** | `agents/bug_investigation/` | Pinpoints error locations from stack traces, tracebacks, or compilation logs. |
| 4 | **Root Cause Agent** | `agents/root_cause/` | Diagnoses underlying bug logic (`NullPointerException`, `ZeroDivisionError`, `IndexError`, etc.). |
| 5 | **Fix Generation Agent** | `agents/fix_generation/` | Generates candidate code fixes and multi-file patches (`file`, `changes`, `reason`). |
| 6 | **Testing Agent** | `agents/testing/` | Executes `pytest`, Maven (`mvn test`), or Gradle (`gradle test`) via Language Adapters. |
| 7 | **Verification Agent** | `agents/verification/` | Compares pre- and post-fix build/test results to verify fix correctness. |

---

## 4. Technology Stack
- **Languages Supported**: Python 3.10+, Java (JDK 11+)
- **Orchestration**: LangGraph, LangChain Core
- **LLM Engine**: Google Gemini API (`google-genai` / `gemini-2.5-flash`)
- **Frontend UI**: Streamlit
- **Build & Test Tools**: PyTest, Maven (`mvn`/`mvnw`), Gradle (`gradle`/`gradlew`), `javac`
- **Database**: SQLite3 (`debug_history.db`)
- **Environment**: `python-dotenv`

---

## 5. Project Directory Structure

```
Autonomous_Debugging_Agent/
├── .env.example                # API key template
├── .gitignore                  # Git exclusion rules
├── README.md                   # Main documentation
├── requirements.txt            # Python dependencies
├── demo_examples.py            # Pre-packaged demo presets (Single file & ZIP projects)
├── utils/
│   ├── __init__.py
│   ├── llm.py                  # Gemini API client & Mock fallback logic
│   └── workspace.py            # Safe ZIP extraction & temporary workspace management
├── language_adapters/          # Language Adapter System
│   ├── __init__.py
│   ├── base_adapter.py         # Abstract Base Language Adapter interface
│   ├── detector.py             # Automatic language & build system detector
│   ├── python/
│   │   ├── __init__.py
│   │   └── adapter.py          # Python language adapter
│   └── java/
│       ├── __init__.py
│       └── adapter.py          # Java language adapter (Maven, Gradle, javac)
├── database/
│   ├── __init__.py
│   ├── database.py             # SQLite persistence helpers
│   └── debug_history.db        # Session history database
├── orchestration/
│   ├── __init__.py
│   ├── state.py                # Shared DebuggingState schema
│   └── graph.py                # StateGraph compiled workflow
├── agents/                     # 7 Specialized Agents
│   ├── supervisor/
│   ├── code_analysis/
│   ├── bug_investigation/
│   ├── root_cause/
│   ├── fix_generation/
│   ├── testing/
│   └── verification/
└── frontend/
    └── streamlit_app.py        # Streamlit web dashboard UI
```

---

## 6. Example Project Structure for ZIP Upload

### Python Project ZIP Example
```
python_bug_project.zip
├── main.py                     # Source code containing bug
├── test_main.py                # PyTest suite
└── requirements.txt            # Project dependencies
```

### Java Maven Project ZIP Example
```
java_bug_project.zip
├── pom.xml                     # Maven project descriptor
└── src/
    ├── main/java/com/example/
    │   └── UserService.java    # Java class containing bug
    └── test/java/com/example/
        └── UserServiceTest.java# Java test suite
```

---

## 7. Installation & Setup

1. **Clone or Open Project**:
   ```bash
   cd Autonomous_Debugging_Agent
   ```

2. **Create & Activate Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and add your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
   > *Note: If no API key is provided, the system automatically runs in **Mock Mode**, using intelligent fallback analyzers so the app can be demonstrated immediately without external API dependency.*

---

## 8. How to Run the Application

Launch the Streamlit UI dashboard:
```bash
streamlit run frontend/streamlit_app.py
```
Open your browser to `http://localhost:8501`.

---

## 9. Troubleshooting Guide

| Issue / Symptom | Possible Cause | Resolution |
|-----------------|----------------|------------|
| **Python not installed** | Python missing from system `PATH`. | Install Python 3.10+ and add to `PATH`. |
| **Java not installed** | JDK missing for Java project debugging. | Install Java JDK 11+ and verify `javac -version` on terminal. |
| **Maven / Gradle not found** | `mvn` or `gradle` binary missing from system `PATH`. | Include project wrappers (`mvnw`/`mvnw.cmd` or `gradlew`/`gradlew.bat`) inside your ZIP archive or install Maven/Gradle CLI. |
| **PyTest not installed** | `pytest` missing from Python environment. | Run `pip install pytest`. |
| **Gemini API unavailable** | Key missing or quota exceeded. | The system gracefully switches to **Mock Mode**; no app crash occurs. |
