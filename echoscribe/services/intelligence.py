"""Meeting intelligence — one structured-output call instead of three.

The previous summarization service made three sequential GPT calls (summary,
action items, key points) and string-parsed each response. In 3.0 we lean on
the model's structured-output mode (JSON schema enforced by OpenAI) and ask
for everything at once — cheaper, faster, and the schema validates the shape
so downstream code doesn't have to.
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are a precise meeting-intelligence analyst. Given a meeting transcript,
extract a complete structured summary. Be concrete and faithful to the
transcript — never invent participants, decisions, or action items that
aren't supported by the text. Each action item must include an owner if one
was assigned in the transcript (otherwise leave owner empty). Each key
decision should capture both the decision and its rationale where stated.
"""


class ActionItem(BaseModel):
    """A single action item from the meeting."""

    task: str = Field(..., description="What needs to be done")
    owner: str = Field("", description="Who is responsible (empty if unassigned)")
    due: str = Field("", description="Deadline if mentioned, empty otherwise")


class Decision(BaseModel):
    """A decision made during the meeting."""

    decision: str = Field(..., description="What was decided")
    rationale: str = Field("", description="Why, where stated in the transcript")


class MeetingIntelligence(BaseModel):
    """Structured output for a meeting transcript."""

    title: str = Field(..., description="Concise inferred meeting title")
    summary: str = Field(..., description="3-5 sentence overview of the meeting")
    participants: list[str] = Field(
        default_factory=list,
        description="Speakers/participants mentioned by name in the transcript",
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Up to 6 main discussion points or topics",
    )
    decisions: list[Decision] = Field(
        default_factory=list,
        description="Concrete decisions made during the meeting",
    )
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Action items with owner + deadline where stated",
    )
    sentiment: Literal["positive", "neutral", "tense", "mixed"] = Field(
        "neutral",
        description="Overall tone of the meeting",
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Open questions or unresolved threads to revisit",
    )


class IntelligenceService:
    """Extract structured meeting intelligence from a transcript."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def extract(self, transcript: str) -> MeetingIntelligence:
        """Run the model and return a validated MeetingIntelligence."""
        if not transcript or not transcript.strip():
            return MeetingIntelligence(
                title="Empty transcript",
                summary="No content was provided to analyze.",
            )

        logger.info("extracting meeting intelligence (%d chars)", len(transcript))

        # Try the strict structured-output path first (parse + Pydantic).
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Meeting transcript:\n\n{transcript}"},
                ],
                response_format=MeetingIntelligence,
            )
            parsed = response.choices[0].message.parsed
            if parsed is not None:
                return parsed
        except (AttributeError, TypeError):
            # SDK older than 1.40 doesn't have `beta.chat.completions.parse`.
            logger.debug("falling back to json_schema response_format")

        return self._extract_via_json_schema(transcript)

    def _extract_via_json_schema(self, transcript: str) -> MeetingIntelligence:
        """Fallback for SDKs without `parse()`: use json_schema response_format."""
        schema = MeetingIntelligence.model_json_schema()
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Meeting transcript:\n\n{transcript}"},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "MeetingIntelligence",
                    "schema": schema,
                    "strict": True,
                },
            },
        )
        content = response.choices[0].message.content or "{}"
        return MeetingIntelligence.model_validate(json.loads(content))
