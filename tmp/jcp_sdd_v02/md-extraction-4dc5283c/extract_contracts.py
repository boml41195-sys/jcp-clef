from pathlib import Path
import json
import re

docs = Path("JCP-SDD")
out = Path("jcp-contract-reference")
out.mkdir(exist_ok=True)
mapping = {
    "10-CONTRATOS-VALIDAVEIS.md": "contracts.py",
    "12-EXEMPLOS-E-TESTES-DE-CONTRATO.md": "examples_and_tests.py",
}
for document, target in mapping.items():
    text = (docs / document).read_text(encoding="utf-8")
    match = re.search(r"```python\n(.*?)\n```", text, flags=re.S)
    if match is None:
        raise RuntimeError(f"Missing Python block: {document}")
    path = out / target
    if path.exists():
        raise FileExistsError(path)
    path.write_text(match.group(1) + "\n", encoding="utf-8")

schema_text = (docs / "10-CONTRATOS-VALIDAVEIS.md").read_text(encoding="utf-8")
schemas = re.findall(r"```json\n(.*?)\n```", schema_text, flags=re.S)
if len(schemas) != 2:
    raise RuntimeError("Expected exactly two schemas")
for name, content in zip(("cjpg-invocation.schema.json", "cjpg-result.schema.json"), schemas):
    path = out / name
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(json.loads(content), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Extracted contracts, tests and schemas into", out)
