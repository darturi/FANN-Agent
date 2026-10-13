ARG PYTHON_IMAGE=python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
ARG DOCKER_IMAGE=docker@sha256:b1805116a6a86cc591b5d5f60a910a0715cdcc9d18d866ad68b1457ead25c35c
FROM ${DOCKER_IMAGE} AS dockercli
FROM ${PYTHON_IMAGE}
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
ARG REQUIREMENTS=core-requirements.txt
COPY ${REQUIREMENTS} /opt/fannagent/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /opt/fannagent/requirements.txt
COPY wheels/ /opt/fannagent/wheels/
ARG BACKEND=fake
RUN pip install --no-cache-dir --no-deps /opt/fannagent/wheels/fannagent-*.whl && \
    if [ "$BACKEND" = pgvector ]; then \
      pip install --no-cache-dir --no-deps /opt/fannagent/wheels/fannagent_pgvector-*.whl; \
    fi && rm -rf /opt/fannagent/wheels
ARG RELEASE_ID
LABEL io.fannagent.release=$RELEASE_ID
ENV MSWEA_GLOBAL_CONFIG_DIR=/tmp/mini MSWEA_SILENT_STARTUP=1 \
    LITELLM_LOCAL_MODEL_COST_MAP=True PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["fannagent"]
