import os
import cv2
import tempfile
from cvmi_analyzer.config import APP_DATA_DIR, STAGE_DESCRIPTIONS

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

def create_annotated_image(image_path: str, landmarks: dict) -> str:
    """
    Renders anatomical landmarks and contour lines onto a copy of the radiograph using OpenCV.
    Saves and returns the filepath of the annotated temp image.
    """
    img = cv2.imread(image_path)
    if img is None:
        return ""
        
    # Vertebra colors in BGR
    colors_bgr = {
        "C2": (80, 80, 255),    # Light Red
        "C3": (80, 255, 80),    # Green
        "C4": (255, 180, 80)    # Blue
    }
    
    connections = [
        ("SA", "SP"),
        ("SP", "IP"),
        ("IP", "IM"),
        ("IM", "IA"),
        ("IA", "SA")
    ]
    
    # Scale text size based on image height for readability
    img_h = img.shape[0]
    thickness = max(2, int(img_h * 0.002))
    circle_r = max(4, int(img_h * 0.005))
    font_scale = max(0.5, img_h * 0.0006)
    
    for vert, points in landmarks.items():
        color = colors_bgr.get(vert, (0, 0, 255))
        
        # 1. Draw contour lines
        for p1_name, p2_name in connections:
            if p1_name in points and p2_name in points:
                pt1 = tuple(map(int, points[p1_name]))
                pt2 = tuple(map(int, points[p2_name]))
                cv2.line(img, pt1, pt2, color, thickness)
                
        # 2. Draw landmark dots and text labels
        for name, coords in points.items():
            pt = tuple(map(int, coords))
            cv2.circle(img, pt, circle_r, color, -1)
            cv2.circle(img, pt, circle_r + 2, (255, 255, 255), 1)
            cv2.putText(
                img, f"{vert}_{name}", (pt[0] + circle_r + 4, pt[1] - 4), 
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA
            )
            
    # Save to app data temp file
    temp_dir = tempfile.gettempdir()
    annotated_path = os.path.join(temp_dir, f"cvmi_temp_{os.path.basename(image_path)}")
    cv2.imwrite(annotated_path, img)
    return annotated_path


