from langgraph.graph import StateGraph, END
from orchestration.state import DebuggingState

# Import 7 Specialized Agents
from agents.code_analysis.agent import analyze_code_agent
from agents.bug_investigation.agent import investigate_bug_agent
from agents.root_cause.agent import analyze_root_cause_agent
from agents.fix_generation.agent import generate_fix_agent
from agents.testing.agent import test_code_agent
from agents.verification.agent import evaluate_verification_agent
from agents.supervisor.agent import supervisor_agent, should_continue

def build_debugging_graph():
    """
    Constructs and compiles the LangGraph autonomous debugging workflow graph.
    """
    workflow = StateGraph(DebuggingState)

    # 1. Add 7 Agent Nodes
    workflow.add_node("code_analysis", analyze_code_agent)
    workflow.add_node("bug_investigation", investigate_bug_agent)
    workflow.add_node("root_cause", analyze_root_cause_agent)
    workflow.add_node("fix_generation", generate_fix_agent)
    workflow.add_node("testing", test_code_agent)
    workflow.add_node("verification", evaluate_verification_agent)
    workflow.add_node("supervisor", supervisor_agent)

    # 2. Define Execution Edges
    workflow.set_entry_point("code_analysis")
    
    workflow.add_edge("code_analysis", "bug_investigation")
    workflow.add_edge("bug_investigation", "root_cause")
    workflow.add_edge("root_cause", "fix_generation")
    workflow.add_edge("fix_generation", "testing")
    workflow.add_edge("testing", "verification")
    workflow.add_edge("verification", "supervisor")

    # 3. Add Conditional Edge for Supervisor Retry Loop
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "end": END,
            "retry_fix": "fix_generation"
        }
    )

    # Compile the graph
    app = workflow.compile()
    return app


# Instantiated compiled graph
debugging_app = build_debugging_graph()
