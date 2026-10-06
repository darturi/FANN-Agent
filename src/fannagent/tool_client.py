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


def main():
    data = {"operation": sys.argv[1], "args": json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}}
    headers = {
        "Authorization": "Bearer " + os.environ["FANNAGENT_TOKEN"],
        "Content-Type": "application/json",
    }
    if os.environ.get("FANNAGENT_QUEUE"):
        folder = Path(os.environ["FANNAGENT_QUEUE"])
        identity = uuid.uuid4().hex
        request_path = folder / (identity + ".request")
        temporary = folder / (identity + ".tmp")
        temporary.write_text(json.dumps({**data, "token": os.environ["FANNAGENT_TOKEN"]}))
        temporary.replace(request_path)
        response_path = folder / (identity + ".response.ready")
        deadline = time.monotonic() + 3600
        while not response_path.exists():
            if time.monotonic() > deadline:
                raise SystemExit("tool broker timed out")
            time.sleep(0.02)
        result = json.loads(response_path.read_text())
        response_path.unlink()
    elif os.environ.get("FANNAGENT_SOCKET"):

        class UnixConnection(http.client.HTTPConnection):
            def connect(self):
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(3600)
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
        with urllib.request.urlopen(request, timeout=3600) as response:
            result = json.load(response)
    print(json.dumps(result))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
