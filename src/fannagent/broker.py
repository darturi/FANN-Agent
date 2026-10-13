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

from .api.policy import validate_policy
from .api.primitives.data import Query
from .api.primitives.descriptors import exact_query_descriptors
from .api.primitives.filters import evaluate_filter
from .config import RunConfig
from .errors import AgentError
from .evaluation_jobs import EvaluationJobs
from .experiments import ExperimentJournal
from .guidance import prepare_guidance
from .store import canonical
from .submission import InvalidSubmission, SubmissionTracker, decode_request, error_response
from .workflow import workflow_plan


def dispatch_request(tools, data):
    turn_id = data.get("turn_id") if isinstance(data, dict) else None
    try:
        operation, args = decode_request(data)
        if isinstance(tools, Tools) and data.get("request_id"):
            value = tools.call(operation, args, request_id=data.get("request_id"))
        else:
            value = tools.call(operation, args)
        result = {"ok": True, "result": value}
    except Exception as exc:
        result = error_response(exc)
    tracker = getattr(tools, "submissions", None)
    if tracker is not None:
        tracker.record(turn_id, error=result.get("error_info"), success=result["ok"])
    return result


class Tools:
    def __init__(self, study, budget, *, turn_limit=None):
        self.study, self.budget = study, budget
        self.turn_limit = turn_limit
        self.submissions = SubmissionTracker()
        config = getattr(study, "config", None) or RunConfig.model_validate(
            study.store.get("config")
        )
        self.guidance = prepare_guidance(config, study.store, study.backend)
        self.experiments = ExperimentJournal(study.store)
        self.evaluation_jobs = EvaluationJobs(study.store)

    def _validate_arguments(self, operation, args):
        query_ops = {"count", "descriptors", "probe", "screen", "audit", "labels"}
        policy_ops = {"development_evaluate", "validate", "calibrate", "submit", "screen"}
        supported = (
            query_ops
            | policy_ops
            | {"inspect", "queries", "sample", "artifact", "experiment", "evaluation_status"}
        )
        if not isinstance(operation, str) or operation not in supported:
            raise InvalidSubmission(
                "invalid_arguments",
                "unknown development tool",
                path="operation",
                hint="Available operations: " + ", ".join(sorted(supported)),
            )
        if not isinstance(args, dict):
            raise InvalidSubmission("invalid_arguments", "args must be a JSON object", path="args")
        if operation in query_ops and not isinstance(args.get("query"), dict):
            raise InvalidSubmission(
                "invalid_query",
                "query must be a JSON object",
                path="query",
                hint="Supply query with id, vector, k, and an optional filter.",
            )
        if operation in policy_ops or (
            operation in {"probe", "audit"} and args.get("policy") is not None
        ):
            if not isinstance(args.get("policy"), dict):
                raise InvalidSubmission(
                    "invalid_policy", "policy must be a JSON object", path="policy"
                )
            # This is an explicit input-validation boundary. Execution exceptions are not
            # classified by their Python type or by matching their message text.
            try:
                validate_policy(args["policy"], self.study.backend.runtime_profile)
            except AgentError as exc:
                raise InvalidSubmission(
                    "invalid_policy",
                    str(exc),
                    path="policy",
                    hint="Supply name and a bounded root using supported runtime features.",
                ) from None
        if operation in {"validate", "calibrate"} and "checkpoint" in args:
            if type(args["checkpoint"]) is not bool:
                raise InvalidSubmission(
                    "invalid_arguments", "checkpoint must be Boolean", path="checkpoint"
                )
        if operation in {"queries", "sample"}:
            for name in ("offset", "limit"):
                if name in args:
                    try:
                        int(args[name])
                    except (ValueError, TypeError, OverflowError):
                        raise InvalidSubmission(
                            "invalid_arguments",
                            f"{name} must be convertible to an integer",
                            path=name,
                        ) from None
        if operation == "artifact" and (not isinstance(args.get("hash"), str) or not args["hash"]):
            raise InvalidSubmission(
                "invalid_arguments", "hash must be a nonempty string", path="hash"
            )

    def _inspection(self):
        s = self.study
        registry = {
            "definitions": {
                n: f.model_dump(mode="json") for n, f in s.backend.runtime_profile.features.items()
            },
            "feature_profile": s.backend.runtime_profile.name,
            "registry_hash": s.backend.runtime_profile.fingerprint,
        }
        full = s.store.put("feature_registry", registry, scope="development")
        capabilities = asdict(s.backend.describe_capabilities())
        supported = set(capabilities["runtime_features"])
        compact = {
            name: {
                key: value[key] for key in ("kind", "group", "population", "scope", "description")
            }
            for name, value in registry["definitions"].items()
            if name in supported
        }
        return {
            "target": s.backend.inspect_target(),
            "capabilities": capabilities,
            "features": {
                "profile": registry["feature_profile"],
                "registry_hash": registry["registry_hash"],
                "runtime": compact,
                "full_registry_artifact": full,
            },
            "budget": self.budget.summary(),
            "checkpoint_policy_hash": s.checkpoint_policy_hash(),
        }

    def startup_context(self):
        """Collect model-visible context on the host before a fresh conversation."""
        inspection = self._inspection()
        target = inspection["target"]
        if not isinstance(target, dict):
            raise AgentError("backend inspection must be a dictionary")
        if "startup_summary" in target:
            summary = target["startup_summary"]
            if not isinstance(summary, dict):
                raise AgentError("backend startup_summary must be a dictionary")
        else:
            summary = {k: target[k] for k in ("settings", "guidance") if k in target}
        context = {
            "backend": inspection["capabilities"]["backend"],
            "capabilities": {
                k: v for k, v in inspection["capabilities"].items() if k != "runtime_features"
            },
            "dataset": self.study.snapshot.description(),
            "target": summary,
            "budget": {k: v for k, v in inspection["budget"].items() if k != "calls"},
            "feature_registry_artifact": inspection["features"]["full_registry_artifact"],
            "checkpoint_policy_hash": inspection["checkpoint_policy_hash"],
        }
        # Export only the development slice, never the private split manifest or anchors.
        items = [
            {"query": item["query"], "group": item["group"]} for item in self.study.development
        ]
        catalog = self.study.store.put(
            "development_query_catalog",
            {"items": items},
            scope="development",
            limit=self.study.config.evidence.max_bytes,
        )
        representatives = {}
        for item in items:
            representatives.setdefault(item["group"], []).append(item["query"]["id"])
        groups = list(representatives)
        # Spread orientation IDs through the catalog instead of presenting an adjacent prefix.
        selected = (
            [
                groups[i * (len(groups) - 1) // min(5, len(groups) - 1)]
                for i in range(min(6, len(groups)))
            ]
            if len(groups) > 1
            else groups
        )
        context["development_queries"] = {
            "count": len(items),
            "independent_vector_groups": len(groups),
            "catalog_artifact": catalog,
            "catalog_path": f"/workspace/artifacts/{catalog}.json",
            "catalog_shape": "items: list of {query: query object, group: vector group}",
            "representative_groups": [
                {"group": group, "query_ids": representatives[group]} for group in selected
            ],
            "pagination": {"default_limit": 20, "maximum_limit": 100, "argument": "offset"},
        }
        allowed = (summary.get("reviews_trial") or {}).get("allowed_collection_groups")
        context["runtime_feature_groups"] = {}
        for name, feature in inspection["features"]["runtime"].items():
            if allowed is None or feature["group"] in allowed:
                context["runtime_feature_groups"].setdefault(feature["group"], []).append(name)
        if self.experiments.required:
            context["research"] = {
                key: self.guidance[key]
                for key in ("mode", "research_protocol_version", "primer_hash", "artifact")
            }
            if self.turn_limit is not None:
                context["workflow"] = workflow_plan(self.turn_limit)
        try:
            canonical(context)
            context["inspection_artifact"] = self.study.store.put(
                "backend_inspection", inspection, scope="development"
            )
        except (TypeError, ValueError) as exc:
            raise AgentError("backend startup context must be JSON serializable") from exc
        return context

    def call(self, operation, args, *, request_id=None):
        if self.study.store.get("frozen") and operation != "evaluation_status":
            raise AgentError("development tools are closed")
        self._validate_arguments(operation, args)
        if operation == "experiment":
            return self.experiments.call(args)
        if operation == "evaluation_status":
            return self.evaluation_jobs.status(args.get("job_id"))
        identity = None
        if operation in {"development_evaluate", "calibrate"}:
            identity, cached = self.evaluation_jobs.begin(operation, args, request_id)
            if cached is not None:
                return cached
            self.study.evaluation_progress = self.evaluation_jobs.progress
        pending = None
        try:
            pending = self.experiments.before(self.study, operation, args)
            result = self._call(operation, args)
        except Exception as exc:
            self.experiments.after(pending, error=exc)
            if identity:
                self.evaluation_jobs.fail(identity, error_response(exc))
                self.study.evaluation_progress = None
            raise
        event_id = self.experiments.after(pending, result=result)
        if self.experiments.required and event_id and isinstance(result, dict):
            result = {**result, "experiment_event_id": event_id}
        if identity:
            result = self.evaluation_jobs.complete(identity, result)
            self.study.evaluation_progress = None
        return result

    def _call(self, operation, args):
        s = self.study
        if operation == "screen":
            return s.screen(args["query"], args["policy"])
        if operation == "inspect":
            return self._inspection()
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
            return s.validate(
                args["policy"],
                calibration=operation == "calibrate",
                checkpoint=args.get("checkpoint", False),
            )
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
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    self.send_error(400)
                    return
                if not 0 < length <= 1024**2:
                    self.send_error(413)
                    return
                try:
                    data = json.loads(self.rfile.read(length))
                    with lock:
                        result = dispatch_request(tools, data)
                except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                    result = InvalidSubmission(
                        "invalid_arguments", "request must contain valid JSON"
                    ).response()
                except Exception as exc:
                    result = error_response(exc)
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
                    try:
                        request = json.loads(raw)
                    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                        raise InvalidSubmission(
                            "invalid_arguments", "request must contain valid JSON"
                        ) from None
                    token = request.get("token", "") if isinstance(request, dict) else ""
                    if not isinstance(token, str) or not hmac.compare_digest(token, self.token):
                        raise AgentError("unauthorized request")
                    request["request_id"] = name.split(".")[0]
                    result = dispatch_request(self.tools, request)
                except Exception as exc:
                    result = error_response(exc)
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
