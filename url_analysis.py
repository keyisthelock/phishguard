"""Offline URL structure checks. This module never performs a network request."""
import re
import ipaddress
from urllib.parse import urlsplit, urlunsplit, parse_qsl
from difflib import SequenceMatcher

def inspect_url(value):
    raw=value.strip()
    if not raw or len(raw)>2048 or re.search(r'[\s\x00-\x1f<>"\\]',raw): raise ValueError('Enter one URL without spaces or control characters (up to 2,048 characters).')
    if not re.match(r'^[a-z][a-z0-9+.-]*://',raw,re.I): raw='https://'+raw
    try:
        p=urlsplit(raw)
        if p.scheme not in {'http','https'}: raise ValueError()
        host=p.hostname
        if not host: raise ValueError()
        host=host.encode('idna').decode('ascii').lower().rstrip('.')
        port=p.port
        try: ipaddress.ip_address(host); is_ip=True
        except ValueError:
            is_ip=False
            if '.' not in host or len(host)>253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',part) for part in host.split('.')): raise ValueError()
    except (ValueError,UnicodeError): raise ValueError('Enter a valid HTTP or HTTPS URL with a complete domain.') from None
    flags=[]
    if p.scheme!='https': flags.append('No HTTPS: transport is not encrypted; this alone does not prove fraud')
    if p.username or p.password: flags.append('User information before @ can disguise the real destination')
    if is_ip: flags.append('IP address instead of a domain: verify who controls the destination')
    if host in {'bit.ly','tinyurl.com','t.co','shorturl.at','is.gd'}: flags.append('Shortened link: the final destination is hidden')
    if 'xn--' in host: flags.append('Punycode domain: visually similar characters may disguise a name')
    if host.count('.')>=3: flags.append('Many subdomains: read the complete hostname carefully')
    if port and port not in {80,443}: flags.append('Unusual port: confirm this service is expected')
    if len(raw)>180: flags.append('Long URL: important destination details can be hard to see')
    if re.search(r'(login|verify|secure|bank|kyc)',host) and ('-' in host or host.endswith(('.xyz','.top','.click'))): flags.append('Account-related words in an unusual domain: possible impersonation')
    domains=('paypal.com','microsoft.com','google.com','amazon.com','apple.com','sbi.co.in','hdfcbank.com')
    if not is_ip:
        for brand in domains:
            if host==brand or host.endswith('.'+brand): continue
            stem=brand.split('.')[0]
            candidate=host.split('.')[-2]
            if stem in host or SequenceMatcher(None,candidate,stem).ratio()>=.78:
                flags.append('Possible lookalike of '+brand+': compare the registered destination with the official domain'); break
    if re.search(r'(password|otp|token|secret|session|auth)',p.query,re.I): flags.append('Sensitive-looking query parameters: avoid sharing credentials through links')
    normalized=urlunsplit((p.scheme,p.netloc,p.path or '/',p.query,p.fragment))
    parts=host.split('.')
    return {'url':normalized,'host':host,'scheme':p.scheme,'subdomain':'.'.join(parts[:-2]) if len(parts)>2 and not is_ip else '—','path':p.path or '/','query_keys':[k for k,v in parse_qsl(p.query,keep_blank_values=True)][:20],'flags':flags,'rule_score':min(96,sum(24 if 'lookalike' in f or 'disguise' in f else 14 for f in flags))}
