#!/usr/bin/env python3
"""
Generate a comprehensive PDF inventory of all clusters, elements, and resources
"""

import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime

DATABASE = "learning_sequence_v2.db"

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def get_all_data():
    """Get all clusters, elements, and resources"""
    db = get_db()
    
    # Get all clusters
    clusters = db.execute('''
        SELECT c.id, c.cluster_number, c.title, yl.name as year_level, s.name as strand
        FROM clusters c
        LEFT JOIN year_levels yl ON c.year_level_id = yl.id
        LEFT JOIN strands s ON c.strand_id = s.id
        ORDER BY c.cluster_number
    ''').fetchall()
    
    data = []
    
    for cluster in clusters:
        cluster_data = {
            'cluster': dict(cluster),
            'elements': []
        }
        
        # Get elements for this cluster
        elements = db.execute('''
            SELECT e.id, e.element_number, e.title, ce.sequence_order
            FROM cluster_elements ce
            JOIN elements e ON ce.element_id = e.id
            WHERE ce.cluster_id = ?
            ORDER BY ce.sequence_order
        ''', [cluster['id']]).fetchall()
        
        for element in elements:
            element_data = {
                'element': dict(element),
                'resources': []
            }
            
            # Get resources for this element
            resources = db.execute('''
                SELECT r.title, r.file_name, rc.name as category, rc.code as category_code
                FROM resources r
                JOIN resource_categories rc ON r.resource_category_id = rc.id
                WHERE r.element_id = ?
                ORDER BY rc.display_order, r.title
            ''', [element['id']]).fetchall()
            
            element_data['resources'] = [dict(res) for res in resources]
            cluster_data['elements'].append(element_data)
        
        data.append(cluster_data)
    
    db.close()
    return data

def create_inventory_pdf():
    """Create PDF inventory"""
    print("Gathering data from database...")
    data = get_all_data()
    
    print(f"Found {len(data)} clusters")
    
    # Create PDF
    pdf_filename = "RESOURCE_INVENTORY.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter,
                           rightMargin=36, leftMargin=36,
                           topMargin=36, bottomMargin=36)
    
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    cluster_style = ParagraphStyle(
        'Cluster',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=colors.HexColor('#2980B9'),
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        leftIndent=0
    )
    
    element_style = ParagraphStyle(
        'Element',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#27AE60'),
        spaceAfter=4,
        spaceBefore=8,
        fontName='Helvetica-Bold',
        leftIndent=20
    )
    
    resource_style = ParagraphStyle(
        'Resource',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=2,
        leftIndent=40,
        fontName='Helvetica'
    )
    
    category_header_style = ParagraphStyle(
        'CategoryHeader',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#7F8C8D'),
        spaceAfter=3,
        spaceBefore=6,
        leftIndent=35,
        fontName='Helvetica-Bold'
    )
    
    # Title page
    elements.append(Paragraph("Learning Sequence Resource Inventory", title_style))
    elements.append(Spacer(1, 12))
    
    date_style = ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    elements.append(Paragraph(f"<i>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</i>", date_style))
    elements.append(Spacer(1, 20))
    
    # Summary statistics
    total_elements = sum(len(cluster['elements']) for cluster in data)
    total_resources = sum(
        len(element['resources']) 
        for cluster in data 
        for element in cluster['elements']
    )
    
    summary_data = [
        ['Total Clusters', str(len(data))],
        ['Total Elements', str(total_elements)],
        ['Total Resources', str(total_resources)],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ECF0F1')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Category legend
    elements.append(Paragraph("<b>Resource Categories:</b>", styles['Normal']))
    elements.append(Spacer(1, 6))
    
    legend_data = [
        ['SANDBOX', 'Sandbox activities'],
        ['INSTRUCTIONAL', 'Instructional materials'],
        ['GUIDED', 'Guided practice'],
        ['INDEPENDENT', 'Independent practice'],
        ['ACTIVITY', 'General activities'],
        ['EXTENSION', 'Extension activities'],
        ['RETRIEVAL', 'Retrieval practice'],
        ['TEACHING_RESOURCE', 'Teaching resources'],
    ]
    legend_table = Table(legend_data, colWidths=[1.5*inch, 3.5*inch])
    legend_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(legend_table)
    
    elements.append(PageBreak())
    
    # Main content
    print("Generating PDF content...")
    
    for cluster_idx, cluster_data in enumerate(data, 1):
        cluster = cluster_data['cluster']
        
        # Cluster header
        cluster_text = (
            f"<b>Cluster {cluster['cluster_number']}: {cluster['title']}</b><br/>"
            f"<font size=8>{cluster['year_level']} • {cluster['strand']}</font>"
        )
        elements.append(Paragraph(cluster_text, cluster_style))
        
        # Elements and resources
        for element_idx, element_data in enumerate(cluster_data['elements'], 1):
            element = element_data['element']
            resources = element_data['resources']
            
            # Element header with resource count
            element_text = (
                f"{element_idx}. {element['title']} "
                f"<font size=7 color='#7F8C8D'>(Element #{element['element_number']} • {len(resources)} resources)</font>"
            )
            elements.append(Paragraph(element_text, element_style))
            
            if resources:
                # Group resources by category
                resources_by_category = {}
                for resource in resources:
                    category = resource['category']
                    if category not in resources_by_category:
                        resources_by_category[category] = []
                    resources_by_category[category].append(resource)
                
                # Display resources by category
                for category, category_resources in resources_by_category.items():
                    # Category header
                    category_text = f"<b>{category}</b> ({len(category_resources)})"
                    elements.append(Paragraph(category_text, category_header_style))
                    
                    # Resources
                    for resource in category_resources:
                        resource_text = f"• {resource['title']}"
                        if resource['file_name']:
                            resource_text += f" <font size=7 color='#95A5A6'>[{resource['file_name']}]</font>"
                        elements.append(Paragraph(resource_text, resource_style))
            else:
                elements.append(Paragraph("<i>No resources</i>", resource_style))
        
        elements.append(Spacer(1, 10))
        
        # Add page break after every 2 clusters to avoid overcrowding
        if cluster_idx % 2 == 0 and cluster_idx < len(data):
            elements.append(PageBreak())
        
        if cluster_idx % 10 == 0:
            print(f"  Processed {cluster_idx}/{len(data)} clusters...")
    
    # Build PDF
    print("Building PDF...")
    doc.build(elements)
    print(f"\n✅ PDF generated successfully: {pdf_filename}")
    print(f"   Total pages: ~{len(data) // 2 + 1}")
    return pdf_filename

if __name__ == '__main__':
    create_inventory_pdf()
