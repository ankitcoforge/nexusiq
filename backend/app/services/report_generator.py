from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from ..models.schemas import FraudReport, FraudFlagSeverity, VerdictType

def generate_pdf_report(report: FraudReport) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("Title", parent=styles["Title"], textColor=colors.HexColor("#1e3a5f"), fontSize=20)
    story.append(Paragraph("NexusIQ — Fraud Detection Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 0.2*inch))

    # Verdict banner
    verdict_color = {
        VerdictType.APPROVE: colors.HexColor("#22c55e"),
        VerdictType.APPROVE_WITH_NOTATION: colors.HexColor("#f59e0b"),
        VerdictType.ESCALATE_SIU: colors.HexColor("#ef4444")
    }.get(report.verdict, colors.gray)
    verdict_style = ParagraphStyle("Verdict", parent=styles["Normal"], textColor=colors.white,
                                   backColor=verdict_color, fontSize=14, spaceAfter=10, spaceBefore=10,
                                   leftIndent=10, rightIndent=10)
    story.append(Paragraph(f"VERDICT: {report.verdict.value}", verdict_style))
    story.append(Spacer(1, 0.15*inch))

    # Summary table
    h_style = ParagraphStyle("H", parent=styles["Heading2"], textColor=colors.HexColor("#1e3a5f"))
    story.append(Paragraph("Summary", h_style))
    summary_data = [
        ["Document", report.document_name],
        ["Session ID", report.session_id[:16] + "..."],
        ["Analysis Date", report.analysis_date[:19]],
        ["Total Flags", str(report.total_flags)],
        ["Critical Flags", str(report.critical_flags)],
        ["Invoice Total", f"${report.invoice_data.total:.2f}"],
        ["Vendor", report.invoice_data.vendor.name.value],
    ]
    t = Table(summary_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))

    # Verdict reasoning
    if report.verdict_reasoning:
        story.append(Paragraph("Verdict Reasoning", h_style))
        story.append(Paragraph(report.verdict_reasoning, styles["Normal"]))
        story.append(Spacer(1, 0.1*inch))

    if report.recommendation:
        story.append(Paragraph("Recommendation", h_style))
        story.append(Paragraph(report.recommendation, styles["Normal"]))
        story.append(Spacer(1, 0.2*inch))

    # Flags
    if report.total_flags > 0:
        story.append(Paragraph("Fraud Flags", h_style))
        for step in report.verification_results:
            for flag in step.flags:
                flag_color = {
                    FraudFlagSeverity.CRITICAL: colors.HexColor("#fee2e2"),
                    FraudFlagSeverity.WARNING: colors.HexColor("#fef9c3"),
                    FraudFlagSeverity.INFO: colors.HexColor("#e0f2fe")
                }.get(flag.severity, colors.white)
                flag_data = [[f"[{flag.severity.value.upper()}] {flag.message}"]]
                ft = Table(flag_data, colWidths=[6.5*inch])
                ft.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), flag_color),
                    ("PADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ]))
                story.append(ft)
                story.append(Spacer(1, 0.05*inch))
        story.append(Spacer(1, 0.1*inch))

    # Verification steps
    story.append(Paragraph("Verification Steps", h_style))
    for step in report.verification_results:
        status_colors_map = {
            "passed": colors.HexColor("#22c55e"),
            "failed": colors.HexColor("#ef4444"),
            "warning": colors.HexColor("#f59e0b"),
            "unavailable": colors.gray,
            "manual_review": colors.HexColor("#8b5cf6")
        }
        sc = status_colors_map.get(step.status.value, colors.gray)
        step_data = [[f"Step {step.step_number}: {step.step_name}", step.summary]]
        st = Table(step_data, colWidths=[2.5*inch, 4*inch])
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), sc),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.05*inch))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
