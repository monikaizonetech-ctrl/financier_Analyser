import os

fp = 'backend/app/services/file_analysis_service.py'
with open(fp, 'r', encoding='utf8') as f:
    text = f.read()

start = text.find('def _draw_activity_heatmap')

func_code = '''def _draw_unusual_txns_card(w, h_min, items):
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

'''

if 'def _draw_unusual_txns_card' not in text:
    text = text[:start] + func_code + text[start:]
    with open(fp, 'w', encoding='utf8') as f:
        f.write(text)
    print('Added _draw_unusual_txns_card!')
else:
    print('Already present')
