# docker/latex-renderer/Dockerfile
# DocSynthFab LaTeX Renderer
#
# Recommended version ranges:
# - Python>=3.10,<3.14
# - fastapi>=0.110,<1.0
# - uvicorn[standard]>=0.27,<1.0
# - pypdfium2>=4,<5
# - Pillow>=10,<12

FROM debian:bookworm-slim

LABEL org.opencontainers.image.title="DocSynthFab LaTeX Renderer"
LABEL org.opencontainers.image.description="HTTP LaTeX-to-PNG renderer for DocSynthFab synthetic document generation"
LABEL org.opencontainers.image.version="0.1.0"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    curl \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install \
    --no-cache-dir \
    --break-system-packages \
    -r /app/requirements.txt

COPY server.py /app/server.py

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]