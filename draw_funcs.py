def _draw_income_vs_expense(w, h, monthly_data):
    d = _draw_card_base(w, h, "Income vs Expense")
    d.add(Circle(w - 85, h - 14, 2.8, fillColor=_GREEN, strokeColor=None))
    d.add(String(w - 79, h - 16.5, "Income", fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MUTED))
    d.add(Circle(w - 42, h - 14, 2.8, fillColor=_RED, strokeColor=None))
    d.add(String(w - 36, h - 16.5, "Expense", fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MUTED))
    
    px, py, pw, ph = 40, 24, w - 50, h - 56
    
    months = [m for m in list(monthly_data.keys()) if m]
    if not months:
        d.add(String(w / 2, h / 2 - 4, "No monthly activity recorded", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    max_val = max(max(m.get("credit", 0), m.get("debit", 0)) for m in monthly_data.values()) or 1000
    
    d.add(Line(px, py, px + pw, py, strokeColor=_CARD_BORDER, strokeWidth=1))
    d.add(Line(px, py + ph / 2, px + pw, py + ph / 2, strokeColor=_GRID_LINE, strokeWidth=0.5))
    d.add(Line(px, py + ph, px + pw, py + ph, strokeColor=_GRID_LINE, strokeWidth=0.5))
    
    d.add(String(px - 4, py + ph - 2, _fmt_inr(max_val), fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    d.add(String(px - 4, py + ph / 2 - 2, _fmt_inr(max_val / 2), fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    d.add(String(px - 4, py - 2, "0", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    
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
            g = Group(transform=(0, 1, -1, 0, x1 + bar_w / 2 + 2, py + cr_h + 3))
            g.add(String(0, 0, _fmt_inr(cr), fontName=FONT_BOLD, fontSize=6, fillColor=_TEXT_MAIN, textAnchor="start"))
            d.add(g)
        
        x2 = gx + gap / 2
        if dr_h > 0:
            d.add(Rect(x2, py, bar_w, dr_h, rx=1.5, ry=1.5, fillColor=_RED, strokeColor=None))
            g = Group(transform=(0, 1, -1, 0, x2 + bar_w / 2 + 2, py + dr_h + 3))
            g.add(String(0, 0, _fmt_inr(dr), fontName=FONT_BOLD, fontSize=6, fillColor=_TEXT_MAIN, textAnchor="start"))
            d.add(g)
        
        lbl = m_name.split()[0][:3] if " " in m_name else m_name[:3]
        d.add(String(gx, py - 11, lbl, fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    return d
    
    max_val = max(max(m.get("credit", 0), m.get("debit", 0)) for m in monthly_data.values()) or 1000
    d.add(String(px - 4, py + ph - 2, _fmt_inr(max_val), fontName=FONT_REGULAR, fontSize=5.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    d.add(String(px - 4, py + ph / 2 - 2, _fmt_inr(max_val / 2), fontName=FONT_REGULAR, fontSize=5.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    d.add(String(px - 4, py - 2, "0", fontName=FONT_REGULAR, fontSize=5.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    
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
            d.add(String(x1 + bar_w / 2, py + cr_h + 2.5, _fmt_inr(cr), fontName=FONT_BOLD, fontSize=5.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
        
        x2 = gx + gap / 2
        if dr_h > 0:
            d.add(Rect(x2, py, bar_w, dr_h, rx=1.5, ry=1.5, fillColor=_RED, strokeColor=None))
            d.add(String(x2 + bar_w / 2, py + dr_h + 2.5, _fmt_inr(dr), fontName=FONT_BOLD, fontSize=5.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
        
        lbl = m_name.split()[0][:3] if " " in m_name else m_name[:3]
        d.add(String(gx, py - 11, lbl, fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    return d


def _draw_net_cash_flow(w, h, points, trend_text="+14% ^"):
    d = _draw_card_base(w, h, "Net Cash Flow Trend", trend_text, _GREEN_BG, _GREEN)
    px, py, pw, ph = 32, 24, w - 44, h - 56
    d.add(Line(px, py, px + pw, py, strokeColor=_CARD_BORDER, strokeWidth=0.75))
    d.add(Line(px, py + ph / 2, px + pw, py + ph / 2, strokeColor=_GRID_LINE, strokeWidth=0.5))
    
    if not points or len(points) < 2:
        d.add(String(w / 2, h / 2 - 4, "No cash flow trajectory data", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    min_v = min(v for _, v in points)
    max_v = max(v for _, v in points)
    rng = (max_v - min_v) or 1
    
    coords = []
    for idx, (lbl, val) in enumerate(points):
        cx = px + (idx / (len(points) - 1)) * pw
        cy = py + ((val - min_v) / rng) * (ph - 14) + 5
        coords.append((cx, cy))
    
    poly_pts = [px, py]
    for cx, cy in coords:
        poly_pts.extend([cx, cy])
    poly_pts.extend([px + pw, py])
    d.add(Polygon(poly_pts, fillColor=_GREEN_AREA, strokeColor=None))
    
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        d.add(Line(x1, y1, x2, y2, strokeColor=_GREEN, strokeWidth=1.8))
        d.add(Circle(x1, y1, 2.2, fillColor=_GREEN, strokeColor=_CARD_BG, strokeWidth=0.8))
    d.add(Circle(coords[-1][0], coords[-1][1], 2.2, fillColor=_GREEN, strokeColor=_CARD_BG, strokeWidth=0.8))
    
    d.add(String(px, py - 11, points[0][0][:6], fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_LIGHT))
    mid_idx = len(points) // 2
    d.add(String(px + pw / 2, py - 11, points[mid_idx][0][:6], fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_LIGHT, textAnchor="middle"))
    d.add(String(px + pw, py - 11, points[-1][0][:6], fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    return d


def _draw_balance_trend(w, h, points, trend_text=None):
    d = _draw_card_base(w, h, "Balance Trend", trend_text, _BLUE_BG, _BLUE)
    px, py, pw, ph = 40, 24, w - 50, h - 56
    
    if not points or len(points) < 2:
        d.add(String(w / 2, h / 2 - 4, "Insufficient balance data points", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    min_v = min(v for _, v in points)
    max_v = max(v for _, v in points)
    if min_v > 0: min_v = 0
    rng = (max_v - min_v) or 1
    
    zero_y = py + ((0 - min_v) / rng) * (ph - 14) + 5
    d.add(Line(px, py, px + pw, py, strokeColor=_CARD_BORDER, strokeWidth=1))
    d.add(Line(px, zero_y, px + pw, zero_y, strokeColor=colors.black, strokeWidth=0.8, strokeDashArray=[2, 2]))
    d.add(Line(px, py + ph, px + pw, py + ph, strokeColor=_GRID_LINE, strokeWidth=0.5))
    
    d.add(String(px - 4, py + ph - 2, _fmt_inr(max_v), fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    d.add(String(px - 4, zero_y - 2, "0", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    if min_v < 0:
        d.add(String(px - 4, py - 2, _fmt_inr(min_v), fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    
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
    
    # X-axis label for every month approximately
    step = max(1, len(coords) // 6)
    for i in range(0, len(coords), step):
        d.add(String(coords[i][0], py - 11, coords[i][2][:6], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_LIGHT, textAnchor="middle"))
    if (len(coords)-1) % step != 0:
        d.add(String(coords[-1][0], py - 11, coords[-1][2][:6], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_LIGHT, textAnchor="middle"))
    
    return d
    
    min_v = min(v for _, v in points)
    max_v = max(v for _, v in points)
    rng = (max_v - min_v) or 1
    
    coords = []
    for idx, (lbl, val) in enumerate(points):
        cx = px + (idx / (len(points) - 1)) * pw
        cy = py + ((val - min_v) / rng) * (ph - 14) + 5
        coords.append((cx, cy))
    
    poly_pts = [px, py]
    for cx, cy in coords:
        poly_pts.extend([cx, cy])
    poly_pts.extend([px + pw, py])
    d.add(Polygon(poly_pts, fillColor=_BLUE_AREA, strokeColor=None))
    
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        d.add(Line(x1, y1, x2, y2, strokeColor=_BLUE, strokeWidth=1.8))
        d.add(Circle(x1, y1, 2.2, fillColor=_BLUE, strokeColor=_CARD_BG, strokeWidth=0.8))
    d.add(Circle(coords[-1][0], coords[-1][1], 2.2, fillColor=_BLUE, strokeColor=_CARD_BG, strokeWidth=0.8))
    
    d.add(String(px, py - 11, points[0][0][:6], fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_LIGHT))
    mid_idx = len(points) // 2
    d.add(String(px + pw / 2, py - 11, points[mid_idx][0][:6], fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_LIGHT, textAnchor="middle"))
    d.add(String(px + pw, py - 11, points[-1][0][:6], fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_LIGHT, textAnchor="end"))
    return d


def _draw_expense_by_category(w, h, cat_list, exclusions_str=None):
    d = _draw_card_base(w, h, "Expense by Category")
    palette = [HexColor("#3B82F6"), HexColor("#F59E0B"), HexColor("#8B5CF6"), HexColor("#10B981"), HexColor("#EF4444"), HexColor("#94A3B8")]
    
    if not cat_list:
        d.add(String(w / 2, h / 2 - 4, "No expense transactions recorded", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    start_y = h - 38
    row_h = (start_y - 12) / max(len(cat_list), 1)
    bar_max_w = w * 0.25
    bar_x = 100
    amt_x = w - 40
    pct_x = w - 10
    footnotes = []
    
    for i, item in enumerate(cat_list[:6]):
        name, amt, pct = str(item[0]), float(item[1]), float(item[2])
        cy = start_y - i * row_h
        color = palette[i % len(palette)]
        
        d.add(Circle(14, cy + 3.5, 3.2, fillColor=color, strokeColor=None))
        
        display_name = name
        if len(name) > 22:
            display_name = name[:20] + ".."
            footnotes.append(name)
            
        d.add(String(24, cy + 1, display_name, fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MAIN))
        
        bw = (pct / 100.0) * bar_max_w
        d.add(Rect(bar_x, cy, bw, 8, rx=2, ry=2, fillColor=color, strokeColor=None))
        d.add(String(amt_x, cy + 1, _fmt_inr(amt), fontName=FONT_BOLD, fontSize=7, fillColor=_TEXT_MAIN, textAnchor="end"))
        d.add(String(pct_x, cy + 1, f"{pct:.1f}%", fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="end"))
        
    if footnotes:
        fn_str = "* " + ", ".join(footnotes)
        if len(fn_str) > 70: fn_str = fn_str[:67] + "..."
        d.add(String(14, 8, fn_str, fontName=FONT_REGULAR, fontSize=5.5, fillColor=_TEXT_MUTED))
    
    return d
    
    start_y = h - 38
    row_h = (start_y - 12) / max(len(cat_list), 1)
    bar_max_w = w * 0.32
    
    for i, item in enumerate(cat_list[:6]):
        name, amt, pct = item[0], item[1], item[2]
        cy = start_y - i * row_h
        color = palette[i % len(palette)]
        
        d.add(Circle(14, cy + 3.5, 3.2, fillColor=color, strokeColor=None))
        d.add(String(24, cy + 1, str(name)[:16], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MAIN))
        
        bx = w * 0.46
        bw = (pct / 100.0) * bar_max_w
        d.add(Rect(bx, cy, bar_max_w, 6.5, rx=2.5, ry=2.5, fillColor=_GRID_LINE, strokeColor=None))
        if bw > 1:
            d.add(Rect(bx, cy, bw, 6.5, rx=2.5, ry=2.5, fillColor=color, strokeColor=None))
        
        d.add(String(w - 36, cy + 1, _fmt_inr(amt), fontName=FONT_BOLD, fontSize=7, fillColor=_TEXT_MAIN, textAnchor="end"))
        d.add(String(w - 10, cy + 1, f"{pct:.0f}%", fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="end"))
        
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
    """Normalize tags_data into list of (label, amount, count) for chart and legend."""
    if not tags_data:
        return []
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

    if not raw_items:
        return []

    # Sort by amount descending
    raw_items.sort(key=lambda x: (-x[2], -x[1]))

    # If already 6 or fewer modes, display all of them
    if len(raw_items) <= 6:
        return [(label, amt, cnt) for label, cnt, amt in raw_items]

    # If more than 6 modes: top 5 specific modes + combine rest into "Other"
    specific = [x for x in raw_items if x[0].upper() != "OTHER"]
    other = [x for x in raw_items if x[0].upper() == "OTHER"]
    top_5 = specific[:5]
    omitted = specific[5:] + other
    result = [(label, amt, cnt) for label, cnt, amt in top_5]
    if omitted:
        other_cnt = sum(x[1] for x in omitted)
        other_amt = round(sum(x[2] for x in omitted), 2)
        result.append(("Other", other_amt, other_cnt))
    return result


def _draw_payment_mode_analysis(w, h, cr_tags, dr_tags, total_cr, total_dr):
    d = _draw_card_base(w, h, "Payment Mode Analysis")
    cr_palette = [
        HexColor("#10B981"),  # Emerald Green
        HexColor("#3B82F6"),  # Blue
        HexColor("#F59E0B"),  # Amber
        HexColor("#8B5CF6"),  # Purple
        HexColor("#EC4899"),  # Pink
        HexColor("#94A3B8"),  # Slate / Grey
    ]
    dr_palette = [
        HexColor("#EF4444"),  # Coral / Red
        HexColor("#3B82F6"),  # Blue
        HexColor("#F59E0B"),  # Amber
        HexColor("#8B5CF6"),  # Purple
        HexColor("#10B981"),  # Emerald
        HexColor("#94A3B8"),  # Slate / Grey
    ]

    cx1 = w * 0.27
    cx2 = w * 0.73
    cy = h * 0.58
    r_out = min(w * 0.15, h * 0.22)
    r_in = r_out * 0.62

    # Extract display items (max 6 items, exact sum)
    cr_items = _extract_display_slices(cr_tags, total_cr)
    dr_items = _extract_display_slices(dr_tags, total_dr)

    # Left donut (Credit)
    d.add(String(cx1, h - 33, "Credit by Mode", fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    cr_slices = [(label, amt) for label, amt, cnt in cr_items if amt > 0]
    if cr_slices:
        _draw_donut_chart(d, cx1, cy, r_out, r_in, cr_slices, cr_palette)
    else:
        d.add(Circle(cx1, cy, r_out, fillColor=_CARD_BG, strokeColor=_GRID_LINE, strokeWidth=1))
        d.add(Circle(cx1, cy, r_in, fillColor=_CARD_BG, strokeColor=_CARD_BG, strokeWidth=0))
    d.add(String(cx1, cy + 2, _fmt_inr(total_cr), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
    d.add(String(cx1, cy - 7, "Total Credit", fontName=FONT_REGULAR, fontSize=5.5, fillColor=_TEXT_MUTED, textAnchor="middle"))

    # Right donut (Debit)
    d.add(String(cx2, h - 33, "Debit by Mode", fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
    dr_slices = [(label, amt) for label, amt, cnt in dr_items if amt > 0]
    if dr_slices:
        _draw_donut_chart(d, cx2, cy, r_out, r_in, dr_slices, dr_palette)
    else:
        d.add(Circle(cx2, cy, r_out, fillColor=_CARD_BG, strokeColor=_GRID_LINE, strokeWidth=1))
        d.add(Circle(cx2, cy, r_in, fillColor=_CARD_BG, strokeColor=_CARD_BG, strokeWidth=0))
    d.add(String(cx2, cy + 2, _fmt_inr(total_dr), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
    d.add(String(cx2, cy - 7, "Total Debit", fontName=FONT_REGULAR, fontSize=5.5, fillColor=_TEXT_MUTED, textAnchor="middle"))

    # Exact 100% integer percentages for legend display
    cr_pcts = _normalize_percentages_int([amt for _, amt, _ in cr_items])
    dr_pcts = _normalize_percentages_int([amt for _, amt, _ in dr_items])

    # Left legends (Credit) in 2 columns below donut
    x1_col0 = 10
    x1_col1 = 66
    for idx, (label, amt, cnt) in enumerate(cr_items[:6]):
        col_x = x1_col0 if (idx % 2 == 0) else x1_col1
        row_y = 56 - (idx // 2) * 14
        pct = cr_pcts[idx] if idx < len(cr_pcts) else 0
        clr = cr_palette[idx % len(cr_palette)]
        d.add(Circle(col_x + 3, row_y + 3, 2.5, fillColor=clr, strokeColor=None))
        lbl_short = "BANK CHG" if label == "BANK CHARGE" else str(label)[:8]
        d.add(String(col_x + 8, row_y + 1, f"{lbl_short} {pct}%", fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MAIN))

    if cr_items:
        d.add(String(x1_col0, 12, "Total: 100%", fontName=FONT_BOLD, fontSize=6, fillColor=_TEXT_MUTED))

    # Right legends (Debit) in 2 columns below donut
    x2_col0 = 135
    x2_col1 = 191
    for idx, (label, amt, cnt) in enumerate(dr_items[:6]):
        col_x = x2_col0 if (idx % 2 == 0) else x2_col1
        row_y = 56 - (idx // 2) * 14
        pct = dr_pcts[idx] if idx < len(dr_pcts) else 0
        clr = dr_palette[idx % len(dr_palette)]
        d.add(Circle(col_x + 3, row_y + 3, 2.5, fillColor=clr, strokeColor=None))
        lbl_short = "BANK CHG" if label == "BANK CHARGE" else str(label)[:8]
        d.add(String(col_x + 8, row_y + 1, f"{lbl_short} {pct}%", fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MAIN))

    if dr_items:
        d.add(String(x2_col0, 12, "Total: 100%", fontName=FONT_BOLD, fontSize=6, fillColor=_TEXT_MUTED))

    return d


def _draw_activity_heatmap(w, h, matrix):
    d = _draw_card_base(w, h, "Transaction Activity by Day")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    shades = [HexColor("#F8FAFC"), HexColor("#D1FAE5"), HexColor("#6EE7B7"), HexColor("#10B981"), HexColor("#047857")]
    
    if not matrix or not any(any(row) for row in matrix):
        d.add(String(w / 2, h / 2 - 4, "No activity heatmap data", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    max_c = max(max(r) for r in matrix) or 10
    sx = 32
    sy = h - 40
    col_w = (w - sx - 14) / 7
    row_h = (sy - 26) / 4
    
    for j, day in enumerate(days):
        d.add(String(sx + j * col_w + col_w / 2, sy + 5, day, fontName=FONT_BOLD, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="middle"))
    
    for i, row in enumerate(matrix[:4]):
        ry = sy - 14 - i * row_h
        d.add(String(12, ry + row_h / 2 - 2, f"W{i+1}", fontName=FONT_BOLD, fontSize=7, fillColor=_TEXT_LIGHT))
        for j, cnt in enumerate(row[:7]):
            cx = sx + j * col_w
            if cnt == 0:
                clr, fg = shades[0], _TEXT_LIGHT
            elif cnt <= max_c * 0.25:
                clr, fg = shades[1], HexColor("#065F46")
            elif cnt <= max_c * 0.5:
                clr, fg = shades[2], HexColor("#065F46")
            elif cnt <= max_c * 0.75:
                clr, fg = shades[3], colors.white
            else:
                clr, fg = shades[4], colors.white
            
            d.add(Rect(cx + 1.5, ry, col_w - 3, row_h - 3, rx=3, ry=3, fillColor=clr, strokeColor=None))
            d.add(String(cx + col_w / 2, ry + row_h / 2 - 2.5, str(cnt), fontName=FONT_BOLD, fontSize=7, fillColor=fg, textAnchor="middle"))
    
    d.add(String(sx, 11, "Less activity", fontName=FONT_REGULAR, fontSize=6, fillColor=_TEXT_LIGHT))
    d.add(Rect(sx + 44, 11, 35, 4.5, rx=2, ry=2, fillColor=_TEAL, strokeColor=None))
    d.add(String(sx + 86, 11, "More activity", fontName=FONT_REGULAR, fontSize=6, fillColor=_TEXT_LIGHT))
    return d


def _draw_top_ranked_card(w, h, title, items, bar_color, exclusions_str=None):
    d = _draw_card_base(w, h, title)
    start_y = h - 38
    if not items:
        d.add(String(w / 2, h / 2 - 4, "No records found", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    row_h = (start_y - 12) / max(len(items), 1)
    bar_max_w = w * 0.28
    
    for i, (name, amt, pct) in enumerate(items[:5]):
        cy = start_y - i * row_h
        d.add(String(14, cy + 1, str(name)[:16], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MAIN))
        d.add(String(w * 0.50, cy + 1, _fmt_inr(amt), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN, textAnchor="end"))
        
        bx = w * 0.54
        bw = (pct / 100.0) * bar_max_w
        d.add(Rect(bx, cy, bar_max_w, 6, rx=2.5, ry=2.5, fillColor=_GRID_LINE, strokeColor=None))
        if bw > 1:
            d.add(Rect(bx, cy, bw, 6, rx=2.5, ry=2.5, fillColor=bar_color, strokeColor=None))
        
        d.add(String(w - 10, cy + 1, f"{pct:.0f}%", fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="end"))
        
    if exclusions_str:
        d.add(String(w / 2, 8, exclusions_str, fontName="Helvetica-Oblique", fontSize=6, fillColor=_TEXT_MUTED, textAnchor="middle"))
        
    return d


def _draw_recurring_card(w, h, items):
    d = _draw_card_base(w, h, "Recurring Transactions")
    d.add(String(14, h - 34, "Merchant / Entity", fontName=FONT_BOLD, fontSize=7, fillColor=_TEXT_LIGHT))
    d.add(String(w * 0.52, h - 34, "Frequency", fontName=FONT_BOLD, fontSize=7, fillColor=_TEXT_LIGHT))
    d.add(String(w - 14, h - 34, "Avg Amount", fontName=FONT_BOLD, fontSize=7, fillColor=_TEXT_LIGHT, textAnchor="end"))
    d.add(Line(14, h - 38, w - 14, h - 38, strokeColor=_GRID_LINE, strokeWidth=0.75))
    
    if not items:
        d.add(String(w / 2, h / 2 - 4, "No recurring debits detected", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    
    start_y = h - 52
    row_h = (start_y - 10) / max(len(items), 1)
    for i, (merchant, freq, amt) in enumerate(items[:5]):
        cy = start_y - i * row_h
        d.add(String(14, cy + 1, str(merchant)[:18], fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MAIN))
        d.add(String(w * 0.52, cy + 1, str(freq), fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED))
        d.add(String(w - 14, cy + 1, _fmt_inr(amt), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN, textAnchor="end"))
    return d


def _draw_unusual_txns_card(w, h_min, items):
    import textwrap
    req_h = 42
    drawn_items = []
    if not items:
        d = _draw_card_base(w, h_min, "Risk & Unusual Activity")
        d.add(Rect(14, h_min / 2 - 16, w - 28, 32, rx=4, ry=4, fillColor=_GREEN_BG, strokeColor=None))
        d.add(String(w / 2, h_min / 2 + 1, "Financial Flow Stable", fontName=FONT_BOLD, fontSize=8, fillColor=_GREEN, textAnchor="middle"))
        d.add(String(w / 2, h_min / 2 - 10, "No anomalous transaction spikes detected", fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d, h_min

    for (tag, detail, sev, s_bg, s_fg) in items[:5]:
        lines = textwrap.wrap(str(detail), width=52)
        if len(lines) > 3:
            rem = len(lines) - 3
            lines = lines[:3]
            lines.append(f"+{rem} more")
        item_h = 16 + len(lines)*8
        req_h += item_h + 8
        drawn_items.append((tag, lines, sev, s_bg, s_fg, item_h))
        
    h = max(h_min, req_h)
    d = _draw_card_base(w, h, "Risk & Unusual Activity")
    
    start_y = h - 42
    for i, (tag, lines, sev, s_bg, s_fg, item_h) in enumerate(drawn_items):
        row_h = item_h + 8
        cy = start_y - (row_h / 2)
        start_y -= row_h
        
        d.add(Rect(12, cy - row_h/2 + 4, w - 24, row_h - 4, rx=4, ry=4, fillColor=_GRID_LINE, strokeColor=None))
        d.add(String(20, cy + row_h/2 - 10, str(tag), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN))
        
        bw = 36
        bx = w - bw - 20
        by = cy + row_h/2 - 17
        d.add(Rect(bx, by, bw, 13, rx=3, ry=3, fillColor=s_bg, strokeColor=None))
        d.add(String(bx + bw / 2, by + 3.5, sev, fontName=FONT_BOLD, fontSize=6.5, fillColor=s_fg, textAnchor="middle"))
        
        for j, line in enumerate(lines):
            d.add(String(20, cy + row_h/2 - 20 - (j*8), line, fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MUTED))
            
    return d, h
    
    start_y = h - 42
    row_h = (start_y - 10) / max(len(items[:5]), 1)
    for i, (tag, detail, sev, s_bg, s_fg) in enumerate(items[:5]):
        cy = start_y - i * row_h
        d.add(Rect(12, cy - 8, w - 24, row_h - 2, rx=4, ry=4, fillColor=_GRID_LINE, strokeColor=None))
        d.add(String(20, cy + (row_h/2) - 8, str(tag), fontName=FONT_BOLD, fontSize=7.5, fillColor=_TEXT_MAIN))
        
        bw = 36
        bx = w - bw - 20
        by = cy + (row_h/2) - 15
        d.add(Rect(bx, by, bw, 13, rx=3, ry=3, fillColor=s_bg, strokeColor=None))
        d.add(String(bx + bw / 2, by + 3.5, sev, fontName=FONT_BOLD, fontSize=6.5, fillColor=s_fg, textAnchor="middle"))
        
        detail_str = str(detail)
        import textwrap
        lines = textwrap.wrap(detail_str, width=42)
        for j, line in enumerate(lines): # Print all lines
            d.add(String(20, cy + (row_h/2) - 17 - (j*8), line, fontName=FONT_REGULAR, fontSize=6.5, fillColor=_TEXT_MUTED))
            
    return d


def _draw_day_of_month_balance(w, h, weeks_data):
    d = _draw_card_base(w, h, "Average Balance by Week")
    px, py, pw, ph = 34, 24, w - 46, h - 56
    d.add(Line(px, py, px + pw, py, strokeColor=_CARD_BORDER, strokeWidth=0.75))
    
    if not weeks_data:
        d.add(String(w / 2, h / 2 - 4, "No weekly balance data available", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    max_v = max(v for _, v in weeks_data) or 1000
    
    col_w = pw / len(weeks_data)
    bar_w = col_w * 0.44
    for i, (w_lbl, val) in enumerate(weeks_data):
        bx = px + i * col_w + (col_w - bar_w) / 2
        bh = max(2, (val / max_v) * (ph - 14)) if val > 0 else 0
        if bh > 0:
            d.add(Rect(bx, py, bar_w, bh, rx=2.5, ry=2.5, fillColor=_PURPLE, strokeColor=None))
            d.add(String(bx + bar_w / 2, py + bh + 3, _fmt_inr(val), fontName=FONT_BOLD, fontSize=6.5, fillColor=_TEXT_MAIN, textAnchor="middle"))
        d.add(String(bx + bar_w / 2, py - 12, w_lbl, fontName=FONT_REGULAR, fontSize=7, fillColor=_TEXT_MUTED, textAnchor="middle"))
    return d


def _draw_counterparty_exposure(w, h, top_cp):
    if not top_cp:
        d = _draw_card_base(w, h, "Top Payees / Counterparties")
        d.add(String(w / 2, h / 2 - 4, "No counterparty exposure data", fontName=FONT_REGULAR, fontSize=7.5, fillColor=_TEXT_MUTED, textAnchor="middle"))
        return d
    return _draw_top_ranked_card(w, h, "Top Payees / Counterparties", top_cp, _TEAL)


def _analytics_charts(a):
    """Legacy helper returning charts for backwards compatibility."""
    d1 = _draw_income_vs_expense(480, 160, a.get("monthly", {}))
    d2 = _draw_balance_trend(480, 160, [])
    d3 = Drawing(240, 140)
    d4 = Drawing(240, 140)
    return [
        ("Monthly Credit Amount vs Debit Amount Comparison", d1),
        ("Average Monthly Balance Trend", d2),
        ("Credit by Payment Mode", d3),
        ("Debit by Payment Mode", d4),
    ]


def _clean_cp_name(name):
    if not name or name == "-":
        return "-"
    s = str(name).strip()
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"[\u200b\u200c\u200d\ufeff\x00-\x1f\x7f-\x9f]", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s


def _get_monthly_counterparties(a: dict):
    """Return dict of {month: {'cr_items': [...], 'dr_items': [...], 'total_cr': ..., 'total_dr': ..., 'cr_cnt': ..., 'dr_cnt': ...}}."""
    months = a.get("months", [])
    rows = a.get("all_rows", [])
    m_data = defaultdict(lambda: {
        "cr": defaultdict(lambda: {"amount": 0.0, "count": 0}),
        "dr": defaultdict(lambda: {"amount": 0.0, "count": 0}),
    })
    for r in rows:
        mk = _month_key(_to_date(r.get("date")))
        if not mk:
            continue
        cr = float(r.get("credit", 0.0) or 0.0)
        dr = float(r.get("debit", 0.0) or 0.0)
        cp = r.get("counterparty") or r.get("description") or "-"
        if cr > 0:
            m_data[mk]["cr"][cp]["amount"] += cr
            m_data[mk]["cr"][cp]["count"] += 1
        if dr > 0:
            m_data[mk]["dr"][cp]["amount"] += dr
            m_data[mk]["dr"][cp]["count"] += 1

    result = {}
    for m in months:
        cr_items = sorted(m_data[m]["cr"].items(), key=lambda kv: -kv[1]["amount"])
        dr_items = sorted(m_data[m]["dr"].items(), key=lambda kv: -kv[1]["amount"])
        m_summary = a.get("monthly", {}).get(m, {})
        tot_cr = m_summary.get("credit", sum(v["amount"] for _, v in cr_items))
        tot_dr = m_summary.get("debit", sum(v["amount"] for _, v in dr_items))
        cr_cnt = m_summary.get("credit_count", sum(v["count"] for _, v in cr_items))
        dr_cnt = m_summary.get("debit_count", sum(v["count"] for _, v in dr_items))
        result[m] = {
            "cr_items": cr_items,
            "dr_items": dr_items,
            "total_cr": tot_cr,
            "total_dr": tot_dr,
            "cr_cnt": cr_cnt,
            "dr_cnt": dr_cnt,
        }
    return result


def _counterparty_totals_table(month_label: str, cp_credit_items: list, cp_debit_items: list,
                               tot_cr: float, tot_dr: float, cr_cnt: int, dr_cnt: int,
                               max_items: int = 5):
    cp_col_widths = [140, 60, 55, 140, 60, 55]
    _cph = ParagraphStyle("CPH_F", fontName=FONT_BOLD, fontSize=7, textColor=colors.white, alignment=TA_CENTER, leading=9)
    _cp_name = ParagraphStyle("CP_N_F", fontName=FONT_REGULAR, fontSize=6.8, leading=8.2, wordWrap="CJK")
    _cp_amt = ParagraphStyle("CP_A_F", fontName=FONT_REGULAR, fontSize=7.2, leading=9, alignment=TA_RIGHT)
    _cp_cnt = ParagraphStyle("CP_C_F", fontName=FONT_REGULAR, fontSize=7.2, leading=9, alignment=TA_CENTER)
    _cp_bname = ParagraphStyle("CP_BN_F", fontName=FONT_BOLD, fontSize=7.2, leading=9)
    _cp_bamt = ParagraphStyle("CP_BA_F", fontName=FONT_BOLD, fontSize=7.2, leading=9, alignment=TA_RIGHT)
    _cp_bcnt = ParagraphStyle("CP_BC_F", fontName=FONT_BOLD, fontSize=7.2, leading=9, alignment=TA_CENTER)

    hdr_row = [
        Paragraph("COUNTERPARTY(CR)", _cph),
        Paragraph("AMOUNT(CR)", _cph),
        Paragraph("ENTRIES (CR)", _cph),
        Paragraph("COUNTERPARTY(DR)", _cph),
        Paragraph("AMOUNT(DR)", _cph),
        Paragraph("ENTRIES (DR)", _cph),
    ]

    total_row = [
        Paragraph(f"Total ({month_label})", _cp_bname),
        Paragraph(f"{tot_cr:,.0f}", _cp_bamt),
        Paragraph(str(cr_cnt), _cp_bcnt),
        Paragraph(f"Total ({month_label})", _cp_bname),
        Paragraph(f"{tot_dr:,.0f}", _cp_bamt),
        Paragraph(str(dr_cnt), _cp_bcnt),
    ]

    data_rows = [hdr_row, total_row]
    num_rows = min(max(len(cp_credit_items), len(cp_debit_items)), max_items)
    for i in range(num_rows):
        cr = cp_credit_items[i] if i < len(cp_credit_items) else ("-", {"amount": 0, "count": 0})
        dr = cp_debit_items[i] if i < len(cp_debit_items) else ("-", {"amount": 0, "count": 0})
        cr_amt_str = f"{cr[1]['amount']:,.0f}" if cr[1]["amount"] else "-"
        dr_amt_str = f"{dr[1]['amount']:,.0f}" if dr[1]["amount"] else "-"
        cr_cnt_str = str(cr[1]["count"]) if cr[1]["count"] else "-"
        dr_cnt_str = str(dr[1]["count"]) if dr[1]["count"] else "-"
        data_rows.append([
            Paragraph(_clean_cp_name(cr[0]), _cp_name),
            Paragraph(cr_amt_str, _cp_amt),
            Paragraph(cr_cnt_str, _cp_cnt),
            Paragraph(_clean_cp_name(dr[0]), _cp_name),
            Paragraph(dr_amt_str, _cp_amt),
            Paragraph(dr_cnt_str, _cp_cnt),
        ])

    small_cr = sum(v["amount"] for _, v in cp_credit_items[max_items:])
    small_dr = sum(v["amount"] for _, v in cp_debit_items[max_items:])
    small_dr_cnt = sum(v["count"] for _, v in cp_debit_items[max_items:])
    small_cr_cnt = sum(v["count"] for _, v in cp_credit_items[max_items:])
    if small_cr > 0 or small_dr > 0:
        data_rows.append([
            Paragraph("Txn Total &lt; 5K" if small_cr else "-", _cp_bname),
            Paragraph(f"{small_cr:,.0f}" if small_cr else "-", _cp_amt),
            Paragraph(str(small_cr_cnt) if small_cr else "-", _cp_cnt),
            Paragraph("Txn Total &lt; 5K" if small_dr else "-", _cp_bname),
            Paragraph(f"{small_dr:,.0f}" if small_dr else "-", _cp_amt),
            Paragraph(str(small_dr_cnt) if small_dr else "-", _cp_cnt),
        ])

    cp_table = Table(data_rows, colWidths=cp_col_widths, repeatRows=1)
    cp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PDF_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, PDF_GREY_LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PDF_GREY]),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EAF2FB")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return cp_table


