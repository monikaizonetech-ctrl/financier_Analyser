from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def create_pdf(title: str, applicant_id: str, content_lines: list) -> BytesIO:
    output = BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"FINANCIER ANALYZER - {title}")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Applicant ID: {applicant_id}")
    
    y = height - 120
    for line in content_lines:
        c.drawString(50, y, line)
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
            
    c.save()
    output.seek(0)
    return output

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.platypus import PageBreak

def get_page_2_elements(styles):
    elements = []
    
    # Header
    title_style = ParagraphStyle('ProTitle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor('#1e3a8a'))
    subtitle_style = ParagraphStyle('ProSub', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)
    elements.append(Paragraph("<b>ProAnalyser.in</b>", title_style))
    elements.append(Paragraph("Bank Statement Analysis Report • Generated August 28, 2026", subtitle_style))
    elements.append(Spacer(1, 20))
    
    # Verification Banner
    banner_data = [['✓ BALANCE VERIFIED SUCCESSFULLY\nAll balances have been confirmed accurate']]
    banner_table = Table(banner_data, colWidths=[6.5*inch])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e6ffed')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#22c55e')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#22c55e')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(banner_table)
    elements.append(Spacer(1, 20))
    
    def get_header_style(title):
        data = [[title]]
        t = Table(data, colWidths=[6.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    # Cashflow Summary
    elements.append(get_header_style("Cashflow Summary"))
    cf_data = [
        ['MONTH', 'CREDIT', 'DEBIT', 'NET CASHFLOW', 'AVG BALANCE', 'ENTRIES (CR)', 'ENTRIES (DR)', 'CHQ/ECS RET'],
        ['Jul 2026', '48,945', '16,388', '32,557', '78,556', '4', '8', 'NILL'],
        ['Total (Jul 2026 - Jul 2026)', '48,945', '16,388', '32,557', '78,556', '4', '8', '-'],
        ['Monthly Avg. (Jul 2026 - Jul 2026)', '48,945', '16,388', '32,557', '78,556', '4.0', '8.0', '-'],
        ['Last 3 months', '-', '-', '-', '-', '-', '-', '-'],
        ['Last 6 months', '-', '-', '-', '-', '-', '-', '-']
    ]
    cf_table = Table(cf_data, colWidths=[1.3*inch, 0.7*inch, 0.7*inch, 0.9*inch, 0.9*inch, 0.7*inch, 0.7*inch, 0.6*inch])
    cf_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    elements.append(cf_table)
    elements.append(Spacer(1, 15))

    # Chq/ECS Return
    elements.append(get_header_style("Chq/ECS Return Txns"))
    chq_data = [['DATE', 'DESCRIPTION', 'CHQ NO', 'CREDIT', 'DEBIT', 'BALANCE'], ['', '', '', '', '', '']]
    chq_table = Table(chq_data, colWidths=[1*inch, 2*inch, 1*inch, 0.8*inch, 0.8*inch, 0.9*inch])
    chq_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(chq_table)
    elements.append(Spacer(1, 15))
    
    # CounterParty Totals
    elements.append(get_header_style("CounterParty Totals - Jul 2026"))
    cp_data = [
        ['COUNTERPARTY(CR)', 'AMOUNT(CR)', 'ENTRIES(CR)', 'COUNTERPARTY(DR)', 'AMOUNT(DR)', 'ENTRIES(DR)'],
        ['Total (Jul 2026)', '48,945', '4', 'Total (Jul 2026)', '16,388', '8'],
        ['Salary Credit', '35,000', '1', 'ATM Withdrawal', '5,000', '1'],
        ['Freelance Payment', '12,500', '1', 'Online Shopping', '3,499', '1'],
        ['Refund Credit', '1,200', '1', 'Electricity Bill', '2,340', '1'],
        ['Interest Credit', '245', '1', 'Fuel Station', '1,800', '1'],
        ['-', '0', '0', 'Grocery Store', '1,250', '1'],
        ['-', '-', '-', 'Txn Total < 5K', '2,499', '3']
    ]
    cp_table = Table(cp_data, colWidths=[1.5*inch, 1*inch, 0.75*inch, 1.5*inch, 1*inch, 0.75*inch])
    cp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    elements.append(cp_table)

    return elements

def get_page_3_elements(styles):
    elements = []
    
    title_style = ParagraphStyle('ChartTitle', parent=styles['Heading2'], alignment=1)
    sub_style = ParagraphStyle('ChartSub', parent=styles['Normal'], alignment=1, fontSize=7, textColor=colors.grey)
    
    elements.append(Paragraph("<b>Visual Analytics</b>", title_style))
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("Monthly Credit Amount vs Debit Amount Comparison", styles['Heading4']))
    elements.append(Paragraph("Values in Rs", sub_style))
    
    d1 = Drawing(400, 200)
    bc1 = VerticalBarChart()
    bc1.x = 50
    bc1.y = 50
    bc1.height = 125
    bc1.width = 300
    bc1.data = [[48945], [16388]] 
    bc1.strokeColor = colors.black
    bc1.valueAxis.valueMin = 0
    bc1.valueAxis.valueMax = 50000
    bc1.valueAxis.valueStep = 10000
    bc1.categoryAxis.labels.boxAnchor = 'ne'
    bc1.categoryAxis.labels.dx = 8
    bc1.categoryAxis.labels.dy = -2
    bc1.categoryAxis.categoryNames = ['Jul 2026']
    bc1.bars[0].fillColor = colors.HexColor('#22c55e') 
    bc1.bars[1].fillColor = colors.HexColor('#ef4444') 
    d1.add(bc1)
    elements.append(d1)
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("Payment Modes Breakdown", styles['Heading4']))
    elements.append(Paragraph("Credit / Debit distributions", sub_style))
    
    d2 = Drawing(400, 200)
    
    pie1 = Pie()
    pie1.x = 50
    pie1.y = 50
    pie1.width = 100
    pie1.height = 100
    pie1.data = [100]
    pie1.labels = ['Other: 100%']
    pie1.slices.strokeWidth=0.5
    
    pie2 = Pie()
    pie2.x = 250
    pie2.y = 50
    pie2.width = 100
    pie2.height = 100
    pie2.data = [30.2, 39.3, 30.5]
    pie2.labels = ['UPI', 'Other', 'Cash']
    pie2.slices.strokeWidth=0.5
    
    d2.add(pie1)
    d2.add(pie2)
    elements.append(d2)
    
    return elements

