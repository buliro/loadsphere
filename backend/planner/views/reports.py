from __future__ import annotations

import json
from io import BytesIO
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import Trip, TRIP_STATUS_COMPLETED


def _unauthorized() -> JsonResponse:
    """Return a 401 JSON response indicating that authentication is required.

    Args:
        None

    Returns:
        JsonResponse: Response payload with a standard authentication error message.
    """
    return JsonResponse({"detail": "Authentication required."}, status=401)


def _build_footer(generated_at: timezone.datetime):
    """Create a footer callback that stamps generation metadata on each PDF page.

    Args:
        generated_at: Localised timestamp indicating when the PDF was produced.

    Returns:
        Callable: ReportLab canvas callback that renders footer content.
    """

    def _footer(canvas, doc):
        """Render footer content onto each PDF page.

        Args:
            canvas: ReportLab canvas object used for drawing operations.
            doc: ReportLab document instance providing page metrics.

        Returns:
            None
        """
        canvas.setFillColor(colors.HexColor("#E5E7EB"))
        canvas.setLineWidth(0.5)
        canvas.line(
            doc.leftMargin,
            doc.bottomMargin - 0.2 * inch,
            doc.pagesize[0] - doc.rightMargin,
            doc.bottomMargin - 0.2 * inch,
        )
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            doc.pagesize[0] - doc.rightMargin,
            doc.bottomMargin - 0.35 * inch,
            f"Generated {generated_at.strftime('%B %d, %Y %H:%M %Z')} • Route Planner",
        )
        canvas.setFillColor(colors.black)

    return _footer


