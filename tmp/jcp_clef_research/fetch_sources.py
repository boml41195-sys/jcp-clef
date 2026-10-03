from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
ROOT.mkdir(exist_ok=True)


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'JCP-applicability-research/0.3'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


manifest = []
for model in ('clef', 'clef-flash'):
    metadata_url = f'https://huggingface.co/api/models/Cloudflare/{model}'
    metadata = json.loads(fetch(metadata_url))
    revision = metadata['sha']
    folder = ROOT / model
    folder.mkdir(exist_ok=True)
    names = {item['rfilename'] for item in metadata['siblings']}
    sources = []
    for name in ('README.md', 'joint_schema_model.py', 'joint_head_config.json', 'config.json', 'LICENSE'):
        if name not in names:
            continue
        url = f'https://huggingface.co/Cloudflare/{model}/resolve/{revision}/{name}'
        data = fetch(url)
        (folder / name).write_bytes(data)
        sources.append({'file': name, 'url': url, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest.append({'model': f'Cloudflare/{model}', 'revision': revision, 'files': sources})

for slug in ('clef', 'clef-flash'):
    url = f'https://developers.cloudflare.com/ai/models/@cf/cloudflare/{slug}/index.md'
    try:
        data = fetch(url)
    except Exception as exc:
        manifest.append({'documentation_url': url, 'error': type(exc).__name__})
    else:
        (ROOT / f'workers-ai-{slug}.md').write_bytes(data)
        manifest.append({'documentation_url': url, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})

(ROOT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=False, indent=2))
