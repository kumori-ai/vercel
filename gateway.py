#!/usr/bin/env python3
"""Find, and prove, the zero-cost models on Vercel AI Gateway.

    python gateway.py free      every model the public catalog prices at input=0 and output=0
    python gateway.py ping      one 8-token prompt to each free chat model: latency, reported cost,
                                and the credit balance before and after
    python gateway.py credits   balance and total used

Key: AI_GATEWAY_API_KEY in the environment (Vercel's own convention).
`free` needs no key; the catalog is public.
Standard library only.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = 'https://ai-gateway.vercel.sh/v1'
PROMPT = 'Reply with the single word: pong'


def _req(path, body=None, key=None, timeout=90):
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = f'Bearer {key}'
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers,
                                 method='POST' if data else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {'error': e.read().decode(errors='ignore')[:300]}


def _key():
    k = os.environ.get('AI_GATEWAY_API_KEY')
    if not k:
        sys.exit('AI_GATEWAY_API_KEY is not set. Create one in the Vercel dashboard: '
                 'AI Gateway -> API Keys.')
    return k


def free_models():
    status, d = _req('/models')
    if status != 200:
        sys.exit(f'catalog HTTP {status}: {d}')
    models = d.get('data', [])
    free = [m for m in models
            if (m.get('pricing') or {}).get('input') == '0'
            and (m.get('pricing') or {}).get('output') == '0']
    return len(models), free


def cmd_free():
    total, free = free_models()
    print(f'{len(free)} of {total} models are priced input=0 output=0 at {BASE}/models\n')
    for m in free:
        tags = ','.join(m.get('tags') or [])
        print(f"{m['id']:40} {m.get('type', '?'):9} ctx={str(m.get('context_window') or '-'):>8} "
              f"no_training={str(m.get('no_training', '?')):5} tags={tags}")


def cmd_credits():
    status, d = _req('/credits', key=_key())
    print(d if status == 200 else f'HTTP {status}: {d}')


def cmd_ping():
    key = _key()
    _, free = free_models()
    chat = [m for m in free if m.get('type') == 'language']
    _, before = _req('/credits', key=key)
    print('credits before:', before)
    for m in chat:
        t0 = time.time()
        status, d = _req('/chat/completions', key=key, body={
            'model': m['id'], 'max_tokens': 8,
            'messages': [{'role': 'user', 'content': PROMPT}]})
        el = time.time() - t0
        if status != 200:
            print(f"{m['id']:40} HTTP {status} {el:4.1f}s  {json.dumps(d)[:140]}")
            continue
        usage = d.get('usage') or {}
        text = (((d.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()
        print(f"{m['id']:40} HTTP {status} {el:4.1f}s  in={usage.get('prompt_tokens')} "
              f"out={usage.get('completion_tokens')} cost={usage.get('cost')} -> {text[:30]!r}")
    _, after = _req('/credits', key=key)
    print('credits after: ', after)


if __name__ == '__main__':
    commands = {'free': cmd_free, 'ping': cmd_ping, 'credits': cmd_credits}
    name = sys.argv[1] if len(sys.argv) > 1 else ''
    if name not in commands:
        sys.exit(__doc__)
    commands[name]()
