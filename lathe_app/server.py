"""
Lathe App HTTP Server

Thin HTTP adapter exposing lathe_app to external tools like OpenWebUI.

OpenWebUI Tool Definitions:
--------------------------
Tool 1: lathe_agent
{
  "name": "lathe_agent",
  "description": "Create a new Lathe run (propose, think, rag, plan)",
  "parameters": {
    "type": "object",
    "properties": {
      "intent": {"type": "string", "enum": ["propose", "think", "rag", "plan"]},
      "task": {"type": "string", "description": "The task to execute"},
      "why": {"type": "object", "description": "WHY record with goal, context, etc."},
      "model": {"type": "string", "description": "Optional model override"}
    },
    "required": ["intent", "task", "why"]
  }
}

Tool 2: lathe_execute
{
  "name": "lathe_execute",
  "description": "Execute a proposal from a previous run",
  "parameters": {
    "type": "object",
    "properties": {
      "run_id": {"type": "string", "description": "ID of the run to execute"},
      "dry_run": {"type": "boolean", "description": "If true, preview only", "default": true}
    },
    "required": ["run_id"]
  }
}
--------------------------

Endpoints:
  POST /agent      - Create a run
  POST /execute    - Execute a proposal
  GET  /health     - Health check
  GET  /runs       - List all runs
  GET  /runs/<id>  - Load a specific run
"""
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import lathe_app
from lathe_app.http_serialization import (
    to_jsonable_runrecord,
    to_jsonable_execution_result,
)

logger = logging.getLogger(__name__)


def make_refusal(reason: str, details: str = "") -> Dict[str, Any]:
    """Create a structured refusal response."""
    return {
        "refusal": True,
        "reason": reason,
        "details": details,
        "results": [],
    }


def make_error_response(message: str) -> Dict[str, Any]:
    """Create a generic error response (still structured, no tracebacks)."""
    return make_refusal(reason="error", details=message)


class AppHandler(BaseHTTPRequestHandler):
    """HTTP request handler for lathe_app endpoints."""
    
    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)
    
    def send_json(self, data: Dict[str, Any], status: int = 200):
        """Send a JSON response."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def read_json_body(self) -> Optional[Dict[str, Any]]:
        """Read and parse JSON from request body."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, ValueError) as e:
            return None
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            
            if path == "/health":
                self.send_json({"ok": True, "results": []})
            elif path == "/runs":
                runs = lathe_app.list_runs()
                self.send_json({"runs": runs, "results": []})
            elif path.startswith("/runs/"):
                run_id = path[6:]
                run = lathe_app.load_run(run_id)
                if run is None:
                    self.send_json(make_refusal("not_found", f"Run {run_id} not found"), 404)
                else:
                    self.send_json(to_jsonable_runrecord(run))
            else:
                self.send_json(make_refusal("not_found", f"Unknown path: {path}"), 404)
        except Exception as e:
            logger.exception("Error in GET handler")
            self.send_json(make_error_response(str(e)), 500)
    
    def do_POST(self):
        """Handle POST requests."""
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            
            body = self.read_json_body()
            if body is None:
                self.send_json(make_refusal("invalid_json", "Request body must be valid JSON"), 400)
                return
            
            if path == "/agent":
                self.handle_agent(body)
            elif path == "/execute":
                self.handle_execute(body)
            else:
                self.send_json(make_refusal("not_found", f"Unknown path: {path}"), 404)
        except Exception as e:
            logger.exception("Error in POST handler")
            self.send_json(make_error_response(str(e)), 500)
    
    def handle_agent(self, body: Dict[str, Any]):
        """Handle POST /agent - create a new run."""
        intent = body.get("intent")
        task = body.get("task")
        why = body.get("why")
        model = body.get("model")
        
        missing = []
        if not intent:
            missing.append("intent")
        if not task:
            missing.append("task")
        if why is None:
            missing.append("why")
        
        if missing:
            self.send_json(
                make_refusal("missing_fields", f"Missing required fields: {', '.join(missing)}"),
                400
            )
            return
        
        run = lathe_app.run_request(
            intent=intent,
            task=task,
            why=why,
            model=model,
        )
        
        response = to_jsonable_runrecord(run)
        self.send_json(response)
    
    def handle_execute(self, body: Dict[str, Any]):
        """Handle POST /execute - execute a proposal."""
        run_id = body.get("run_id")
        dry_run = body.get("dry_run", True)
        
        if not run_id:
            self.send_json(make_refusal("missing_fields", "Missing required field: run_id"), 400)
            return
        
        result = lathe_app.execute_proposal(run_id, dry_run=dry_run)
        response = to_jsonable_execution_result(result)
        self.send_json(response)


def create_server(host: str = "0.0.0.0", port: int = 3000) -> HTTPServer:
    """Create the HTTP server instance."""
    server = HTTPServer((host, port), AppHandler)
    return server


def run_server(host: str = "0.0.0.0", port: int = 3000):
    """Run the HTTP server."""
    server = create_server(host, port)
    logger.info(f"Lathe App Server listening on {host}:{port}")
    print(f"Lathe App Server listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down")
        server.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()
