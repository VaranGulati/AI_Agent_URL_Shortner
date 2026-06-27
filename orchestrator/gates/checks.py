import re
import ast

def check_requirements_entry(state: dict) -> tuple[bool, str]:
    reqs = state.get("requirements", "")
    if not reqs or len(reqs.strip()) < 10:
        return False, "Requirements are empty or too short."
    return True, ""

def check_design_exit(architecture: dict) -> tuple[bool, str]:
    if not architecture:
        return False, "Architecture object is empty."
    if "components" not in architecture:
        return False, "Architecture is missing 'components' field."
    return True, ""

def check_decomposition_exit(tasks: list) -> tuple[bool, str]:
    if not tasks or len(tasks) == 0:
        return False, "No tasks generated."
    for idx, t in enumerate(tasks):
        if "description" not in t or "filename" not in t:
            return False, f"Task {idx} missing description or filename."
    return True, ""

def check_implementation_exit(code_dict: dict) -> tuple[bool, str]:
    for filename, code in code_dict.items():
        # 1. AST check for syntax errors in python files
        if filename.endswith(".py"):
            try:
                ast.parse(code)
            except SyntaxError as e:
                return False, f"Syntax error in {filename}: {str(e)}"
        
        # 2. Hardcoded secrets check
        # Look for typical patterns like API_KEY = "..." or password = '...'
        secret_patterns = [
            r"(?i)(api_key|password|secret|token)\s*=\s*['\"][a-zA-Z0-9_\-]+['\"]"
        ]
        for pattern in secret_patterns:
            if re.search(pattern, code):
                return False, f"Potential hardcoded secret found in {filename}."
                
    return True, ""

def check_testing_exit(state: dict) -> tuple[bool, str]:
    # In a real scenario, this would run `pytest` via subprocess and check the return code.
    # For the prototype, if tests_code is populated, we simulate success for now.
    tests = state.get("tests_code", {})
    if not tests:
        return False, "No tests were generated."
    return True, ""
