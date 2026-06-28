import json
from .llm import invoke_agent
from ..gates.checks import (
    check_requirements_entry, check_design_exit, 
    check_decomposition_exit, check_implementation_exit, check_testing_exit
)
from ..engine.metrics import MetricsLogger
import time

import re

def extract_json(text: str) -> dict | list:
    """Helper to safely extract json from markdown or raw text (supports objects and lists)."""
    try:
        # Strip markdown code blocks if any
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        
        # Find first occurrence of either '{' or '['
        start_brace = cleaned.find("{")
        start_bracket = cleaned.find("[")
        
        if start_brace == -1 and start_bracket == -1:
            return {}
            
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            start = start_brace
            closing_char = '}'
        else:
            start = start_bracket
            closing_char = ']'
            
        json_candidate = cleaned[start:]
        # Find all closing characters
        braces = [i for i, char in enumerate(json_candidate) if char == closing_char]
        
        # Try parsing from the rightmost closing character leftwards
        for idx in reversed(braces):
            try:
                candidate = json_candidate[:idx + 1]
                # Clean trailing commas
                candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        return {}
    except Exception as e:
        print(f"[Parser Error] Failed to extract JSON: {e}")
        return {}

def requirements_node(state: dict):
    logger = MetricsLogger(state["run_id"])
    logger.log_event("Requirements", "START")
    start_t = time.time()
    
    passed, msg = check_requirements_entry(state)
    if not passed:
        logger.log_event("Requirements", "FAIL", error_msg=msg)
        state["errors"].append(f"Req Entry Failed: {msg}")
        return state

    prompt = f"Analyze these requirements and output a clean JSON with 'problem_statement' and 'core_features' list. Reqs: {state['requirements']}"
    mock_resp = '{"problem_statement": "Build a lean URL shortener API", "core_features": ["shorten URL", "redirect"]}'
    
    res = invoke_agent("You are an expert PM.", prompt, mock_resp)
    
    parsed = extract_json(res)
    duration = int((time.time() - start_t) * 1000)
    
    if "problem_statement" in parsed:
        state["requirements"] = parsed["problem_statement"]
        logger.log_event("Requirements", "SUCCESS", duration_ms=duration)
    else:
        logger.log_event("Requirements", "FAIL", duration_ms=duration, error_msg="Invalid JSON")
        state["errors"].append("Requirements parsing failed.")
        
    return state

def design_node(state: dict):
    logger = MetricsLogger(state["run_id"])
    logger.log_event("Design", "START")
    start_t = time.time()
    
    prompt = (
        f"Design the architecture changes for this requirement: {state['requirements']}.\n"
        f"Output your design strictly in JSON format. Do not write any conversational text before or after the JSON.\n"
        f"Example JSON structure:\n"
        f"{{\n"
        f"  \"components\": [\n"
        f"    {{\"name\": \"Database Schema\", \"description\": \"Add a clicks column to URLMap\", \"filename\": \"app/main.py\"}}\n"
        f"  ]\n"
        f"}}\n"
    )
    mock_resp = '{"components": ["app/main.py", "app/database.py"]}'
    
    res = invoke_agent("You are a Software Architect.", prompt, mock_resp)
    parsed = extract_json(res)
    duration = int((time.time() - start_t) * 1000)
    
    passed, msg = check_design_exit(parsed)
    if not passed:
        print(f"\n[DEBUG] Design Failed Exit Check.")
        print(f"Raw LLM Response:\n{res}\n")
        print(f"Parsed Object: {parsed}\n")
        logger.log_event("Design", "FAIL", duration_ms=duration, error_msg=msg)
        state["errors"].append(f"Design Exit Failed: {msg}")
    else:
        state["architecture"] = parsed
        logger.log_event("Design", "SUCCESS", duration_ms=duration)
        
    return state

def decomposition_node(state: dict):
    logger = MetricsLogger(state["run_id"])
    logger.log_event("Decomposition", "START")
    start_t = time.time()
    
    prompt = f"Decompose this architecture into coding tasks. Architecture: {json.dumps(state['architecture'])}. Output JSON list of objects with 'description' and 'filename'."
    mock_resp = '{"tasks": [{"description": "Create FastAPI app", "filename": "app/main.py"}, {"description": "DB connection", "filename": "app/database.py"}]}'
    
    res = invoke_agent("You are an Engineering Manager.", prompt, mock_resp)
    parsed = extract_json(res)
    duration = int((time.time() - start_t) * 1000)
    
    # Handle both dict with 'tasks' key and direct list outputs
    tasks = []
    if isinstance(parsed, list):
        tasks = parsed
    elif isinstance(parsed, dict):
        tasks = parsed.get("tasks", [])
        
    passed, msg = check_decomposition_exit(tasks)
    
    if not passed:
        print(f"\n[DEBUG] Decomposition Failed Exit Check.")
        print(f"Raw LLM Response:\n{res}\n")
        print(f"Parsed Object: {parsed}\n")
        logger.log_event("Decomposition", "FAIL", duration_ms=duration, error_msg=msg)
        state["errors"].append(f"Decomposition Exit Failed: {msg}")
    else:
        state["tasks"] = tasks
        logger.log_event("Decomposition", "SUCCESS", duration_ms=duration)
        
    return state

