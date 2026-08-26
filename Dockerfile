FROM python:3.11-slim

LABEL maintainer="Tinker Tailor Authors"
LABEL description="Reproducibility container for Tinker Tailor (USENIX Security)"

WORKDIR /opt/tinker_tailor

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Default: run the one-command, checksum-verified reproduction of every
# synthetic table (exit non-zero on any mismatch). Override to use the CLI:
#   docker run tinker-tailor python -m tinker_tailor --help
#   docker run tinker-tailor python verify_reproduction.py --figures
ENTRYPOINT []
CMD ["python", "verify_reproduction.py"]