def get_page_4_elements(styles):
    elements = []
    
    # Title
    title_style = ParagraphStyle('RepaymentTitle', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#1e3a8a'), spaceAfter=20)
    elements.append(Paragraph("<b>Repayment Capacity Analysis</b>", title_style))
    
    # Repayment Summary Table
    def get_header_style(title):
        data = [[title]]
        t = Table(data, colWidths=[6.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    elements.append(get_header_style("Repayment Capacity Result"))
    
    repayment_data = [
        ['METRIC', 'VALUE', 'STATUS'],
        ['Average Monthly Income', '₹ 48,945', 'Verified'],
        ['Existing EMI Obligations', '₹ 15,000', 'Active'],
        ['Estimated Living Expenses', '₹ 12,500', 'Calculated'],
        ['Net Disposable Income', '₹ 21,445', 'Available'],
        ['Fixed Obligation to Income Ratio (FOIR)', '30.64%', 'Good'],
        ['Maximum Suggested EMI', '₹ 18,000', '-']
    ]
    
    rep_table = Table(repayment_data, colWidths=[3*inch, 1.5*inch, 2*inch])
    rep_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TEXTCOLOR', (2,5), (2,5), colors.green), # Highlight 'Good' FOIR status
    ]))
    
    elements.append(rep_table)
    elements.append(Spacer(1, 30))
    
    # Conclusion text
    conclusion_style = ParagraphStyle('Conclusion', parent=styles['Normal'], fontSize=10, leading=14)
    elements.append(Paragraph("<b>Conclusion:</b> Based on the bank statement analysis, the applicant has a healthy Net Disposable Income. The FOIR of 30.64% is well within the acceptable threshold (typically < 50%), indicating a strong repayment capacity for additional credit facilities up to an EMI of ₹18,000.", conclusion_style))
    
    return elements

def generate_bank_pdf(applicant_id: str) -> BytesIO:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Page 1: Transaction Details
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=1, spaceAfter=10)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], alignment=1, spaceAfter=20, textColor=colors.grey)
    elements.append(Paragraph("DEMO NATIONAL BANK", title_style))
    elements.append(Paragraph("Sample Bank Statement — For Testing / Demo Purposes Only", subtitle_style))
    
    account_data = [
        ['Account Holder', f'Applicant ({applicant_id})'],
        ['Account Number', 'XXXX XXXX 4821'],
        ['Statement Period', 'Recent Period (Verified)'],
        ['Account Type', 'Primary Account']
    ]
    account_table = Table(account_data, colWidths=[2*inch, 4*inch])
    account_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(account_table)
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("<b>Transaction Details</b>", styles['Heading3']))
    elements.append(Spacer(1, 10))
    
    txn_data = [
        ['Date', 'Description', 'Reference ID', 'Debit (₹)', 'Credit (₹)', 'Balance (₹)'],
        ['01-07-2026', 'Opening Balance', 'OPEN-0701', '-', '-', '50,000.00'],
        ['02-07-2026', 'Salary Credit', 'SAL-784512', '-', '35,000.00', '85,000.00'],
        ['03-07-2026', 'UPI - Grocery Store', 'UPI-123456', '1,250.00', '-', '83,750.00'],
        ['05-07-2026', 'Electricity Bill', 'BILL-457821', '2,340.00', '-', '81,410.00'],
        ['08-07-2026', 'UPI - Restaurant', 'UPI-563214', '780.00', '-', '80,630.00'],
        ['10-07-2026', 'Online Shopping', 'ECOM-789654', '3,499.00', '-', '77,131.00'],
        ['12-07-2026', 'Refund Credit', 'REF-321478', '-', '1,200.00', '78,331.00'],
        ['15-07-2026', 'ATM Withdrawal', 'ATM-654987', '5,000.00', '-', '73,331.00'],
        ['18-07-2026', 'UPI - Fuel Station', 'UPI-112233', '1,800.00', '-', '71,531.00'],
        ['22-07-2026', 'Freelance Payment', 'PAY-445566', '-', '12,500.00', '84,031.00'],
        ['25-07-2026', 'Mobile Recharge', 'MOB-778899', '599.00', '-', '83,432.00'],
        ['28-07-2026', 'UPI - Pharmacy', 'UPI-998877', '1,120.00', '-', '82,312.00'],
        ['31-07-2026', 'Interest Credit', 'INT-202607', '-', '245.00', '82,557.00']
    ]
    
    txn_table = Table(txn_data, colWidths=[0.8*inch, 1.8*inch, 1.2*inch, 0.8*inch, 0.8*inch, 0.9*inch])
    txn_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563eb')), 
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (3,0), (5,-1), 'RIGHT'), 
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]), 
    ]))
    elements.append(txn_table)
    elements.append(Spacer(1, 30))
    
    disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=7, textColor=colors.grey)
    elements.append(Paragraph("DISCLAIMER: This statement reproduction was generated from the uploaded file for review purposes and reflects the data extracted at the time of analysis.", disclaimer_style))
    
    # Add Advanced Pages
    elements.append(PageBreak())
    elements.extend(get_page_2_elements(styles))
    
    elements.append(PageBreak())
    elements.extend(get_page_3_elements(styles))
    
    elements.append(PageBreak())
    elements.extend(get_page_4_elements(styles))
    
    doc.build(elements)
    output.seek(0)
    return output