def implementation_node(state: dict):
    logger = MetricsLogger(state["run_id"])
    logger.log_event("Implementation", "START")
    start_t = time.time()
    
    code_dict = {}
    feedback = state.get("gate_feedback", "")
    for task in state["tasks"]:
        prompt = f"Write Python code for this task: {task['description']}. Context: {json.dumps(state['architecture'])}."
        if feedback:
            prompt += f"\nNOTE: The previous code generation attempt failed validation check with this error: {feedback}. Please correct the code to resolve this issue."
        prompt += "\nONLY output the raw code, no markdown wrappers."
        mock_code = f"# Mock implementation for {task['filename']}\nprint('hello')\n"
        
        res = invoke_agent("You are a Senior Python Developer.", prompt, mock_code)
        # Clean up markdown if llm ignored instructions
        res = res.replace("```python", "").replace("```", "").strip()
        code_dict[task["filename"]] = res
        time.sleep(1.0)

    duration = int((time.time() - start_t) * 1000)
    
    passed, msg = check_implementation_exit(code_dict)
    if not passed:
        retries = state.get("retry_count", 0)
        if retries < 3:
            state["retry_count"] = retries + 1
            state["gate_feedback"] = msg
            logger.log_event("Implementation", "RETRY", duration_ms=duration, error_msg=msg)
            print(f"\n[ORCHESTRATOR] Implementation validation failed. Retrying (Attempt {state['retry_count']}/3)...")
        else:
            logger.log_event("Implementation", "FAIL", duration_ms=duration, error_msg=msg)
            state["errors"].append(f"Implementation Exit Failed after 3 retries: {msg}")
    else:
        state["implementation_code"] = code_dict
        state["gate_feedback"] = ""
        state["retry_count"] = 0
        state["errors"] = [e for e in state.get("errors", []) if "Implementation Exit Failed" not in e]
        logger.log_event("Implementation", "SUCCESS", duration_ms=duration)
        
    return state

def generate_stub(code: str) -> str:
    """Uses AST to extract class fields and function/endpoint signatures, stripping function bodies to fit token limits."""
    try:
        import ast
        tree = ast.parse(code)
        stub_lines = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                decorators = "".join([f"@{ast.unparse(d)}\n" for d in node.decorator_list])
                stub_lines.append(f"{decorators}class {node.name}:")
                has_body = False
                for body_node in node.body:
                    if isinstance(body_node, ast.AnnAssign):  # Pydantic fields / typed attributes
                        stub_lines.append(f"    {ast.unparse(body_node)}")
                        has_body = True
                    elif isinstance(body_node, ast.FunctionDef):  # Class methods
                        method_decs = "".join([f"    @{ast.unparse(d)}\n" for d in body_node.decorator_list])
                        args = ast.unparse(body_node.args)
                        stub_lines.append(f"{method_decs}    def {body_node.name}({args}): ...")
                        has_body = True
                if not has_body:
                    stub_lines.append("    pass")
                stub_lines.append("")
            elif isinstance(node, ast.FunctionDef):
                decorators = "".join([f"@{ast.unparse(d)}\n" for d in node.decorator_list])
                args = ast.unparse(node.args)
                stub_lines.append(f"{decorators}def {node.name}({args}): ...\n")
        return "\n".join(stub_lines)
    except Exception:
        # Fallback to truncation if AST parsing fails
        return code[:800] + "\n... [TRUNCATED due to token limits] ..."

def testing_node(state: dict):
    logger = MetricsLogger(state["run_id"])
    logger.log_event("Testing", "START")
    start_t = time.time()
    
    # Construct stubbed code context for the testing agent to fit the 8000 token limit
    code_context = ""
    for fname, code in state.get("implementation_code", {}).items():
        if fname.endswith(".py"):
            stubbed = generate_stub(code)
            code_context += f"\n\n# --- Stubbed File: {fname} ---\n{stubbed}\n"
        else:
            # Exclude non-python files from context to save tokens
            pass
        
    prompt = (
        f"Write a Pytest test suite using FastAPI's TestClient to test the following generated code.\n"
        f"Strictly only use imports, models, database sessions, and endpoints defined in the code below. "
        f"Do not assume any external config modules, sqlmodel, or auth systems unless they exist in the code below.\n"
        f"Generated Code Context (Signatures & Stubs):{code_context}\n\n"
        f"ONLY output the raw python code for the test suite, no markdown block wrappers."
    )
    mock_code = "def test_mock(): assert True\n"
    
    res = invoke_agent("You are an SDET.", prompt, mock_code)
    res = res.replace("```python", "").replace("```", "").strip()
    
    duration = int((time.time() - start_t) * 1000)
    
    state["tests_code"] = {"tests/test_main.py": res}
    passed, msg = check_testing_exit(state)
    
    if not passed:
        logger.log_event("Testing", "FAIL", duration_ms=duration, error_msg=msg)
        state["errors"].append(f"Testing Exit Failed: {msg}")
    else:
        logger.log_event("Testing", "SUCCESS", duration_ms=duration)
        
    return state

def release_readiness_node(state: dict):
    logger = MetricsLogger(state["run_id"])
    logger.log_event("ReleaseReadiness", "START")
    start_t = time.time()
    
    import os
    product_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../product"))
    os.makedirs(product_dir, exist_ok=True)
    
    # Write code to product dir
    for fname, code in state.get("implementation_code", {}).items():
        path = os.path.join(product_dir, fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
            
    for fname, code in state.get("tests_code", {}).items():
        path = os.path.join(product_dir, fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

    duration = int((time.time() - start_t) * 1000)
    logger.log_event("ReleaseReadiness", "SUCCESS", duration_ms=duration)
    return state
