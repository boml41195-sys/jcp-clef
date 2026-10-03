from pathlib import Path
import json
import platform
import pydantic

from contracts import CjpgInvocation, CjpgResult
from examples_and_tests import INVOCATION, example_cases, run_tests


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'JCP-SDD'
HERE = Path(__file__).resolve().parent


def fence(language, text):
    return f'```{language}\n{text.rstrip()}\n```\n'


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


intro = '''# Contratos validáveis e schemas de referência

Revisão documental 0.2. O protocolo proposto continua em 0.1 e a capacidade de referência em 1.0.0: ainda não existe uma implementação pública lançada cuja compatibilidade precise ser migrada.

Este documento entrega um perfil executável de contrato para `tjsp.cjpg.search_decisions`. Ele formaliza o primeiro caso vertical; não pretende fingir que schemas de todos os portais foram implementados. A arquitetura dos demais objetos está no documento 03. Cada nova capacidade precisa de seus próprios modelos e verificadores.

## 1. O que foi executado

O código Python abaixo foi executado localmente com Python {python_version} e Pydantic {pydantic_version}. Os 34 casos de contrato do documento 12 passaram. Isso verifica comportamento dos modelos, consistência entre chamada e resposta e exportação de schemas. Não é teste de navegação, de autenticidade de evidência, de integração Browser Use ou de consulta judicial real.

O pacote continua composto por Markdown. O desenvolvedor pode copiar o primeiro bloco Python deste documento para `contracts.py`; o documento 12 contém exemplos, testes e um extrator reproduzível para os dois arquivos Python e os schemas.

## 2. Decisões normativas deste perfil

- Envelope fechado: propriedades desconhecidas são rejeitadas. Identidade de tenant e principal vem do gateway, nunca do texto gerado pelo modelo.
- Tipos estritos: não converter booleano em limite inteiro nem texto numérico em número silenciosamente. Datas ISO em JSON são aceitas e validadas.
- CJPG começa com filtro de disponibilização (`availability`). A existência de outro campo de data no objeto de saída não significa suporte a pesquisar por esse campo.
- Os limites numéricos abaixo são limites de referência escolhidos para o perfil de desenvolvimento. Não foram medidos como capacidade dos tribunais. A política pode reduzi-los na admissão e deve informar o orçamento efetivo.
- `freshness=live` exige `max_age_ms=0`. `cached_if_fresh` exige idade máxima positiva e nunca elimina a revalidação de autorização. O MVP pode não oferecer cache de resultado.
- `arguments.cursor` é opcional e opaco. Seu suporte de execução deve constar da certificação. O documento 13 define sua vinculação; um token não autoriza ampliar origem nem identidade.
- Zero chamadas de modelo é uma configuração válida. Ter `allow_repair=true` não supera um orçamento de modelo igual a zero: só reparos determinísticos cabíveis permanecem elegíveis.
- `source_exhausted` é obrigatório e admite `null` quando desconhecido. `complete` descreve satisfação do escopo solicitado.
- `success` exige os cinco grupos de verificação, escopo satisfeito e ausência de erro. Vazio exige confirmação de esgotamento da fonte naquele filtro.
- `partial` publica apenas itens úteis e verificados, com escopo incompleto e motivo de parada. Itens rejeitados ficam no diagnóstico protegido.
- Este perfil publica itens apenas em `success` ou `partial`. Streaming progressivo de itens é uma extensão futura e precisa de contrato próprio.

## 3. Fronteira entre validação estrutural e prova real

O cliente não pode enviar um Result para o servidor e, com isso, certificar seus próprios dados. Result é produzido pelo runtime. O código abaixo confere coerência da representação, mas não prova que um ID de evidência existe, que o portal respondeu ou que a página pertence ao processo correto.

Os JSON Schemas gerados capturam tipos, campos, enums e limites. `model_validator` e `validate_against_invocation` contêm regras relacionais que NÃO são automaticamente exportadas para JSON Schema pelo Pydantic. Um cliente que só valida JSON Schema não reproduz toda a validação do servidor.

Ficam obrigatórios no runtime: autenticação e autorização; resolução das evidências; origem permitida; verificação de filtros na fonte; normalização de identificadores quando aplicável; contagem real de chamadas, bytes e tempo; proteção de segredos; política de cache; e vínculo de run/principal. Um campo `passed` não é um substituto para executar esses controles.

Os limites de payload devem ser impostos antes de carregar o JSON inteiro. Rejeitar chaves duplicadas no parser do gateway; o modelo Pydantic abaixo não é usado como defesa contra esse caso. O ledger do run fornece o vínculo confiável entre invocação e resposta.

## 4. Implementação de referência dos modelos

O bloco é completo para o perfil CJPG de demonstração. Não abre navegador nem faz requisições.

'''.format(python_version=platform.python_version(), pydantic_version=pydantic.__version__)

