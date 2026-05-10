"""Render `MeetingIntelligence` into Slack, Markdown, or JSON.

One source of truth → many surfaces. Each formatter is a pure function so
callers (CLI, FastAPI server, watch mode) can pick the shape they need.
"""

from __future__ import annotations

from echoscribe.services.intelligence import MeetingIntelligence


def to_markdown(meeting: MeetingIntelligence) -> str:
    """Render a human-readable Markdown brief — pasteable into Notion, Linear, email."""
    lines: list[str] = [f"# {meeting.title}", "", meeting.summary, ""]

    if meeting.participants:
        lines += ["## Participants", ", ".join(meeting.participants), ""]

    if meeting.key_points:
        lines += ["## Key points"]
        lines += [f"- {p}" for p in meeting.key_points]
        lines.append("")

    if meeting.decisions:
        lines += ["## Decisions"]
        for d in meeting.decisions:
            if d.rationale:
                lines.append(f"- **{d.decision}** — _{d.rationale}_")
            else:
                lines.append(f"- **{d.decision}**")
        lines.append("")

    if meeting.action_items:
        lines += ["## Action items"]
        for a in meeting.action_items:
            owner = f" — **{a.owner}**" if a.owner else ""
            due = f" _(due {a.due})_" if a.due else ""
            lines.append(f"- [ ] {a.task}{owner}{due}")
        lines.append("")

    if meeting.follow_up_questions:
        lines += ["## Follow-up questions"]
        lines += [f"- {q}" for q in meeting.follow_up_questions]
        lines.append("")

    lines.append(f"_Sentiment: {meeting.sentiment}_")
    return "\n".join(lines)


def to_slack(meeting: MeetingIntelligence) -> str:
    """Render in Slack's mrkdwn dialect — bullet · bold · italics."""
    lines: list[str] = [f"🎙️ *{meeting.title}*", "", meeting.summary, ""]

    if meeting.participants:
        lines += ["*👥 Participants*", "  " + " · ".join(meeting.participants), ""]

    if meeting.key_points:
        lines.append("*💡 Key points*")
        lines += [f"  • {p}" for p in meeting.key_points]
        lines.append("")

    if meeting.decisions:
        lines.append("*🧭 Decisions*")
        for d in meeting.decisions:
            tail = f" _({d.rationale})_" if d.rationale else ""
            lines.append(f"  • {d.decision}{tail}")
        lines.append("")

    if meeting.action_items:
        lines.append("*✅ Action items*")
        for a in meeting.action_items:
            owner = f" — *{a.owner}*" if a.owner else ""
            due = f" _due {a.due}_" if a.due else ""
            lines.append(f"  • {a.task}{owner}{due}")
        lines.append("")

    if meeting.follow_up_questions:
        lines.append("*❓ Follow-up*")
        lines += [f"  • {q}" for q in meeting.follow_up_questions]
        lines.append("")

    lines.append(f"_sentiment: {meeting.sentiment}_")
    return "\n".join(lines)


def to_json(meeting: MeetingIntelligence, *, indent: int = 2) -> str:
    """Render as JSON — for piping into `jq`, webhooks, or downstream tools."""
    return meeting.model_dump_json(indent=indent)
