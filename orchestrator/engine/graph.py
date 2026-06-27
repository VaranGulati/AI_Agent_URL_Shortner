from langgraph.graph import StateGraph, END
from .state import GraphState
from ..agents.nodes import (
    requirements_node, design_node, decomposition_node, 
    implementation_node, testing_node, release_readiness_node
)

def build_graph():
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("Requirements", requirements_node)
    workflow.add_node("Design", design_node)
    workflow.add_node("Decomposition", decomposition_node)
    workflow.add_node("Implementation", implementation_node)
    workflow.add_node("Testing", testing_node)
    workflow.add_node("ReleaseReadiness", release_readiness_node)
    
    # Add edges
    workflow.set_entry_point("Requirements")
    
    def check_errors(state):
        if state.get("errors"):
            return "Fail"
        return "Pass"
        
    def check_design_approval(state):
        if state.get("errors"):
            return "Fail"
        print("\n\n--- HUMAN APPROVAL CHECKPOINT: POST-DESIGN ---")
        print(f"Proposed Architecture: {state.get('architecture')}")
        print(f"Tasks: {state.get('tasks')}")
        ans = input("Approve? [y/N]: ")
        if ans.lower() == 'y':
            return "Pass"
        return "Fail"
        
    workflow.add_conditional_edges("Requirements", check_errors, {"Pass": "Design", "Fail": END})
    workflow.add_conditional_edges("Design", check_errors, {"Pass": "Decomposition", "Fail": END})
    workflow.add_conditional_edges("Decomposition", check_design_approval, {"Pass": "Implementation", "Fail": END})
    workflow.add_conditional_edges("Implementation", check_errors, {"Pass": "Testing", "Fail": END})
    workflow.add_conditional_edges("Testing", check_errors, {"Pass": "ReleaseReadiness", "Fail": END})
    workflow.add_edge("ReleaseReadiness", END)
    
    return workflow.compile()
