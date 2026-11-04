import os
import json
import secrets
import functools
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque, OrderedDict
from types import SimpleNamespace
from urllib.parse import quote_plus
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from sqlalchemy import create_engine, select, func, event
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash
import config
from detector import analyze, translate, redact

from models_db import Base, User, Scan, DetectionResult, WarningIndicator, Feedback, SchemaVersion
from migrations import migrate
from analytics import summarize

def create_app(database_url=None):
    app=Flask(__name__)
    instance=config.ROOT/'instance'; instance.mkdir(exist_ok=True)
    secret=os.getenv('SECRET_KEY')
    if not secret:
        path=instance/'session.key'
        if not path.exists(): path.write_text(secrets.token_hex(32))
        secret=path.read_text()
    app.config.update(SECRET_KEY=secret,MAX_CONTENT_LENGTH=24000,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','false').lower()=='true',PERMANENT_SESSION_LIFETIME=timedelta(hours=2))
    cloud=bool(config.SQL_CONNECTION) and database_url is None
    uri=database_url or ('mssql+pyodbc:///?odbc_connect='+quote_plus(config.SQL_CONNECTION) if cloud else 'sqlite:///'+str(instance/'phishguard.db'))
    engine=create_engine(uri,pool_pre_ping=True)
    if uri.startswith('sqlite'):
        @event.listens_for(engine,'connect')
        def enable_fk(connection, _): connection.execute('PRAGMA foreign_keys=ON')
    migrate(engine)
    app.extensions['db_engine']=engine
    attempts=OrderedDict()
    guest_records=OrderedDict()
    azure_credentials=OrderedDict()
    scan_limits=OrderedDict()

    def browser_id():
        session.setdefault('browser_id',secrets.token_hex(24))
        return session['browser_id']

    def guest_rows():
        key=browser_id()
        if key not in guest_records:
            if len(guest_records)>=500: guest_records.popitem(last=False)
            guest_records[key]=deque(maxlen=25)
        guest_records.move_to_end(key)
        return guest_records[key]

    def protect(admin=False):
        def decorator(fn):
            @functools.wraps(fn)
            def wrapped(*args,**kwargs):
                with Session(engine) as db: user=db.get(User,session.get('user_id')) if session.get('user_id') else None
                if not user: return redirect(url_for('login'))
                if admin and user.role!='admin': abort(403)
                return fn(*args,**kwargs)
            return wrapped
        return decorator

    @app.before_request
    def csrf():
        session.setdefault('csrf',secrets.token_hex(24))
        if request.method=='POST' and request.endpoint in {'index','register','feedback','test_azure'}:
            rate_key=(request.remote_addr,request.endpoint)
            now=datetime.now(timezone.utc).timestamp()
            if rate_key not in scan_limits:
                if len(scan_limits)>=2000: scan_limits.popitem(last=False)
                scan_limits[rate_key]=deque()
            bucket=scan_limits[rate_key]
            while bucket and bucket[0]<now-60: bucket.popleft()
            if len(bucket)>=(10 if request.endpoint=='register' else 30): abort(429,'Too many requests. Please wait a minute.')
            bucket.append(now)
        if request.method=='POST' and not secrets.compare_digest(session['csrf'],request.form.get('csrf','')): abort(400,'Invalid form token. Reload the page.')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        response.headers['Cache-Control']='no-store'
        return response

    @app.context_processor
    def context():
        with Session(engine) as db: user=db.get(User,session.get('user_id')) if session.get('user_id') else None
        return {'current_user':user,'azure_sql':cloud,'translator_ready':bool(config.TRANSLATOR_KEY or azure_credentials.get(browser_id())),'csrf_token':session.get('csrf','')}

    @app.route('/login',methods=['GET','POST'])
    def login():
        if request.method=='POST':
            key=request.remote_addr; now=datetime.now(timezone.utc).timestamp()
            if key not in attempts:
                if len(attempts)>=2000: attempts.popitem(last=False)
                attempts[key]=deque()
            while attempts[key] and attempts[key][0]<now-300: attempts[key].popleft()
            if len(attempts[key])>=10: return render_template('auth.html',error='Too many attempts. Wait five minutes.',mode='login'),429
            attempts[key].append(now)
            with Session(engine) as db: user=db.scalar(select(User).where(User.username==request.form.get('username','').strip().lower()))
            if user and check_password_hash(user.password_hash,request.form.get('password','')):
                session.clear(); session.update(user_id=user.id,csrf=secrets.token_hex(24)); session.permanent=True
                attempts[key].clear(); return redirect(url_for('index'))
            return render_template('auth.html',mode='login',error='Username or password is incorrect.'),401
        return render_template('auth.html',mode='login')

    @app.route('/register',methods=['GET','POST'])
    def register():
        if request.method=='POST':
            import re
            username=request.form.get('username','').strip().lower(); password=request.form.get('password','')
            if not re.fullmatch(r'[a-z0-9_]{3,40}',username) or not 8<=len(password)<=128:
                return render_template('auth.html',mode='register',error='Use a 3–40 character username (letters, numbers, underscore) and an 8–128 character password.'),400
            from sqlalchemy.exc import IntegrityError
            try:
                with Session(engine) as db:
                    db.add(User(username=username,password_hash=generate_password_hash(password),role='user')); db.commit()
            except IntegrityError: return render_template('auth.html',mode='register',error='That username is already registered.'),409
            flash('Account created. Sign in to begin.'); return redirect(url_for('login'))
        return render_template('auth.html',mode='register')

    @app.post('/logout')
    def logout(): session.clear(); return redirect(url_for('login'))

    @app.post('/guest')
    def guest():
        session.clear()
        session['csrf']=secrets.token_hex(24)
        return redirect(url_for('index'))

    @app.route('/',methods=['GET','POST'])
    def index():
        result=None; message=''; error=None
        if request.method=='POST':
            mode=request.form.get('mode','message')
            message=request.form.get('url' if mode=='url' else 'message','').strip(); language=request.form.get('language','en') if mode=='message' else 'en'
            if mode not in {'message','url'}: abort(400,'Unknown scanner mode.')
            if not 3<=len(message)<=5000: error='Enter between 3 and 5,000 characters.'
            elif language not in {'en','auto','hi','mr','ta','te','bn','gu','kn','ml','ur','es','fr'}: error='Unsupported language selection.'
            else:
                try:
                    english,detected,translated=translate(message,language,azure_credentials.get(browser_id()))
                    result=analyze(english,mode)
                    result.update(translated=translated,language=detected,english=english if translated else None,analyzed_at=datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC'))
                    stored={**result,'english':None,'segments':[],'urls':[{**u,'url':u['scheme']+'://'+u['host'],'path':'[not retained]','query_keys':[]} for u in result['urls']]}
                    stored.pop('analyzed_at',None)
                    preview=redact(message) if request.form.get('include_content')=='yes' else 'Content not retained'
                    if session.get('user_id') and request.form.get('save')=='yes':
                        with Session(engine) as db:
                            row=Scan(user_id=session['user_id'],message=preview,result=json.dumps(stored),label=result['label'],score=result['score'],language=detected)
                            db.add(row); db.flush()
                            db.add(DetectionResult(scan_id=row.id,mode=mode,ml_score=round(result['ml_score']) if result['ml_score'] is not None else None,rule_score=result['rule_score']))
                            for reason in result['reasons']:
                                if not reason.startswith('No strong'): db.add(WarningIndicator(scan_id=row.id,description=reason[:255]))
                            db.commit(); result['scan_id']=row.id
                        result['saved']=True
                    elif not session.get('user_id'):
                        rows=guest_rows(); scan_id=secrets.randbelow(2**48)
                        rows.appendleft(SimpleNamespace(id=scan_id,message=preview,result=stored,label=result['label'],score=result['score'],language=detected,created_at=datetime.now(timezone.utc).replace(tzinfo=None),feedback=None))
                        result.update(guest_saved=True,scan_id=scan_id)
                except ValueError as exc: error=str(exc)
        return render_template('scan.html',result=result,message=message,error=error)

    @app.get('/history')
    def history():
        if not session.get('user_id'):
            return render_template('history.html',rows=list(guest_rows()),guest_mode=True)
        with Session(engine) as db:
            rows=db.scalars(select(Scan).where(Scan.user_id==session['user_id']).order_by(Scan.id.desc()).limit(100)).all()
        return render_template('history.html',rows=rows)

    @app.post('/history/<int:scan_id>/delete')
    def delete_scan(scan_id):
        if not session.get('user_id'):
            rows=guest_rows()
            row=next((r for r in rows if r.id==scan_id),None)
            if not row: abort(404)
            rows.remove(row)
            return redirect(url_for('history'))
        with Session(engine) as db:
            row=db.get(Scan,scan_id)
            if not row or row.user_id!=session['user_id']: abort(404)
            for model in [Feedback,WarningIndicator,DetectionResult]:
                from sqlalchemy import delete
                db.execute(delete(model).where(model.scan_id==scan_id))
            db.delete(row); db.commit()
        flash('Scan deleted.'); return redirect(url_for('history'))

    @app.get('/dashboard')
    def dashboard(): return dashboard_view(False)

    @app.get('/admin')
    @protect(admin=True)
    def admin(): return dashboard_view(True)

    def dashboard_view(all_users):
        try: days=int(request.args.get('days','30'))
        except ValueError: days=30
        if days not in {0,7,30,90}: days=30
        guest=not session.get('user_id') and not all_users
        with Session(engine) as db:
            rows=list(guest_rows()) if guest else db.scalars(select(Scan).where(*([] if all_users else [Scan.user_id==session['user_id']])).order_by(Scan.id.desc())).all()
            feedback=[] if guest else db.scalars(select(Feedback).where(*([] if all_users else [Feedback.user_id==session['user_id']]))).all()
            if guest:
                feedback=[SimpleNamespace(scan_id=r.id,verdict=r.feedback) for r in rows if r.feedback]
            users=db.scalar(select(func.count(User.id))) if all_users else None
            reviews=db.scalars(select(Feedback).order_by(Feedback.created_at.desc()).limit(50)).all() if all_users else []
        return render_template('dashboard.html',**summarize(rows,feedback,days),users=users,admin_view=all_users,guest_mode=guest,reviews=reviews)

    def owned_scan(scan_id, db):
        if not session.get('user_id'):
            row=next((r for r in guest_rows() if r.id==scan_id),None)
        else:
            row=db.get(Scan,scan_id)
            if row and row.user_id!=session['user_id']: row=None
        if not row: abort(404)
        return row

    @app.get('/history/<int:scan_id>')
    def scan_detail(scan_id):
        with Session(engine) as db:
            row=owned_scan(scan_id,db)
            result=json.loads(row.result) if isinstance(row.result,str) else dict(row.result)
            result.update(scan_id=row.id,analyzed_at=row.created_at.strftime('%d %b %Y, %H:%M UTC'))
        return render_template('scan_detail.html',row=row,result=result)

    @app.post('/feedback/<int:scan_id>')
    def feedback(scan_id):
        verdict=request.form.get('verdict')
        if verdict not in {'correct','false_positive','false_negative'}: abort(400,'Choose a feedback option.')
        with Session(engine) as db:
            row=owned_scan(scan_id,db)
            if session.get('user_id'):
                item=db.get(Feedback,scan_id)
                if not item: item=Feedback(scan_id=scan_id,user_id=session['user_id']); db.add(item)
                item.verdict=verdict; item.note=redact(request.form.get('note','')[:400]); item.reviewed=0; db.commit()
            else: row.feedback=verdict
        flash('Feedback saved. Reports are reviewed before any model changes.')
        return redirect(url_for('scan_detail',scan_id=scan_id))

    @app.post('/admin/feedback/<int:scan_id>/review')
    @protect(admin=True)
    def review_feedback(scan_id):
        with Session(engine) as db:
            item=db.get(Feedback,scan_id)
            if not item: abort(404)
            item.reviewed=1; db.commit()
        flash('Feedback marked reviewed.'); return redirect(url_for('admin'))

    @app.post('/history/clear')
    def clear_history():
        with Session(engine) as db:
            if session.get('user_id'):
                ids=select(Scan.id).where(Scan.user_id==session['user_id'])
                from sqlalchemy import delete
                for model in [Feedback,WarningIndicator,DetectionResult]: db.execute(delete(model).where(model.scan_id.in_(ids)))
                db.execute(delete(Scan).where(Scan.user_id==session['user_id'])); db.commit()
            else: guest_rows().clear()
        flash('Your scan history has been cleared.'); return redirect(url_for('history'))

    @app.get('/history/export.csv')
    def export_history():
        import csv,io
        from flask import Response
        with Session(engine) as db:
            rows=list(guest_rows()) if not session.get('user_id') else db.scalars(select(Scan).where(Scan.user_id==session['user_id']).order_by(Scan.id.desc())).all()
        output=io.StringIO(newline=''); writer=csv.writer(output)
        writer.writerow(['Scan ID','Assessment','Risk','Language','UTC','Redacted preview'])
        for r in rows:
            preview=r.message
            if preview.lstrip().startswith(('=','+','-','@')): preview="'"+preview
            writer.writerow([r.id,r.label,r.score,r.language,r.created_at.isoformat(),preview])
        return Response(output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=phishguard-history.csv'})

    @app.get('/learn')
    def learn():
        from learning import LESSONS
        return render_template('learn.html',lessons=LESSONS)

    @app.get('/challenge')
    def challenge():
        from learning import CHALLENGES
        return render_template('challenge.html',challenges=CHALLENGES)

    @app.get('/privacy')
    def privacy(): return render_template('privacy.html')

    @app.route('/azure',methods=['GET','POST'])
    def azure():
        key_id=browser_id()
        if request.method=='POST':
            if request.form.get('action')=='disconnect':
                azure_credentials.pop(key_id,None)
                flash('Your Azure key has been removed from this session.')
            else:
                key=request.form.get('key','').strip()
                region=request.form.get('region','').strip().lower()
                import re
                if not 16<=len(key)<=256 or not re.fullmatch(r'[a-z0-9-]{2,40}',region):
                    return render_template('azure.html',error='Enter a valid resource key and region.',configured=key_id in azure_credentials),400
                if len(azure_credentials)>=500 and key_id not in azure_credentials: azure_credentials.popitem(last=False)
                azure_credentials[key_id]={'key':key,'region':region}
                flash('Azure settings saved for this session. Try a translated scan to verify the connection.')
            return redirect(url_for('azure'))
        return render_template('azure.html',configured=key_id in azure_credentials)

    @app.get('/integrations')
    def integrations():
        metrics=json.loads((config.ROOT/'models/metrics.json').read_text())
        return render_template('integrations.html',metrics=metrics,model_date=datetime.fromtimestamp((config.ROOT/'models/detector.joblib').stat().st_mtime,timezone.utc).strftime('%d %b %Y UTC'))

    @app.post('/azure/test')
    def test_azure():
        from azure_diagnostics import check_translator
        outcome=check_translator(azure_credentials.get(browser_id()))
        flash(outcome['message'])
        return redirect(url_for('azure'))

    @app.get('/health')
    def health():
        try:
            with engine.connect() as conn: conn.execute(select(1))
            return jsonify(status='ok',database='azure-sql' if cloud else 'sqlite')
        except Exception: return jsonify(status='unavailable'),503

    @app.cli.command('create-admin')
    def create_admin():
        import click
        username=click.prompt('Admin username').strip().lower()
        password=click.prompt('Admin password',hide_input=True,confirmation_prompt=True)
        if len(password)<8 or len(username)>40 or not username: raise click.ClickException('Use a username and a password of at least 8 characters.')
        with Session(engine) as db:
            if db.scalar(select(User).where(User.username==username)): raise click.ClickException('Username already exists.')
            db.add(User(username=username,password_hash=generate_password_hash(password),role='admin')); db.commit()
        click.echo('Administrator created.')

    @app.errorhandler(429)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(400)
    @app.errorhandler(413)
    def error_page(error): return render_template('error.html',error=error),error.code
    @app.errorhandler(500)
    def server_error(error): return render_template('error.html',error=SimpleNamespace(code=500,description='The request could not be completed. Please retry. Your credentials are not shown.')),500
    return app

if __name__=='__main__':
    from waitress import serve
    serve(create_app(),host='127.0.0.1',port=int(os.getenv('PORT','5000')))
