#!/usr/bin/env python3
"""
ics_builder.py
==============
Build a buyer-facing iCalendar (.ics) string for a real estate showing.

Used by the post-showing flow when the agent's CALENDAR_PROVIDER is `lofty`
or `skip`. In those cases the chosen calendar adapter cannot email the buyer,
so we generate a polished .ics and send it through Lofty.

When CALENDAR_PROVIDER is `google` or `outlook`, do NOT call this module.
Those providers email the buyer their own native invite via attendeeEmails.
Sending the .ics on top would duplicate the invite in the buyer's inbox.

Usage:
    from ics_builder import build_ics

    ics_text = build_ics(
        uid="showing-12345-1717180800@sellingpdxhomes.com",
        summary="Showing: 1234 Main St",
        description="3 bed / 2 bath in Portland. See you there.",
        location="1234 Main St, Portland, OR 97214",
        start_iso="2026-05-15T14:00:00-07:00",
        end_iso="2026-05-15T14:30:00-07:00",
        organizer_name="Joe Saling",
        organizer_email="joe@sellingpdxhomes.com",
        attendee_name="Jane Buyer",
        attendee_email="jane@example.com",
    )

CLI smoke test:
    python3 ics_builder.py
    # Prints a sample .ics to stdout

Implementation notes:
    - No external dependencies (no `icalendar`, no `pytz`). Standard library only.
    - Times are converted to UTC and formatted as YYYYMMDDTHHMMSSZ per RFC 5545.
    - Special characters in text fields (commas, semicolons, newlines, backslashes)
      are escaped per RFC 5545 section 3.3.11.
    - Long lines are folded at 75 octets per RFC 5545 section 3.1.
"""

from datetime import datetime, timezone
from typing import Optional


# RFC 5545 says lines longer than 75 octets MUST be folded. We fold at 73 to
# leave room for the leading space on continuation lines.
MAX_LINE_OCTETS = 73


