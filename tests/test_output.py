"""Tests for the Slack / Markdown / JSON output formatters."""

import json

from echoscribe.output import to_json, to_markdown, to_slack
from echoscribe.services.intelligence import ActionItem, Decision, MeetingIntelligence


def _meeting() -> MeetingIntelligence:
    return MeetingIntelligence(
        title="Q3 Planning",
        summary="Planning Q3 roadmap. Decided on three priorities.",
        participants=["Alice", "Bob", "Carol"],
        key_points=["Priorities locked", "Launch in week 4"],
        decisions=[
            Decision(decision="Adopt monorepo", rationale="Easier cross-team work"),
            Decision(decision="Move to weekly demos"),
        ],
        action_items=[
            ActionItem(task="Draft RFC", owner="Alice", due="2026-05-15"),
            ActionItem(task="Schedule design review"),
        ],
        sentiment="positive",
        follow_up_questions=["Migration timeline?"],
    )


class TestMarkdown:
    def test_renders_title_and_summary(self):
        md = to_markdown(_meeting())
        assert "# Q3 Planning" in md
        assert "Planning Q3 roadmap" in md

    def test_renders_all_sections(self):
        md = to_markdown(_meeting())
        for header in ("Participants", "Key points", "Decisions", "Action items", "Follow-up"):
            assert header in md

    def test_action_item_with_owner_and_due(self):
        md = to_markdown(_meeting())
        assert "Draft RFC" in md
        assert "**Alice**" in md
        assert "2026-05-15" in md

    def test_decision_with_rationale_uses_italics(self):
        md = to_markdown(_meeting())
        assert "Adopt monorepo" in md
        assert "Easier cross-team work" in md


class TestSlack:
    def test_uses_mrkdwn_bold(self):
        text = to_slack(_meeting())
        assert "*Q3 Planning*" in text
        assert "*👥 Participants*" in text

    def test_action_items_with_owner(self):
        text = to_slack(_meeting())
        assert "Draft RFC" in text
        assert "*Alice*" in text


class TestJson:
    def test_round_trips(self):
        m = _meeting()
        as_json = to_json(m)
        parsed = json.loads(as_json)
        assert parsed["title"] == "Q3 Planning"
        assert parsed["sentiment"] == "positive"
        assert len(parsed["action_items"]) == 2
