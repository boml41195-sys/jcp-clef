from __future__ import annotations

import ast
from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parent


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ignored = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data):
        if not self.ignored and data.strip():
            self.parts.append(data.strip())


for model in ('clef', 'clef-flash'):
    parser = VisibleText()
    parser.feed((ROOT / f'workers-ai-{model}.md').read_text(encoding='utf-8'))
    (ROOT / f'workers-ai-{model}.txt').write_text('\n'.join(parser.parts), encoding='utf-8')

source_path = ROOT / 'clef' / 'joint_schema_model.py'
source = ast.parse(source_path.read_text(encoding='utf-8'))
allowed = {'render', 'question_options', 'EncodedQuestion', 'EncodedRecord', '_tokens', '_encode_media', 'encode_record', 'systemone_answer'}
constants = {'SYSTEM_PROMPT', 'IMAGE_PLACEHOLDER', 'VIDEO_PLACEHOLDER', 'MEDIA_BATCH_KEYS', 'MEDIA_TOKEN_KEYS', 'QUESTION_TYPES'}
nodes = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)]
for node in source.body:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in allowed:
        nodes.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets):
        nodes.append(node)
module = ModuleType('clef_semantics_probe')
sys.modules[module.__name__] = module
module.__dict__.update(json=json, dataclass=dataclass, dataclass_field=field, Any=Any)
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(source_path), 'exec'), module.__dict__)

checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append({'test': name, 'status': 'passed'})


question = {'type': 'choice', 'criteria': {'z': 'Última opção', 'a': 'Primeira opção'}}
check('choice options are sorted for encoding', [k for k, _ in module.question_options(question)] == ['a', 'z'])
check('noul encodes true and false', [k for k, _ in module.question_options({'type': 'noul'})] == ['true', 'false'])
check('score options use ordinal string IDs', [k for k, _ in module.question_options({'type': 'score', 'criteria': ['low', 'medium', 'high']})] == ['0', '1', '2'])
answer = module.systemone_answer(question, {'z': 0.8, 'a': 0.2})
check('choice uses highest probability', answer['choice'] == 'z')
check('confidence equals selected probability', answer['confidence'] == 0.8)
rounded = module.systemone_answer(question, {'z': 0.123456, 'a': 0.876544})
check('probabilities rounded to four decimals', rounded['probabilities']['z'] == 0.1235)
score = module.systemone_answer({'type': 'score', 'criteria': ['low', 'medium', 'high']}, {'0': 0.2, '1': 0.3, '2': 0.5})
check('score is weighted expectation, not winning index', score['score'] == 1.3)
check('score includes ordinal legend', score['legend'] == {'0': 'low', '1': 'medium', '2': 'high'})
check('noul returns probability, not bool', module.systemone_answer({'type': 'noul'}, {'true': 0.8, 'false': 0.2}) == {'type': 'noul', 'noul': 0.8})
check('choice tie follows criteria insertion order', module.systemone_answer(question, {'z': 0.5, 'a': 0.5})['choice'] == 'z')
check('JSON render preserves Unicode', 'decisão' in module.render({'field': 'decisão'}))


class CharacterTokenizer:
    """Synthetic tokenizer for branch testing; not the real Clef tokenizer."""
    def __call__(self, text, add_special_tokens=False):
        return SimpleNamespace(input_ids=[ord(c) for c in text])


tokenizer = CharacterTokenizer()
record = {'state': 'STATE_START_' + 'x' * 3000 + '_CRITICAL_TAIL', 'questions': {'target': question}}
encoded = module.encode_record(tokenizer, record, max_length=10000)
check('question identity preserved by encoding', encoded.questions[0].question_id == 'target')
check('full state retained when there is room', '_CRITICAL_TAIL' in ''.join(map(chr, encoded.input_ids)))
truncated = module.encode_record(tokenizer, record, max_length=900)
decoded = ''.join(map(chr, truncated.input_ids))
check('encoder truncates state suffix', '_CRITICAL_TAIL' not in decoded and 'STATE_START_' in decoded)
check('schema survives state truncation', 'ALLOWED OPTIONS:' in decoded and 'Primeira opção' in decoded)
limited = module.encode_record(tokenizer, record, max_length=10000, max_state_tokens=5)
check('explicit state cap is applied', 'STATE_START_' not in ''.join(map(chr, limited.input_ids)))
try:
    module.encode_record(tokenizer, record, max_length=10)
except ValueError:
    check('oversized schema is rejected', True)
else:
    raise AssertionError('oversized schema accepted')
try:
    module.encode_record(tokenizer, {'state': 'x', 'questions': {}}, max_length=10000)
except ValueError:
    check('record without questions is rejected', True)
else:
    raise AssertionError('empty questions accepted')

report = {'source': str(source_path), 'passed': len(checks), 'failed': 0,
          'torch_imported': 'torch' in sys.modules, 'model_inference_executed': False,
          'real_tokenizer_used': False, 'tests': checks}
(ROOT / 'semantics_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
