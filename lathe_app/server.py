"""
Lathe App HTTP Server

Thin HTTP adapter exposing lathe_app to external tools like OpenWebUI.

Port assignments:
- OpenWebUI → 3000 (external, not managed here)
- Lathe App → 3001 (default)

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
  "description": "Execute an approved proposal from a previous run",
  "parameters": {
    "type": "object",
    "properties": {
      "run_id": {"type": "string", "description": "ID of the run to execute"},
      "dry_run": {"type": "boolean", "description": "If true, preview only", "default": true}
    },
    "required": ["run_id"]
  }
}

Tool 3: lathe_runs
{
  "name": "lathe_runs",
  "description": "Search and query run history (read-only)",
  "parameters": {
    "type": "object",
    "properties": {
      "intent": {"type": "string", "description": "Filter by intent type"},
      "outcome": {"type": "string", "enum": ["success", "refusal"]},
      "file": {"type": "string", "description": "Filter by file path touched"},
      "since": {"type": "string", "description": "ISO timestamp lower bound"},
      "until": {"type": "string", "description": "ISO timestamp upper bound"},
      "limit": {"type": "integer", "default": 100}
    }
  }
}

Tool 4: lathe_review
{
  "name": "lathe_review",
  "description": "Review, approve, or reject a proposal",
  "parameters": {
    "type": "object",
    "properties": {
      "run_id": {"type": "string", "description": "ID of the run to review"},
      "action": {"type": "string", "enum": ["review", "approve", "reject"]},
      "comment": {"type": "string", "description": "Optional review comment"}
    },
    "required": ["run_id", "action"]
  }
}

Tool 5: lathe_fs
{
  "name": "lathe_fs",
  "description": "Read-only filesystem inspection (tree, git status, diff)",
  "parameters": {
    "type": "object",
    "properties": {
      "operation": {"type": "string", "enum": ["tree", "status", "diff"]},
      "path": {"type": "string", "description": "Path for tree operation", "default": "."},
      "staged": {"type": "boolean", "description": "Show staged diff", "default": false}
    },
    "required": ["operation"]
  }
}
--------------------------

Endpoints:
  POST /agent      - Create a run
  POST /execute    - Execute an approved proposal
  POST /review     - Review/approve/reject a proposal
  GET  /health     - Health check
  GET  /runs       - List/search runs
  GET  /runs/<id>  - Load a specific run
  GET  /runs/<id>/review - Get review state
  GET  /fs/tree    - Directory tree (read-only)
  GET  /fs/status  - Git status (read-only)
  GET  /fs/diff    - Git diff (read-only)
  GET  /fs/run/<id>/files - Files touched by run
  GET  /knowledge/status - Knowledge index status
  POST /knowledge/ingest - Ingest documents into knowledge index
  GET  /workspace/list   - List all workspaces
  POST /workspace/create - Create a new workspace
"""
import json
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