def generate_pdf_report(
    pdf_path: str, 
    patient: dict, 
    radiograph: dict, 
    assessment: dict, 
    examiner_name: str
) -> bool:
    """Generates a professional multi-page PDF assessment report."""
    if not HAS_REPORTLAB:
        print("ReportLab is not installed. PDF report cannot be generated.")
        return False
        
    try:
        # Create doc template
        doc = SimpleDocTemplate(
            pdf_path, 
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f62fe"),
            alignment=1, # Center
            spaceAfter=15
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#333333"),
            spaceBefore=10,
            spaceAfter=6,
            borderColor=colors.HexColor("#0f62fe"),
            borderWidth=1,
            borderPadding=4
        )
        
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#444444")
        )
        
        bold_body_style = ParagraphStyle(
            'BoldBodyText',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        elements = []
        
        # --- Page 1 Header ---
        elements.append(Paragraph("CVMI Analyzer Pro - Clinical Report", title_style))
        elements.append(Paragraph("Generated on: " + assessment["created_at"][:10], body_style))
        elements.append(Spacer(1, 10))
        
        # --- Patient Demographics Table ---
        elements.append(Paragraph("Patient Information", section_style))
        patient_data = [
            [Paragraph("<b>Patient ID:</b>", body_style), Paragraph(patient["patient_id"], body_style),
             Paragraph("<b>Date of Birth:</b>", body_style), Paragraph(patient["dob"], body_style)],
            [Paragraph("<b>First Name:</b>", body_style), Paragraph(patient["first_name"], body_style),
             Paragraph("<b>Last Name:</b>", body_style), Paragraph(patient["last_name"], body_style)],
            [Paragraph("<b>Gender:</b>", body_style), Paragraph(patient["gender"], body_style),
             Paragraph("<b>Phone:</b>", body_style), Paragraph(patient["phone"], body_style)]
        ]
        
        pat_table = Table(patient_data, colWidths=[100, 160, 100, 160])
        pat_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8f9fa")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#e9ecef")),
        ]))
        elements.append(pat_table)
        elements.append(Spacer(1, 15))
        
        # --- CVMI Diagnostic Results ---
        elements.append(Paragraph("CVMI Stage Determination", section_style))
        stage_code = assessment["selected_stage"]
        stage_desc = STAGE_DESCRIPTIONS.get(stage_code, "")
        
        is_ai = "Yes" if assessment["is_ai_assisted"] == 1 else "No"
        ai_pred = assessment["predicted_stage"] or "N/A"
        ai_conf = f"{assessment['predicted_confidence']:.1%}" if assessment['predicted_confidence'] else "N/A"
        
        results_data = [
            [Paragraph("<b>Final CVMI Stage:</b>", body_style), Paragraph(f"<b>{stage_code}</b>", bold_body_style)],
            [Paragraph("<b>Clinical Stage Description:</b>", body_style), Paragraph(stage_desc, body_style)],
            [Paragraph("<b>AI Assisted Assessment:</b>", body_style), Paragraph(is_ai, body_style)],
            [Paragraph("<b>AI Raw Prediction:</b>", body_style), Paragraph(f"{ai_pred} ({ai_conf} confidence)", body_style)]
        ]
        
        res_table = Table(results_data, colWidths=[160, 360])
        res_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f3f5")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
        ]))
        elements.append(res_table)
        elements.append(Spacer(1, 15))
        
        # --- Quantitative Anatomical Measurements Table ---
        elements.append(Paragraph("Vertebral Body Measurements", section_style))
        meas_header = [
            Paragraph("<b>Vertebra</b>", bold_body_style),
            Paragraph("<b>Concavity Depth</b>", bold_body_style),
            Paragraph("<b>Aspect Ratio (W/H)</b>", bold_body_style),
            Paragraph("<b>Wedge Shape (AH/PH)</b>", bold_body_style),
            Paragraph("<b>Avg Height</b>", bold_body_style)
        ]
        
        meas_rows = [meas_header]
        for v in ["C2", "C3", "C4"]:
            v_metrics = assessment["measurements"].get(v, {})
            row = [
                Paragraph(f"<b>{v}</b>", body_style),
                Paragraph(f"{v_metrics.get('CD', 0.0):.2f} mm", body_style),
                Paragraph(f"{v_metrics.get('AR', 0.0):.2f}", body_style),
                Paragraph(f"{v_metrics.get('WS', 0.0):.2f}", body_style),
                Paragraph(f"{v_metrics.get('H_avg', 0.0):.1f} mm", body_style)
            ]
            meas_rows.append(row)
            
        meas_table = Table(meas_rows, colWidths=[100, 110, 110, 110, 90])
        meas_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e9ecef")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#dee2e6")),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(meas_table)
        elements.append(Spacer(1, 15))
        
        # --- Comments & Reviewer Sign-off ---
        elements.append(Paragraph("Clinical Remarks & Reviewer", section_style))
        comments_txt = assessment["comments"] or "No examiner comments recorded."
        
        sign_data = [
            [Paragraph("<b>Examiner Notes:</b>", body_style), Paragraph(comments_txt, body_style)],
            [Paragraph("<b>Clinical Examiner:</b>", body_style), Paragraph(examiner_name, bold_body_style)],
            [Paragraph("<b>Signature:</b>", body_style), Paragraph("___________________________", body_style)]
        ]
        
        sign_table = Table(sign_data, colWidths=[120, 400])
        sign_table.setStyle(TableStyle([
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#e9ecef")),
        ]))
        elements.append(sign_table)
        
        # --- Page Break ---
        elements.append(PageBreak())
        
        # --- Page 2: Radiograph Attachments ---
        elements.append(Paragraph("Radiographic Attachments", title_style))
        elements.append(Spacer(1, 15))
        
        # Draw the landmarks in OpenCV and retrieve temp annotated path
        annotated_img_path = create_annotated_image(radiograph["image_path"], assessment["landmarks"])
        
        # We add the original image and annotated image side by side
        img_table_data = []
        
        # Verify if images exist and scale them
        orig_img_flow = None
        annot_img_flow = None
        
        img_w, img_h = 240, 320 # Constrain image boundaries
        
        if os.path.exists(radiograph["image_path"]):
            orig_img_flow = Image(radiograph["image_path"], width=img_w, height=img_h)
        if os.path.exists(annotated_img_path):
            annot_img_flow = Image(annotated_img_path, width=img_w, height=img_h)
            
        if orig_img_flow and annot_img_flow:
            img_table_data = [
                [Paragraph("<b>Original Cephalogram</b>", bold_body_style), Paragraph("<b>Annotated Vertebrae (C2-C4)</b>", bold_body_style)],
                [orig_img_flow, annot_img_flow]
            ]
        elif orig_img_flow:
            img_table_data = [
                [Paragraph("<b>Original Cephalogram</b>", bold_body_style)],
                [orig_img_flow]
            ]
            
        if img_table_data:
            col_w = [260, 260] if len(img_table_data[0]) == 2 else [520]
            img_table = Table(img_table_data, colWidths=col_w)
            img_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            elements.append(img_table)
            
        # Build Document
        doc.build(elements)
        
        # Clean up temp file
        if annotated_img_path and os.path.exists(annotated_img_path):
            try:
                os.remove(annotated_img_path)
            except Exception:
                pass
                
        return True
    except Exception as e:
        print(f"Error compiling PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
