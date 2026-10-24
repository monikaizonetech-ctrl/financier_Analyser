import pdfplumber, re

pdf_path = 'uploads/937a137f-587a-477a-b67d-c63e43441e9a/gstr input.pdf'

def _sf(v):
    try:
        return float(str(v).replace(',', '').replace('%', '').strip() or 0)
    except:
        return 0.0

states = {}
with pdfplumber.open(pdf_path) as pdf:
    for page_idx in range(0, 12, 2):
        for p in [pdf.pages[page_idx], pdf.pages[page_idx+1]]:
            tbl = p.extract_tables()[0]
            hdr = tbl[0]
            m1 = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', hdr[2])
            m2 = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', hdr[7])
            p1 = f'{m1.group(1)} {m1.group(2)}'
            p2 = f'{m2.group(1)} {m2.group(2)}'
            
            for row in tbl[1:]:
                code = row[0].strip()
                name = row[1].strip()
                if code not in states:
                    states[code] = {'name': name, 'periods': {}}
                
                states[code]['periods'][p1] = {
                    'elig_raw': row[2], 'ontime_raw': row[3], 'late_raw': row[4], 'filed_raw': row[5], 'pct_raw': row[6],
                    'elig': _sf(row[2]), 'ontime': _sf(row[3]), 'late': _sf(row[4]), 'filed': _sf(row[5]), 'pct': _sf(row[6])
                }
                states[code]['periods'][p2] = {
                    'elig_raw': row[7], 'ontime_raw': row[8], 'late_raw': row[9], 'filed_raw': row[10], 'pct_raw': row[11],
                    'elig': _sf(row[7]), 'ontime': _sf(row[8]), 'late': _sf(row[9]), 'filed': _sf(row[10]), 'pct': _sf(row[11])
                }

print('=== STATE CODE 38 (Ladakh) ===')
for p, vals in states['38']['periods'].items():
    print(p, vals)

print('\n=== STATE CODE 97 (Other Territory) ===')
for p, vals in states['97']['periods'].items():
    print(p, vals)

print('\n=== ALL JURISDICTIONS LIST ===')
for c in sorted(states.keys(), key=lambda x: int(x)):
    s_raw = [states[c]['periods'][p]['elig_raw'] for p in states[c]['periods']]
    has_data = any(v and v != '-' and _sf(v) > 0 for v in s_raw)
    tot_f = sum(states[c]['periods'][p]['filed'] for p in states[c]['periods'])
    tot_e = sum(states[c]['periods'][p]['elig'] for p in states[c]['periods'])
    rate = (tot_f / tot_e * 100) if tot_e > 0 else None
    rate_str = f"{rate:.2f}%" if rate is not None else "N/A"
    print(f"Code {c:>2}: {states[c]['name']:<30} | HasData={str(has_data):<5} | Elig={tot_e:11,.0f} | Filed={tot_f:11,.0f} | Rate={rate_str}")

# Top 5 states by total filed
sorted_states = sorted(
    [s for s in states.items() if any(states[s[0]]['periods'][p]['elig'] > 0 for p in states[s[0]]['periods'])],
    key=lambda x: sum(x[1]['periods'][p]['filed'] for p in x[1]['periods']),
    reverse=True
)
print('\n=== TOP 5 STATES BY TOTAL FILED ===')
for idx, (c, data) in enumerate(sorted_states[:5], 1):
    tot_f = sum(data['periods'][p]['filed'] for p in data['periods'])
    tot_e = sum(data['periods'][p]['elig'] for p in data['periods'])
    rate = tot_f / tot_e * 100
    print(f"{idx}. Code {c:>2} {data['name']} - Total Filed: {tot_f:,.0f}, Eligible: {tot_e:,.0f}, Filing Rate: {rate:.2f}%")