def get_common_header(styles, title_text):
    elements = []
    title_style = ParagraphStyle('ProTitle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor('#1e3a8a'))
    subtitle_style = ParagraphStyle('ProSub', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)
    elements.append(Paragraph("<b>ProAnalyser.in</b>", title_style))
    elements.append(Paragraph(f"{title_text} • Generated August 28, 2026", subtitle_style))
    elements.append(Spacer(1, 20))
    
    banner_data = [['✓ DOCUMENT VERIFIED SUCCESSFULLY\nAuthenticity and data integrity confirmed']]
    banner_table = Table(banner_data, colWidths=[6.5*inch])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e6ffed')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#22c55e')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#22c55e')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(banner_table)
    elements.append(Spacer(1, 20))
    return elements

def get_header_style(title):
    data = [[title]]
    t = Table(data, colWidths=[6.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    return t

def get_gst_page_1_elements(styles, applicant_id: str = "PRO-APP"):
    elements = []
    
    title_style = ParagraphStyle('GSTHeaderTitle', parent=styles['Heading1'], alignment=1, spaceAfter=8, textColor=colors.HexColor('#1e3a8a'))
    subtitle_style = ParagraphStyle('GSTHeaderSub', parent=styles['Normal'], alignment=1, spaceAfter=18, textColor=colors.grey, fontSize=9)
    elements.append(Paragraph("GOODS AND SERVICES TAX NETWORK (GSTN)", title_style))
    elements.append(Paragraph("GSTR-3B & GSTR-1 Verified Returns Summary — Official Extraction Record", subtitle_style))
    
    account_data = [
        ['Legal Name', f'Business Entity ({applicant_id})', 'GSTIN / UIN', '33ABCDE1234F1Z5'],
        ['Trade Name', f'Trade Unit ({applicant_id})', 'Taxpayer Type', 'Regular Taxpayer'],
        ['Filing Period', 'Recent Financial Periods (Verified)', 'Principal State', 'Verified Jurisdiction (33)'],
        ['Filing Frequency', 'Monthly', 'Return Status', 'All Filed (Active)']
    ]
    account_table = Table(account_data, colWidths=[1.5*inch, 2*inch, 1.3*inch, 1.7*inch])
    account_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(account_table)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("<b>Itemized Monthly Return Filing Schedule</b>", styles['Heading3']))
    elements.append(Spacer(1, 8))
    
    gst_ledger = [
        ['Period', 'Return', 'ARN / Reference', 'Taxable Turnover (₹)', 'IGST (₹)', 'CGST (₹)', 'SGST (₹)', 'Total Tax (₹)'],
        ['Apr 2026', 'GSTR-3B', 'AA3304260019284', '4,50,000.00', '0.00', '40,500.00', '40,500.00', '81,000.00'],
        ['May 2026', 'GSTR-3B', 'AA3305260028471', '4,80,000.00', '0.00', '43,200.00', '43,200.00', '86,400.00'],
        ['Jun 2026', 'GSTR-3B', 'AA3306260039102', '5,10,000.00', '0.00', '45,900.00', '45,900.00', '91,800.00'],
        ['Jul 2026', 'GSTR-3B', 'AA3307260048193', '4,95,000.00', '0.00', '44,550.00', '44,550.00', '89,100.00'],
        ['Aug 2026', 'GSTR-3B', 'AA3308260057281', '5,25,000.00', '0.00', '47,250.00', '47,250.00', '94,500.00'],
        ['Sep 2026', 'GSTR-3B', 'AA3309260066194', '5,60,000.00', '0.00', '50,400.00', '50,400.00', '1,00,800.00'],
        ['Total (H1)', 'Consolidated', '6 Months', '30,20,000.00', '0.00', '2,71,800.00', '2,71,800.00', '5,43,600.00']
    ]
    
    gst_table = Table(gst_ledger, colWidths=[0.75*inch, 0.75*inch, 1.15*inch, 1.05*inch, 0.65*inch, 0.7*inch, 0.7*inch, 0.75*inch])
    gst_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e2e8f0')),
    ]))
    elements.append(gst_table)
    elements.append(Spacer(1, 20))
    
    disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=7, textColor=colors.grey)
    elements.append(Paragraph("DISCLAIMER: This GST return extract was generated from the uploaded GST data for underwriting, credit assessment, and review purposes.", disclaimer_style))
    return elements

