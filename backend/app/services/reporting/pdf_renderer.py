from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_pdf(content: dict, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.grey)

    story = []
    summary = content["incident_summary"]

    story.append(Paragraph("Mini-SOC Incident Report", h1))
    story.append(Paragraph(summary["title"], h2))
    story.append(
        Paragraph(
            f"Severity: {summary['severity']} | Status: {summary['status']} | "
            f"Created: {summary['created_at']} | Incident ID: {summary['id']}",
            body,
        )
    )
    story.append(Spacer(1, 12))
    story.append(Paragraph(summary["description"] or "No description available.", body))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Alerts", h2))
    table_data = [["Title", "Severity", "Rule", "Source IP", "Status"]]
    for a in content["alerts"]:
        table_data.append([a["title"], a["severity"], a["detection_rule"], a["source_ip"] or "-", a["status"]])
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Timeline", h2))
    for item in content["timeline"]:
        story.append(Paragraph(f"{item['timestamp']} - {item['event']}", body))
    story.append(Spacer(1, 16))

    story.append(Paragraph("AI Investigation & Risk Assessment", h2))
    for inv in content["investigations"]:
        story.append(Paragraph(f"Investigation {inv['id']} (status: {inv['status']})", styles["Heading3"]))
        story.append(Paragraph(f"Risk score: {inv['risk_score']} | LLM available: {inv['llm_available']}", body))
        if inv.get("risk_factors"):
            story.append(Paragraph("Risk factors: " + "; ".join(inv["risk_factors"]), small))
        if inv.get("ai_summary"):
            story.append(Paragraph(f"AI summary: {inv['ai_summary']}", body))
            story.append(
                Paragraph(
                    f"AI severity: {inv.get('ai_severity')} | AI confidence: {inv.get('ai_confidence')} | "
                    f"MITRE: {inv.get('mitre_technique') or '-'} | OWASP: {inv.get('owasp_category') or '-'}",
                    body,
                )
            )
            if inv.get("recommended_actions"):
                story.append(Paragraph("Recommended actions (require human approval):", body))
                for action in inv["recommended_actions"]:
                    story.append(Paragraph(f"- {action}", body))
            if inv.get("ai_references"):
                cited = "; ".join(
                    f"[{r['id']}] {r['source']}" + (f" p. {r['page']}" if r.get("page") else "") for r in inv["ai_references"]
                )
                story.append(Paragraph(f"Knowledge cited by the AI: {cited}", small))
        else:
            story.append(Paragraph("AI analysis was not available for this investigation.", body))

        if inv.get("threat_intelligence"):
            story.append(Paragraph("Threat intelligence:", body))
            for ti in inv["threat_intelligence"]:
                story.append(
                    Paragraph(
                        f"- {ti['indicator']} ({ti['indicator_type']}): {ti['reputation']} "
                        f"[source: {ti['source']}, confidence: {ti['confidence']}]",
                        small,
                    )
                )
        if inv.get("rag_sources"):
            sources = ", ".join(sorted({s["source"] for s in inv["rag_sources"] if s.get("source")}))
            story.append(Paragraph(f"Knowledge base sources referenced: {sources}", small))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Containment Status", h2))
    story.append(Paragraph(content["containment_status"], body))

    doc.build(story)
