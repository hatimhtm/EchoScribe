"""Tests for the structured-intelligence service."""

import json
from unittest.mock import MagicMock

import pytest

from echoscribe.services.intelligence import (
    ActionItem,
    Decision,
    IntelligenceService,
    MeetingIntelligence,
)


def _fake_meeting() -> MeetingIntelligence:
    return MeetingIntelligence(
        title="Weekly Sync",
        summary="Discussed Q3 roadmap and onboarding.",
        participants=["Alice", "Bob"],
        key_points=["Launch on Friday", "Hire two designers"],
        decisions=[Decision(decision="Ship v3 Friday", rationale="Demo deadline")],
        action_items=[ActionItem(task="Draft launch post", owner="Alice", due="2026-05-15")],
        sentiment="positive",
        follow_up_questions=["Who owns the launch post if Alice is OOO?"],
    )


class TestIntelligenceService:
    @pytest.fixture
    def service(self):
        svc = IntelligenceService(api_key="sk-test")
        svc._client = MagicMock()
        return svc

    def test_empty_transcript_short_circuits(self, service):
        result = service.extract("   ")
        assert result.title == "Empty transcript"
        assert result.action_items == []

    def test_parse_path_returns_parsed_pydantic(self, service):
        # `beta.chat.completions.parse` returns the parsed object directly
        parsed = _fake_meeting()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(parsed=parsed))]
        service._client.beta.chat.completions.parse.return_value = response

        result = service.extract("Some transcript")

        assert isinstance(result, MeetingIntelligence)
        assert result.title == "Weekly Sync"
        assert len(result.action_items) == 1
        assert result.action_items[0].owner == "Alice"

    def test_fallback_to_json_schema_when_parse_unavailable(self, service):
        # Force the parse() path to raise AttributeError → fallback should run
        service._client.beta.chat.completions.parse.side_effect = AttributeError
        fake_json = _fake_meeting().model_dump_json()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content=fake_json))]
        service._client.chat.completions.create.return_value = response

        result = service.extract("Some transcript")

        assert isinstance(result, MeetingIntelligence)
        assert result.title == "Weekly Sync"
        # Validates that json_schema response_format was requested
        call = service._client.chat.completions.create.call_args
        assert call.kwargs["response_format"]["type"] == "json_schema"

    def test_fallback_handles_bad_json_via_pydantic_validation(self, service):
        service._client.beta.chat.completions.parse.side_effect = AttributeError
        response = MagicMock()
        response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({"title": "T", "summary": "S"})))
        ]
        service._client.chat.completions.create.return_value = response

        result = service.extract("transcript")
        # Required fields present; defaults fill the rest
        assert result.title == "T"
        assert result.participants == []
        assert result.sentiment == "neutral"


class TestPydanticModels:
    def test_action_item_owner_is_optional(self):
        a = ActionItem(task="Buy milk")
        assert a.owner == ""
        assert a.due == ""

    def test_meeting_intelligence_round_trips_via_json(self):
        m = _fake_meeting()
        as_json = m.model_dump_json()
        restored = MeetingIntelligence.model_validate_json(as_json)
        assert restored == m