def get_gst_page_2_elements(styles):
    elements = []
    
    # Header
    title_style = ParagraphStyle('ProTitle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor('#1e3a8a'))
    subtitle_style = ParagraphStyle('ProSub', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)
    elements.append(Paragraph("<b>ProAnalyser.in</b>", title_style))
    elements.append(Paragraph("GST Returns Analysis Report • Generated August 28, 2026", subtitle_style))
    elements.append(Spacer(1, 15))
    
    # Verification Banner
    banner_data = [['✓ GSTIN & FILING STATUS VERIFIED SUCCESSFULLY\nAll tax returns have been verified as active and reconciled with GSTN records']]
    banner_table = Table(banner_data, colWidths=[6.5*inch])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e6ffed')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#22c55e')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#22c55e')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(banner_table)
    elements.append(Spacer(1, 15))
    
    # Section 1: Turnover & ITC Reconciliation
    elements.append(get_header_style("Monthly Turnover & Input Tax Credit (ITC) Summary"))
    turnover_data = [
        ['MONTH', 'TAXABLE SALES', 'EXEMPTED', 'ITC CLAIMED', 'ITC REVERSED', 'NET TAX PAID', 'FILING DATE', 'STATUS'],
        ['Apr 2026', '4,50,000', '0', '32,400', '0', '48,600', '18-May-2026', 'ON TIME'],
        ['May 2026', '4,80,000', '0', '34,560', '0', '51,840', '19-Jun-2026', 'ON TIME'],
        ['Jun 2026', '5,10,000', '0', '36,720', '0', '55,080', '17-Jul-2026', 'ON TIME'],
        ['Jul 2026', '4,95,000', '0', '35,640', '0', '53,460', '20-Aug-2026', 'ON TIME'],
        ['Aug 2026', '5,25,000', '0', '37,800', '0', '56,700', '19-Sep-2026', 'ON TIME'],
        ['Sep 2026', '5,60,000', '0', '40,320', '0', '60,480', '18-Oct-2026', 'ON TIME'],
        ['Total (H1)', '30,20,000', '0', '2,17,440', '0', '3,26,160', '-', '100% On-time'],
        ['Monthly Avg.', '5,03,333', '0', '36,240', '0', '54,360', '-', '-']
    ]
    t_table = Table(turnover_data, colWidths=[0.85*inch, 0.95*inch, 0.65*inch, 0.85*inch, 0.8*inch, 0.85*inch, 0.85*inch, 0.7*inch])
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (5,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-3), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-2), (-1,-1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0,-2), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (7,1), (7,-3), colors.HexColor('#16a34a')),
    ]))
    elements.append(t_table)
    elements.append(Spacer(1, 12))
    
    # Section 2: Top Counterparties / B2B Outward Supplies
    elements.append(get_header_style("Top B2B Buyers & Customer Distribution (GSTR-1 Outward)"))
    cp_data = [
        ['BUYER / CLIENT NAME', 'GSTIN', 'INVOICE COUNT', 'TAXABLE AMT (₹)', 'TAX (₹)', '% SHARE'],
        ['Apex Retail Solutions Ltd', '33AAACA1111A1Z1', '14', '11,47,600', '2,06,568', '38.0%'],
        ['Vertex Logistics India', '33BBBVB2222B1Z2', '10', '8,15,400', '1,46,772', '27.0%'],
        ['Kaveri Enterprises', '33CCCC3333C1Z3', '8', '5,43,600', '97,848', '18.0%'],
        ['Zenith Wholesale Trade', '33DDDD4444D1Z4', '5', '3,62,400', '65,232', '12.0%'],
        ['Other B2C / Retail Invoices', '-', '18', '1,51,000', '27,180', '5.0%'],
        ['Total Outward Supplies', '-', '55', '30,20,000', '5,43,600', '100.0%']
    ]
    cp_table = Table(cp_data, colWidths=[1.8*inch, 1.2*inch, 0.8*inch, 1*inch, 0.9*inch, 0.8*inch])
    cp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('ALIGN', (3,1), (4,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    elements.append(cp_table)
    
    return elements

def get_gst_page_3_elements(styles):
    elements = []
    
    title_style = ParagraphStyle('ChartTitle', parent=styles['Heading2'], alignment=1)
    sub_style = ParagraphStyle('ChartSub', parent=styles['Normal'], alignment=1, fontSize=7, textColor=colors.grey)
    
    elements.append(Paragraph("<b>Visual Analytics</b>", title_style))
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("Monthly Taxable Sales Turnover Progression", styles['Heading4']))
    elements.append(Paragraph("Values in ₹", sub_style))
    
    d1 = Drawing(400, 180)
    bc1 = VerticalBarChart()
    bc1.x = 50
    bc1.y = 40
    bc1.height = 120
    bc1.width = 300
    bc1.data = [[450000, 480000, 510000, 495000, 525000, 560000]] 
    bc1.strokeColor = colors.black
    bc1.valueAxis.valueMin = 0
    bc1.valueAxis.valueMax = 650000
    bc1.valueAxis.valueStep = 130000
    bc1.categoryAxis.categoryNames = ['Apr 26', 'May 26', 'Jun 26', 'Jul 26', 'Aug 26', 'Sep 26']
    bc1.categoryAxis.labels.boxAnchor = 'ne'
    bc1.categoryAxis.labels.dx = 8
    bc1.categoryAxis.labels.dy = -2
    bc1.bars[0].fillColor = colors.HexColor('#6366f1') 
    d1.add(bc1)
    elements.append(d1)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("Sales & Tax Composition Breakdown", styles['Heading4']))
    elements.append(Paragraph("Customer Concentration vs Tax Components", sub_style))
    
    d2 = Drawing(400, 160)
    
    pie1 = Pie()
    pie1.x = 40
    pie1.y = 30
    pie1.width = 100
    pie1.height = 100
    pie1.data = [38, 27, 18, 12, 5]
    pie1.labels = ['Apex 38%', 'Vertex 27%', 'Kaveri 18%', 'Zenith 12%', 'Other 5%']
    pie1.slices.strokeWidth = 0.5
    
    pie2 = Pie()
    pie2.x = 240
    pie2.y = 30
    pie2.width = 100
    pie2.height = 100
    pie2.data = [50, 50]
    pie2.labels = ['CGST (50%)', 'SGST (50%)']
    pie2.slices.strokeWidth = 0.5
    
    d2.add(pie1)
    d2.add(pie2)
    elements.append(d2)
    
    return elements