contract_text = intro + fence('python', (HERE / 'contracts.py').read_text(encoding='utf-8'))
contract_text += '''
## 5. JSON Schema da chamada

Schema gerado a partir de `CjpgInvocation.model_json_schema(mode="validation")`, com declaração do dialeto 2020-12. Referências `$defs` são locais; não há downloads durante a resolução. As invariantes relacionais continuam sendo as do código acima.

'''
schemas = []
for model in (CjpgInvocation, CjpgResult):
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', **model.model_json_schema(mode='validation')}
    schemas.append(schema)
contract_text += fence('json', pretty(schemas[0]))
contract_text += '\n## 6. JSON Schema da resposta\n\n'
contract_text += fence('json', pretty(schemas[1]))
contract_text += '''
## 7. Evolução

Adicionar outro tribunal não significa trocar os Literals desta classe por strings livres e perder validação. O gateway seleciona um perfil pelo par capacidade/versão. Cada perfil usa schema fechado e seu verificador; o envelope comum pode ser extraído para uma base compartilhada na implementação.

Mudança compatível de documentação não é nova versão de protocolo. Mudança de significado de campo, filtro ou efeito exige nova versão de capacidade e matriz de compatibilidade. Receitas fixam essa versão. O cliente deve receber a versão selecionada, sem fallback silencioso para interpretação diferente.

Referências: [contrato conceitual](03-CONTRATOS-DO-PROTOCOLO.md), [semântica do executor](11-DSL-E-SEMANTICA-DO-EXECUTOR.md), [exemplos e testes](12-EXEMPLOS-E-TESTES-DE-CONTRATO.md), [API e estados](13-API-ESTADOS-E-CONCORRENCIA.md).
'''
(DOCS / '10-CONTRATOS-VALIDAVEIS.md').write_text(contract_text, encoding='utf-8')

report = run_tests()
examples = '''# Exemplos completos e testes de contrato

Todos os dados deste documento são sintéticos. `fixture.invalid`, referências de evidência e números rotulados como sintéticos não representam processos ou decisões reais. Os exemplos demonstram o contrato; não certificam acesso ao TJSP. A allowlist de produção deve rejeitar esse domínio.

## 1. Chamada de referência

Esta chamada pede um item, o que permite mostrar a diferença entre satisfazer o pedido e esgotar uma fonte com mais resultados.

'''
examples += fence('json', pretty(INVOCATION))
for cid, title, invocation, result in example_cases():
    examples += f'\n## {cid} — {title}\n\n'
    if cid == 'C03':
        examples += 'Neste caso, a chamada usa `arguments.limit=10`; os demais campos permanecem os da chamada de referência. Duas páginas foram percorridas e um item útil passou pelos verificadores. O token de continuação é somente ilustrativo.\n\n'
    if cid == 'C05':
        examples += 'A capacidade de referência é pública, mas uma sessão opcional pode expirar no runtime; este fixture exercita o envelope de estado. Não afirma que a busca pública CJPG exija autenticação. Em produção, o resolvedor pode reiniciar uma leitura pública sem sessão quando a política e o fluxo permitirem.\n\n'
    if cid == 'C06':
        examples += 'A extração falhou. Nenhum item é publicado e a falha não aparece como uma busca bem-sucedida sem resultados.\n\n'
    examples += fence('json', pretty(result))