def trip_pdf_report_view(request: HttpRequest, trip_id: int) -> HttpResponse:
    """
    Generate a PDF summary for a completed trip using ReportLab platypus.

    Args:
        request: Incoming HTTP request containing the authenticated user context.
        trip_id: Primary key for the Trip that should be rendered as a report.

    Returns:
        HttpResponse: PDF bytes with appropriate Content-Disposition when successful or a
        JsonResponse: Error payload with the relevant HTTP status code if validation fails.
    """
    if not request.user.is_authenticated:
        return _unauthorized()

    try:
        trip = Trip.objects.select_related("route").prefetch_related("logs", "logs__segments").get(
            id=trip_id,
            user=request.user,
        )
    except Trip.DoesNotExist:
        return JsonResponse({"detail": "Trip not found."}, status=404)

    if trip.status != TRIP_STATUS_COMPLETED:
        return JsonResponse({"detail": "PDF reports are only available for completed trips."}, status=400)

    disposition = request.GET.get("disposition", "attachment").lower()
    if disposition not in {"attachment", "inline"}:
        disposition = "attachment"

    generated_at = timezone.localtime()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.9 * inch,
        bottomMargin=1.1 * inch,
        title=f"Route Report - Trip {trip.id}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="MetaLabel", fontName="Helvetica-Bold", fontSize=9.5, textColor=colors.HexColor("#1E3A8A")))
    styles.add(ParagraphStyle(name="MetaValue", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#1F2937")))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#111827")))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=10, leading=12))
    styles.add(
        ParagraphStyle(
            name="LogSubheading",
            parent=styles["BodyText"],
            fontSize=10.5,
            leading=12,
            textColor=colors.HexColor("#1E3A8A"),
            fontName="Helvetica-Bold",
            spaceBefore=6,
            spaceAfter=2,
        )
    )

    def _location_paragraph(label: str, location: dict[str, Any] | None) -> Paragraph:
        """Create a styled paragraph describing a route location.

        Args:
            label: Human-readable location label (e.g., "Start").
            location: Location dictionary containing address and coordinates, if available.

        Returns:
            Paragraph: ReportLab paragraph element ready to insert into the story flow.
        """
        if not location:
            return Paragraph(f"<b>{label}</b>: —", styles["BodySmall"])
        address = location.get("address") or "—"
        lat = location.get("lat")
        lng = location.get("lng")
        coords = (
            f" (lat {lat:.4f}, lng {lng:.4f})"
            if isinstance(lat, (int, float)) and isinstance(lng, (int, float))
            else ""
        )
        return Paragraph(f"<b>{label}</b>: {address}{coords}", styles["BodySmall"])

    def _segment_location(raw: str | None) -> str:
        if not raw:
            return "—"

        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            parsed = None

        if isinstance(parsed, dict):
            address = parsed.get("address")
            if address:
                return str(address)

        return str(raw)

    story: list[Any] = []

    story.append(Paragraph("Route Planner", styles["Title"]))
    story.append(Spacer(1, 0.18 * inch))

    completed_on = timezone.localtime(trip.updated_at).strftime("%B %d, %Y at %H:%M %Z")
    metadata_rows = [
        [Paragraph("Trip ID", styles["MetaLabel"]), Paragraph(str(trip.id), styles["MetaValue"])],
        [Paragraph("Completed", styles["MetaLabel"]), Paragraph(completed_on, styles["MetaValue"])],
        [Paragraph("Cycle hours used", styles["MetaLabel"]), Paragraph(f"{trip.cycle_hours_used or 0:.1f} hrs", styles["MetaValue"])],
    ]

    metadata_table = Table(metadata_rows, colWidths=[1.6 * inch, 4.65 * inch], hAlign="LEFT")
    metadata_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EFF6FF")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1E3A8A")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#BFDBFE")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DBEAFE")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(metadata_table)
    story.append(Spacer(1, 0.22 * inch))

    story.append(Paragraph("Route details", styles["SectionHeading"]))

    details_rows = [
        [Paragraph("Tractor", styles["MetaLabel"]), Paragraph(trip.tractor_number or "—", styles["MetaValue"])],
        [Paragraph("Trailers", styles["MetaLabel"]), Paragraph(", ".join(trip.trailer_numbers) if trip.trailer_numbers else "—", styles["MetaValue"])],
        [Paragraph("Carriers", styles["MetaLabel"]), Paragraph(", ".join(trip.carrier_names) if trip.carrier_names else "—", styles["MetaValue"])],
        [Paragraph("Shipper", styles["MetaLabel"]), Paragraph(trip.shipper_name or "—", styles["MetaValue"])],
        [Paragraph("Commodity", styles["MetaLabel"]), Paragraph(trip.commodity or "—", styles["MetaValue"])],
    ]

    if getattr(trip, "route", None):
        details_rows.extend(
            [
                [Paragraph("Total distance", styles["MetaLabel"]), Paragraph(f"{trip.route.total_distance:.1f} mi", styles["MetaValue"])],
                [Paragraph("Estimated duration", styles["MetaLabel"]), Paragraph(f"{trip.route.estimated_duration:.1f} hrs", styles["MetaValue"])],
            ]
        )

    details_table = Table(details_rows, colWidths=[1.6 * inch, 4.65 * inch], hAlign="LEFT")
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(details_table)
    story.append(Spacer(1, 0.18 * inch))

    story.extend(
        [
            _location_paragraph("Start", trip.start_location),
            _location_paragraph("Pickup", trip.pickup_location),
            _location_paragraph("Dropoff", trip.dropoff_location),
        ]
    )
    story.append(Spacer(1, 0.24 * inch))

    story.append(Paragraph("Driver logs", styles["SectionHeading"]))

    logs = list(trip.logs.all().order_by("day_number"))
    if not logs:
        story.append(Paragraph("No driver logs recorded for this trip.", styles["BodySmall"]))
    else:
        log_rows: list[list[Paragraph]] = [
            [
                Paragraph("Day", styles["MetaLabel"]),
                Paragraph("Date", styles["MetaLabel"]),
                Paragraph("Driving hrs", styles["MetaLabel"]),
                Paragraph("On duty hrs", styles["MetaLabel"]),
                Paragraph("Off duty hrs", styles["MetaLabel"]),
                Paragraph("Sleeper hrs", styles["MetaLabel"]),
            ]
        ]

        for log in logs:
            driving = (log.total_driving_minutes or 0) / 60
            on_duty = (log.total_on_duty_minutes or 0) / 60
            off_duty = (log.total_off_duty_minutes or 0) / 60
            sleeper = (log.total_sleeper_minutes or 0) / 60
            log_date = log.log_date.strftime("%Y-%m-%d")

            log_rows.append(
                [
                    Paragraph(str(log.day_number), styles["BodySmall"]),
                    Paragraph(log_date, styles["BodySmall"]),
                    Paragraph(f"{driving:.1f}", styles["BodySmall"]),
                    Paragraph(f"{on_duty:.1f}", styles["BodySmall"]),
                    Paragraph(f"{off_duty:.1f}", styles["BodySmall"]),
                    Paragraph(f"{sleeper:.1f}", styles["BodySmall"]),
                ]
            )

        logs_table = Table(
            log_rows,
            colWidths=[0.8 * inch, 1.2 * inch, 1.0 * inch, 1.05 * inch, 1.05 * inch, 1.05 * inch],
            hAlign="LEFT",
        )
        logs_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D4ED8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F1F5F9")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5F5")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(logs_table)

        for log in logs:
            segments = list(log.segments.all().order_by("start_time"))
            log_heading = f"Day {log.day_number} segments ({log.log_date.strftime('%Y-%m-%d')})"
            story.append(Spacer(1, 0.14 * inch))
            story.append(Paragraph(log_heading, styles["LogSubheading"]))

            if log.notes:
                story.append(Paragraph(f"Notes: {log.notes}", styles["BodySmall"]))

            if not segments:
                story.append(Paragraph("No duty status segments recorded.", styles["BodySmall"]))
                continue

            segment_rows: list[list[Paragraph]] = [
                [
                    Paragraph("Start", styles["MetaLabel"]),
                    Paragraph("End", styles["MetaLabel"]),
                    Paragraph("Status", styles["MetaLabel"]),
                    Paragraph("Location", styles["MetaLabel"]),
                    Paragraph("Activity", styles["MetaLabel"]),
                    Paragraph("Remarks", styles["MetaLabel"]),
                ]
            ]

            for segment in segments:
                start_time = segment.start_time.strftime("%H:%M") if segment.start_time else "—"
                end_time = segment.end_time.strftime("%H:%M") if segment.end_time else "—"
                location_text = _segment_location(segment.location)
                activity = segment.activity or "—"
                remarks = segment.remarks or "—"
                status_label = dict(log.STATUS_CHOICES).get(segment.status, segment.status)

                segment_rows.append(
                    [
                        Paragraph(start_time, styles["BodySmall"]),
                        Paragraph(end_time, styles["BodySmall"]),
                        Paragraph(status_label.title(), styles["BodySmall"]),
                        Paragraph(location_text, styles["BodySmall"]),
                        Paragraph(activity, styles["BodySmall"]),
                        Paragraph(remarks, styles["BodySmall"]),
                    ]
                )

            segment_table = Table(
                segment_rows,
                colWidths=[0.7 * inch, 0.7 * inch, 1.2 * inch, 1.8 * inch, 1.1 * inch, 1.7 * inch],
                hAlign="LEFT",
            )
            segment_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#EEF2FF")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5F5")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(segment_table)

    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Generated report is intended for internal review only.", styles["BodySmall"]))

    footer = _build_footer(generated_at)
    document.build(story, onFirstPage=footer, onLaterPages=footer)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"trip_{trip.id}_route_report.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    response["Content-Length"] = str(len(pdf_bytes))
    return response
