import json
import http.server
import socketserver
from pathlib import Path
from lathe.rag import retrieve_rag_evidence
from lathe.agent import AgentReasoning
from lathe.exec import validate_why_input

class LatheHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/agent':
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            intent = data.get('intent')
            task = data.get('task')
            why = data.get('why')

            if not intent or not task or not why:
                self.send_error(400, "Missing intent, task, or why")
                return

            # Validation occurs here via Lathe internals
            why_data = validate_why_input(json.dumps(why))
            agent = AgentReasoning()

            response_data = {}
            
            if intent == 'propose':
                evidence = retrieve_rag_evidence(task, channel="actionable")
                response_data = agent.propose(task, why_data, evidence)
            elif intent == 'think':
                evidence = retrieve_rag_evidence(task, channel="conceptual")
                response_data = agent.think(task, why_data, evidence)
            elif intent == 'context':
                # Simplified context retrieval for agent endpoint
                from lathe.context.builder import get_file_context_from_lines
                path_part, range_part = task.rsplit(":", 1)
                start_str, end_str = range_part.split("-")
                f_path = Path(path_part)
                with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                    all_lines = f.readlines()
                response_data = get_file_context_from_lines(path_part, all_lines, int(start_str), int(end_str))
            elif intent == 'rag':
                # Returns both for inspection if requested, but usually separate
                response_data = {
                    "conceptual": retrieve_rag_evidence(task, channel="conceptual"),
                    "actionable": retrieve_rag_evidence(task, channel="actionable")
                }
            else:
                self.send_error(400, f"Unknown intent: {intent}")
                return

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

def run_server(port=5000):
    with socketserver.TCPServer(("0.0.0.0", port), LatheHandler) as httpd:
        print(f"Lathe Agent Server running on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