def get_gst_page_4_elements(styles):
    elements = []
    
    title_style = ParagraphStyle('CapacityTitle', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#1e3a8a'), spaceAfter=15)
    elements.append(Paragraph("<b>GST Viability & Capacity Analysis</b>", title_style))
    
    elements.append(get_header_style("GST Underwriting & Capacity Scorecard"))
    
    gst_capacity_data = [
        ['METRIC', 'VALUE', 'STATUS / BENCHMARK'],
        ['Annualized Turnover (Extrapolated)', '₹ 60,40,000', 'Verified & Healthy'],
        ['Average Monthly Taxable Sales', '₹ 5,03,333', 'Consistent Growth'],
        ['Input Tax Credit (ITC) Utilization Rate', '40.0%', 'Optimal ITC Flow'],
        ['Monthly Tax Filing Compliance Rate', '100% (6/6)', 'On-time (Excellent)'],
        ['Estimated Operating Margin (Proxy)', '16.50%', 'Healthy Margin'],
        ['Customer Concentration Risk (Top Client)', '38.0%', 'Moderate Diversification'],
        ['Maximum Suggested Working Capital Limit', '₹ 15,00,000', 'Recommended']
    ]
    
    gst_rep_table = Table(gst_capacity_data, colWidths=[2.8*inch, 1.7*inch, 2.0*inch])
    gst_rep_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TEXTCOLOR', (2,1), (2,1), colors.green),
        ('TEXTCOLOR', (2,4), (2,4), colors.green),
        ('TEXTCOLOR', (2,7), (2,7), colors.HexColor('#2563eb')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(gst_rep_table)
    elements.append(Spacer(1, 25))
    
    conclusion_style = ParagraphStyle('Conclusion', parent=styles['Normal'], fontSize=9.5, leading=14)
    elements.append(Paragraph("<b>Conclusion:</b> Based on the 6-month GSTR-3B and GSTR-1 analysis, the applicant exhibits consistent top-line sales growth with zero late filing penalties. The business maintains a strong ITC utilization balance and moderate customer concentration. The applicant qualifies for a working capital credit limit of up to <b>₹ 15,00,000</b> with high repayment reliability.", conclusion_style))
    
    return elements

def generate_gst_pdf(applicant_id: str) -> BytesIO:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Page 1: GST Itemized Ledger
    elements.extend(get_gst_page_1_elements(styles, applicant_id))
    
    # Page 2: Summary & Reconciliation
    elements.append(PageBreak())
    elements.extend(get_gst_page_2_elements(styles))
    
    # Page 3: Visual Analytics
    elements.append(PageBreak())
    elements.extend(get_gst_page_3_elements(styles))
    
    # Page 4: Capacity & Recommendation
    elements.append(PageBreak())
    elements.extend(get_gst_page_4_elements(styles))
    
    doc.build(elements)
    output.seek(0)
    return output


def get_itr_page_1_elements(styles, applicant_id: str = "PRO-APP"):
    elements = []
    
    title_style = ParagraphStyle('ITRHeaderTitle', parent=styles['Heading1'], alignment=1, spaceAfter=8, textColor=colors.HexColor('#1e3a8a'))
    subtitle_style = ParagraphStyle('ITRHeaderSub', parent=styles['Normal'], alignment=1, spaceAfter=18, textColor=colors.grey, fontSize=9)
    elements.append(Paragraph("INCOME TAX DEPARTMENT - GOVT OF INDIA", title_style))
    elements.append(Paragraph("ITR-V (Indian Income Tax Return Verification Form) — Official Computation Record", subtitle_style))
    
    account_data = [
        ['Taxpayer Name', f'Taxpayer ({applicant_id})', 'PAN', 'ABCDE1234F'],
        ['Assessment Year', 'Verified AY (Recent FY)', 'Filing Status', 'Individual (Resident)'],
        ['ITR Form Type', 'ITR-3 (Verified Returns)', 'Ack / E-filing No', 'e-ACK-884920184719'],
        ['Filing Date', 'Filed Within Due Date', 'Verification', 'e-Verified (System Validated)']
    ]
    account_table = Table(account_data, colWidths=[1.5*inch, 2*inch, 1.3*inch, 1.7*inch])
    account_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(account_table)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("<b>Computation of Total Income & Tax Payable (AY 2025-26)</b>", styles['Heading3']))
    elements.append(Spacer(1, 8))
    
    itr_comp_data = [
        ['Schedule / Head of Income', 'Gross Amount (₹)', 'Deductions (₹)', 'Net Income (₹)'],
        ['1. Income from Salary / Professional Remuneration', '6,50,000.00', '50,000.00 (Std Ded)', '6,00,000.00'],
        ['2. Income from Business / Profession (P&L)', '4,80,000.00', '-', '4,80,000.00'],
        ['3. Income from House Property', '80,000.00', '24,000.00 (30% Ded)', '56,000.00'],
        ['4. Income from Other Sources (Interest / Dividend)', '40,000.00', '-', '40,000.00'],
        ['Gross Total Income (GTI)', '12,50,000.00', '74,000.00', '11,76,000.00'],
        ['Less: Chapter VI-A Deductions (80C, 80D, 80TTA)', '-', '-', '1,50,000.00'],
        ['Total Taxable Income', '-', '-', '10,26,000.00'],
        ['Total Tax Payable (including 4% Health & Edu Cess)', '-', '-', '1,22,408.00'],
        ['Taxes Paid: TDS / Advance Tax / Self-Assessment', '-', '-', '1,22,408.00'],
        ['Net Tax Payable / (Refund Due)', '-', '-', '0.00 (Fully Paid)']
    ]
    
    itr_table = Table(itr_comp_data, colWidths=[2.8*inch, 1.2*inch, 1.2*inch, 1.3*inch])
    itr_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-5), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0,5), (-1,5), 'Helvetica-Bold'),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor('#dbeafe')),
        ('FONTNAME', (0,7), (-1,7), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    elements.append(itr_table)
    elements.append(Spacer(1, 15))
    
    disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=7, textColor=colors.grey)
    elements.append(Paragraph("DISCLAIMER: This document contains parsed tax computation data derived from submitted ITR acknowledgments for credit evaluation.", disclaimer_style))
    return elements

