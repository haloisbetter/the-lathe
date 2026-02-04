import json
import http.server
import socketserver
from pathlib import Path
from lathe.rag import retrieve_rag_evidence
from lathe.agent import AgentReasoning
from lathe.exec import validate_why_input

class LatheHandler(http.server.BaseHTTPRequestHandler):
    def _send_structured_refusal(self, reason, details=None):
        """Return structured refusal. Refusal is a successful deterministic outcome."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "refusal": True,
            "reason": reason,
            "details": details or "",
            "results": []
        }).encode('utf-8'))

    def do_POST(self):
        if self.path != '/agent':
            self.send_error(404, "Not Found")
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_structured_refusal("Empty request body")
                return
                
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self._send_structured_refusal("Invalid JSON payload")
                return

            intent = data.get('intent')
            task = data.get('task')
            why = data.get('why')

            if not intent or not task or not why:
                self._send_structured_refusal("Missing required fields: intent, task, or why")
                return

            # Validation occurs here via Lathe internals
            try:
                why_data = validate_why_input(json.dumps(why))
            except Exception as e:
                self._send_structured_refusal(f"Invalid 'why' object: {str(e)}")
                return

            agent = AgentReasoning()
            response_data = {}
            
            if intent == 'propose':
                evidence = retrieve_rag_evidence(task, channel="actionable")
                response_data = agent.propose(task, why_data, evidence)
            elif intent == 'think':
                evidence = retrieve_rag_evidence(task, channel="conceptual")
                response_data = agent.think(task, why_data, evidence)
            elif intent == 'context':
                try:
                    from lathe.context.builder import get_file_context_from_lines
                    path_part, range_part = task.rsplit(":", 1)
                    start_str, end_str = range_part.split("-")
                    f_path = Path(path_part)
                    if not f_path.exists():
                        self._send_structured_refusal(f"File not found: {path_part}")
                        return
                    with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                        all_lines = f.readlines()
                    response_data = get_file_context_from_lines(path_part, all_lines, int(start_str), int(end_str))
                except Exception as e:
                    self._send_structured_refusal(f"Context retrieval failed: {str(e)}")
                    return
            elif intent == 'rag':
                response_data = {
                    "conceptual": retrieve_rag_evidence(task, channel="conceptual"),
                    "actionable": retrieve_rag_evidence(task, channel="actionable")
                }
            else:
                self._send_structured_refusal(f"Unknown intent: {intent}")
                return

            # Normalize: ensure "results" key exists for OpenWebUI compatibility
            if "results" not in response_data:
                response_data["results"] = []
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            # Fallback for truly unexpected errors, still returning JSON
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Internal Server Error",
                    "details": str(e)
                }).encode('utf-8'))
            except:
                pass

def run_server(port=5000):
    # Use a custom server class to set allow_reuse_address
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("0.0.0.0", port), LatheHandler) as httpd:
        print(f"Lathe Agent Server running on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
