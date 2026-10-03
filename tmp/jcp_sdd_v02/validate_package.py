from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'JCP-SDD'
files = sorted(DOCS.glob('*.md'))
if len(files) != 16:
    raise AssertionError(f'Expected 16 Markdown files, found {len(files)}')

links = json_blocks = python_blocks = words = 0
for path in files:
    text = path.read_text(encoding='utf-8', errors='strict')
    if not text.strip():
        raise AssertionError(f'Empty file: {path.name}')
    words += len(text.split())
    if len(re.findall(r'^```', text, re.M)) % 2:
        raise AssertionError(f'Unbalanced code fences: {path.name}')
    if '\ufffd' in text or re.search(r'turn\d+(?:search|view|fetch)\d+', text):
        raise AssertionError(f'Unexpected encoding/citation marker: {path.name}')
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        target = target.strip('<> ').split('#', 1)[0]
        if not target or re.match(r'^[a-z]+://', target):
            continue
        if not (path.parent / target).is_file():
            raise AssertionError(f'Broken link in {path.name}: {target}')
        links += 1
    for language, block in re.findall(r'^```([^\n]*)\n(.*?)^```', text, re.M | re.S):
        if language.strip() == 'json':
            json.loads(block)
            json_blocks += 1
        if language.strip() == 'python':
            ast.parse(block)
            python_blocks += 1

smoke = Path(__file__).parent / ('md-extraction-' + uuid.uuid4().hex[:8])
smoke.mkdir()
(smoke / 'JCP-SDD').mkdir()
for name in ('10-CONTRATOS-VALIDAVEIS.md', '12-EXEMPLOS-E-TESTES-DE-CONTRATO.md'):
    shutil.copyfile(DOCS / name, smoke / 'JCP-SDD' / name)
test_doc = (DOCS / '12-EXEMPLOS-E-TESTES-DE-CONTRATO.md').read_text(encoding='utf-8')
blocks = re.findall(r'```python\n(.*?)\n```', test_doc, re.S)
if len(blocks) != 2:
    raise AssertionError('Expected test code and extractor code')
(smoke / 'extract_contracts.py').write_text(blocks[1] + '\n', encoding='utf-8')
subprocess.run([sys.executable, 'extract_contracts.py'], cwd=smoke, check=True, capture_output=True, text=True)
test_run = subprocess.run([sys.executable, 'jcp-contract-reference/examples_and_tests.py'], cwd=smoke,
                          check=True, capture_output=True, text=True, encoding='utf-8')
tests = json.loads(test_run.stdout)
if tests['passed'] != 34 or tests['failed'] != 0:
    raise AssertionError('Contract reference tests failed')

model_path = smoke / 'jcp-contract-reference' / 'contracts.py'
spec = importlib.util.spec_from_file_location('extracted_contracts', model_path)
models = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = models
spec.loader.exec_module(models)
for model, name in ((models.CjpgInvocation, 'cjpg-invocation.schema.json'), (models.CjpgResult, 'cjpg-result.schema.json')):
    saved = json.loads((model_path.parent / name).read_text(encoding='utf-8'))
    actual = {'$schema': 'https://json-schema.org/draft/2020-12/schema', **model.model_json_schema(mode='validation')}
    if saved != actual:
        raise AssertionError(f'Schema differs from the embedded code: {name}')
    def check_refs(node):
        if isinstance(node, dict):
            if '$ref' in node:
                ref = node['$ref']
                if not ref.startswith('#/'):
                    raise AssertionError(f'Nonlocal schema reference: {ref}')
                current = saved
                for key in ref[2:].split('/'):
                    current = current[key.replace('~1', '/').replace('~0', '~')]
            for value in node.values():
                check_refs(value)
        elif isinstance(node, list):
            for value in node:
                check_refs(value)
    check_refs(saved)

legacy = (DOCS / '03-CONTRATOS-DO-PROTOCOLO.md').read_text(encoding='utf-8')
legacy_blocks = re.findall(r'```json\n(.*?)\n```', legacy, re.S)
if len(legacy_blocks) != 2:
    raise AssertionError('Unexpected conceptual contract examples')
invocation = models.CjpgInvocation.model_validate_json(legacy_blocks[0])
result = models.CjpgResult.model_validate_json(legacy_blocks[1])
models.validate_against_invocation(invocation, result)

archive = ROOT / 'JCP-SDD-v0.2-2026-10-03.zip'
if archive.exists():
    raise FileExistsError(archive)
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in files:
        zf.write(path, arcname='JCP-SDD/' + path.name)
with zipfile.ZipFile(archive) as zf:
    if zf.testzip() is not None or len(zf.namelist()) != len(files):
        raise AssertionError('ZIP integrity check failed')
    for path in files:
        if zf.read('JCP-SDD/' + path.name) != path.read_bytes():
            raise AssertionError(f'ZIP content mismatch: {path.name}')

report = {
    'zip': str(archive), 'markdown_files': len(files), 'words_including_code': words,
    'internal_links_checked': links, 'json_blocks_parsed': json_blocks,
    'python_blocks_syntax_checked': python_blocks,
    'contract_tests_from_extracted_markdown': tests['passed'],
    'schemas_match_embedded_models': True, 'schema_refs_resolved': True,
    'conceptual_examples_match_executable_contracts': True,
    'zip_integrity_verified': True, 'zip_bytes': archive.stat().st_size,
    'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'runtime_or_portal_tests_executed': False,
}
(Path(__file__).parent / 'package_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