def _format_utc(iso_string: str) -> str:
    """Convert an ISO 8601 datetime with offset to UTC YYYYMMDDTHHMMSSZ.

    Accepts strings like "2026-05-15T14:00:00-07:00" or with "Z" suffix.
    Naive datetimes (no offset) are rejected because real-estate showings
    span timezone changes (DST) and ambiguous local times cause mis-sent
    invites.
    """
    if iso_string.endswith("Z"):
        iso_string = iso_string[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(iso_string)
    except ValueError as e:
        raise ValueError(
            f"Could not parse ISO 8601 datetime '{iso_string}'. "
            f"Expected format like '2026-05-15T14:00:00-07:00'. "
            f"Underlying error: {e}"
        )
    if dt.tzinfo is None:
        raise ValueError(
            f"Datetime '{iso_string}' has no timezone offset. "
            f"Showing times must include an offset (e.g. -07:00 for Pacific DST)."
        )
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%SZ")


def _escape_text(text: str) -> str:
    """Escape per RFC 5545 section 3.3.11.

    Order matters: backslash MUST be escaped first so we don't double-escape
    the slashes we add for the other characters.
    """
    if text is None:
        return ""
    return (text.replace("\\", "\\\\")
                .replace(",", "\\,")
                .replace(";", "\\;")
                .replace("\r\n", "\\n")
                .replace("\n", "\\n"))


def _fold_line(line: str) -> str:
    """Fold long lines per RFC 5545 section 3.1.

    Lines longer than 75 octets must be split. Continuation lines start with
    a single space. We use UTF-8 octet length (not character length) because
    the spec is octet-based and emoji or accented chars can push us over.
    """
    encoded = line.encode("utf-8")
    if len(encoded) <= MAX_LINE_OCTETS:
        return line
    # Walk the bytes and re-decode in chunks. A safer approach than slicing
    # the string by character count, since UTF-8 chars are variable width.
    parts = []
    start = 0
    while start < len(encoded):
        # Try the full chunk first; back off if it lands mid-character.
        end = min(start + MAX_LINE_OCTETS, len(encoded))
        while end > start:
            try:
                chunk = encoded[start:end].decode("utf-8")
                break
            except UnicodeDecodeError:
                end -= 1
        parts.append(chunk)
        start = end
    # First part stands alone; remaining parts get a leading space.
    return parts[0] + "".join("\r\n " + p for p in parts[1:])


def _emit(buf, key: str, value: str) -> None:
    """Append a folded `KEY:value` line (CRLF terminated) to the buffer."""
    buf.append(_fold_line(f"{key}:{value}"))


def build_ics(
    uid: str,
    summary: str,
    description: str,
    location: str,
    start_iso: str,
    end_iso: str,
    organizer_name: str,
    organizer_email: str,
    attendee_name: Optional[str] = None,
    attendee_email: Optional[str] = None,
    prodid: str = "-//Saling Homes//Lofty Cowork Helper//EN",
) -> str:
    """Build a single-event iCalendar string suitable for emailing the buyer.

    Args:
        uid: Stable, globally-unique event ID. Recommended pattern:
            f"showing-{lead_id}-{int(start.timestamp())}@<your-domain>"
            Stable UIDs let the buyer's calendar update existing events on
            reschedules instead of creating duplicates.
        summary: Short title shown in the calendar UI.
        description: Long-form details. Plain text recommended (most calendars
            don't render HTML in DESCRIPTION). Newlines OK.
        location: Free-form address. Calendars geocode this for the map link.
        start_iso, end_iso: ISO 8601 with timezone offset.
        organizer_name, organizer_email: The agent.
        attendee_name, attendee_email: The buyer. Optional; pass None if the
            lead has no email and the .ics is being attached to an SMS link.
        prodid: Identifier for this skill in the .ics PRODID field. Adjust
            per agent if you want to brand the source.

    Returns:
        The full iCalendar string with CRLF line endings, ready to be:
            - included as a `text/calendar` MIME attachment, OR
            - written to disk as `showing.ics`, OR
            - inlined into an email body in a code block (less polished but works).
    """
    if not summary:
        raise ValueError("summary is required")
    if not uid:
        raise ValueError("uid is required")

    dt_start = _format_utc(start_iso)
    dt_end = _format_utc(end_iso)
    dt_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    buf = []
    buf.append("BEGIN:VCALENDAR")
    buf.append("VERSION:2.0")
    _emit(buf, "PRODID", prodid)
    buf.append("CALSCALE:GREGORIAN")
    buf.append("METHOD:REQUEST")
    buf.append("BEGIN:VEVENT")
    _emit(buf, "UID", uid)
    _emit(buf, "DTSTAMP", dt_stamp)
    _emit(buf, "DTSTART", dt_start)
    _emit(buf, "DTEND", dt_end)
    _emit(buf, "SUMMARY", _escape_text(summary))
    if description:
        _emit(buf, "DESCRIPTION", _escape_text(description))
    if location:
        _emit(buf, "LOCATION", _escape_text(location))
    # Organizer
    organizer_line = f'ORGANIZER;CN="{_escape_text(organizer_name)}":mailto:{organizer_email}'
    buf.append(_fold_line(organizer_line))
    # Attendee, optional
    if attendee_email:
        cn = _escape_text(attendee_name or attendee_email)
        attendee_line = (
            f'ATTENDEE;CN="{cn}";'
            f'RSVP=TRUE;PARTSTAT=NEEDS-ACTION;ROLE=REQ-PARTICIPANT:'
            f'mailto:{attendee_email}'
        )
        buf.append(_fold_line(attendee_line))
    buf.append("STATUS:CONFIRMED")
    buf.append("TRANSP:OPAQUE")
    buf.append("END:VEVENT")
    buf.append("END:VCALENDAR")
    return "\r\n".join(buf) + "\r\n"


# -----------------------------------------------------------------
# CLI smoke test
# -----------------------------------------------------------------
def _smoke_test():
    """Print a sample .ics string and run a few sanity checks."""
    sample = build_ics(
        uid="showing-12345-1717180800@sellingpdxhomes.com",
        summary="Showing: 1234 Main St with Jane Buyer",
        description=(
            "3 bed / 2 bath, 1850 sqft. Listed at $625,000.\n"
            "Park on the street. Lockbox on the front door.\n"
            "After the showing, expect a quick feedback text from Joe.\n"
            "- Joe Saling, Saling Homes at eXp Realty, 503-910-7364"
        ),
        location="1234 Main St, Portland, OR 97214",
        start_iso="2026-05-15T14:00:00-07:00",
        end_iso="2026-05-15T14:30:00-07:00",
        organizer_name="Joe Saling",
        organizer_email="joe@sellingpdxhomes.com",
        attendee_name="Jane Buyer",
        attendee_email="jane@example.com",
    )
    print(sample)

    # Sanity checks
    assert "BEGIN:VCALENDAR" in sample
    assert "END:VCALENDAR" in sample
    assert "DTSTART:20260515T210000Z" in sample, \
        "Pacific 14:00 -07:00 should convert to 21:00 UTC"
    assert "DTEND:20260515T213000Z" in sample
    assert "ORGANIZER" in sample and "mailto:joe@sellingpdxhomes.com" in sample
    assert "ATTENDEE" in sample and "mailto:jane@example.com" in sample
    assert "Saling Homes\\, " not in sample, \
        "PRODID does not contain a comma so it should not be escaped"
    print("---")
    print("All smoke-test assertions passed.")


def _test_naive_rejected():
    """Naive datetimes (no offset) must be rejected."""
    try:
        build_ics(
            uid="x",
            summary="x",
            description="",
            location="",
            start_iso="2026-05-15T14:00:00",  # no offset
            end_iso="2026-05-15T14:30:00",
            organizer_name="a",
            organizer_email="a@a.com",
        )
    except ValueError as e:
        assert "no timezone offset" in str(e)
        print("Naive datetime correctly rejected.")
        return
    raise AssertionError("Naive datetime should have raised ValueError")


def _test_escape():
    """Commas and semicolons in summary/description must be escaped."""
    out = build_ics(
        uid="x",
        summary="Showing, with friends; bring snacks",
        description="Line 1\nLine 2",
        location="100 Main, Portland, OR",
        start_iso="2026-05-15T14:00:00-07:00",
        end_iso="2026-05-15T14:30:00-07:00",
        organizer_name="A",
        organizer_email="a@a.com",
    )
    assert "Showing\\, with friends\\; bring snacks" in out
    assert "Line 1\\nLine 2" in out
    assert "100 Main\\, Portland\\, OR" in out
    print("Escape behavior correct.")


def _test_long_line_folding():
    """Lines over 73 octets should fold."""
    long_desc = "A" * 200
    out = build_ics(
        uid="x",
        summary="Short",
        description=long_desc,
        location="",
        start_iso="2026-05-15T14:00:00-07:00",
        end_iso="2026-05-15T14:30:00-07:00",
        organizer_name="A",
        organizer_email="a@a.com",
    )
    # The description line must contain at least one CRLF + space (the fold marker)
    assert "\r\n " in out, "Long DESCRIPTION line should have been folded"
    print("Long-line folding works.")


if __name__ == "__main__":
    _smoke_test()
    _test_naive_rejected()
    _test_escape()
    _test_long_line_folding()
    print("ics_builder smoke tests: ALL PASSED")
