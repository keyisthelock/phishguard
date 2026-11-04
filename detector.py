import re
import ipaddress
from urllib.parse import urlsplit
import joblib
import requests
import config
from url_analysis import inspect_url

MODEL = None
def translate(message, language, credentials=None):
    if language == 'en': return message, 'en', False
    key=(credentials or {}).get('key') or config.TRANSLATOR_KEY
    region=(credentials or {}).get('region') or config.TRANSLATOR_REGION
    if not key:
        raise ValueError('Translation is not connected. Open Azure settings to add your key, or choose English.')
    headers = {'Ocp-Apim-Subscription-Key':key,'Content-Type':'application/json'}
    if region: headers['Ocp-Apim-Subscription-Region'] = region
    params = {'api-version':'3.0','to':'en'}
    if language != 'auto': params['from'] = language
    try:
        response = requests.post(config.TRANSLATOR_ENDPOINT+'/translate',params=params,headers=headers,json=[{'Text':message}],timeout=(5,15))
        response.raise_for_status()
        body = response.json()[0]
        return body['translations'][0]['text'], body.get('detectedLanguage',{}).get('language',language), True
    except requests.HTTPError as error:
        code=error.response.status_code if error.response is not None else None
        messages={401:'Azure rejected the key. Check the Translator resource key and region.',403:'Azure denied this request. Check the resource region, permissions and subscription.',429:'Azure translation quota or rate limit reached. Wait and check your resource usage.'}
        raise ValueError(messages.get(code,'Azure translation service could not complete the request. Retry shortly.')) from None
    except requests.Timeout:
        raise ValueError('Azure translation timed out. Check your connection and retry.') from None
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        raise ValueError('Azure translation failed. Check the resource key, region, endpoint and network, then retry.') from None

def analyze(message, mode='message'):
    global MODEL
    if MODEL is None: MODEL = joblib.load(config.ROOT/'models/detector.joblib')
    probability = float(MODEL.predict_proba([message])[0][1]) if mode=='message' else None
    reasons=[]
    patterns = [(r'\b(urgent|immediately|within \d+ hours?|account.{0,15}(blocked|suspended)|act now)\b','Urgency or account suspension pressure',18), (r'\b(otp|password|pin|cvv|credentials)\b','Sensitive credential or verification-code request',22), (r'\b(won|lottery|prize|free money|reward|claim.{0,15}(cash|gift))\b','Prize or reward lure',18), (r'\b(transfer|pay|payment|bank|upi|kyc|verify.{0,15}account)\b','Financial or account-verification language',10)]
    rule_score=0
    for pattern,reason,weight in patterns:
        if mode=='message' and re.search(pattern,message,re.I): reasons.append(reason); rule_score+=weight
    urls=[]
    for raw in ([message] if mode=='url' else re.findall(r'(?:https?://|www\.)[^\s<>"\']+',message,re.I)):
        raw=raw.rstrip('.,;!?)')
        try: item=inspect_url(raw)
        except ValueError:
            if mode=='url': raise
            reasons.append('Malformed link: verify its spelling and destination'); rule_score+=15; continue
        urls.append(item)
        rule_score+=item['rule_score']; reasons.extend(item['flags'])
    rule_score=min(96,rule_score)
    score=round(max((probability or 0)*100,rule_score))
    label='Phishing / scam' if score>=65 else 'Suspicious' if score>=35 else 'Likely safe'
    segments=[]; cursor=0
    if mode=='message':
        for match in re.finditer('|'.join(p[0] for p in patterns),message,re.I):
            if match.start()>cursor: segments.append({'text':message[cursor:match.start()],'marked':False})
            segments.append({'text':match.group(),'marked':True});cursor=match.end()
        segments.append({'text':message[cursor:],'marked':False})
    techniques=[]
    if any('Urgency' in r for r in reasons): techniques.append('Pressure tactic: a deadline reduces time to verify the sender.')
    if any('credential' in r for r in reasons): techniques.append('Credential harvesting: a request for secrets can lead to account takeover.')
    if any('Prize' in r for r in reasons): techniques.append('Reward lure: an unexpected benefit can prompt risky payments or clicks.')
    if any('lookalike' in r or 'impersonation' in r for r in reasons): techniques.append('Brand impersonation: a familiar name can disguise an unrelated domain.')
    return {'label':label,'score':score,'ml_score':round(probability*100,1) if probability is not None else None,'rule_score':rule_score,'mode':mode,'segments':segments,'techniques':techniques,'reasons':list(dict.fromkeys(reasons)) or ['No strong rule-based warning signs found; consider sender identity and context.'],'urls':urls,'recommendation':'Do not share credentials or follow payment instructions. Verify through the official app or a known contact.' if score>=35 else 'Verify the sender and destination before acting. A low score does not guarantee safety.'}

def redact(text):
    text=re.sub(r'(https?://)[^/\s@]+@',r'\1[credentials hidden]@',text)
    text=re.sub(r'(?i)\b(password|otp|pin|cvv|token|secret)\s*[:=]\s*\S+',r'\1: [hidden]',text)
    text=re.sub(r'(https?://[^\s?#]+)[?#][^\s]*',r'\1?[details hidden]',text)
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email hidden]', text)
    return re.sub(r'\b\d{4,}\b','[number hidden]',text)