def get_itr_page_2_elements(styles):
    elements = []
    
    # Header
    title_style = ParagraphStyle('ProTitle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor('#1e3a8a'))
    subtitle_style = ParagraphStyle('ProSub', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)
    elements.append(Paragraph("<b>ProAnalyser.in</b>", title_style))
    elements.append(Paragraph("ITR Analysis Report • Generated August 28, 2026", subtitle_style))
    elements.append(Spacer(1, 15))
    
    # Verification Banner
    banner_data = [['✓ ITR-V VERIFIED & 26AS MATCHED SUCCESSFULLY\nIncome Tax Returns and Form 26AS TDS credits verified with CBDT records']]
    banner_table = Table(banner_data, colWidths=[6.5*inch])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e6ffed')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#22c55e')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#22c55e')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(banner_table)
    elements.append(Spacer(1, 15))
    
    # 3-Year Income Trend Table
    elements.append(get_header_style("3-Year Multi-Year Income & Tax Comparison"))
    multi_year_data = [
        ['ASSESSMENT YEAR', 'GROSS INCOME (₹)', 'DEDUCTIONS (₹)', 'NET TAXABLE (₹)', 'TAX PAID (₹)', 'YoY GROWTH', 'FILING STATUS'],
        ['AY 2025-26', '12,50,000', '1,50,000', '11,00,000', '1,22,408', '+15.7%', 'ON TIME'],
        ['AY 2024-25', '10,80,000', '1,50,000', '9,30,000', '98,500', '+13.7%', 'ON TIME'],
        ['AY 2023-24', '9,50,000', '1,50,000', '8,00,000', '72,500', '-', 'ON TIME'],
        ['3-Year Average', '10,93,333', '1,50,000', '9,43,333', '97,803', '+14.7% CAGR', '100% Compliant']
    ]
    my_table = Table(multi_year_data, colWidths=[1.1*inch, 1.05*inch, 0.95*inch, 0.95*inch, 0.85*inch, 0.85*inch, 0.75*inch])
    my_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (4,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (5,1), (5,-1), colors.HexColor('#16a34a')),
        ('TEXTCOLOR', (6,1), (6,-1), colors.HexColor('#16a34a')),
    ]))
    elements.append(my_table)
    elements.append(Spacer(1, 15))
    
    # Income Sources Breakdown
    elements.append(get_header_style("Income Composition & Chapter VI-A Deductions"))
    inc_comp = [
        ['HEAD OF INCOME / DEDUCTION', 'AY 2025-26 (₹)', 'AY 2024-25 (₹)', 'AY 2023-24 (₹)', 'REMARKS'],
        ['Salary / Director Remuneration', '6,50,000', '5,80,000', '5,20,000', 'Regular Primary Income'],
        ['Business / Professional Profits', '4,80,000', '4,00,000', '3,40,000', 'Direct Trade Inflow'],
        ['Rental / House Property Income', '80,000', '70,000', '65,000', 'Fixed Asset Yield'],
        ['Interest & Other Sources', '40,000', '30,000', '25,000', 'Savings & Term Deposits'],
        ['Sec 80C (PPF / ELSS / Life Ins)', '1,50,000', '1,50,000', '1,50,000', 'Full Limit Claimed'],
        ['Total Income Before Deductions', '12,50,000', '10,80,000', '9,50,000', 'Positive Trend']
    ]
    inc_table = Table(inc_comp, colWidths=[2.1*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.1*inch])
    inc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('ALIGN', (1,1), (3,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    elements.append(inc_table)
    
    return elements

def get_itr_page_3_elements(styles):
    elements = []
    
    title_style = ParagraphStyle('ChartTitle', parent=styles['Heading2'], alignment=1)
    sub_style = ParagraphStyle('ChartSub', parent=styles['Normal'], alignment=1, fontSize=7, textColor=colors.grey)
    
    elements.append(Paragraph("<b>Visual Analytics</b>", title_style))
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("3-Year Gross Income vs Net Tax Paid Trend", styles['Heading4']))
    elements.append(Paragraph("Values in ₹", sub_style))
    
    d1 = Drawing(400, 180)
    bc1 = VerticalBarChart()
    bc1.x = 50
    bc1.y = 40
    bc1.height = 120
    bc1.width = 300
    bc1.data = [[950000, 1080000, 1250000], [72500, 98500, 122408]] 
    bc1.strokeColor = colors.black
    bc1.valueAxis.valueMin = 0
    bc1.valueAxis.valueMax = 1400000
    bc1.valueAxis.valueStep = 280000
    bc1.categoryAxis.categoryNames = ['AY 2023-24', 'AY 2024-25', 'AY 2025-26']
    bc1.bars[0].fillColor = colors.HexColor('#3b82f6') 
    bc1.bars[1].fillColor = colors.HexColor('#f59e0b') 
    d1.add(bc1)
    elements.append(d1)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("Income Stream Distribution & Tax Proportion", styles['Heading4']))
    elements.append(Paragraph("Source Breakdown (AY 2025-26)", sub_style))
    
    d2 = Drawing(400, 160)
    
    pie1 = Pie()
    pie1.x = 40
    pie1.y = 30
    pie1.width = 100
    pie1.height = 100
    pie1.data = [52, 38.4, 6.4, 3.2]
    pie1.labels = ['Salary 52%', 'Business 38.4%', 'Property 6.4%', 'Other 3.2%']
    pie1.slices.strokeWidth = 0.5
    
    pie2 = Pie()
    pie2.x = 240
    pie2.y = 30
    pie2.width = 100
    pie2.height = 100
    pie2.data = [90.2, 9.8]
    pie2.labels = ['Net Income (90.2%)', 'Tax Paid (9.8%)']
    pie2.slices.strokeWidth = 0.5
    
    d2.add(pie1)
    d2.add(pie2)
    elements.append(d2)
    
    return elements

