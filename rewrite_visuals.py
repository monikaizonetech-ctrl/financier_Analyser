import os
import re

fp = 'backend/app/services/file_analysis_service.py'
with open(fp, 'r', encoding='utf8') as f:
    text = f.read()

# 1. Add _fmt_inr_compact
compact_func = '''
def _fmt_inr_compact(val):
    if val is None: return "0"
    v = abs(float(val))
    sign = "-" if val < 0 else ""
    if v >= 10000000: return f"{sign}Rs.{v/10000000:.1f}Cr".replace(".0Cr", "Cr")
    elif v >= 100000: return f"{sign}Rs.{v/100000:.1f}L".replace(".0L", "L")
    elif v >= 1000: return f"{sign}Rs.{v/1000:.1f}K".replace(".0K", "K")
    else: return f"{sign}Rs.{int(v)}"

'''
if '_fmt_inr_compact' not in text:
    text = text.replace('def _fmt_inr(', compact_func + 'def _fmt_inr(')

# 2. Extract and replace functions
start = text.find('def _draw_income_vs_expense')
end = text.find('def _draw_counterparty_exposure')

new_funcs = '''def _draw_income_vs_expense(w, h, monthly_data):
    d = _draw_card_base(w, h, "Income vs Expense")
    d.add(Circle(w - 55, h - 14, 2.8, fillColor=_GREEN, strokeColor=None))
    d.add(String(w - 49, h - 16.5, "Income", fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MUTED))
    d.add(Circle(w - 22, h - 14, 2.8, fillColor=_RED, strokeColor=None))
    d.add(String(w - 16, h - 16.5, "Expense", fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MUTED))
    
    px, py, pw, ph = 36, 24, w - 46, h - 56
    
    months = [m for m in list(monthly_data.keys()) if m]
    if not months:
        d.add(String(w / 2, h / 2 - 4, "No monthly activity recorded", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    max_val = max(max(m.get("credit", 0), m.get("debit", 0)) for m in monthly_data.values()) or 1000
    
    d.add(Line(px, py, px + pw, py, strokeColor=_CARD_BORDER, strokeWidth=1))
    d.add(Line(px, py + ph / 2, px + pw, py + ph / 2, strokeColor=_GRID_LINE, strokeWidth=0.5))
    d.add(Line(px, py + ph, px + pw, py + ph, strokeColor=_GRID_LINE, strokeWidth=0.5))
    
    d.add(String(px + 2, py + ph - 8, _fmt_inr_compact(max_val), fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="start"))
    d.add(String(px + 2, py + ph / 2 - 8, _fmt_inr_compact(max_val / 2), fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="start"))
    d.add(String(px + 2, py + 2, "0", fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="start"))
    
    n_m = len(months)
    group_w = pw / n_m
    bar_w = min(12, max(4.5, group_w * 0.32))
    gap = 2
    for i, m_name in enumerate(months):
        gx = px + i * group_w + group_w / 2
        cr = monthly_data[m_name].get("credit", 0)
        dr = monthly_data[m_name].get("debit", 0)
        cr_h = max(2, (cr / max_val) * (ph - 14)) if cr else 0
        dr_h = max(2, (dr / max_val) * (ph - 14)) if dr else 0
        
        x1 = gx - bar_w - gap / 2
        if cr_h > 0:
            d.add(Rect(x1, py, bar_w, cr_h, rx=1.5, ry=1.5, fillColor=_GREEN, strokeColor=None))
            d.add(String(x1 + bar_w / 2, py + cr_h + 2, _fmt_inr_compact(cr), fontName=FONT_BOLD, fontSize=6.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
        
        x2 = gx + gap / 2
        if dr_h > 0:
            d.add(Rect(x2, py, bar_w, dr_h, rx=1.5, ry=1.5, fillColor=_RED, strokeColor=None))
            d.add(String(x2 + bar_w / 2, py + dr_h + 2, _fmt_inr_compact(dr), fontName=FONT_BOLD, fontSize=6.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
        
        lbl = m_name.split()[0][:3] if " " in m_name else m_name[:3]
        d.add(String(gx, py - 11, lbl, fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    return d


def _draw_net_cash_flow(w, h, points, trend_text="+14% ^"):
    return _draw_card_base(w, h, "Net Cash Flow Trend", trend_text, _GREEN_BG, _GREEN)


def _draw_balance_trend(w, h, points, trend_text=None):
    d = _draw_card_base(w, h, "Balance Trend", trend_text, _BLUE_BG, _BLUE)
    px, py, pw, ph = 36, 24, w - 46, h - 56
    
    if not points or len(points) < 2:
        d.add(String(w / 2, h / 2 - 4, "Insufficient balance data points", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    min_v = min(v for _, v in points)
    max_v = max(v for _, v in points)
    if min_v > 0: min_v = 0
    rng = (max_v - min_v) or 1
    
    zero_y = py + ((0 - min_v) / rng) * (ph - 14) + 5
    d.add(Line(px, py, px + pw, py, strokeColor=_CARD_BORDER, strokeWidth=1))
    d.add(Line(px, zero_y, px + pw, zero_y, strokeColor=_GRID_LINE, strokeWidth=0.8, strokeDashArray=[2, 2]))
    d.add(Line(px, py + ph, px + pw, py + ph, strokeColor=_GRID_LINE, strokeWidth=0.5))
    
    d.add(String(px + 2, py + ph - 8, _fmt_inr_compact(max_v), fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="start"))
    d.add(String(px + 2, zero_y + 2, "0", fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="start"))
    if min_v < 0:
        d.add(String(px + 2, py + 2, _fmt_inr_compact(min_v), fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="start"))
    
    coords = []
    for idx, (lbl, val) in enumerate(points):
        cx = px + (idx / (len(points) - 1)) * pw
        cy = py + ((val - min_v) / rng) * (ph - 14) + 5
        coords.append((cx, cy, lbl))
    
    for i in range(len(coords) - 1):
        x1, y1, _ = coords[i]
        x2, y2, _ = coords[i + 1]
        d.add(Line(x1, y1, x2, y2, strokeColor=_BLUE, strokeWidth=1.8))
        d.add(Circle(x1, y1, 2.2, fillColor=_BLUE, strokeColor=_CARD_BG, strokeWidth=0.8))
    d.add(Circle(coords[-1][0], coords[-1][1], 2.2, fillColor=_BLUE, strokeColor=_CARD_BG, strokeWidth=0.8))
    
    if len(coords) >= 3:
        step = (len(coords) - 1) // 2
        d.add(String(coords[0][0], py - 11, coords[0][2][:6], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        d.add(String(coords[step][0], py - 11, coords[step][2][:6], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        d.add(String(coords[-1][0], py - 11, coords[-1][2][:6], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    else:
        for cx, cy, lbl in coords:
            d.add(String(cx, py - 11, lbl[:6], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    
    return d


def _draw_expense_by_category(w, h, cat_list, exclusions_str=None):
    d = _draw_card_base(w, h, "Expense by Category")
    palette = [HexColor("#3B82F6"), HexColor("#F59E0B"), HexColor("#8B5CF6"), HexColor("#10B981"), HexColor("#EF4444"), HexColor("#94A3B8")]
    
    if not cat_list:
        d.add(String(w / 2, h / 2 - 4, "No expense transactions recorded", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    start_y = h - 38
    row_h = (start_y - 12) / max(len(cat_list), 1)
    
    lbl_w = w * 0.38
    bar_w = w * 0.34
    amt_w = w * 0.16
    
    for i, item in enumerate(cat_list[:6]):
        name, amt, pct = str(item[0]), float(item[1]), float(item[2])
        cy = start_y - i * row_h
        color = palette[i % len(palette)]
        
        d.add(Circle(14, cy + 3.5, 3.2, fillColor=color, strokeColor=None))
        display_name = name[:18] + ".." if len(name) > 20 else name
        d.add(String(24, cy + 1, display_name, fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MAIN))
        
        bx = 10 + lbl_w
        bw = (pct / 100.0) * bar_w
        d.add(Rect(bx, cy, bar_w - 4, 6, rx=2, ry=2, fillColor=_GRID_LINE, strokeColor=None))
        if bw > 1:
            d.add(Rect(bx, cy, bw, 6, rx=2, ry=2, fillColor=color, strokeColor=None))
        
        ax = bx + bar_w
        d.add(String(ax + amt_w - 4, cy + 1, _fmt_inr_compact(amt), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN, textAnchor="end"))
        d.add(String(w - 10, cy + 1, f"{pct:.0f}%", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="end"))
        
    if exclusions_str:
        d.add(String(w / 2, 8, exclusions_str, fontName="Helvetica-Oblique", fontSize=6, fillColor=_TEXT_MUTED, textAnchor="middle"))
    
    return d


def _draw_donut_chart(d, cx, cy, r_out, r_in, slices_data, palette):
    total = sum(v for _, v in slices_data) or 1
    cur_ang = 90
    for idx, (label, val) in enumerate(slices_data):
        deg = (val / total) * 360
        if deg > 0:
            color = palette[idx % len(palette)]
            d.add(Wedge(cx, cy, r_out, cur_ang, cur_ang + deg, fillColor=color, strokeColor=_CARD_BG, strokeWidth=1))
            cur_ang += deg
    d.add(Circle(cx, cy, r_in, fillColor=_CARD_BG, strokeColor=_CARD_BG, strokeWidth=0))


def _extract_display_slices(tags_data, total_amt):
    if not tags_data: return []
    raw_items = []
    if isinstance(tags_data, dict):
        for k, v in tags_data.items():
            if isinstance(v, dict):
                amt = float(v.get("total_amount") or v.get("amount") or 0.0)
                cnt = int(v.get("transaction_count") or v.get("count") or 0)
            else:
                amt = float(v or 0.0)
                cnt = 1
            if amt > 0 or cnt > 0:
                raw_items.append((k, cnt, round(amt, 2)))
    elif isinstance(tags_data, list):
        for item in tags_data:
            if isinstance(item, dict):
                k = item.get("payment_mode") or item.get("label") or "Other"
                amt = float(item.get("total_amount") or item.get("amount") or 0.0)
                cnt = int(item.get("transaction_count") or item.get("count") or 0)
                if amt > 0 or cnt > 0:
                    raw_items.append((k, cnt, round(amt, 2)))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                raw_items.append((str(item[0]), 1, float(item[1] or 0.0)))
    if not raw_items: return []
    raw_items.sort(key=lambda x: (-x[2], -x[1]))
    if len(raw_items) <= 6: return [(label, amt, cnt) for label, cnt, amt in raw_items]
    specific = [x for x in raw_items if x[0].upper() != "OTHER"]
    other = [x for x in raw_items if x[0].upper() == "OTHER"]
    top_5 = specific[:5]
    omitted = specific[5:] + other
    result = [(label, amt, cnt) for label, cnt, amt in top_5]
    if omitted:
        result.append(("Other", round(sum(x[2] for x in omitted), 2), sum(x[1] for x in omitted)))
    return result


def _draw_payment_mode_analysis(w, h, cr_tags, dr_tags, total_cr, total_dr):
    d = _draw_card_base(w, h, "Payment Mode Analysis")
    cr_palette = [HexColor("#10B981"), HexColor("#3B82F6"), HexColor("#F59E0B"), HexColor("#8B5CF6"), HexColor("#EC4899"), HexColor("#94A3B8")]
    dr_palette = [HexColor("#EF4444"), HexColor("#3B82F6"), HexColor("#F59E0B"), HexColor("#8B5CF6"), HexColor("#10B981"), HexColor("#94A3B8")]

    cx1 = w * 0.25
    cx2 = w * 0.75
    cy = h * 0.58
    r_out = min(w * 0.16, h * 0.22)
    r_in = r_out * 0.65

    cr_items = _extract_display_slices(cr_tags, total_cr)
    dr_items = _extract_display_slices(dr_tags, total_dr)

    # Left donut
    d.add(String(cx1, h - 33, "Credit by Mode", fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    cr_slices = [(label, amt) for label, amt, cnt in cr_items if amt > 0]
    if cr_slices:
        _draw_donut_chart(d, cx1, cy, r_out, r_in, cr_slices, cr_palette)
    else:
        d.add(Circle(cx1, cy, r_out, fillColor=_CARD_BG, strokeColor=_GRID_LINE, strokeWidth=1))
        d.add(Circle(cx1, cy, r_in, fillColor=_CARD_BG, strokeColor=_CARD_BG, strokeWidth=0))
    d.add(String(cx1, cy + 2, _fmt_inr_compact(total_cr), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
    d.add(String(cx1, cy - 7, "Total Credit", fontName=FONT_REGULAR, fontSize=5.5, fillColor=_TEXT_MUTED, textAnchor="middle"))

    # Right donut
    d.add(String(cx2, h - 33, "Debit by Mode", fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    dr_slices = [(label, amt) for label, amt, cnt in dr_items if amt > 0]
    if dr_slices:
        _draw_donut_chart(d, cx2, cy, r_out, r_in, dr_slices, dr_palette)
    else:
        d.add(Circle(cx2, cy, r_out, fillColor=_CARD_BG, strokeColor=_GRID_LINE, strokeWidth=1))
        d.add(Circle(cx2, cy, r_in, fillColor=_CARD_BG, strokeColor=_CARD_BG, strokeWidth=0))
    d.add(String(cx2, cy + 2, _fmt_inr_compact(total_dr), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
    d.add(String(cx2, cy - 7, "Total Debit", fontName=FONT_REGULAR, fontSize=5.5, fillColor=_TEXT_MUTED, textAnchor="middle"))

    cr_pcts = _normalize_percentages_int([amt for _, amt, _ in cr_items])
    dr_pcts = _normalize_percentages_int([amt for _, amt, _ in dr_items])

    x1_col0, x1_col1 = 8, 62
    for idx, (label, amt, cnt) in enumerate(cr_items[:6]):
        col_x = x1_col0 if (idx % 2 == 0) else x1_col1
        row_y = 56 - (idx // 2) * 14
        pct = cr_pcts[idx] if idx < len(cr_pcts) else 0
        clr = cr_palette[idx % len(cr_palette)]
        d.add(Circle(col_x + 3, row_y + 3, 2.5, fillColor=clr, strokeColor=None))
        d.add(String(col_x + 8, row_y + 1, f"{str(label)[:8]} {pct}%", fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MAIN))

    x2_col0, x2_col1 = 132, 186
    for idx, (label, amt, cnt) in enumerate(dr_items[:6]):
        col_x = x2_col0 if (idx % 2 == 0) else x2_col1
        row_y = 56 - (idx // 2) * 14
        pct = dr_pcts[idx] if idx < len(dr_pcts) else 0
        clr = dr_palette[idx % len(dr_palette)]
        d.add(Circle(col_x + 3, row_y + 3, 2.5, fillColor=clr, strokeColor=None))
        d.add(String(col_x + 8, row_y + 1, f"{str(label)[:8]} {pct}%", fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MAIN))

    return d


def _draw_activity_heatmap(w, h, matrix):
    return _draw_card_base(w, h, "Transaction Activity by Day")


def _draw_top_ranked_card(w, h, title, items, bar_color, exclusions_str=None):
    d = _draw_card_base(w, h, title)
    start_y = h - 38
    if not items:
        d.add(String(w / 2, h / 2 - 4, "No records found", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    row_h = (start_y - 12) / max(len(items), 1)
    lbl_w = w * 0.38
    bar_w = w * 0.34
    amt_w = w * 0.16
    
    for i, (name, amt, pct) in enumerate(items[:5]):
        cy = start_y - i * row_h
        display_name = str(name)[:18] + ".." if len(str(name)) > 20 else str(name)
        d.add(String(14, cy + 1, display_name, fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MAIN))
        
        bx = 10 + lbl_w
        bw = (pct / 100.0) * bar_w
        d.add(Rect(bx, cy, bar_w - 4, 6, rx=2, ry=2, fillColor=_GRID_LINE, strokeColor=None))
        if bw > 1:
            d.add(Rect(bx, cy, bw, 6, rx=2, ry=2, fillColor=bar_color, strokeColor=None))
        
        ax = bx + bar_w
        d.add(String(ax + amt_w - 4, cy + 1, _fmt_inr_compact(amt), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN, textAnchor="end"))
        d.add(String(w - 10, cy + 1, f"{pct:.0f}%", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="end"))
        
    if exclusions_str:
        d.add(String(w / 2, 8, exclusions_str, fontName="Helvetica-Oblique", fontSize=6, fillColor=_TEXT_MUTED, textAnchor="middle"))
        
    return d

'''

text = text[:start] + new_funcs + text[end:]

with open(fp, 'w', encoding='utf8') as f:
    f.write(text)
print("Rewrote visual analytics functions!")
