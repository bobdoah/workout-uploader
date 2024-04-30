FROM python:3.12-slim

WORKDIR /usr/src/app

RUN pip install uv

COPY requirements.txt .

RUN uv venv && uv pip sync requirements.txt

COPY uploader.py strava_client.py .

ENTRYPOINT ["/usr/src/app/.venv/bin/python", "/usr/src/app/uploader.py"]
