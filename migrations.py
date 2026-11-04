"""Additive, restart-safe v2 migration for SQLite and Azure SQL."""
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from models_db import Base, Scan, DetectionResult, WarningIndicator, SchemaVersion

def migrate(engine):
    Base.metadata.create_all(engine)
    for index in Scan.__table__.indexes: index.create(engine,checkfirst=True)
    with Session(engine) as db:
        if db.get(SchemaVersion,2): return
        for scan in db.scalars(select(Scan)).all():
            if db.get(DetectionResult,scan.id): continue
            try: result=json.loads(scan.result)
            except (TypeError,ValueError): result={}
            ml=result.get('ml_score')
            db.add(DetectionResult(scan_id=scan.id,mode=result.get('mode','message'),ml_score=round(ml) if ml is not None else None,rule_score=result.get('rule_score',0)))
            for reason in result.get('reasons',[]):
                if not reason.startswith('No strong'): db.add(WarningIndicator(scan_id=scan.id,description=reason[:255]))
        db.add(SchemaVersion(version=2)); db.commit()
