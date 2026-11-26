# -*- coding: utf-8 -*-
import csv, re
from pathlib import Path
H = Path(__file__).resolve().parent
rows = []
for line in (H / 'ratings_raw.txt').read_text(encoding='utf-8').splitlines():
    if not line.strip():
        continue
    item, rater, body = line.split('|', 2)
    d = dict(kv.split('=', 1) for kv in [x.strip() for x in body.split(';')] if '=' in kv)
    rows.append({'item': item, 'rater': rater, **d})
rows.sort(key=lambda r: (r['item'], r['rater']))
f = ['item', 'rater', 'pick', 'tech_X', 'tech_Y', 'read_X', 'read_Y', 'ai_X', 'ai_Y', 'reason']
with (H / 'ratings.csv').open('w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=f); w.writeheader(); w.writerows(rows)
print(len(rows))
