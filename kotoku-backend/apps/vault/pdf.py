import hashlib
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def render_vault_pdf(snapshot: dict) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    doc_id = hashlib.md5(snapshot.get("snapshot_hash", "").encode()).hexdigest()
    c._doc._ID = f"({doc_id})".encode()
    width, height = A4
    y = height - 20 * mm

    def text(line, bold=False):
        nonlocal y
        if bold:
            c.setFont("Helvetica-Bold", 11)
        else:
            c.setFont("Helvetica", 10)
        c.drawString(15 * mm, y, line)
        y -= 5 * mm

    def gap(n=3):
        nonlocal y
        y -= n * mm

    text("KOTOKU — Sealed Agreement Record", bold=True)
    gap()
    text(f"Agreement ID: {snapshot.get('agreement_id', '')}")
    text(f"Title: {snapshot.get('title', '')}")
    text(f"Scenario: {snapshot.get('scenario_template', '')}")
    text(f"Sealed At: {snapshot.get('sealed_at', '')}")
    gap()

    text("Parties", bold=True)
    for p in snapshot.get("parties", []):
        text(f"  {p.get('display_name', '')} — {p.get('role', '')} ({p.get('phone', '')})")
    if not snapshot.get("parties"):
        text("  (none)")
    gap()

    text("Evidence Items", bold=True)
    for e in snapshot.get("evidence_items", []):
        text(
            f"  {e.get('original_name', '')} [{e.get('file_type', '')}] "
            f"hash={e.get('file_hash', '')}"
        )
    if not snapshot.get("evidence_items"):
        text("  (none)")
    gap()

    text("Consent Records", bold=True)
    for cr in snapshot.get("consent_records", []):
        text(f"  {cr.get('actor', '')} — consented at {cr.get('consented_at', 'N/A')}")
    if not snapshot.get("consent_records"):
        text("  (none)")
    gap()

    text("Integrity", bold=True)
    text(f"Snapshot Hash: {snapshot.get('snapshot_hash', '')}")
    text(f"Generated: {snapshot.get('sealed_at', '')}")

    c.showPage()
    c.save()
    return buffer.getvalue()