import lathe_app
from lathe_app.http_serialization import (
    to_jsonable_runrecord,
    to_jsonable_execution_result,
    to_jsonable_query_result,
    to_jsonable_review_result,
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
            query = parse_qs(parsed.query)
            
            if path == "/health":
                self.send_json({"ok": True, "results": []})
            elif path == "/runs":
                self.handle_runs_query(query)
            elif path.startswith("/runs/") and "/review" in path:
                run_id = path.split("/")[2]
                self.handle_get_review(run_id)
            elif path.startswith("/runs/"):
                run_id = path[6:]
                run = lathe_app.load_run(run_id)
                if run is None:
                    self.send_json(make_refusal("not_found", f"Run {run_id} not found"), 404)
                else:
                    self.send_json(to_jsonable_runrecord(run))
            elif path == "/fs/tree":
                self.handle_fs_tree(query)
            elif path == "/fs/status":
                result = lathe_app.fs_status()
                self.send_json(result.to_dict())
            elif path == "/fs/diff":
                staged = query.get("staged", ["false"])[0].lower() == "true"
                result = lathe_app.fs_diff(staged=staged)
                self.send_json(result.to_dict())
            elif path.startswith("/fs/run/") and path.endswith("/files"):
                run_id = path.split("/")[3]
                files = lathe_app.fs_run_files(run_id)
                self.send_json({"run_id": run_id, "files": files, "results": []})
            elif path == "/knowledge/status":
                self.handle_knowledge_status()
            elif path == "/workspace/list":
                self.handle_workspace_list()
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
            elif path == "/review":
                self.handle_review(body)
            elif path == "/knowledge/ingest":
                self.handle_knowledge_ingest(body)
            elif path == "/workspace/create":
                self.handle_workspace_create(body)
            else:
                self.send_json(make_refusal("not_found", f"Unknown path: {path}"), 404)
        except Exception as e:
            logger.exception("Error in POST handler")
            self.send_json(make_error_response(str(e)), 500)
    
    def handle_agent(self, body: Dict[str, Any]):
        """Handle POST /agent - create a new run or process context intent."""
        intent = body.get("intent")
        task = body.get("task")
        why = body.get("why")
        model = body.get("model")
        
        if intent == "context" and task == "ingest_workspace":
            self.handle_workspace_ingest(body)
            return
        
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
        """Handle POST /execute - execute an approved proposal."""
        run_id = body.get("run_id")
        dry_run = body.get("dry_run", True)
        
        if not run_id:
            self.send_json(make_refusal("missing_fields", "Missing required field: run_id"), 400)
            return
        
        result = lathe_app.execute_proposal(run_id, dry_run=dry_run)
        response = to_jsonable_execution_result(result)
        self.send_json(response)
    
    def handle_review(self, body: Dict[str, Any]):
        """Handle POST /review - review/approve/reject a proposal."""
        run_id = body.get("run_id")
        action = body.get("action")
        comment = body.get("comment")
        
        missing = []
        if not run_id:
            missing.append("run_id")
        if not action:
            missing.append("action")
        
        if missing:
            self.send_json(
                make_refusal("missing_fields", f"Missing required fields: {', '.join(missing)}"),
                400
            )
            return
        
        result = lathe_app.review_run(run_id, action, comment=comment)
        response = to_jsonable_review_result(result)
        self.send_json(response)
    
    def handle_runs_query(self, query: Dict[str, Any]):
        """Handle GET /runs with query parameters."""
        intent = query.get("intent", [None])[0]
        outcome = query.get("outcome", [None])[0]
        file = query.get("file", [None])[0]
        since = query.get("since", [None])[0]
        until = query.get("until", [None])[0]
        
        try:
            limit = int(query.get("limit", [100])[0])
        except ValueError:
            limit = 100
        
        result = lathe_app.search_runs(
            intent=intent,
            outcome=outcome,
            file=file,
            since=since,
            until=until,
            limit=limit,
        )
        
        response = to_jsonable_query_result(result)
        self.send_json(response)
    
    def handle_get_review(self, run_id: str):
        """Handle GET /runs/<id>/review - get review state."""
        state = lathe_app.get_review_state(run_id)
        
        if state is None:
            self.send_json(make_refusal("not_found", f"No review found for run {run_id}"), 404)
            return
        
        state["results"] = []
        self.send_json(state)
    
    def handle_fs_tree(self, query: Dict[str, Any]):
        """Handle GET /fs/tree - directory tree."""
        path = query.get("path", ["."])[0]
        try:
            max_depth = int(query.get("max_depth", [3])[0])
        except ValueError:
            max_depth = 3
        
        result = lathe_app.fs_tree(path, max_depth=max_depth)
        self.send_json(result.to_dict())
    
    def handle_knowledge_status(self):
        """Handle GET /knowledge/status - get knowledge index status."""
        try:
            from lathe_app.knowledge import get_status
            status = get_status()
            response = status.to_dict()
            response["results"] = []
            self.send_json(response)
        except Exception as e:
            self.send_json(make_refusal("knowledge_error", str(e)))
    
    def handle_knowledge_ingest(self, body: Dict[str, Any]):
        """Handle POST /knowledge/ingest - ingest documents into knowledge index."""
        path = body.get("path")
        rebuild = body.get("rebuild", False)
        
        if not path:
            self.send_json(make_refusal("missing_fields", "Missing required field: path"), 400)
            return
        
        try:
            from lathe_app.knowledge import ingest_path, get_default_index, get_status
            
            index = get_default_index()
            
            if rebuild:
                index.clear()
            
            documents, chunks, errors = ingest_path(path)
            
            for doc in documents:
                index.add_document(doc)
            for chunk in chunks:
                index.add_chunk(chunk)
            
            status = get_status()
            
            response = {
                "ingested_documents": len(documents),
                "ingested_chunks": len(chunks),
                "errors": errors,
                "index_status": status.to_dict(),
                "results": [],
            }
            self.send_json(response)
        except Exception as e:
            self.send_json(make_refusal("ingestion_error", str(e)))
    
    def handle_workspace_ingest(self, body: Dict[str, Any]):
        """Handle intent=context, task=ingest_workspace via POST /agent."""
        ws_config = body.get("workspace")
        if not ws_config or not isinstance(ws_config, dict):
            self.send_json(
                make_refusal("missing_fields", "Missing required field: workspace"),
                400
            )
            return

        name = ws_config.get("name")
        root_path = ws_config.get("root_path")
        if not name or not root_path:
            self.send_json(
                make_refusal("missing_fields", "workspace requires 'name' and 'root_path'"),
                400
            )
            return

        try:
            from lathe_app.workspace.errors import (
                WorkspaceError,
            )
            from lathe_app.workspace.registry import (
                RegisteredWorkspace,
                get_default_registry,
            )
            from lathe_app.workspace.scanner import scan_workspace, collect_extensions
            from lathe_app.workspace.indexer import get_default_indexer
            from lathe_app.workspace.manager import UNSAFE_PATHS
            import os
            from datetime import datetime

            abs_path = os.path.abspath(root_path)

            for unsafe in UNSAFE_PATHS:
                if abs_path == unsafe or abs_path.startswith(unsafe + os.sep):
                    self.send_json(
                        make_refusal("unsafe_path", f"Cannot ingest system directory: {unsafe}"),
                        400
                    )
                    return

            if not os.path.exists(abs_path):
                self.send_json(
                    make_refusal("path_not_found", f"Path not found: {abs_path}"),
                    400
                )
                return

            if not os.path.isdir(abs_path):
                self.send_json(
                    make_refusal("not_directory", f"Path is not a directory: {abs_path}"),
                    400
                )
                return

            lathe_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            if abs_path == lathe_root or abs_path.startswith(lathe_root + os.sep):
                self.send_json(
                    make_refusal("self_ingestion", "Cannot ingest the Lathe repository itself"),
                    400
                )
                return

            include = ws_config.get("include")
            exclude = ws_config.get("exclude")
            manifest = ws_config.get("manifest", "unknown")

            files = scan_workspace(abs_path, include=include, exclude=exclude)

            if not files:
                self.send_json(
                    make_refusal("empty_workspace", f"Zero files matched filters in: {abs_path}"),
                    400
                )
                return

            indexer = get_default_indexer()
            doc_count, chunk_count, errors = indexer.ingest_files(name, files, abs_path)

            extensions = collect_extensions(files)

            registry = get_default_registry()
            registered = RegisteredWorkspace(
                name=name,
                root_path=abs_path,
                manifest=manifest,
                include=include or [],
                exclude=exclude or [],
                file_count=len(files),
                indexed_extensions=extensions,
                registered_at=datetime.utcnow().isoformat(),
                indexed=True,
            )
            registry.register(registered)

            response = {
                "workspace": registered.to_dict(),
                "documents_indexed": doc_count,
                "chunks_indexed": chunk_count,
                "errors": errors,
                "results": [],
            }
            self.send_json(response)

        except WorkspaceError as e:
            self.send_json(make_refusal("workspace_error", str(e)), 400)
        except Exception as e:
            logger.exception("Error in workspace ingestion")
            self.send_json(make_error_response(str(e)), 500)

    def handle_workspace_list(self):
        """Handle GET /workspace/list - list all workspaces."""
        try:
            from lathe_app.workspace import get_default_manager
            
            manager = get_default_manager()
            workspaces = manager.list_workspaces()
            
            response = {
                "workspaces": [ws.to_dict() for ws in workspaces],
                "count": len(workspaces),
                "results": [],
            }
            self.send_json(response)
        except Exception as e:
            self.send_json(make_refusal("workspace_error", str(e)))
    
    def handle_workspace_create(self, body: Dict[str, Any]):
        """Handle POST /workspace/create - create a new workspace."""
        path = body.get("path")
        workspace_id = body.get("workspace_id")
        
        if not path:
            self.send_json(make_refusal("missing_fields", "Missing required field: path"), 400)
            return
        
        try:
            from lathe_app.workspace import get_default_manager
            
            manager = get_default_manager()
            workspace = manager.create_workspace(path, workspace_id=workspace_id)
            
            response = {
                "workspace": workspace.to_dict(),
                "results": [],
            }
            self.send_json(response)
        except ValueError as e:
            self.send_json(make_refusal("invalid_path", str(e)), 400)
        except Exception as e:
            self.send_json(make_refusal("workspace_error", str(e)))


DEFAULT_PORT = 3001


def get_port(cli_port: int = None) -> int:
    """
    Resolve port with priority: CLI > env var > default.
    
    Port assignments:
    - OpenWebUI → 3000 (external, not managed here)
    - Lathe App → 3001 (default)
    """
    if cli_port is not None:
        return cli_port
    
    env_port = os.environ.get("LATHE_APP_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            logger.warning(f"Invalid LATHE_APP_PORT={env_port}, using default")
    
    return DEFAULT_PORT


def create_server(host: str = "0.0.0.0", port: int = None) -> HTTPServer:
    """Create the HTTP server instance."""
    if port is None:
        port = DEFAULT_PORT
    server = HTTPServer((host, port), AppHandler)
    return server


def run_server(host: str = "0.0.0.0", port: int = None):
    """Run the HTTP server."""
    resolved_port = get_port(port)
    server = create_server(host, resolved_port)
    logger.info(f"Lathe App Server listening on {host}:{resolved_port}")
    print(f"Lathe App Server listening on {host}:{resolved_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down")
        server.shutdown()


def main():
    """CLI entry point with --port flag support."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Lathe App HTTP Server")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help=f"Port to listen on (default: {DEFAULT_PORT}, or LATHE_APP_PORT env var)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
