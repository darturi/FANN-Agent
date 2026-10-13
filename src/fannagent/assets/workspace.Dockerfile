ARG PYTHON_IMAGE=python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
FROM ${PYTHON_IMAGE}
ARG TOOL_CLIENT_SHA256
LABEL io.fannagent.tool_client=$TOOL_CLIENT_SHA256
COPY client.py /tools/client.py
COPY workspace-requirements.txt /tools/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /tools/requirements.txt && \
    printf '#!/bin/sh\nexec python /tools/client.py "$@"\n' > /usr/local/bin/fannagent-tool && \
    chmod +x /usr/local/bin/fannagent-tool && useradd -m -u 1000 agent
USER agent
