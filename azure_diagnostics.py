"""Sanitized connection checks. Never print keys, connection strings or driver errors."""
import argparse
import json
import config
from detector import translate

def configuration_status():
    import pyodbc
    drivers=pyodbc.drivers()
    return {'translator':'configured, not verified' if config.TRANSLATOR_KEY else 'not configured', 'translator_region':'configured' if config.TRANSLATOR_REGION else 'not configured', 'azure_sql':'configured, not verified' if config.SQL_CONNECTION else 'not configured', 'odbc_driver_18':'installed' if 'ODBC Driver 18 for SQL Server' in drivers else 'not installed'}

def check_sql():
    import pyodbc
    if not config.SQL_CONNECTION: return {'ok':False,'message':'Azure SQL is not configured. Follow AZURE_SETUP.md and set the encrypted connection string in .env.'}
    if 'ODBC Driver 18 for SQL Server' not in pyodbc.drivers(): return {'ok':False,'message':'Install Microsoft ODBC Driver 18 for SQL Server first.'}
    try:
        connection=pyodbc.connect(config.SQL_CONNECTION,timeout=10)
        try:
            row=connection.cursor().execute('SELECT 1').fetchone()
            return {'ok':bool(row and row[0]==1),'message':'Azure SQL connectivity verified. This check did not create tables or migrate data.'}
        finally: connection.close()
    except pyodbc.Error:
        return {'ok':False,'message':'Azure SQL connection failed. Check the server firewall, database name, authentication and encrypted connection settings. Credentials are not displayed.'}

def check_translator(credentials=None):
    try:
        output,language,translated=translate('नमस्ते। यह एक परीक्षण संदेश है।','hi',credentials)
        if not translated or not output: return {'ok':False,'message':'The service returned no translation.'}
        return {'ok':True,'message':'Azure Translator verified with a synthetic Hindi test message. No personal message was sent.'}
    except ValueError as error: return {'ok':False,'message':str(error)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Check configuration without showing secrets. Live flags contact Azure; the default is offline.')
    parser.add_argument('--translator',action='store_true');parser.add_argument('--sql',action='store_true')
    args=parser.parse_args(); report={'configuration':configuration_status()}
    if args.translator: report['translator_test']=check_translator()
    if args.sql: report['sql_test']=check_sql()
    print(json.dumps(report,indent=2))
    if any(not result['ok'] for name,result in report.items() if name.endswith('_test')): raise SystemExit(1)
