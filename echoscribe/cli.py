"""EchoScribe CLI - Meeting transcription and summarization tool."""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer

from echoscribe.config import Config
from echoscribe.services.transcription import TranscriptionService
from echoscribe.services.summarization import SummarizationService
from echoscribe.services.slack import SlackService
from echoscribe.services.recorder import AudioRecorder

app = typer.Typer(
    name="echoscribe",
    help="📝 Meeting transcription and summarization tool",
    add_completion=False,
)

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def transcribe(
    audio_file: Path = typer.Argument(..., help="Path to audio file to transcribe"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for transcription"),
    language: str = typer.Option("en-US", "--language", "-l", help="Language code (BCP-47)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Transcribe an audio file to text."""
    setup_logging(debug)
    
    if not audio_file.exists():
        typer.echo(f"Error: File not found: {audio_file}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"🎙️ Transcribing: {audio_file}")
    
    try:
        service = TranscriptionService(language_code=language)
        result = service.transcribe(audio_file)
        
        if result and result.text:
            typer.echo(f"\n📝 Transcription ({result.confidence:.0%} confidence):\n")
            typer.echo(result.text)
            
            if output:
                output.write_text(result.text)
                typer.echo(f"\n✅ Saved to: {output}")
        else:
            typer.echo("No transcription available", err=True)
            raise typer.Exit(1)
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def summarize(
    transcription_file: Path = typer.Argument(..., help="Path to transcription text file"),
    post_slack: bool = typer.Option(False, "--slack", "-s", help="Post summary to Slack"),
    channel: Optional[str] = typer.Option(None, "--channel", "-c", help="Slack channel to post to"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Summarize a meeting transcription."""
    setup_logging(debug)
    
    config = Config.from_env()
    
    if not config.openai.api_key:
        typer.echo("Error: OPENAI_API_KEY environment variable required", err=True)
        raise typer.Exit(1)
    
    if not transcription_file.exists():
        typer.echo(f"Error: File not found: {transcription_file}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"📊 Summarizing: {transcription_file}")
    
    try:
        transcription = transcription_file.read_text()
        
        summarizer = SummarizationService(
            api_key=config.openai.api_key,
            model=config.openai.model,
        )
        
        summary = summarizer.summarize(transcription)
        formatted = summarizer.format_for_slack(summary)
        
        typer.echo(f"\n{formatted}")
        
        if post_slack:
            if not config.slack.api_token:
                typer.echo("Error: SLACK_API_TOKEN required for --slack", err=True)
                raise typer.Exit(1)
            
            slack = SlackService(
                token=config.slack.api_token,
                default_channel=channel or config.slack.channel,
            )
            slack.post_meeting_summary(formatted)
            typer.echo(f"\n✅ Posted to Slack: {channel or config.slack.channel}")
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def process(
    audio_file: Path = typer.Argument(..., help="Path to audio file"),
    post_slack: bool = typer.Option(True, "--slack/--no-slack", help="Post to Slack"),
    channel: Optional[str] = typer.Option(None, "--channel", "-c", help="Slack channel"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Full pipeline: transcribe audio and summarize."""
    setup_logging(debug)
    
    config = Config.from_env()
    errors = config.validate()
    
    if errors:
        for error in errors:
            typer.echo(f"Config error: {error}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"🎙️ Processing: {audio_file}")
    
    try:
        # Step 1: Transcribe
        typer.echo("  → Transcribing audio...")
        transcriber = TranscriptionService()
        result = transcriber.transcribe(audio_file)
        
        if not result or not result.text:
            typer.echo("Error: No transcription available", err=True)
            raise typer.Exit(1)
        
        typer.echo(f"  ✓ Transcription complete ({len(result.text)} chars)")
        
        # Step 2: Summarize
        typer.echo("  → Summarizing...")
        summarizer = SummarizationService(
            api_key=config.openai.api_key,
            model=config.openai.model,
        )
        summary = summarizer.summarize(result.text)
        formatted = summarizer.format_for_slack(summary)
        
        typer.echo(f"  ✓ Summary complete")
        typer.echo(f"\n{formatted}")
        
        # Step 3: Post to Slack
        if post_slack:
            typer.echo("  → Posting to Slack...")
            slack = SlackService(
                token=config.slack.api_token,
                default_channel=channel or config.slack.channel,
            )
            slack.post_meeting_summary(formatted)
            typer.echo(f"  ✓ Posted to {channel or config.slack.channel}")
        
        typer.echo("\n✅ Done!")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def check_config() -> None:
    """Validate configuration and show status."""
    config = Config.from_env()
    errors = config.validate()
    
    typer.echo("📋 Configuration Status\n")
    
    # Slack
    slack_ok = bool(config.slack.api_token)
    status = "✓" if slack_ok else "✗"
    typer.echo(f"  {status} SLACK_API_TOKEN: {'set' if slack_ok else 'missing'}")
    typer.echo(f"    Channel: {config.slack.channel}")
    
    # OpenAI
    openai_ok = bool(config.openai.api_key)
    status = "✓" if openai_ok else "✗"
    typer.echo(f"  {status} OPENAI_API_KEY: {'set' if openai_ok else 'missing'}")
    typer.echo(f"    Model: {config.openai.model}")
    
    # Google Cloud
    import os
    google_ok = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    status = "✓" if google_ok else "✗"
    typer.echo(f"  {status} GOOGLE_APPLICATION_CREDENTIALS: {'set' if google_ok else 'missing'}")
    
    typer.echo("")
    
    if errors:
        typer.echo("❌ Configuration incomplete")
        raise typer.Exit(1)
    else:
        typer.echo("✅ All required configuration is set")


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
