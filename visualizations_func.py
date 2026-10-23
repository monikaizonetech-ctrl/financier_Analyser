def _pdf_visualizations_page(elements, styles, summary: dict, a: dict):
    """Page 2: Visual Analytics Dashboard displaying 6 charts in a balanced 2x3 grid."""
    generated_dt = datetime.fromisoformat(summary.get("generated_at", datetime.utcnow().isoformat()))
    all_rows = a.get("all_rows", [])
    pw = 510
    card_w = (pw - 10) / 2  # 250 pt per card
    card_h = 196            # 196 pt fits 3 rows cleanly

    # 1. Prepare Monthly Data
    monthly_data = a.get("monthly", {})

    # 2. Net Cash Flow & Balance Trajectory Series
    daily_items = a.get("daily_balance") or a.get("full_daily_series") or []
    bal_points_raw = []
    for item in daily_items:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            d_val, bal_val = item[0], item[1]
            d_obj = _to_date(d_val)
            dt_lbl = d_obj.strftime("%d %b") if d_obj else str(d_val)[:6]
            bal_points_raw.append((dt_lbl, bal_val))
    
    step = max(1, len(bal_points_raw) // 8)
    bal_points = bal_points_raw[::step]
    if bal_points_raw and bal_points_raw[-1] not in bal_points:
        bal_points.append(bal_points_raw[-1])

    open_bal = a.get("opening_balance", 0.0)
    close_bal = a.get("closing_balance", 0.0)
    # FIX 2 Option A: Remove misleading 0% badge
    bal_growth_txt = None

    # 3. Expense by Category (strictly categorized, no payment mode tags)
    exp_by_cat = defaultdict(float)
    dr_own = 0.0
    dr_pt = 0.0
    for r in all_rows:
        dr = float(r.get("debit") or 0.0)
        if dr > 0:
            if r.get("is_own_transfer"):
                dr_own += dr
                continue
            if r.get("is_pass_through"):
                dr_pt += dr
                continue
            cat = r.get("category")
            if not cat or cat.strip() in ("", "-", "None", "Unknown"):
                cat = "Vendor & Contractor Payments"
            exp_by_cat[cat] += dr
    tot_dr = sum(exp_by_cat.values()) or 1.0
    sorted_exp = sorted(exp_by_cat.items(), key=lambda x: -x[1])
    cat_list = [(c, amt, (amt / tot_dr) * 100) for c, amt in sorted_exp[:5]]
    rem_dr = sum(amt for _, amt in sorted_exp[5:])
    
    if rem_dr > 0:
        cat_list.append(("Others", rem_dr, (rem_dr / tot_dr) * 100))

    # 4. Payment Modes (independent CREDIT and DEBIT analysis)
    cr_by_tag = defaultdict(float)
    dr_by_tag = defaultdict(float)
    for r in all_rows:
        mode = r.get("payment_mode") or _classify_payment_mode(r.get("description", ""))
        cr = float(r.get("credit") or 0.0)
        dr = float(r.get("debit") or 0.0)
        if cr > 0:
            cr_by_tag[mode] += cr
        if dr > 0:
            dr_by_tag[mode] += dr

    # 5. Top 5 Income Sources (grouped by normalized counterparty/source)
    inc_by_src = defaultdict(float)
    cr_own = 0.0
    cr_pt = 0.0
    for r in all_rows:
        cr = float(r.get("credit") or 0.0)
        if cr > 0:
            if r.get("is_own_transfer"):
                cr_own += cr
                continue
            if r.get("is_pass_through"):
                cr_pt += cr
                continue
            src = _clean_cp_name(r.get("counterparty") or r.get("description") or "")
            if not src or src.strip() in ("", "-", "None", "Unknown"):
                src = "Unknown / Other Income Source"
            inc_by_src[src] += cr
    tot_cr = sum(inc_by_src.values()) or 1.0
    sorted_inc = sorted(inc_by_src.items(), key=lambda x: -x[1])
    top_income = [(s, amt, (amt / tot_cr) * 100) for s, amt in sorted_inc[:5]]
    
    ex = []
    if dr_own > 0 or cr_own > 0: ex.append(f"own transfers {dr_own:,.2f}/{cr_own:,.2f}")
    if dr_pt > 0 or cr_pt > 0: ex.append(f"pass-through {dr_pt:,.2f}/{cr_pt:,.2f}")
    combined_exclusions_str = f"Excluded: {', '.join(ex)}" if ex else None

    # 6. Unusual Transactions (dynamic statistical alerts, neutral terminology)
    unusual_items = []
    if a.get("unusual_txns"):
        for u in a.get("unusual_txns", [])[:5]:
            u_title = u.get("type", "Unusual Transaction")
            desc = u.get("description", "")
            severity = u.get("severity", "Medium")
            if severity == "High":
                bg, fg = _RED_BG, _RED
            elif severity == "Medium":
                bg, fg = _AMBER_BG, _AMBER
            else:
                bg, fg = _BLUE_BG, _BLUE
            unusual_items.append((u_title, desc, severity, bg, fg))
    else:
        dr_rows = [r for r in all_rows if float(r.get("debit") or 0.0) > 0]
        if dr_rows:
            max_dr = max(dr_rows, key=lambda r: float(r.get("debit") or 0.0))
            dt_str = _fmt_date(max_dr["date"])
            unusual_items.append(("Large Debit Alert", f"Rs.{float(max_dr['debit']):,.0f} | {dt_str}", "High", _RED_BG, _RED))
        cr_rows = [r for r in all_rows if float(r.get("credit") or 0.0) > 0]
        if cr_rows:
            max_cr = max(cr_rows, key=lambda r: float(r.get("credit") or 0.0))
            dt_str = _fmt_date(max_cr["date"])
            unusual_items.append(("Large Credit Alert", f"Rs.{float(max_cr['credit']):,.0f} | {dt_str}", "Medium", _AMBER_BG, _AMBER))
        counts_by_day = defaultdict(int)
        for r in all_rows:
            d_str = str(r.get("date"))[:10]
            counts_by_day[d_str] += 1
        if counts_by_day:
            max_day, max_cnt = max(counts_by_day.items(), key=lambda x: x[1])
            unusual_items.append(("Peak Txn Volume Day", f"{max_cnt} txns | {_fmt_date(max_day)}", "Medium", _AMBER_BG, _AMBER))

    # Assemble Page 2
    elements.append(Paragraph(
        f"Visual Analytics \u2022 Financial Intelligence \u2022 Generated {generated_dt.strftime('%B %d, %Y')}",
        styles["ReportSubTitle"],
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=PDF_GREY_LINE, spaceBefore=2, spaceAfter=6))
    elements.append(Paragraph("Transaction Visualizations \u2014 Trends & Activity, Insights & Exposures", styles["VisualAnalyticsTitle"]))
    elements.append(Spacer(1, 4))

    # Row 1 (Income vs Expense & Balance Trend)
    c1 = _draw_income_vs_expense(card_w, card_h, monthly_data)
    c2 = _draw_balance_trend(card_w, card_h, bal_points, None)
    row1 = Table([[c1, c2]], colWidths=[card_w, card_w])
    row1.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(row1)
    elements.append(Spacer(1, 6))

    # Row 2 (Expense by Category & Top Income Sources)
    c3 = _draw_expense_by_category(card_w, card_h, cat_list, combined_exclusions_str)
    c4 = _draw_top_ranked_card(card_w, card_h, "Top 5 Income Sources", top_income, _GREEN, combined_exclusions_str)
    row2 = Table([[c3, c4]], colWidths=[card_w, card_w])
    row2.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(row2)
    elements.append(Spacer(1, 6))

    # Row 3 (Payment Mode & Risk Alerts)
    c6, c6_h = _draw_unusual_txns_card(card_w, card_h, unusual_items)
    row3_h = max(card_h, c6_h)
    c5 = _draw_payment_mode_analysis(card_w, row3_h, a.get("payment_modes_credit") or cr_by_tag, a.get("payment_modes_debit") or dr_by_tag, a.get("total_credit", 0.0), a.get("total_debit", 0.0))
    
    row3 = Table([[c5, c6]], colWidths=[card_w, card_w])
    row3.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(row3)

    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=0.6, color=PDF_GREY_LINE, spaceAfter=4))
    elements.append(Paragraph(
        f"Report generated on {generated_dt.strftime('%B %d, %Y')} \u2022 iZone Analyzer \u2022 Computer-generated document",
        styles["Footer"],
    ))
    elements.append(CondPageBreak(2000))


