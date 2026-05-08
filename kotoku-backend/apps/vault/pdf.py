"""Plain, deterministic PDF renderer for sealed vault entries.

The PDF is intentionally simple: a header, key agreement fields, parties
table, and evidence list.  No images or complex layout — just a readable
A4 document that can be printed or shared.
"""
from __future__ import annotations

import io
from datetime import timezone as dt_timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_STYLES = getSampleStyleSheet()

_HEADING = ParagraphStyle(
    "KotokuHeading",
    parent=_STYLES["Heading1"],
    fontSize=16,
    spaceAfter=6,
)
_SUBHEADING = ParagraphStyle(
    "KotokuSubheading",
    parent=_STYLES["Heading2"],
    fontSize=12,
    spaceBefore=12,
    spaceAfter=4,
)
_BODY = ParagraphStyle(
    "KotokuBody",
    parent=_STYLES["Normal"],
    fontSize=10.5,
    leading=14,
)
_SMALL = ParagraphStyle(
    "KotokuSmall",
    parent=_STYLES["Normal"],
    fontSize=8,
    textColor=colors.grey,
)
_MONO = ParagraphStyle(
    "KotokuMono",
    parent=_STYLES["Normal"],
    fontSize=8,
    leading=11,
    fontName="Courier",
    textColor=colors.HexColor("#333333"),
)
_SECTION = ParagraphStyle(
    "KotokuSection",
    parent=_STYLES["Heading2"],
    fontSize=11,
    spaceBefore=14,
    spaceAfter=4,
    textColor=colors.HexColor("#1a1a2e"),
)

_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
])


def _fmt_dt(dt) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is not None:
        dt = dt.astimezone(dt_timezone.utc).replace(tzinfo=None)
    return dt.strftime("%d %b %Y, %H:%M UTC")


def render_vault_pdf(entry_id: int) -> bytes:
    """Return a PDF as raw bytes for the given VaultEntry id."""
    from apps.vault.models import VaultEntry  # noqa: PLC0415

    entry = (
        VaultEntry.objects.select_related("agreement", "agreement__created_by")
        .prefetch_related(
            "agreement__parties",
            "agreement__evidence_items",
            "agreement__revisions",
            "agreement__annotations",
        )
        .get(pk=entry_id)
    )
    agreement = entry.agreement

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []

    # ── Header ──────────────────────────────────────────────────────────── #
    story.append(Paragraph("KOTOKU — SEALED AGREEMENT", _HEADING))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.3 * cm))

    # ── Core fields ──────────────────────────────────────────────────────── #
    story.append(Paragraph(f"<b>Title:</b> {agreement.title}", _BODY))
    story.append(Paragraph(f"<b>Scenario:</b> {agreement.scenario_template or '—'}", _BODY))
    story.append(Paragraph(f"<b>Status:</b> {agreement.status}", _BODY))
    story.append(Paragraph(f"<b>Sealed at:</b> {_fmt_dt(agreement.sealed_at)}", _BODY))
    if agreement.description:
        story.append(Paragraph(f"<b>Description:</b> {agreement.description}", _BODY))
    story.append(Spacer(1, 0.5 * cm))

    # ── Parties ──────────────────────────────────────────────────────────── #
    story.append(Paragraph("Parties", _SECTION))
    parties = list(agreement.parties.order_by("role"))
    if parties:
        party_data = [["Role", "Name", "ID Type", "ID Number", "Phone"]]
        for p in parties:
            party_data.append([
                p.role.title(),
                p.display_name,
                p.id_type or "—",
                p.id_number or "—",
                p.phone or "—",
            ])
        t = Table(party_data, colWidths=[2.5 * cm, 4 * cm, 2.5 * cm, 4 * cm, 3 * cm])
        t.setStyle(_TABLE_STYLE)
        story.append(t)
    else:
        story.append(Paragraph("No parties recorded.", _BODY))

    # ── Evidence ─────────────────────────────────────────────────────────── #
    story.append(Paragraph("Evidence", _SECTION))
    evidence = list(
        agreement.evidence_items.filter(upload_status="confirmed").order_by("evidence_type")
    )
    if evidence:
        ev_data = [["Type", "File Type", "File Hash (SHA-256)"]]
        for e in evidence:
            ev_data.append([
                e.evidence_type or "—",
                e.file_type,
                e.file_hash if e.file_hash else "—",
            ])
        t = Table(ev_data, colWidths=[5 * cm, 3 * cm, 8 * cm])
        t.setStyle(_TABLE_STYLE)
        story.append(t)
    else:
        story.append(Paragraph("No confirmed evidence recorded.", _BODY))

    # ── Agreement Details (field_data) ──────────────────────────────────── #
    if agreement.field_data:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Agreement Details", _SECTION))
        fd_rows = [["Field", "Value"]]
        for key, value in agreement.field_data.items():
            label = key.replace("_", " ").title()
            fd_rows.append([label, str(value)])
        fd_table = Table(fd_rows, colWidths=[5 * cm, 11 * cm])
        fd_table.setStyle(_TABLE_STYLE)
        story.append(fd_table)

    # ── Revision History ────────────────────────────────────────────────── #
    revisions = list(agreement.revisions.all())
    if revisions:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Revision History", _SECTION))
        rev_data = [["#", "Sealed At", "Seal Hash"]]
        for rev in revisions:
            rev_data.append([
                str(rev.revision_number),
                _fmt_dt(rev.sealed_at),
                rev.seal_hash,
            ])
        rev_table = Table(rev_data, colWidths=[1.5 * cm, 4.5 * cm, 10 * cm])
        rev_table.setStyle(_TABLE_STYLE)
        story.append(rev_table)

    # ── Annotations ─────────────────────────────────────────────────────── #
    annotations = list(agreement.annotations.select_related("author_party").all())
    if annotations:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Notes", _SECTION))
        ann_data = [["Author", "Note", "Date"]]
        for ann in annotations:
            ann_data.append([
                ann.author_party.display_name,
                ann.body[:200],
                _fmt_dt(ann.created_at),
            ])
        ann_table = Table(ann_data, colWidths=[3.5 * cm, 9 * cm, 3.5 * cm])
        ann_table.setStyle(_TABLE_STYLE)
        story.append(ann_table)

    # ── Integrity ────────────────────────────────────────────────────────── #
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "<b>Seal hash (SHA-256):</b>",
        _SMALL,
    ))
    story.append(Paragraph(
        agreement.seal_hash or "—",
        _MONO,
    ))
    story.append(Paragraph(
        "This document is a tamper-evident record generated by Kotoku. "
        "The seal hash above is a SHA-256 digest of the agreement's state at the time of sealing.",
        _SMALL,
    ))

    doc.build(story)
    return buf.getvalue()
