"""EchoScribe CLI — audio → structured meeting intelligence → your tool of choice."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer

from echoscribe import __version__
from echoscribe.config import Config
from echoscribe.output import to_json, to_markdown, to_slack
from echoscribe.services.intelligence import IntelligenceService
from echoscribe.services.slack import SlackService
from echoscribe.services.transcription import TranscriptionService

app = typer.Typer(
    name="echoscribe",
    help="Audio → Whisper → structured meeting intelligence → your tool of choice.",
    add_completion=False,
    no_args_is_help=True,
)

logger = logging.getLogger(__name__)


def _setup_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _die(message: str, code: int = 1) -> None:
    typer.secho(f"✗ {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


def _render(meeting, fmt: str) -> str:
    if fmt == "markdown":
        return to_markdown(meeting)
    if fmt == "slack":
        return to_slack(meeting)
    if fmt == "json":
        return to_json(meeting)
    _die(f"unknown format: {fmt} (expected one of: markdown, slack, json)")
    return ""  # unreachable


# ─────────────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def transcribe(
    audio: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write transcript to file."),
    language: str | None = typer.Option(
        None, "--language", "-l", help="BCP-47 language hint (auto-detect if omitted)."
    ),
    debug: bool = typer.Option(False, "--debug", help="Verbose logging."),
) -> None:
    """Transcribe an audio file via Whisper."""
    _setup_logging(debug)
    cfg = Config.from_env()
    if errors := cfg.required_errors():
        for e in errors:
            _die(e)

    service = TranscriptionService(
        api_key=cfg.openai.api_key,
        model=cfg.openai.whisper_model,
        language=language,
    )
    result = service.transcribe(audio)
    if not result.text:
        _die("Whisper returned no text.")

    typer.echo(result.text)
    if output:
        output.write_text(result.text)
        typer.secho(
            f"✓ wrote {output} ({result.word_count} words)", fg=typer.colors.GREEN, err=True
        )


@app.command()
def intelligence(
    transcript: Path = typer.Argument(
        ..., exists=True, file_okay=True, dir_okay=False, readable=True
    ),
    format: str = typer.Option("markdown", "--format", "-f", help="markdown · slack · json"),
    output: Path | None = typer.Option(None, "--output", "-o"),
    post_slack: bool = typer.Option(False, "--slack", help="Also post to Slack."),
    channel: str | None = typer.Option(None, "--channel", "-c"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Run structured meeting-intelligence extraction on a transcript text file."""
    _setup_logging(debug)
    cfg = Config.from_env()
    if errors := cfg.required_errors(need_slack=post_slack):
        for e in errors:
            _die(e)

    service = IntelligenceService(api_key=cfg.openai.api_key, model=cfg.openai.model)
    meeting = service.extract(transcript.read_text())

    rendered = _render(meeting, format)
    typer.echo(rendered)
    if output:
        output.write_text(rendered)
        typer.secho(f"✓ wrote {output}", fg=typer.colors.GREEN, err=True)

    if post_slack:
        slack = SlackService(
            token=cfg.slack.api_token, default_channel=channel or cfg.slack.channel
        )
        slack.post_message(to_slack(meeting))
        typer.secho(f"✓ posted to {channel or cfg.slack.channel}", fg=typer.colors.GREEN, err=True)


