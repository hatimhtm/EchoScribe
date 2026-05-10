"""FastAPI server for EchoScribe.

Expose the same pipeline the CLI uses over HTTP so Zapier / n8n / cron /
your meeting tool of choice can POST an audio file and get back a structured
brief. Install with the `[server]` extra:

    pip install 'echoscribe[server]'
    echoscribe serve --port 8000
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from echoscribe.config import Config
from echoscribe.output import to_json, to_markdown, to_slack
from echoscribe.services.intelligence import IntelligenceService, MeetingIntelligence
from echoscribe.services.slack import SlackService
from echoscribe.services.transcription import TranscriptionService

logger = logging.getLogger(__name__)


def create_app(config: Config | None = None):
    """Build the FastAPI app. Imports are lazy so the rest of the package
    doesn't depend on FastAPI being installed."""
    try:
        from fastapi import FastAPI, File, Form, HTTPException, UploadFile
        from fastapi.responses import JSONResponse, PlainTextResponse
    except ImportError as exc:
        raise ImportError(
            "FastAPI is required for server mode. "
            "Install with: pip install 'echoscribe[server]'"
        ) from exc

    cfg = config or Config.from_env()

    app = FastAPI(
        title="EchoScribe",
        version="3.0.0",
        description="Audio → Whisper → structured meeting intelligence → your tool of choice.",
    )

    def require_openai_key() -> str:
        if not cfg.openai.api_key:
            raise HTTPException(500, "OPENAI_API_KEY is not configured on the server.")
        return cfg.openai.api_key

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "openai_configured": bool(cfg.openai.api_key),
            "slack_configured": bool(cfg.slack.api_token),
        }

    @app.post(
        "/v1/transcribe",
        summary="Transcribe an audio file via Whisper.",
        response_class=PlainTextResponse,
    )
    async def transcribe(file: UploadFile = File(...)) -> str:
        api_key = require_openai_key()
        suffix = Path(file.filename or "audio.mp3").suffix or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
        try:
            transcriber = TranscriptionService(api_key=api_key, model=cfg.openai.whisper_model)
            return transcriber.transcribe(tmp_path).text
        finally:
            tmp_path.unlink(missing_ok=True)

    @app.post(
        "/v1/intelligence",
        summary="Run structured meeting-intelligence extraction on an existing transcript.",
    )
    async def intelligence(transcript: str = Form(...)) -> MeetingIntelligence:
        api_key = require_openai_key()
        service = IntelligenceService(api_key=api_key, model=cfg.openai.model)
        return service.extract(transcript)

    @app.post(
        "/v1/process",
        summary="Full pipeline: audio → transcript → meeting brief. "
        "Returns Markdown, Slack, or JSON depending on `?format=`.",
    )
    async def process(
        file: UploadFile = File(...),
        format: str = "json",
        post_to_slack: bool = False,
        slack_channel: str | None = None,
    ):
        api_key = require_openai_key()
        if format not in {"json", "markdown", "slack"}:
            raise HTTPException(422, "format must be one of: json, markdown, slack")

        suffix = Path(file.filename or "audio.mp3").suffix or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)

        try:
            transcriber = TranscriptionService(api_key=api_key, model=cfg.openai.whisper_model)
            transcript = transcriber.transcribe(tmp_path).text

            intel = IntelligenceService(api_key=api_key, model=cfg.openai.model)
            meeting = intel.extract(transcript)
        finally:
            tmp_path.unlink(missing_ok=True)

        if post_to_slack:
            if not cfg.slack.api_token:
                raise HTTPException(500, "SLACK_API_TOKEN is not configured on the server.")
            slack = SlackService(
                token=cfg.slack.api_token,
                default_channel=slack_channel or cfg.slack.channel,
            )
            slack.post_message(to_slack(meeting))

        if format == "markdown":
            return PlainTextResponse(to_markdown(meeting))
        if format == "slack":
            return PlainTextResponse(to_slack(meeting))
        return JSONResponse(content=meeting.model_dump())

    return app


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the server. Used by the CLI's `serve` command."""
    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(
            "uvicorn is required for server mode. "
            "Install with: pip install 'echoscribe[server]'"
        ) from exc

    uvicorn.run(create_app(), host=host, port=port)
