"""Derived statistics only; no fabricated charts or trend values."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import json

def summarize(rows, feedback, days):
    cutoff=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=days) if days else None
    rows=[r for r in rows if cutoff is None or r.created_at.replace(tzinfo=None)>=cutoff]
    counts=Counter(r.label for r in rows); languages=Counter(r.language for r in rows)
    activity=Counter(r.created_at.strftime('%Y-%m-%d') for r in rows)
    indicators=Counter()
    for row in rows:
        result=json.loads(row.result) if isinstance(row.result,str) else row.result
        indicators.update(reason for reason in result.get('reasons',[]) if not reason.startswith('No strong'))
    ids={r.id for r in rows}
    filtered=[f for f in feedback if f.scan_id in ids]
    return dict(counts=dict(counts),total=len(rows),avg=round(sum(r.score for r in rows)/len(rows)) if rows else 0,languages=list(languages.items()),activity=sorted(activity.items()),indicators=indicators.most_common(8),feedback_counts=Counter(f.verdict for f in filtered),recent=rows[:6],feedback_total=len(filtered),days=days)