@app.command()
def process(
    audio: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    format: str = typer.Option("markdown", "--format", "-f"),
    output: Path | None = typer.Option(None, "--output", "-o"),
    save_transcript: Path | None = typer.Option(
        None, "--save-transcript", help="Also write the raw transcript to this path."
    ),
    post_slack: bool = typer.Option(False, "--slack"),
    channel: str | None = typer.Option(None, "--channel", "-c"),
    language: str | None = typer.Option(None, "--language", "-l"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Full pipeline: audio → transcript → structured meeting brief."""
    _setup_logging(debug)
    cfg = Config.from_env()
    if errors := cfg.required_errors(need_slack=post_slack):
        for e in errors:
            _die(e)

    transcriber = TranscriptionService(
        api_key=cfg.openai.api_key,
        model=cfg.openai.whisper_model,
        language=language,
    )
    typer.secho(f"→ transcribing {audio.name}…", err=True)
    transcript_result = transcriber.transcribe(audio)
    if not transcript_result.text:
        _die("Whisper returned no text.")
    typer.secho(
        f"  ✓ {transcript_result.word_count} words, {transcript_result.duration_seconds:.1f}s",
        fg=typer.colors.GREEN,
        err=True,
    )

    if save_transcript:
        save_transcript.write_text(transcript_result.text)

    typer.secho("→ extracting intelligence…", err=True)
    intel = IntelligenceService(api_key=cfg.openai.api_key, model=cfg.openai.model)
    meeting = intel.extract(transcript_result.text)
    typer.secho(
        f"  ✓ {len(meeting.action_items)} actions, "
        f"{len(meeting.decisions)} decisions, "
        f"{len(meeting.key_points)} key points",
        fg=typer.colors.GREEN,
        err=True,
    )

    rendered = _render(meeting, format)
    typer.echo(rendered)
    if output:
        output.write_text(rendered)
        typer.secho(f"  ✓ wrote {output}", fg=typer.colors.GREEN, err=True)

    if post_slack:
        slack = SlackService(
            token=cfg.slack.api_token, default_channel=channel or cfg.slack.channel
        )
        slack.post_message(to_slack(meeting))
        typer.secho(
            f"  ✓ posted to {channel or cfg.slack.channel}", fg=typer.colors.GREEN, err=True
        )


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port", "-p"),
) -> None:
    """Start the FastAPI server (requires `pip install 'echoscribe[server]'`)."""
    _setup_logging(False)
    cfg = Config.from_env()
    if not cfg.openai.api_key:
        typer.secho(
            "⚠ OPENAI_API_KEY is not set — the server will start but /v1/* will return 500.",
            fg=typer.colors.YELLOW,
            err=True,
        )
    from echoscribe.server import run as run_server

    run_server(host=host, port=port)


@app.command()
def watch(
    directory: Path = typer.Argument(..., help="Directory to watch for new audio files."),
    format: str = typer.Option("markdown", "--format", "-f"),
    post_slack: bool = typer.Option(False, "--slack"),
    channel: str | None = typer.Option(None, "--channel", "-c"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Watch a directory and process every new audio file that lands in it.

    The structured brief is written next to the source file:
    `meeting.mp3` → `meeting.brief.md` (or `.slack.txt` / `.json`).
    """
    _setup_logging(debug)
    cfg = Config.from_env()
    if errors := cfg.required_errors(need_slack=post_slack):
        for e in errors:
            _die(e)

    from echoscribe.watch import watch_directory

    suffix = {"markdown": ".brief.md", "slack": ".slack.txt", "json": ".brief.json"}[format]

    def handle(audio_path: Path) -> None:
        transcriber = TranscriptionService(
            api_key=cfg.openai.api_key, model=cfg.openai.whisper_model
        )
        transcript = transcriber.transcribe(audio_path).text
        meeting = IntelligenceService(api_key=cfg.openai.api_key, model=cfg.openai.model).extract(
            transcript
        )

        rendered = _render(meeting, format)
        out_path = audio_path.with_suffix(audio_path.suffix + suffix)
        out_path.write_text(rendered)
        typer.secho(f"  ✓ {audio_path.name} → {out_path.name}", fg=typer.colors.GREEN, err=True)

        if post_slack:
            slack = SlackService(
                token=cfg.slack.api_token, default_channel=channel or cfg.slack.channel
            )
            slack.post_message(to_slack(meeting))

    typer.secho(f"watching {directory.resolve()} for new audio files…", err=True)
    watch_directory(directory, handle)


@app.command(name="check-config")
def check_config() -> None:
    """Print which environment variables are set vs missing."""
    cfg = Config.from_env()

    def row(label: str, ok: bool, hint: str = "") -> None:
        mark = (
            typer.style("✓", fg=typer.colors.GREEN) if ok else typer.style("✗", fg=typer.colors.RED)
        )
        status = "set" if ok else "missing"
        line = f"  {mark} {label}: {status}"
        if hint:
            line += f"  ({hint})"
        typer.echo(line)

    typer.echo("EchoScribe configuration")
    typer.echo("")
    row(
        "OPENAI_API_KEY",
        bool(cfg.openai.api_key),
        f"model={cfg.openai.model}, whisper={cfg.openai.whisper_model}",
    )
    row("SLACK_API_TOKEN", bool(cfg.slack.api_token), f"channel={cfg.slack.channel} (optional)")
    typer.echo("")

    if cfg.openai.api_key:
        typer.secho("✓ ready", fg=typer.colors.GREEN)
    else:
        typer.secho("✗ OPENAI_API_KEY required to run the pipeline", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Print version and exit."""
    typer.echo(f"echoscribe {__version__}")


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        typer.secho("\n✗ interrupted", fg=typer.colors.YELLOW, err=True)
        sys.exit(130)


if __name__ == "__main__":
    main()
