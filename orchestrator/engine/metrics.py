import json
import os
import time
from datetime import datetime

class MetricsLogger:
    def __init__(self, run_id: str, log_dir: str = "runs"):
        self.run_id = run_id
        # Creates a run specific log directory
        self.run_dir = os.path.join(log_dir, f"run_{run_id}")
        os.makedirs(self.run_dir, exist_ok=True)
        self.log_file = os.path.join(self.run_dir, "events.jsonl")
    
    def log_event(self, stage_name: str, event_type: str, duration_ms: int = 0, tokens_used: int = 0, error_msg: str = ""):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": self.run_id,
            "stage_name": stage_name,
            "event_type": event_type, # START, SUCCESS, FAIL, RETRY, ROLLBACK, APPROVAL_WAIT
            "duration_ms": duration_ms,
            "tokens_used": tokens_used,
            "error_msg": error_msg
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
