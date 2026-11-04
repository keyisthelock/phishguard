import json
import pytest
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash
from app import create_app, User, Scan
from detector import analyze

@pytest.fixture
def app(tmp_path):
    app=create_app('sqlite:///'+str(tmp_path/'test.db'))
    app.config['TESTING']=True
    return app

def post(client,path,**data):
    client.get('/login')
    with client.session_transaction() as s: token=s['csrf']
    return client.post(path,data={'csrf':token,**data},follow_redirects=False)

def signup(client,name='tester'):
    assert post(client,'/register',username=name,password='test-password-2026').status_code==302
    assert post(client,'/login',username=name,password='test-password-2026').status_code==302

def test_full_flow(app):
    c=app.test_client(); signup(c)
    for path in ['/','/dashboard','/history','/integrations']:
        assert c.get(path).status_code==200
    r=post(c,'/',message='URGENT! Your bank account will be suspended. Verify your password and OTP at http://secure-bank-verify.xyz now.',language='en',save='yes',include_content='yes')
    assert r.status_code==200 and b'Phishing / scam' in r.data
    assert b'Saved to your history' in r.data
    assert b'secure-bank-verify' in c.get('/history').data
    assert c.get('/admin').status_code==403
    assert post(c,'/history/1/delete').status_code==302
    assert b'No saved scans yet' in c.get('/history').data

def test_authorization_and_csrf(app):
    c=app.test_client(); assert c.get('/history').status_code==200
    assert c.post('/register',data={}).status_code==400
    signup(c,'owner')
    post(c,'/',message='Meet me at the library tomorrow at noon.',language='en',save='yes')
    other=app.test_client(); signup(other,'other')
    assert b'Meet me at the library' not in other.get('/history').data
    assert post(other,'/history/1/delete').status_code==404
    assert post(other,'/',message='x',language='en').status_code==200
    assert b'between 3 and' in post(other,'/',message='x',language='en').data

def test_privacy_xss_and_unsaved(app):
    c=app.test_client(); signup(c)
    r=post(c,'/',message='<script>alert(1)</script> OTP 123456 sent to name@example.com',language='en',save='yes',include_content='yes')
    assert b'<script>alert(1)</script>' not in r.data
    h=c.get('/history'); assert b'123456' not in h.data and b'name@example.com' not in h.data
    assert b'&lt;script&gt;' in h.data
    post(c,'/',message='Please bring the slides tomorrow.',language='en')
    with Session(app.extensions['db_engine']) as db: assert len(db.query(Scan).all())==1

def test_admin_and_health(app):
    with Session(app.extensions['db_engine']) as db:
        db.add(User(username='admin',password_hash=generate_password_hash('admin-testing-password'),role='admin')); db.commit()
    c=app.test_client(); post(c,'/login',username='admin',password='admin-testing-password')
    assert c.get('/admin').status_code==200
    assert c.get('/health').json['status']=='ok'

def test_translation_adapter(monkeypatch):
    import detector
    monkeypatch.setattr(detector.config,'TRANSLATOR_KEY','test-placeholder')
    class Response:
        def raise_for_status(self): pass
        def json(self): return [{'detectedLanguage':{'language':'hi'},'translations':[{'text':'Share your OTP immediately'}]}]
    calls=[]
    monkeypatch.setattr(detector.requests,'post',lambda *a,**kw:(calls.append(kw) or Response()))
    text,lang,translated=detector.translate('नमस्ते','auto')
    assert lang=='hi' and translated and text=='Share your OTP immediately'
    assert calls[0]['params']['to']=='en'

def test_detection():
    assert analyze('URGENT: Your bank account will be blocked. Verify your password and OTP immediately at http://bank-verify.xyz')['score']>=65
    assert analyze('Hi, let us meet at the library tomorrow to discuss our project.')['label']=='Likely safe'
    assert analyze('Check http://127.0.0.1/path')['urls'][0]['flags']

def test_guest_scan_cannot_save_or_access_accounts(app):
    c=app.test_client()
    assert b'Continue as guest' in c.get('/login').data
    assert c.get('/').status_code==200
    r=post(c,'/',message='URGENT! Share your OTP and password immediately to verify your bank account.',language='en',save='yes')
    assert r.status_code==200 and b'Phishing / scam' in r.data
    assert b'Added to temporary history.' in r.data
    with Session(app.extensions['db_engine']) as db: assert db.query(Scan).count()==0
    for path in ['/history','/dashboard','/azure','/integrations']:
        assert c.get(path).status_code==200
    assert c.get('/admin').status_code==302
    other=app.test_client()
    assert b'Share your OTP' not in other.get('/history').data

def test_azure_session_settings(app):
    c=app.test_client()
    assert post(c,'/azure',key='short',region='centralindia').status_code==400
    secret='test-placeholder-key-123456789'
    assert post(c,'/azure',key=secret,region='centralindia').status_code==302
    page=c.get('/azure').data
    assert b'Configured' in page and secret.encode() not in page
    with c.session_transaction() as s: assert secret not in str(dict(s))
    assert b'Not connected' in app.test_client().get('/azure').data
    assert post(c,'/azure',action='disconnect').status_code==302
    assert b'Not connected' in c.get('/azure').data

def test_guest_history_delete_and_dashboard(app):
    c=app.test_client()
    post(c,'/',message='Meet me at the library tomorrow.',language='en',include_content='yes')
    assert b'Meet me at the library' in c.get('/history').data
    assert b'Temporary guest activity' in c.get('/dashboard').data
    import re
    scan_id=re.search(rb'/history/(\d+)/delete',c.get('/history').data).group(1).decode()
    assert post(c,f'/history/{scan_id}/delete').status_code==302
    assert b'No saved scans yet' in c.get('/history').data
