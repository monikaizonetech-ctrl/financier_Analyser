import os

fp = 'backend/app/services/file_analysis_service.py'
with open(fp, 'r', encoding='utf8') as f:
    text = f.read()

# Add NumberedCanvas
canvas_class = '''
from reportlab.pdfgen import canvas
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont(FONT_REGULAR, 7.5)
        self.setFillColor(colors.grey)
        self.drawRightString(self._pagesize[0] - 15*mm, 10*mm, f"Page {self._pageNumber} of {page_count}")

'''

if 'class NumberedCanvas' not in text:
    text = text.replace('class izoneReportTemplate', canvas_class + 'class izoneReportTemplate')

# Modify on_page to NOT draw the page number
text = text.replace('canvas.drawRightString(self.pagesize[0] - 15*mm, 10*mm, f"Page {doc.page}")', '')

# Modify build_pdf_report to use NumberedCanvas
text = text.replace('doc.multiBuild(elements)', 'doc.multiBuild(elements, canvasmaker=NumberedCanvas)')


# Add Cashflow Summary logic
start_cf = text.find('    # SECTION 1: Cashflow Summary')
end_cf = text.find('    # SECTION 2: Chq/ECS Return Txns')

cf_logic = '''    # SECTION 1: Cashflow Summary
    cf_col_widths = [66, 55, 55, 65, 60, 55, 50, 50, 54]
    hdr1 = _section_header_table("Cashflow Summary", cf_col_widths)
    
    cf_rows = []
    tot_cr, tot_dr, tot_net, tot_avg, tot_all_tx, tot_cr_tx, tot_dr_tx, tot_chq = 0, 0, 0, 0, 0, 0, 0, 0
    for m in months:
        md = a.get("monthly", {}).get(m, {})
        net = round(md.get("credit", 0) - md.get("debit", 0), 2)
        cr = md.get("credit", 0)
        dr = md.get("debit", 0)
        avg = md.get("avg_balance", 0)
        cr_c = md.get("credit_count", 0)
        dr_c = md.get("debit_count", 0)
        all_tx = cr_c + dr_c
        chq = md.get("chq_retn", 0) or 0
        
        tot_cr += cr
        tot_dr += dr
        tot_net += net
        tot_avg += avg
        tot_cr_tx += cr_c
        tot_dr_tx += dr_c
        tot_all_tx += all_tx
        tot_chq += chq
        
        cf_rows.append([
            m,
            f"{cr:,.0f}", f"{dr:,.0f}", f"{net:,.0f}", f"{avg:,.0f}",
            str(all_tx), str(cr_c), str(dr_c), str(chq) if chq else "0"
        ])
        
    if months:
        tot_avg = tot_avg / len(months)
    cf_rows.append([
        Paragraph("<b>Total</b>", ParagraphStyle("CTot", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL)),
        Paragraph(f"<b>{tot_cr:,.0f}</b>", ParagraphStyle("CTotA", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL, alignment=TA_RIGHT)),
        Paragraph(f"<b>{tot_dr:,.0f}</b>", ParagraphStyle("CTotA", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL, alignment=TA_RIGHT)),
        Paragraph(f"<b>{tot_net:,.0f}</b>", ParagraphStyle("CTotA", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL, alignment=TA_RIGHT)),
        Paragraph(f"<b>{tot_avg:,.0f}</b>", ParagraphStyle("CTotA", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL, alignment=TA_RIGHT)),
        Paragraph(f"<b>{tot_all_tx}</b>", ParagraphStyle("CTotC", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL, alignment=TA_CENTER)),
        Paragraph(f"<b>{tot_cr_tx}</b>", ParagraphStyle("CTotC", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL, alignment=TA_CENTER)),
        Paragraph(f"<b>{tot_dr_tx}</b>", ParagraphStyle("CTotC", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL, alignment=TA_CENTER)),
        Paragraph(f"<b>{tot_chq}</b>", ParagraphStyle("CTotC", fontName=FONT_BOLD, fontSize=8.5, textColor=_TEAL, alignment=TA_CENTER)),
    ])
    
    t_cf = _data_table(["MONTH", "CREDIT", "DEBIT", "NET CASHFLOW", "AVG BALANCE", "TOTAL TXNS", "CR TXNS", "DR TXNS", "CHQ RTN"], cf_rows, cf_col_widths)
    if not months:
        t_cf.setStyle(TableStyle([("SPAN", (0, 1), (-1, 1))]))
        
    elements.append(KeepTogether([hdr1, t_cf]))
    elements.append(Spacer(1, 6))

'''

text = text[:start_cf] + cf_logic + text[end_cf:]

with open(fp, 'w', encoding='utf8') as f:
    f.write(text)
print("Updated Cashflow and NumberedCanvas")
