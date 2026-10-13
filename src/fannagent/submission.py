"""Internal validation feedback and host-side accounting of invalid agent turns."""

from __future__ import annotations

import json
import threading
import uuid

from .errors import AgentError

MAX_CONSECUTIVE_INVALID_TURNS = 3
CORRECTION_GUIDANCE = """Malformed submissions return error_info with a code,
field details and a hint.
Correct the identified input and issue a new tool call. Commands must be nonempty strings;
use fannagent-tool OP 'JSON_OBJECT'. Query vectors must match the supplied dataset profile.
The system does not rewrite or replay a rejected command. Three consecutive invalid turns
end exploration with no recommendation. Every model attempt still consumes the budget.
"""


def _bounded(value, limit):
    # Bound encoded bytes too: ensure_ascii JSON can expand a single character sixfold.
    return str(value).encode("ascii", "backslashreplace")[:limit].decode("ascii")


class InvalidSubmission(AgentError):
    def __init__(self, code, message, *, path="", details=(), hint="Correct the input and retry."):
        super().__init__(message)
        self.info = {
            "code": _bounded(code, 64),
            "message": _bounded(message, 512),
            "details": [
                {"path": _bounded(d["path"], 128), "message": _bounded(d["message"], 256)}
                for d in list(details)[:5]
            ],
            "hint": _bounded(hint, 256),
        }
        if path and not self.info["details"]:
            self.info["details"] = [{"path": _bounded(path, 128), "message": self.info["message"]}]
        # Quotes/control characters also expand under JSON serialization.
        while len(json.dumps(self.response()).encode()) > 4096:
            if self.info["details"]:
                self.info["details"].pop()
            else:
                self.info["message"] = self.info["message"][:256]
                break

    def response(self):
        return {"ok": False, "error": self.info["message"], "error_info": self.info}


def error_response(exc):
    if isinstance(exc, InvalidSubmission):
        return exc.response()
    return {"ok": False, "error": str(exc) if isinstance(exc, AgentError) else type(exc).__name__}


def validate_action(action):
    command = action.get("command") if isinstance(action, dict) else None
    if not isinstance(command, str) or not command.strip() or "\x00" in command:
        raise InvalidSubmission(
            "invalid_tool_call",
            "command must be a nonempty string without NUL characters",
            path="command",
            hint='Call bash with {"command": "fannagent-tool inspect \'{}\'"}.',
        )
    return command


def decode_request(data):
    if not isinstance(data, dict):
        raise InvalidSubmission("invalid_arguments", "request must be a JSON object")
    if "argv" in data:
        if "operation" in data or "args" in data:
            raise InvalidSubmission("invalid_arguments", "use argv or operation/args, not both")
        argv = data["argv"]
        if (
            not isinstance(argv, list)
            or not 1 <= len(argv) <= 2
            or any(not isinstance(value, str) for value in argv)
        ):
            raise InvalidSubmission(
                "invalid_arguments",
                "expected an operation and optional JSON object",
                hint="Usage: fannagent-tool OP 'JSON_OBJECT'.",
            )
        operation = argv[0]
        try:
            args = json.loads(argv[1]) if len(argv) == 2 else {}
        except json.JSONDecodeError as exc:
            raise InvalidSubmission(
                "invalid_arguments",
                f"invalid argument JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
                path="args",
                hint="Quote the JSON object as one shell argument; use double quotes inside.",
            ) from None
        except RecursionError:
            raise InvalidSubmission(
                "invalid_arguments", "argument JSON is too deeply nested"
            ) from None
    else:
        operation, args = data.get("operation"), data.get("args", {})
    if not isinstance(operation, str) or not operation:
        raise InvalidSubmission(
            "invalid_arguments", "operation must be a nonempty string", path="operation"
        )
    if not isinstance(args, dict):
        raise InvalidSubmission("invalid_arguments", "args must be a JSON object", path="args")
    return operation, args


class SubmissionTracker:
    """Only events for the active turn affect its outcome; stdout is never parsed."""

    def __init__(self):
        self.lock = threading.Lock()
        self.turn_id = None
        self.invalid = None
        self.failed = False
        self.completed = False

    def begin_turn(self):
        with self.lock:
            self.turn_id = uuid.uuid4().hex
            self.invalid, self.failed, self.completed = None, False, False
            return self.turn_id

    def record(self, turn_id, *, error=None, success=None):
        with self.lock:
            if not turn_id or turn_id != self.turn_id:
                return
            if error is not None:
                self.invalid = error
            if success is not None:
                self.failed |= not success
                self.completed = True

    def finish_turn(self):
        with self.lock:
            result = (self.invalid, self.completed and not self.failed and self.invalid is None)
            self.turn_id = None
            return result

    def error_for(self, turn_id):
        with self.lock:
            return self.invalid if turn_id and turn_id == self.turn_id else None