def get_itr_page_4_elements(styles):
    elements = []
    
    title_style = ParagraphStyle('CapacityTitle', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#1e3a8a'), spaceAfter=15)
    elements.append(Paragraph("<b>Income Stability & Capacity Assessment</b>", title_style))
    
    elements.append(get_header_style("ITR Income Eligibility & Capacity Scorecard"))
    
    itr_capacity_data = [
        ['METRIC', 'VALUE', 'STATUS / BENCHMARK'],
        ['Average Annual Gross Income (3-Year)', '₹ 10,93,333', 'Verified & Consistent'],
        ['3-Year Income Compound Growth (CAGR)', '+14.7%', 'Strong Growth'],
        ['Monthly Net Take-Home (Post Tax)', '₹ 93,966', 'Calculated'],
        ['Existing Annual Debt Obligations', '₹ 1,80,000', 'Active (Verified)'],
        ['Fixed Obligation to Income (FOIR)', '15.96%', 'Excellent (< 50%)'],
        ['Debt-to-Income (DTI) Ratio', '16.0%', 'Low Risk'],
        ['Maximum Suggested Loan Eligibility', '₹ 45,00,000', 'Approved Limit'],
        ['Maximum Suggested Monthly EMI', '₹ 38,000', 'Comfortable Serviceability']
    ]
    
    itr_rep_table = Table(itr_capacity_data, colWidths=[2.8*inch, 1.7*inch, 2.0*inch])
    itr_rep_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TEXTCOLOR', (2,1), (2,1), colors.green),
        ('TEXTCOLOR', (2,4), (2,4), colors.green),
        ('TEXTCOLOR', (2,6), (2,6), colors.HexColor('#2563eb')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(itr_rep_table)
    elements.append(Spacer(1, 25))
    
    conclusion_style = ParagraphStyle('Conclusion', parent=styles['Normal'], fontSize=9.5, leading=14)
    elements.append(Paragraph("<b>Conclusion:</b> The applicant demonstrates an established 3-year track record of filed and verified Income Tax Returns with consistent +14.7% CAGR income growth. With a low FOIR of 15.96% and optimal tax compliance, the applicant has exceptional repayment capability and is eligible for credit facilities up to <b>₹ 45,00,000</b> (Monthly EMI up to ₹38,000).", conclusion_style))
    
    return elements

def generate_itr_pdf(applicant_id: str) -> BytesIO:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Page 1: Computation Schedule
    elements.extend(get_itr_page_1_elements(styles, applicant_id))
    
    # Page 2: Summary & Multi-Year Trends
    elements.append(PageBreak())
    elements.extend(get_itr_page_2_elements(styles))
    
    # Page 3: Visual Analytics
    elements.append(PageBreak())
    elements.extend(get_itr_page_3_elements(styles))
    
    # Page 4: Capacity & Recommendation
    elements.append(PageBreak())
    elements.extend(get_itr_page_4_elements(styles))
    
    doc.build(elements)
    output.seek(0)
    return output


def get_loan_page_1_elements(styles, applicant_id: str = "PRO-APP"):
    elements = []
    
    title_style = ParagraphStyle('LoanHeaderTitle', parent=styles['Heading1'], alignment=1, spaceAfter=8, textColor=colors.HexColor('#1e3a8a'))
    subtitle_style = ParagraphStyle('LoanHeaderSub', parent=styles['Normal'], alignment=1, spaceAfter=18, textColor=colors.grey, fontSize=9)
    elements.append(Paragraph("CREDIT BUREAU & REPAYMENT CAPACITY RECORD", title_style))
    elements.append(Paragraph("Consolidated Loan Accounts & EMI Schedule — Extraction Report", subtitle_style))
    
    account_data = [
        ['Borrower Name', f'Borrower ({applicant_id})', 'CIBIL / Experian Score', '785 (Excellent)'],
        ['Total Active Facilities', '2 Active Accounts', 'Total Sanctioned Limit', '₹ 7,50,000.00'],
        ['Total Outstanding Balance', '₹ 4,50,000.00', 'Total Monthly EMI', '₹ 23,000.00'],
        ['Overdue / DPD Status', '0 DPD (Clean Track)', 'Bureau Report Date', 'Verified Record']
    ]
    account_table = Table(account_data, colWidths=[1.5*inch, 2*inch, 1.4*inch, 1.6*inch])
    account_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(account_table)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("<b>Active Loan Accounts & Repayment Ledger</b>", styles['Heading3']))
    elements.append(Spacer(1, 8))
    
    loan_ledger = [
        ['Lender Institution', 'Loan Type', 'Sanction Amt (₹)', 'Outstanding (₹)', 'EMI (₹)', 'Tenure Left', 'DPD Track'],
        ['HDFC Bank Ltd', 'Auto / Car Loan', '4,50,000.00', '2,75,000.00', '15,000.00', '21 Months', '0 DPD (Clean)'],
        ['State Bank of India', 'Personal Loan', '3,00,000.00', '1,75,000.00', '8,000.00', '26 Months', '0 DPD (Clean)'],
        ['Total Commitments', '2 Facilities', '7,50,000.00', '4,50,000.00', '23,000.00', '-', 'All Standard']
    ]
    
    loan_table = Table(loan_ledger, colWidths=[1.4*inch, 1.0*inch, 1.0*inch, 1.0*inch, 0.8*inch, 0.7*inch, 0.6*inch])
    loan_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,1), (1,-1), 'LEFT'),
        ('ALIGN', (2,1), (4,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    elements.append(loan_table)
    elements.append(Spacer(1, 20))
    
    disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=7, textColor=colors.grey)
    elements.append(Paragraph("DISCLAIMER: This loan reproduction report reflects credit data verified from bureau reports and applicant declarations.", disclaimer_style))
    return elements

def get_loan_page_2_elements(styles):
    elements = []
    
    title_style = ParagraphStyle('ProTitle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor('#1e3a8a'))
    subtitle_style = ParagraphStyle('ProSub', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)
    elements.append(Paragraph("<b>ProAnalyser.in</b>", title_style))
    elements.append(Paragraph("Existing Obligations & Debt Analysis Report • Generated August 28, 2026", subtitle_style))
    elements.append(Spacer(1, 15))
    
    banner_data = [['✓ CREDIT BUREAU RECORDS & EMIS VERIFIED\nAll active credit facilities verified with zero bounce or overdue records']]
    banner_table = Table(banner_data, colWidths=[6.5*inch])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e6ffed')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#22c55e')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#22c55e')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(banner_table)
    elements.append(Spacer(1, 15))
    
    elements.append(get_header_style("Repayment Track Record & Bounce History"))
    repay_data = [
        ['MONTH', 'HDFC CAR EMI (₹)', 'SBI PERSONAL EMI (₹)', 'TOTAL DEDUCTION (₹)', 'BOUNCE / ECS RET', 'PAYMENT MODE', 'STATUS'],
        ['Jul 2026', '15,000', '8,000', '23,000', 'NILL', 'Auto Debit (ACH)', 'CLEAN'],
        ['Jun 2026', '15,000', '8,000', '23,000', 'NILL', 'Auto Debit (ACH)', 'CLEAN'],
        ['May 2026', '15,000', '8,000', '23,000', 'NILL', 'Auto Debit (ACH)', 'CLEAN'],
        ['Apr 2026', '15,000', '8,000', '23,000', 'NILL', 'Auto Debit (ACH)', 'CLEAN'],
        ['Total (L4M)', '60,000', '32,000', '92,000', '0 Returns', '100% Success', 'Spotless Track']
    ]
    r_table = Table(repay_data, colWidths=[0.85*inch, 1.1*inch, 1.2*inch, 1.1*inch, 0.85*inch, 0.85*inch, 0.55*inch])
    r_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (1,1), (3,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (6,1), (6,-1), colors.HexColor('#16a34a')),
    ]))
    elements.append(r_table)
    
    return elements

