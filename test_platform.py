import json
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select
from models_db import Scan, Feedback, DetectionResult, WarningIndicator, User
from test_app import app,post,signup
from url_analysis import inspect_url
from migrations import migrate
from werkzeug.security import generate_password_hash

@pytest.mark.parametrize('url',['javascript:alert(1)','file:///etc/passwd','https://','https://bad host.example','https://bad.example:wrong','https://-bad.example','http://[invalid'])
def test_url_rejects_unsafe_or_invalid(url):
    with pytest.raises(ValueError): inspect_url(url)

def test_url_is_offline_and_structural(monkeypatch):
    import requests
    monkeypatch.setattr(requests,'get',lambda *a,**kw:pytest.fail('Must not fetch URL'))
    item=inspect_url('https://paypal-login.example/path?token=fictional')
    assert item['host']=='paypal-login.example' and item['path']=='/path'
    assert 'token' in item['query_keys'] and any('lookalike' in r for r in item['flags'])
    assert inspect_url('example.com')['scheme']=='https'

def test_url_scan_and_default_privacy(app):
    c=app.test_client(); signup(c)
    r=post(c,'/',mode='url',url='http://paypal-login.example/path?token=not-a-real-secret',save='yes')
    assert r.status_code==200 and b'Not used' in r.data
    with Session(app.extensions['db_engine']) as db:
        row=db.scalar(select(Scan)); result=db.get(DetectionResult,row.id)
        assert row.message=='Content not retained'
        assert 'not-a-real-secret' not in row.result
        assert result.mode=='url' and result.ml_score is None
        assert db.query(WarningIndicator).count()>0

def test_feedback_ownership_review_and_cascade(app):
    c=app.test_client();signup(c)
    post(c,'/',message='Please share your OTP immediately.',language='en',save='yes')
    assert post(c,'/feedback/1',verdict='false_negative',note='Please review').status_code==302
    other=app.test_client();signup(other,'other')
    assert other.get('/history/1').status_code==404
    assert post(other,'/feedback/1',verdict='correct').status_code==404
    assert post(other,'/admin/feedback/1/review').status_code==403
    with Session(app.extensions['db_engine']) as db:
        db.add(User(username='reviewer',password_hash=generate_password_hash('review-password'),role='admin'));db.commit()
    admin=app.test_client();post(admin,'/login',username='reviewer',password='review-password')
    assert post(admin,'/admin/feedback/1/review').status_code==302
    with Session(app.extensions['db_engine']) as db: assert db.get(Feedback,1).reviewed==1
    assert post(c,'/history/1/delete').status_code==302
    with Session(app.extensions['db_engine']) as db:
        assert db.query(Feedback).count()==db.query(DetectionResult).count()==db.query(WarningIndicator).count()==0

def test_analytics_filter_and_csv(app):
    c=app.test_client();signup(c)
    post(c,'/',message='Hi, meet at the library tomorrow.',save='yes',language='en')
    post(c,'/',message='Urgent! Share your password and OTP immediately.',save='yes',language='en')
    with Session(app.extensions['db_engine']) as db:
        db.get(Scan,1).created_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=50);db.commit()
    from analytics import summarize
    with Session(app.extensions['db_engine']) as db:
        data=summarize(db.scalars(select(Scan)).all(),[],7)
        assert data['total']==1 and len(data['activity'])==1
    csv=c.get('/history/export.csv')
    assert csv.status_code==200 and b'Content not retained' in csv.data
    assert b'Content not retained' in c.get('/history/1').data
    assert post(c,'/history/clear').status_code==302
    with Session(app.extensions['db_engine']) as db: assert db.query(Scan).count()==0

def test_learning_and_rate_limit(app):
    c=app.test_client()
    for path in ['/learn','/challenge','/privacy']:
        assert c.get(path).status_code==200
    c.get('/')
    with c.session_transaction() as s: token=s['csrf']
    for _ in range(30): assert c.post('/',data={'csrf':token,'message':'x'}).status_code==200
    assert c.post('/',data={'csrf':token,'message':'x'}).status_code==429

def test_migration_repeatable(app):
    migrate(app.extensions['db_engine']); migrate(app.extensions['db_engine'])
    with Session(app.extensions['db_engine']) as db:
        from models_db import SchemaVersion
        assert db.query(SchemaVersion).count()==1
