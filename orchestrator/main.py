import uuid
import json
import argparse
from .engine.graph import build_graph
from .engine.state import init_db, Run, Stage

def main():
    parser = argparse.ArgumentParser(description="Agentic SDLC Orchestrator")
    parser.add_argument("--requirement", type=str, required=True, help="The initial requirement text")
    parser.add_argument("--scenario", type=str, default="greenfield", help="Scenario type")
    args = parser.parse_args()

    run_id = str(uuid.uuid4())
    print(f"Starting SDLC Orchestrator. Run ID: {run_id}")
    
    # Init DB
    session = init_db()
    db_run = Run(id=run_id, scenario=args.scenario)
    session.add(db_run)
    session.commit()

    graph = build_graph()
    
    initial_state = {
        "run_id": run_id,
        "scenario": args.scenario,
        "requirements": args.requirement,
        "architecture": {},
        "tasks": [],
        "implementation_code": {},
        "tests_code": {},
        "docs": {},
        "errors": [],
        "gate_feedback": "",
        "retry_count": 0,
        "current_stage": "Requirements",
        "db_path": "sqlite:///runs/state.sqlite"
    }

    print("\n--- Invoking DAG ---")
    final_state = graph.invoke(initial_state)
    
    print("\n\n--- Execution Finished ---")
    if final_state.get("errors"):
        print("Completed with errors:")
        for e in final_state["errors"]:
            print(f"- {e}")
            
    # Persist final run state
    db_run.status = "FAILED" if final_state.get("errors") else "SUCCESS"
    session.commit()
    
    print(f"\nReview logs in runs/run_{run_id}/events.jsonl")
    
if __name__ == "__main__":
    main()
