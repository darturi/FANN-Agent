FROM python:3.12-slim
RUN pip install --no-cache-dir numpy pyarrow && \
    printf '#!/bin/sh\nexec python /tools/client.py "$@"\n' > /usr/local/bin/fannagent-tool && \
    chmod +x /usr/local/bin/fannagent-tool && useradd -m -u 1000 agent
USER agent
