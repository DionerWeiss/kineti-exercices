"""Generates one exercise clip with Veo (Gemini API), starting and ending on the
same keyframe so the clip loops and the character stays the Kineti one.

    GEMINI_API_KEY=... python3 tool/genvideo/veo_generate.py <keyframe.png> <prompt.txt> <out.mp4> [--model veo-...]
        [--vertex --project <id> --location us-central1]

The keyframe is a still of the Kineti character in the start pose (a frame of
the 3D render). Without --model, the newest Veo model the key can use is
picked from the model list. Each call is billed per second of video.
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request

API = 'https://generativelanguage.googleapis.com/v1beta'


def call(url, key, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'x-goog-api-key': key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def newest_veo(key):
    models = call(f'{API}/models?pageSize=200', key).get('models', [])
    veo = [m['name'] for m in models if 'veo' in m['name'] and 'predictLongRunning' in m.get('supportedGenerationMethods', [])]
    if not veo:
        raise SystemExit('No Veo model available to this key.')
    return sorted(veo)[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('keyframe')
    ap.add_argument('prompt')
    ap.add_argument('out')
    ap.add_argument('--model')
    ap.add_argument('--seconds', type=int, default=8)
    ap.add_argument('--vertex', action='store_true')
    ap.add_argument('--samples', type=int, default=1, help='Vertex: variations to generate (saved as out_1.mp4, ...)')
    ap.add_argument('--resolution', help='720p or 1080p (Vertex)')
    ap.add_argument('--last', help='last frame image (default: the keyframe, so the clip loops)')
    ap.add_argument('--project')
    ap.add_argument('--location', default='us-central1')
    a = ap.parse_args()
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_TTS_API_KEY')
    if not key:
        raise SystemExit('Set GEMINI_API_KEY.')
    img = {'bytesBase64Encoded': base64.b64encode(open(a.keyframe, 'rb').read()).decode(), 'mimeType': 'image/png'}
    last = img if not a.last else {'bytesBase64Encoded': base64.b64encode(open(a.last, 'rb').read()).decode(),
                                    'mimeType': 'image/png'}
    instance = {'prompt': open(a.prompt, encoding='utf-8').read().strip(), 'image': img, 'lastFrame': last}
    params = {'aspectRatio': '16:9', 'durationSeconds': a.seconds, 'personGeneration': 'allow_adult'}
    if a.vertex:  # Vertex AI: billed to the Google Cloud project
        model = a.model or 'veo-3.1-fast-generate-001'
        base = f'https://{a.location}-aiplatform.googleapis.com/v1/projects/{a.project}/locations/{a.location}/publishers/google/models/{model}'
        params['sampleCount'] = a.samples
        if a.resolution:
            params['resolution'] = a.resolution
        op = call(f'{base}:predictLongRunning', key, {'instances': [instance], 'parameters': params})
        print('model', model)
        while not op.get('done'):
            time.sleep(10)
            op = call(f'{base}:fetchPredictOperation', key, {'operationName': op['name']})
            print('.', end='', flush=True)
        print()
        if 'error' in op:
            raise SystemExit(f'Veo error: {op["error"]}')
        vids = op['response'].get('videos', [])
        if not vids or 'bytesBase64Encoded' not in vids[0]:
            raise SystemExit(f'no video returned: {json.dumps(op["response"])[:400]}')
        outs = [a.out] if len(vids) == 1 else [a.out.replace('.mp4', f'_{i + 1}.mp4') for i in range(len(vids))]
        for v, o in zip(vids, outs):
            open(o, 'wb').write(base64.b64decode(v['bytesBase64Encoded']))
            print('saved', o)
        return
    model = a.model or newest_veo(key)
    body = {'instances': [instance], 'parameters': params}
    print('model', model)
    op = call(f'{API}/{model}:predictLongRunning', key, body)
    while not op.get('done'):
        time.sleep(10)
        op = call(f'{API}/{op["name"]}', key)
        print('.', end='', flush=True)
    print()
    if 'error' in op:
        raise SystemExit(f'Veo error: {op["error"]}')
    resp = op['response']
    samples = resp.get('generateVideoResponse', resp).get('generatedSamples') or resp.get('generatedVideos')
    uri = samples[0]['video']['uri']
    req = urllib.request.Request(uri, headers={'x-goog-api-key': key})
    with urllib.request.urlopen(req, timeout=300) as r, open(a.out, 'wb') as f:
        f.write(r.read())
    print('saved', a.out)


if __name__ == '__main__':
    sys.exit(main())