examples += '\n## 2. Matriz executada\n\n'
examples += '| ID | Caso | Expectativa | Resultado local |\n|---|---|---|---|\n'
for item in report:
    expected = 'Aceitar' if item['expected'] == 'accept' else 'Rejeitar'
    examples += f"| {item['id']} | {item['scenario']} | {expected} | Passou |\n"
examples += '''
São 34 casos locais: 6 positivos e 28 negativos. Os casos N19–N23, N25 e N28 incluem regras que dependem da chamada original, além do schema do resultado. Não extrapolar esse número para cobertura de todos os campos nem para testes de portais.

## 3. Testes reproduzíveis

Salvar o bloco a seguir como `examples_and_tests.py` no mesmo diretório de `contracts.py`. Ele usa apenas a biblioteca padrão e Pydantic, executa os casos e falha se uma mutação inválida for aceita. Não acessa a rede.

'''
examples += fence('python', (HERE / 'examples_and_tests.py').read_text(encoding='utf-8'))
examples += '''
## 4. Extrair os blocos a partir do pacote Markdown

Salvar este bloco como `extract_contracts.py` ao lado da pasta `JCP-SDD` e executar com Python. Ele não instala dependências e não faz requisições. O ambiente de teste usado nesta entrega tinha Pydantic instalado; o ambiente do desenvolvedor precisa disponibilizá-lo.

'''
extractor = '''from pathlib import Path
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
    match = re.search(r"```python\\n(.*?)\\n```", text, flags=re.S)
    if match is None:
        raise RuntimeError(f"Missing Python block: {document}")
    path = out / target
    if path.exists():
        raise FileExistsError(path)
    path.write_text(match.group(1) + "\\n", encoding="utf-8")

schema_text = (docs / "10-CONTRATOS-VALIDAVEIS.md").read_text(encoding="utf-8")
schemas = re.findall(r"```json\\n(.*?)\\n```", schema_text, flags=re.S)
if len(schemas) != 2:
    raise RuntimeError("Expected exactly two schemas")
for name, content in zip(("cjpg-invocation.schema.json", "cjpg-result.schema.json"), schemas):
    path = out / name
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(json.loads(content), ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
print("Extracted contracts, tests and schemas into", out)
'''
examples += fence('python', extractor)
examples += fence('text', 'python extract_contracts.py\npython jcp-contract-reference/examples_and_tests.py')
examples += '''
Resultado esperado do segundo comando: `passed: 34`, `failed: 0`. A suíte usa `model_validate_json`, pois datas chegam pelo contrato como JSON. Para chamar `model_validate` diretamente em Python com modo estrito, fornecer objetos `date`/`datetime`, em vez de presumir coerção de strings.

## 5. Testes ainda necessários

Esta suíte não faz afirmações sobre sessão, navegador, worker Go, verificador de origem, artefatos reais ou precisão jurídica. Esses testes continuam no plano 08 e no backlog 14. Também é necessário usar um validador JSON Schema independente no CI do produto se clientes de outras linguagens dependerem dos schemas; nesta entrega a exportação foi feita pelo Pydantic e as regras foram executadas em Python.

Uma resposta falsa, porém coerente em todos os campos, pode passar num validador de representação. Por isso a certificação do runtime exige evidências produzidas pelo executor e verificadas por código confiável. Os fixtures são suficientes para testar a forma do contrato, não para substituir essa cadeia.
'''
(DOCS / '12-EXEMPLOS-E-TESTES-DE-CONTRATO.md').write_text(examples, encoding='utf-8')
(HERE / 'contract_test_report.json').write_text(pretty({'passed': len(report), 'failed': 0, 'cases': report}), encoding='utf-8')
print(pretty({'documents_written': ['10-CONTRATOS-VALIDAVEIS.md', '12-EXEMPLOS-E-TESTES-DE-CONTRATO.md'], 'tests_passed': len(report)}))
