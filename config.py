"""Customer-owned credentials: environment / local .env only, never browser code."""
import os
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
TRANSLATOR_KEY = os.getenv('AZURE_TRANSLATOR_KEY', '')
TRANSLATOR_REGION = os.getenv('AZURE_TRANSLATOR_REGION', '')
TRANSLATOR_ENDPOINT = os.getenv('AZURE_TRANSLATOR_ENDPOINT', 'https://api.cognitive.microsofttranslator.com').rstrip('/')
SQL_CONNECTION = os.getenv('AZURE_SQL_CONNECTION_STRING', '')
