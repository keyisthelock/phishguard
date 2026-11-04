import requests
import pytest
from test_app import app,post
from azure_diagnostics import check_sql,configuration_status
from detector import translate

def test_offline_diagnostics_are_safe(monkeypatch):
    import config
    monkeypatch.setattr(config,'TRANSLATOR_KEY','private-placeholder-key')
    monkeypatch.setattr(config,'SQL_CONNECTION','private-placeholder-connection')
    status=configuration_status()
    assert 'private-placeholder' not in str(status)
    assert status['translator']=='configured, not verified'

def test_sql_unconfigured_does_not_connect(monkeypatch):
    import config,pyodbc
    monkeypatch.setattr(config,'SQL_CONNECTION','')
    monkeypatch.setattr(pyodbc,'connect',lambda *a,**kw:pytest.fail('Must not connect without configuration'))
    assert check_sql()['ok'] is False

@pytest.mark.parametrize('status,expected',[(401,'rejected the key'),(403,'denied'),(429,'quota')])
def test_translation_errors_never_expose_keys(monkeypatch,status,expected):
    response=requests.Response();response.status_code=status
    monkeypatch.setattr(requests,'post',lambda *a,**kw:response)
    with pytest.raises(ValueError) as error:
        translate('fictional','hi',{'key':'private-placeholder-key','region':'centralindia'})
    assert expected in str(error.value) and 'private-placeholder' not in str(error.value)

def test_connection_test_uses_session_credentials_and_csrf(app,monkeypatch):
    import azure_diagnostics
    c=app.test_client()
    assert c.post('/azure/test').status_code==400
    post(c,'/azure',key='test-placeholder-key-123456789',region='centralindia')
    calls=[]
    monkeypatch.setattr(azure_diagnostics,'check_translator',lambda credentials:(calls.append(credentials) or {'ok':True,'message':'Synthetic connection verified.'}))
    assert post(c,'/azure/test').status_code==302
    assert calls[0]['region']=='centralindia'
    page=c.get('/azure').data
    assert b'Synthetic connection verified' in page and b'test-placeholder-key' not in page
