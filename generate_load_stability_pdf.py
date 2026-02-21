#!/usr/bin/env python3
"""
Generate PDF from the Load and Stability Report (LOAD_AND_STABILITY_REPORT.md)
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import re


def parse_md_table(lines):
    """Parse markdown table into list of rows."""
    rows = []
    for line in lines:
        line = line.strip()
        if not line or re.match(r'^\|?[\s\-:]+\|', line):
            continue
        cells = [c.strip().replace('**', '') for c in line.split('|')]
        cells = [c for c in cells if c]
        if cells:
            rows.append(cells)
    return rows


def md_to_reportlab(md_text):
    """Convert markdown to reportlab flowables."""
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        fontSize=20, textColor=colors.HexColor('#2C3E50'),
        spaceAfter=12, spaceBefore=0, alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    h1_style = ParagraphStyle(
        'H1', parent=styles['Heading1'],
        fontSize=14, textColor=colors.HexColor('#34495E'),
        spaceAfter=8, spaceBefore=16, fontName='Helvetica-Bold'
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Heading2'],
        fontSize=12, textColor=colors.HexColor('#34495E'),
        spaceAfter=6, spaceBefore=12, fontName='Helvetica-Bold'
    )
    normal_style = ParagraphStyle(
        'Normal', parent=styles['Normal'],
        fontSize=10, spaceAfter=6, alignment=TA_JUSTIFY
    )
    bullet_style = ParagraphStyle(
        'Bullet', parent=styles['Normal'],
        fontSize=10, spaceAfter=4, leftIndent=20, bulletIndent=10
    )
    
    elements = []
    lines = md_text.split('\n')
    i = 0
    in_table = False
    table_lines = []
    
    while i < len(lines):
        line = lines[i]
        
        # Tables
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
            i += 1
            continue
        else:
            if in_table and table_lines:
                rows = parse_md_table(table_lines)
                if rows:
                    ncols = len(rows[0])
                    col_width = 450 / ncols if ncols else 100
                    t = Table(rows, colWidths=[col_width] * ncols)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#777777')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
                    ]))
                    elements.append(t)
                    elements.append(Spacer(1, 12))
                in_table = False
                table_lines = []
            in_table = False
        
        # Headers
        def fmt(s):
            s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
            s = re.sub(r'\*(.+?)\*', r'<i>\1</i>', s)
            return s
        
        if line.startswith('# '):
            elements.append(Paragraph(fmt(line[2:]), title_style))
        elif line.startswith('## '):
            elements.append(Paragraph(fmt(line[3:]), h1_style))
        elif line.startswith('### '):
            elements.append(Paragraph(fmt(line[4:]), h2_style))
        elif line.strip() == '---':
            elements.append(Spacer(1, 8))
        elif line.strip().startswith('- '):
            elements.append(Paragraph(f"• {fmt(line.strip()[2:])}", bullet_style))
        elif line.strip():
            text = fmt(line.strip())
            elements.append(Paragraph(text, normal_style))
        
        i += 1
    
    return elements


def main():
    with open('LOAD_AND_STABILITY_REPORT.md', 'r') as f:
        md_text = f.read()
    
    # Update report date in content
    report_date = datetime.now().strftime('%d %B %Y')
    md_text = md_text.replace('**Report Date:** February 2025', f'<b>Report Date:</b> {report_date}')
    
    pdf_filename = f"LOAD_AND_STABILITY_REPORT_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=72)
    
    elements = []
    styles = getSampleStyleSheet()
    date_style = ParagraphStyle('Date', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=20)
    
    # Title and date at top
    elements.append(Paragraph("Intrinsic Load and Concept Stability", 
        ParagraphStyle('MainTitle', fontSize=22, textColor=colors.HexColor('#2C3E50'), 
        spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold')))
    elements.append(Paragraph("Methodology and Rationale", 
        ParagraphStyle('Subtitle', fontSize=14, textColor=colors.HexColor('#7F8C8D'), 
        spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica')))
    elements.append(Paragraph(f"Learning Sequence Database (AIDB) — Report Date: {report_date}", date_style))
    elements.append(Spacer(1, 20))
    
    # Parse and add content (skip first few lines which we've handled)
    content_start = md_text.find('## Executive Summary')
    content_md = md_text[content_start:]
    
    flowables = md_to_reportlab(content_md)
    elements.extend(flowables)
    
    doc.build(elements)
    print(f"✅ PDF generated: {pdf_filename}")
    return pdf_filename


if __name__ == '__main__':
    main()