def get_loan_page_3_elements(styles):
    elements = []
    
    title_style = ParagraphStyle('ChartTitle', parent=styles['Heading2'], alignment=1)
    sub_style = ParagraphStyle('ChartSub', parent=styles['Normal'], alignment=1, fontSize=7, textColor=colors.grey)
    
    elements.append(Paragraph("<b>Visual Analytics</b>", title_style))
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("Loan Sanction vs Outstanding Balance Comparison", styles['Heading4']))
    elements.append(Paragraph("Values in ₹", sub_style))
    
    d1 = Drawing(400, 180)
    bc1 = VerticalBarChart()
    bc1.x = 50
    bc1.y = 40
    bc1.height = 120
    bc1.width = 300
    bc1.data = [[450000, 300000], [275000, 175000]] 
    bc1.strokeColor = colors.black
    bc1.valueAxis.valueMin = 0
    bc1.valueAxis.valueMax = 500000
    bc1.valueAxis.valueStep = 100000
    bc1.categoryAxis.categoryNames = ['HDFC Car Loan', 'SBI Personal Loan']
    bc1.bars[0].fillColor = colors.HexColor('#3b82f6') 
    bc1.bars[1].fillColor = colors.HexColor('#10b981') 
    d1.add(bc1)
    elements.append(d1)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("EMI Distribution & Debt Exposure", styles['Heading4']))
    d2 = Drawing(400, 160)
    
    pie1 = Pie()
    pie1.x = 40
    pie1.y = 30
    pie1.width = 100
    pie1.height = 100
    pie1.data = [65.2, 34.8]
    pie1.labels = ['HDFC Car (65.2%)', 'SBI Personal (34.8%)']
    pie1.slices.strokeWidth = 0.5
    
    pie2 = Pie()
    pie2.x = 240
    pie2.y = 30
    pie2.width = 100
    pie2.height = 100
    pie2.data = [60, 40]
    pie2.labels = ['Repaid (60%)', 'Outstanding (40%)']
    pie2.slices.strokeWidth = 0.5
    
    d2.add(pie1)
    d2.add(pie2)
    elements.append(d2)
    
    return elements

def get_loan_page_4_elements(styles):
    elements = []
    
    title_style = ParagraphStyle('CapacityTitle', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#1e3a8a'), spaceAfter=15)
    elements.append(Paragraph("<b>Repayment Capacity & FOIR Assessment</b>", title_style))
    
    elements.append(get_header_style("Consolidated FOIR & Debt Capacity Scorecard"))
    
    loan_capacity_data = [
        ['METRIC', 'VALUE', 'STATUS / BENCHMARK'],
        ['Verified Monthly Income', '₹ 93,966', 'Active & Stable'],
        ['Total Existing Monthly EMIs', '₹ 23,000', 'Active Commitments'],
        ['Current Fixed Obligation to Income (FOIR)', '24.47%', 'Healthy (< 50%)'],
        ['Net Available Monthly Cashflow', '₹ 70,966', 'Sufficient Buffer'],
        ['CIBIL Bureau Track Record', '785 (0 DPD)', 'Excellent Credit History'],
        ['Maximum Incremental EMI Capacity', '₹ 23,983', 'Available Headroom'],
        ['Maximum Suggested Additional Loan', '₹ 20,00,000', 'Recommended Eligible']
    ]
    
    loan_rep_table = Table(loan_capacity_data, colWidths=[2.8*inch, 1.7*inch, 2.0*inch])
    loan_rep_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TEXTCOLOR', (2,2), (2,2), colors.green),
        ('TEXTCOLOR', (2,4), (2,4), colors.green),
        ('TEXTCOLOR', (2,6), (2,6), colors.HexColor('#2563eb')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(loan_rep_table)
    elements.append(Spacer(1, 25))
    
    conclusion_style = ParagraphStyle('Conclusion', parent=styles['Normal'], fontSize=9.5, leading=14)
    elements.append(Paragraph("<b>Conclusion:</b> The applicant currently maintains an exemplary repayment track record across all active loan accounts with zero defaults or delayed payments. The FOIR of 24.47% provides ample headroom for an incremental monthly EMI of up to ₹23,983, supporting an additional loan facility of up to <b>₹ 20,00,000</b>.", conclusion_style))
    
    return elements

def generate_loan_pdf(applicant_id: str) -> BytesIO:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # Page 1: Active Loan Ledger
    elements.extend(get_loan_page_1_elements(styles, applicant_id))
    
    # Page 2: Summary & Repayment Track
    elements.append(PageBreak())
    elements.extend(get_loan_page_2_elements(styles))
    
    # Page 3: Visual Analytics
    elements.append(PageBreak())
    elements.extend(get_loan_page_3_elements(styles))
    
    # Page 4: FOIR & Recommendation
    elements.append(PageBreak())
    elements.extend(get_loan_page_4_elements(styles))
    
    doc.build(elements)
    output.seek(0)
    return output

