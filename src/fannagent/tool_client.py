"""Standard-library-only client copied into the development container."""

import http.client
import json
import os
import socket
import sys
import time
import urllib.request
import uuid
from pathlib import Path

BROKER_WAIT_SECONDS = 10800


def main():
    # Host-side decoding produces the same feedback for every transport, even when
    # the CLI arguments contain invalid JSON or the operation is missing.
    data = {
        "argv": sys.argv[1:],
        "turn_id": os.environ.get("FANNAGENT_TURN_ID"),
        "request_id": uuid.uuid4().hex,
    }
    headers = {
        "Authorization": "Bearer " + os.environ["FANNAGENT_TOKEN"],
        "Content-Type": "application/json",
    }
    if os.environ.get("FANNAGENT_QUEUE"):
        folder = Path(os.environ["FANNAGENT_QUEUE"])
        identity = data["request_id"]
        request_path = folder / (identity + ".request")
        temporary = folder / (identity + ".tmp")
        temporary.write_text(json.dumps({**data, "token": os.environ["FANNAGENT_TOKEN"]}))
        temporary.replace(request_path)
        response_path = folder / (identity + ".response.ready")
        deadline = time.monotonic() + BROKER_WAIT_SECONDS
        while True:
            try:
                result = json.loads(response_path.read_text())
                break
            except FileNotFoundError:
                # Docker Desktop can expose a directory entry before the file is readable.
                # Wait for this response without submitting the operation again.
                if time.monotonic() > deadline:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "tool broker timed out",
                                "evaluation_job_id": identity,
                                "recovery": "retrieve evaluation_status with job_id; never replay",
                            }
                        )
                    )
                    raise SystemExit(1) from None
                time.sleep(0.02)
        response_path.unlink(missing_ok=True)
    elif os.environ.get("FANNAGENT_SOCKET"):

        class UnixConnection(http.client.HTTPConnection):
            def connect(self):
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(BROKER_WAIT_SECONDS)
                self.sock.connect(os.environ["FANNAGENT_SOCKET"])

        connection = UnixConnection("localhost")
        connection.request("POST", "/tool", json.dumps(data), headers)
        result = json.load(connection.getresponse())
        connection.close()
    else:
        request = urllib.request.Request(
            os.environ["FANNAGENT_BROKER"] + "/tool",
            data=json.dumps(data).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=BROKER_WAIT_SECONDS) as response:
            result = json.load(response)
    try:
        print(json.dumps(result), flush=True)
    except BrokenPipeError:
        # A consumer such as head can close stdout after taking its requested prefix.
        # Redirect before shutdown so Python does not try to flush the broken pipe again.
        fd = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(fd, sys.stdout.fileno())
        finally:
            os.close(fd)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
