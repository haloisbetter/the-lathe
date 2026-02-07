"""
Lathe HTTP Client

Pure HTTP client for communicating with lathe_app.server.
No imports from lathe or lathe_app. No filesystem access.
"""
import requests
from typing import Any, Dict, Optional


class LatheClientError:
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "error_type": self.error_type,
            "message": self.message,
        }


class LatheClient:
    def __init__(self, base_url: str = "http://127.0.0.1:3001", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            resp = requests.get(
                f"{self.base_url}{path}",
                params=params,
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {"ok": False, "missing_endpoint": True, "status": 404, "path": path}
            data = resp.json()
            data["_status"] = resp.status_code
            data.setdefault("ok", resp.status_code < 400)
            return data
        except requests.ConnectionError:
            return LatheClientError("connection_refused", f"Cannot connect to {self.base_url}").to_dict()
        except requests.Timeout:
            return LatheClientError("timeout", f"Request to {path} timed out after {self.timeout}s").to_dict()
        except Exception as e:
            return LatheClientError("request_error", str(e)).to_dict()

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = requests.post(
                f"{self.base_url}{path}",
                json=body,
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {"ok": False, "missing_endpoint": True, "status": 404, "path": path}
            data = resp.json()
            data["_status"] = resp.status_code
            data.setdefault("ok", resp.status_code < 400)
            return data
        except requests.ConnectionError:
            return LatheClientError("connection_refused", f"Cannot connect to {self.base_url}").to_dict()
        except requests.Timeout:
            return LatheClientError("timeout", f"Request to {path} timed out after {self.timeout}s").to_dict()
        except Exception as e:
            return LatheClientError("request_error", str(e)).to_dict()

    def health(self) -> Dict[str, Any]:
        return self._get("/health")

    def health_summary(self) -> Dict[str, Any]:
        return self._get("/health/summary")

    def runs_list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._get("/runs", params=params)

    def runs_get(self, run_id: str) -> Dict[str, Any]:
        return self._get(f"/runs/{run_id}")

    def runs_stats(self) -> Dict[str, Any]:
        return self._get("/runs/stats")

    def run_review_get(self, run_id: str) -> Dict[str, Any]:
        return self._get(f"/runs/{run_id}/review")

    def run_staleness_get(self, run_id: str) -> Dict[str, Any]:
        return self._get(f"/runs/{run_id}/staleness")

    def review_submit(self, run_id: str, action: str, comment: str = "") -> Dict[str, Any]:
        body = {"run_id": run_id, "action": action}
        if comment:
            body["comment"] = comment
        return self._post("/review", body)

    def workspace_list(self) -> Dict[str, Any]:
        return self._get("/workspace/list")

    def workspace_stats(self) -> Dict[str, Any]:
        return self._get("/workspace/stats")

    def fs_tree(self, path: str = ".", max_depth: int = 3) -> Dict[str, Any]:
        return self._get("/fs/tree", params={"path": path, "max_depth": max_depth})

    def fs_run_files(self, run_id: str) -> Dict[str, Any]:
        return self._get(f"/fs/run/{run_id}/files")
