from datetime import date
from typing import List, Dict, Any

def calculate_repayment_capacity(
    all_rows: List[Dict[str, Any]], 
    start_date: date, 
    end_date: date,
    is_integrity_verified: bool,
    max_foir: float = 0.50,
    proposed_emi: float = None,
    statement_total_credit: float = None,
    statement_total_debit: float = None
) -> Dict[str, Any]:
    duration_days = (end_date - start_date).days + 1
    
    if duration_days < 28:
        return {
            "status": {
                "status_code": "InsufficientData",
                "title": "Limited Transaction History",
                "description": "Statement period is too short for reliable monthly analysis.",
                "reason": f"Duration is {duration_days} days (minimum 28 required).",
                "severity": "Warning"
            },
            "message": "Statement period is too short for reliable monthly analysis.",
            "analysis_months": round(duration_days / 30.436875, 1),
            "analysis_period_days": duration_days
        }

    months_exact = duration_days / 30.436875
    analysis_months = max(1.0, float(round(months_exact)) if abs(months_exact - round(months_exact)) < 0.15 else round(months_exact, 1))

    # Calculate raw totals from the provided rows
    raw_total_credit = round(sum(float(r.get("credit") or 0.0) for r in all_rows), 2)
    raw_total_debit = round(sum(float(r.get("debit") or 0.0) for r in all_rows), 2)

    # If statement totals are not provided, we fall back to raw totals (assuming extraction is perfect, or handled externally)
    total_verified_debits = statement_total_debit if statement_total_debit is not None else raw_total_debit
    total_verified_credits = statement_total_credit if statement_total_credit is not None else raw_total_credit

    # Determine validation status based on totals matching (if provided)
    repayment_status = "Calculated"
    if statement_total_credit is not None and abs(statement_total_credit - raw_total_credit) > 1.0:
        repayment_status = "REVIEW REQUIRED — Statement extraction totals do not match transaction totals."
    elif statement_total_debit is not None and abs(statement_total_debit - raw_total_debit) > 1.0:
        repayment_status = "REVIEW REQUIRED — Statement extraction totals do not match transaction totals."

    # Initialize tracking variables for exact ONE primary financial treatment per transaction
    total_verified_income = 0.0
    total_emi_paid = 0.0
    total_living_expenses = 0.0
    ignored_reversals = 0.0
    ignored_own_account = 0.0
    ignored_investments = 0.0
    unclassified_debits = 0.0
    unclassified_credits = 0.0

    _emi_kws = ("emi", "loan installment", "loan repayment", "loan", "loanemi", "equated monthly")
    _own_account_kws = ("internal", "own account", "transfer to own", "self")
    _reversal_kws = ("refund", "reversal", "bounce", "return", "dishonour")
    _investment_kws = ("investment", "fd", "fixed deposit", "mutual fund", "sip", "stocks", "shares")

    classified_transactions = []

    _income_kws = ("salary", "wage", "payroll", "stipend", "interest", "dividend", "credita", "bonus", "incentive", "upi")
    _expense_kws = ("food", "fuel", "grocery", "amazon", "swiggy", "zomato", "restaurant", "mart", "supermarket", "medical", "pharmacy", "bill", "recharge", "airtel", "jio", "electricity", "water", "rent", "atm", "pos", "petrol", "diesel")

    for r in all_rows:
        credit = float(r.get("credit") or 0.0)
        debit = float(r.get("debit") or 0.0)
        desc = (r.get("description") or "").lower()
        cat = (r.get("category") or "").lower()
        date_val = r.get("date", "")
        
        c_class = "UNCLASSIFIED"
        c_reason = "No matching patterns"

        if credit > 0:
            if any(kw in desc for kw in _reversal_kws):
                ignored_reversals += credit
                c_class = "IGNORED (REVERSAL)"
                c_reason = "Matched reversal keyword"
            elif any(kw in desc for kw in _own_account_kws) or "internal" in cat:
                ignored_own_account += credit
                c_class = "IGNORED (OWN ACCOUNT)"
                c_reason = "Matched internal transfer keyword"
            elif any(kw in desc for kw in ["loan"]) and not any(kw in desc for kw in _emi_kws):
                unclassified_credits += credit
                c_class = "UNCLASSIFIED CREDIT"
                c_reason = "Loan disbursal treated as unclassified"
            elif any(kw in desc for kw in _income_kws) or "income" in cat or "salary" in cat:
                total_verified_income += credit
                c_class = "VERIFIED INCOME"
                c_reason = "Matched income keyword or category"
            else:
                unclassified_credits += credit
                c_class = "UNCLASSIFIED CREDIT"
                c_reason = "Did not match any verified income pattern"
                
            classified_transactions.append({
                "date": date_val, "description": r.get("description", ""), 
                "amount": credit, "type": "CREDIT", "classification": c_class, "reason": c_reason
            })
        
        elif debit > 0:
            if any(kw in cat for kw in ("emi", "loan")) or any(kw in desc for kw in _emi_kws):
                total_emi_paid += debit
                c_class = "EMI OBLIGATION"
                c_reason = "Matched EMI/Loan keyword"
            elif any(kw in desc for kw in _own_account_kws) or "internal" in cat:
                ignored_own_account += debit
                c_class = "IGNORED (OWN ACCOUNT)"
                c_reason = "Matched internal transfer keyword"
            elif any(kw in desc for kw in _investment_kws) or "investment" in cat:
                ignored_investments += debit
                c_class = "IGNORED (INVESTMENT)"
                c_reason = "Matched investment keyword"
            elif any(kw in desc for kw in _reversal_kws):
                ignored_reversals += debit
                c_class = "IGNORED (REVERSAL)"
                c_reason = "Matched reversal keyword"
            elif any(kw in desc for kw in _expense_kws) or cat not in ("", "unclassified", "other"):
                total_living_expenses += debit
                c_class = "VERIFIED LIVING EXPENSE"
                c_reason = "Matched expense keyword or valid category"
            else:
                unclassified_debits += debit
                c_class = "UNCLASSIFIED DEBIT"
                c_reason = "Did not match verified living expense pattern"
                
            classified_transactions.append({
                "date": date_val, "description": r.get("description", ""), 
                "amount": debit, "type": "DEBIT", "classification": c_class, "reason": c_reason
            })

    # HARD LIMIT: Verified income cannot exceed total extracted credits
    if total_verified_income > raw_total_credit:
        return {
            "status": {
                "status_code": "ValidationFailed",
                "title": "Validation Failed",
                "description": "Verified income exceeds total extracted credits.",
                "reason": "Classification anomaly detected.",
                "severity": "Error"
            },
            "message": "Verified income exceeds total extracted credits. This indicates a classification bug."
        }

    # HARD LIMIT: Classified living expenses cannot exceed total extracted debits
    if total_living_expenses > raw_total_debit:
        return {
            "status": {
                "status_code": "ValidationFailed",
                "title": "Validation Failed",
                "description": "Classified living expenses exceed total extracted debits.",
                "reason": "Double counting or classification bug.",
                "severity": "Error"
            },
            "message": "Classified living expenses exceed total extracted debits. This indicates double counting or a classification bug."
        }

    average_monthly_income = round(total_verified_income / analysis_months, 2) if total_verified_income > 0 else None
    existing_emi = round(total_emi_paid / analysis_months, 2) if total_emi_paid > 0 else None
    average_monthly_living_expenses = round(total_living_expenses / analysis_months, 2)
    
    if average_monthly_income is not None and existing_emi is not None:
        net_disposable_income = round(average_monthly_income - existing_emi - average_monthly_living_expenses, 2)
    else:
        net_disposable_income = None
    
    if average_monthly_income is not None and existing_emi is not None:
        current_foir = round((existing_emi / average_monthly_income) * 100, 2)
    else:
        current_foir = None
        
    max_total_obligation = round(average_monthly_income * max_foir, 2) if average_monthly_income is not None else None
    
    if existing_emi is not None and max_total_obligation is not None:
        foir_based_additional_emi = round(max_total_obligation - existing_emi, 2)
        maximum_additional_emi = min(foir_based_additional_emi, net_disposable_income) if net_disposable_income is not None else 0.0
        if maximum_additional_emi < 0:
            maximum_additional_emi = 0.0
    else:
        foir_based_additional_emi = None
        maximum_additional_emi = None
        
    status = repayment_status
    if status == "Calculated":
        if unclassified_debits > 0 and unclassified_credits > 0:
            status = f"REVIEW REQUIRED — Credit and debit transaction classification incomplete. ₹{unclassified_credits:,.2f} of credits and ₹{unclassified_debits:,.2f} of debits remain unclassified."
        elif unclassified_debits > 0:
            status = f"REVIEW REQUIRED — Debit transaction classification incomplete. ₹{unclassified_debits:,.2f} remain unclassified."
        elif unclassified_credits > 0:
            status = f"REVIEW REQUIRED — Credit transaction classification incomplete. ₹{unclassified_credits:,.2f} remain unclassified."
        elif average_monthly_income is None and existing_emi is None:
            status = "REVIEW REQUIRED — Income classification incomplete; EMI not identified."
        elif average_monthly_income is None:
            status = "REVIEW REQUIRED — Verified income could not be established from classified transactions."
        elif existing_emi is None:
            status = "REVIEW REQUIRED — Existing EMI obligations could not be identified."
        elif net_disposable_income is not None and net_disposable_income < 0:
            status = "Insufficient disposable income"
            
    # Do not calculate repayment capacity until both credit and debit classification reconciliation passes
    if "REVIEW REQUIRED" in status or status == "Validation Failed":
        net_disposable_income = None
        current_foir = None
        max_total_obligation = None
        foir_based_additional_emi = None
        maximum_additional_emi = None
    
    projected_foir = None
    if proposed_emi is not None and existing_emi is not None and average_monthly_income is not None:
        projected_total_emi = existing_emi + proposed_emi
        projected_foir = round((projected_total_emi / average_monthly_income) * 100, 2)
        if status == "Calculated":
            if projected_foir <= (max_foir * 100):
                status = "Within configured FOIR limit"
            else:
                status = "Above configured FOIR limit"

    status_obj = {
        "status_code": "Excellent",
        "title": "Excellent Repayment Capacity",
        "description": "The applicant shows strong financial stability.",
        "reason": "Net Disposable Income is sufficient.",
        "severity": "Success"
    }

    if "REVIEW REQUIRED" in status:
        status_obj = {
            "status_code": "ReviewRequired",
            "title": "Manual Review Required",
            "description": "Transaction classification is incomplete or uncertain.",
            "reason": status,
            "severity": "Warning"
        }
    elif status == "Validation Failed":
        status_obj = {
            "status_code": "ValidationFailed",
            "title": "Validation Failed",
            "description": "Classification anomalies detected.",
            "reason": "Living expenses or income exceeds bounds.",
            "severity": "Error"
        }
    elif status == "Insufficient disposable income":
        status_obj = {
            "status_code": "HighRisk",
            "title": "Insufficient Disposable Income",
            "description": "Net disposable income is negative.",
            "reason": "Expenses and EMI exceed verified income.",
            "severity": "High"
        }
    elif status == "Within configured FOIR limit":
        status_obj = {
            "status_code": "Good",
            "title": "Good Repayment Capacity",
            "description": "Applicant is within the maximum FOIR limit.",
            "reason": "Proposed EMI fits within disposable income.",
            "severity": "Success"
        }
    elif status == "Above configured FOIR limit":
        status_obj = {
            "status_code": "HighRisk",
            "title": "High FOIR Risk",
            "description": "Proposed EMI pushes FOIR above maximum limit.",
            "reason": "Requested loan amount exceeds calculated capacity.",
            "severity": "High"
        }
        
    return {
        "verified_income": total_verified_income if total_verified_income > 0 else None,
        "verified_living_expenses": total_living_expenses,
        "average_monthly_income": average_monthly_income,
        "average_monthly_living_expenses": average_monthly_living_expenses,
        "existing_emi": existing_emi,
        "net_disposable_income": net_disposable_income,
        "current_foir": current_foir,
        "max_foir": max_foir * 100,
        "max_total_obligation": max_total_obligation,
        "foir_based_additional_emi": foir_based_additional_emi,
        "maximum_additional_emi": maximum_additional_emi,
        "proposed_emi": proposed_emi,
        "projected_foir": projected_foir,
        "status": status_obj,
        "analysis_months": analysis_months,
        "analysis_period_days": duration_days,
        "validation_metrics": {
            "raw_total_credit": raw_total_credit,
            "raw_total_debit": raw_total_debit,
            "statement_total_credit": statement_total_credit,
            "statement_total_debit": statement_total_debit,
            "total_verified_income": total_verified_income,
            "total_living_expenses": total_living_expenses,
            "total_emi_paid": total_emi_paid,
            "ignored_reversals": ignored_reversals,
            "ignored_own_account": ignored_own_account,
            "ignored_investments": ignored_investments,
            "unclassified_debits": unclassified_debits,
            "unclassified_credits": unclassified_credits,
            "classified_transactions": classified_transactions
        }
    }
