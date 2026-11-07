"""One image from Gemini (image model), from a prompt and reference images.

    GEMINI_API_KEY=... python3 tool/genvideo/gemini_image.py <out.png> <prompt.txt> [ref.png ...] [--model ...] [--vertex]

--vertex uses Vertex AI (billed to the Google Cloud project; the key must be a
Vertex AI express-mode key) instead of the Gemini API (AI Studio).
"""

import argparse
import base64
import json
import os
import urllib.error
import urllib.request

API = 'https://generativelanguage.googleapis.com/v1beta'
VERTEX = 'https://aiplatform.googleapis.com/v1/publishers/google'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('prompt')
    ap.add_argument('refs', nargs='*')
    ap.add_argument('--model', default='gemini-3-pro-image')
    ap.add_argument('--aspect', default='16:9')
    ap.add_argument('--vertex', action='store_true')
    ap.add_argument('--project', help='Vertex: project id or number, to reach a region other than the key\'s')
    ap.add_argument('--location', default='global')
    a = ap.parse_args()
    key = os.environ['GEMINI_API_KEY']
    parts = [{'inline_data': {'mime_type': 'image/png', 'data': base64.b64encode(open(r, 'rb').read()).decode()}}
             for r in a.refs]
    parts.append({'text': open(a.prompt, encoding='utf-8').read().strip()})
    body = {'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': a.aspect}}}
    base = VERTEX if a.vertex else API
    if a.vertex and a.project:
        base = f'https://aiplatform.googleapis.com/v1/projects/{a.project}/locations/{a.location}/publishers/google'
    req = urllib.request.Request(f'{base}/models/{a.model}:generateContent', data=json.dumps(body).encode(),
                                 headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read())
            d = d[0] if isinstance(d, list) else d
    except urllib.error.HTTPError as e:
        raise SystemExit(f'HTTP {e.code}: {e.read().decode()[:400]}')
    for c in d.get('candidates', []):
        for p in c.get('content', {}).get('parts', []):
            data = p.get('inlineData') or p.get('inline_data')
            if data:
                open(a.out, 'wb').write(base64.b64decode(data['data']))
                print('saved', a.out)
                return
    raise SystemExit(f'no image returned: {json.dumps(d)[:400]}')


if __name__ == '__main__':
    main()
