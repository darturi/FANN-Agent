from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import socketserver
import tempfile
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .api.primitives.data import Query
from .api.primitives.descriptors import exact_query_descriptors
from .api.primitives.filters import evaluate_filter
from .errors import AgentError


class Tools:
    def __init__(self, study, budget):
        self.study, self.budget = study, budget

    def call(self, operation, args):
        s = self.study
        if s.store.get("frozen"):
            raise AgentError("development tools are closed")
        if operation == "inspect":
            registry = {
                "definitions": {
                    n: f.model_dump(mode="json")
                    for n, f in s.backend.runtime_profile.features.items()
                },
                "feature_profile": s.backend.runtime_profile.name,
                "registry_hash": s.backend.runtime_profile.fingerprint,
            }
            full = s.store.put("feature_registry", registry, scope="development")
            supported = set(s.backend.describe_capabilities().runtime_features)
            compact = {
                name: {
                    key: value[key]
                    for key in ("kind", "group", "population", "scope", "description")
                }
                for name, value in registry["definitions"].items()
                if name in supported
            }
            return {
                "target": s.backend.inspect_target(),
                "capabilities": asdict(s.backend.describe_capabilities()),
                "features": {
                    "profile": registry["feature_profile"],
                    "registry_hash": registry["registry_hash"],
                    "runtime": compact,
                    "full_registry_artifact": full,
                },
                "budget": self.budget.summary(),
            }
        if operation == "queries":
            start = max(0, int(args.get("offset", 0)))
            limit = min(100, max(1, int(args.get("limit", 20))))
            return [i["query"] for i in s.development[start : start + limit]]
        if operation == "sample":
            result = []
            for row in s.snapshot.rows[max(0, int(args.get("offset", 0))) :]:
                try:
                    s.permitted({"id": "sample", "vector": row["vector"], "k": 1})
                except AgentError:
                    continue
                result.append(row)
                if len(result) >= min(100, max(1, int(args.get("limit", 20)))):
                    break
            return result
        if operation == "count":
            query = s.permitted(args["query"])
            metadata = s.snapshot.data.metadata
            count = (
                int(evaluate_filter(query["filter"], metadata).sum())
                if query.get("filter")
                else len(s.snapshot.rows)
            )
            return {
                "eligible_count": count,
                "selectivity": count / len(s.snapshot.rows),
                "provenance": "offline_snapshot_predicate_evaluation",
            }
        if operation == "descriptors":
            query = s.permitted(args["query"])
            result = exact_query_descriptors(
                s.snapshot.data, Query.model_validate(query), seed=s.config.workload.seed
            )
            return {
                "artifact": s.store.put(
                    "offline_descriptors",
                    result,
                    scope="development",
                    limit=s.config.evidence.max_bytes,
                ),
                "provenance": "offline exact analysis; forbidden as runtime policy inputs",
            }
        if operation == "development_evaluate":
            policy = s.backend.validate_policy(args["policy"])
            return s.measure(policy, "development")
        if operation in {"probe", "audit"}:
            policy = s.backend.validate_policy(args["policy"]) if args.get("policy") else None
            return s.probe(args["query"], policy, audit=operation == "audit")
        if operation == "labels":
            query = s.permitted(args["query"])
            result = s.stop_labels(query)
            return {"artifact": s.store.put("real_stop_labels", result, scope="development")}
        if operation == "artifact":
            return s.store.read(args["hash"], agent=True)
        if operation in {"validate", "calibrate"}:
            return s.validate(args["policy"], calibration=operation == "calibrate")
        if operation == "submit":
            return s.submit(args["policy"])
        raise AgentError("unknown development tool")


class Broker:
    def __init__(self, tools, host="127.0.0.1", socket_path=None):
        self.token = secrets.token_urlsafe(32)
        token, lock = self.token, threading.Lock()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                if self.path != "/tool" or not hmac.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + token
                ):
                    self.send_error(403)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024**2:
                    self.send_error(413)
                    return
                try:
                    data = json.loads(self.rfile.read(length))
                    with lock:
                        result = {
                            "ok": True,
                            "result": tools.call(data["operation"], data.get("args", {})),
                        }
                except Exception as exc:
                    result = {
                        "ok": False,
                        "error": str(exc) if isinstance(exc, AgentError) else type(exc).__name__,
                    }
                body = json.dumps(result, allow_nan=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.socket_path = socket_path
        if socket_path:

            class UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
                daemon_threads = True

            self.socket_folder = tempfile.TemporaryDirectory(prefix="fannagent-", dir="/tmp")
            socket_path = Path(self.socket_folder.name) / "broker.sock"
            self.socket_path = socket_path
            self.server = UnixServer(str(socket_path), Handler)
            os.chmod(socket_path, 0o666)  # authentication remains a per-run random token
        else:
            self.server = ThreadingHTTPServer((host, 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        if self.socket_path:
            self.socket_path.unlink(missing_ok=True)
            self.socket_folder.cleanup()


class FileBroker:
    """Authenticated request queue. Works across Docker Desktop without a network route.

    Pin the directory inode and refuse symlinks; the shell cannot redirect trusted reads/writes.
    """

    def __init__(self, tools, folder):
        self.tools, self.folder = tools, folder
        self.token = secrets.token_urlsafe(32)
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def serve(self):
        while not self.stop.is_set():
            for name in os.listdir(self.fd):
                if not re.fullmatch(r"[0-9a-f]{32}\.request", name):
                    continue
                try:
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
                    with os.fdopen(fd, "rb") as handle:
                        import stat

                        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                            continue
                        raw = handle.read(1024**2 + 1)
                    if len(raw) > 1024**2:
                        raise AgentError("request too large")
                    request = json.loads(raw)
                    if not hmac.compare_digest(request.get("token", ""), self.token):
                        raise AgentError("unauthorized request")
                    result = {
                        "ok": True,
                        "result": self.tools.call(request["operation"], request.get("args", {})),
                    }
                except Exception as exc:
                    result = {
                        "ok": False,
                        "error": str(exc) if isinstance(exc, AgentError) else type(exc).__name__,
                    }
                response_name = name.replace(".request", ".response")
                try:
                    fd = os.open(
                        response_name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=self.fd,
                    )
                    with os.fdopen(fd, "w") as handle:
                        json.dump(result, handle, allow_nan=False)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.rename(
                        response_name,
                        response_name + ".ready",
                        src_dir_fd=self.fd,
                        dst_dir_fd=self.fd,
                    )
                except OSError:
                    pass
                try:
                    os.unlink(name, dir_fd=self.fd)
                except OSError:
                    pass
            self.stop.wait(0.02)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()
        os.close(self.fd)
