"""One free synthetic-only capability check; never load or send study evidence."""

import json

from common import DEST, accept_count, sha, write
from dispatch import post

PAYLOAD = {
    "model": "claude-sonnet-5-5",
    "system": "Synthetic token-count endpoint compatibility check. No study data.",
    "messages": [{"role": "user", "content": "Synthetic context check."}],
    "tools": [
        {
            "name": "synthetic_check",
            "description": "Synthetic schema only.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        }
    ],
    "thinking": {"type": "between_tools"},
    "output_config": {"effort": "high"},
}


def check():
    target = DEST / "synthetic-count-endpoint-check"
    response = post("/v1/messages/count_tokens", PAYLOAD, target)
    count = accept_count(response)
    receipt = {
        "status": "verified_free_count_endpoint_pinned_model_version_and_fields",
        "api_version": "2023-06-01",
        "input_tokens": count,
        "request_sha256": sha(target / "request.json"),
        "response_sha256": sha(target / "response.json"),
        "source_sha256": sha(__import__("pathlib").Path(__file__)),
        "synthetic_count_requests": 1,
        "development_count_requests": 0,
        "Messages_requests": 0,
        "paid_spend_usd": "0",
        "study_data_sent": False,
    }
    write(target / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    check()
