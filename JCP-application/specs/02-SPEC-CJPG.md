# 02 — Especificação da Claw CJPG (TJSP)

**JCP-application | browser-use + CLEF | PoC**

Esta especificação define o contrato e o comportamento esperado da única claw do MVP.
É a fonte de verdade para o parser, o verificador e os testes de aceitação.

---

## 1. Identidade da capacidade

```python
CapabilitySpec(
    id="tjsp.cjpg.search_decisions",
    name="Busca de Decisões CJPG — TJSP",
    version="0.1.0",
    level="experimental",  # nunca "certified" sem T01-T22 aprovados ao vivo
    transport="browser",
    requires_auth=False,
    base_url="https://esaj.tjsp.jus.br/cjpg/",
)
```

**Nível `experimental`** — a receita executa em casos limitados e exige verificação estreita.
Não promover para `certified` sem aceite ao vivo com verificador independente.

---

## 2. Função externa (`search_decisions`)

### 2.1 Invocation

```python
class CJPGInvocation(BaseModel):
    tribunal: Literal["TJSP"] = "TJSP"
    texto: str                          # termo de busca livre
    data_inicio: date | None = None     # formato YYYY-MM-DD
    data_fim: date | None = None        # formato YYYY-MM-DD
    classe: str | None = None           # ex: "Apelação Cível"
    assunto: str | None = None          # código ou nome do assunto
    max_pages: PositiveInt = 1          # MVP: sempre 1
    freshness: Literal["live"] = "live" # MVP não aceita cache de resultado
```

**Validações de entrada (rejeitadas antes de abrir navegador):**
- `texto` vazio → `INVALID_ARGUMENT`
- `data_fim` anterior a `data_inicio` → `INVALID_ARGUMENT`
- `max_pages > 1` → `NOT_SUPPORTED` (fora do escopo do MVP)
- `freshness != "live"` → `NOT_SUPPORTED`

### 2.2 Result

```python
class Decision(BaseModel):
    numero_processo: str        # ex: "1234567-89.2024.8.26.0100"
    data_julgamento: date | None
    data_publicacao: date | None
    classe: str | None
    assunto: str | None
    ementa_trecho: str          # primeiros 500 chars da ementa
    url_inteiro_teor: str | None  # presente mas não baixado no MVP
    origem: str                 # "TJSP/CJPG"

class CJPGResult(BaseModel):
    status: Literal["ok", "empty", "needs_auth", "error"]
    decisions: list[Decision]   # vazio se status != "ok"
    evidence: Evidence
    recipe_version: str
    llm_calls: int              # DEVE ser 0 no caminho estável
    pages_fetched: int          # sempre 1 no MVP
    scope_declared: str         # "TJSP CJPG — primeira página"
```

### 2.3 Evidence

```python
class Evidence(BaseModel):
    source_url: str
    captured_at: datetime       # UTC
    filters_applied: dict       # espelho dos argumentos usados
    recipe_id: str
    recipe_version: str
    pages_visited: list[str]
    verification_passed: bool
```

**Regra:** `scope_declared` deve sobreviver à síntese do agente consumidor.
Um resultado de primeira página não pode ser apresentado como busca nacional completa.

---

## 3. Receita DSL mínima (CJPG v0.1)

```yaml
id: tjsp-cjpg-search-v0.1
capability: tjsp.cjpg.search_decisions
version: "0.1.0"
transport: browser
parameters:
  - name: texto
    binding: invocation.texto
    required: true
  - name: data_inicio
    binding: invocation.data_inicio
    required: false
  - name: data_fim
    binding: invocation.data_fim
    required: false

steps:
  - id: s01_navigate
    op: goto
    url: "https://esaj.tjsp.jus.br/cjpg/pesquisar.do"
    wait_for: load
    timeout_ms: 15000

  - id: s02_fill_text
    op: fill
    selector: "#iddados\\.buscaInteiroTeor"
    value: "{{texto}}"
    precondition: element_visible

  - id: s03_fill_date_start
    op: fill
    selector: "#iddados\\.dtJulgamentoInicio"
    value: "{{data_inicio | date_br}}"    # formato DD/MM/YYYY exigido pelo portal
    when: "invocation.data_inicio != null"

  - id: s04_fill_date_end
    op: fill
    selector: "#iddados\\.dtJulgamentoFim"
    value: "{{data_fim | date_br}}"
    when: "invocation.data_fim != null"

  - id: s05_submit
    op: click
    selector: "#pbSubmit"
    wait_for: network_idle
    timeout_ms: 30000

  - id: s06_check_state
    op: classify_page_state
    options:
      - id: results      # tabela de resultados presente
      - id: empty        # mensagem "Nenhum documento encontrado"
      - id: auth         # redirecionado para login
      - id: error        # erro inesperado
    on_auth: return needs_auth
    on_error: raise ExecutionError
    on_empty: return empty_result

  - id: s07_extract
    op: extract_decisions
    parser: cjpg_decision_parser_v1
    max_items: 20
    on_no_items: return empty_result

verification:
  - check: filters_preserved
    filters: [texto, data_inicio, data_fim]
  - check: origin_matches
    expected_origin: "TJSP/CJPG"
  - check: process_numbers_valid
    pattern: "^\\d{7}-\\d{2}\\.\\d{4}\\.8\\.26\\.\\d{4}$"
```

**Importante:**
- Os seletores CSS acima são ponto de partida baseado em código de terceiros (juscraper).
  **Devem ser validados contra o portal real antes de marcar a receita como `experimental`.**
- O filtro `date_br` converte `YYYY-MM-DD` para `DD/MM/YYYY` — transformação determinística, sem LLM.
- O passo `s06_check_state` pode usar CLEF se houver ambiguidade entre candidatos de estado.

---

## 4. Parser CJPG v1 (comportamento esperado)

O parser recebe o HTML da página de resultados e extrai:

| Campo | Seletor provável | Transformação |
|---|---|---|
| `numero_processo` | `td.numProcesso` ou similar | Normalizar para `NNNNNNN-NN.AAAA.8.26.NNNN` |
| `data_julgamento` | coluna "Data do Julgamento" | Parse `DD/MM/AAAA` → `date` |
| `data_publicacao` | coluna "Data de Publicação" | Parse `DD/MM/AAAA` → `date` |
| `classe` | coluna "Classe" | String normalizada |
| `ementa_trecho` | `div.ementa` ou `td.ementa` | Primeiros 500 chars, sem HTML |
| `url_inteiro_teor` | link "Inteiro Teor" | URL absoluta |

**Regras do parser:**
- Resultado vazio é estado válido — não lançar erro
- Falha em parse de um campo não invalida o item inteiro — registrar `null`
- `data_julgamento` e `data_publicacao` são campos diferentes — não intercambiar
- Nunca usar LLM para interpretar o HTML

---

## 5. Verificador (independente do executor)

O verificador roda **após** a extração e **não pode ser alterado pelo executor ou pelo reparo**:

```python
class CJPGVerifier:
    def verify(self, invocation: CJPGInvocation, result: CJPGResult) -> VerificationReport:
        checks = []
        # 1. Texto buscado aparece em pelo menos um item OU resultado é explicitamente vazio
        checks.append(self._check_text_relevance(invocation.texto, result.decisions))
        # 2. Datas dos resultados estão dentro do intervalo solicitado (se fornecido)
        checks.append(self._check_date_range(invocation, result.decisions))
        # 3. Todos os números de processo seguem o padrão CNJ
        checks.append(self._check_process_numbers(result.decisions))
        # 4. origin == "TJSP/CJPG" em todos os itens
        checks.append(self._check_origin(result.decisions))
        # 5. llm_calls == 0
        checks.append(self._check_zero_llm(result.llm_calls))
        return VerificationReport(passed=all(c.passed for c in checks), checks=checks)
```

**O verificador não pode:**
- Ser instanciado pelo executor durante a execução
- Ter seus critérios modificados por uma receita candidata de reparo
- Retornar `passed=True` quando `llm_calls > 0` no modo determinístico

---

## 6. Estados de erro e o que retornar em cada um

| Estado | Causa | Retorno correto |
|---|---|---|
| Portal fora do ar | Timeout na navegação | `status="error"`, `error_code="PORTAL_UNAVAILABLE"` |
| Login exigido | Redirecionamento para autenticação | `status="needs_auth"`, não `status="empty"` |
| CAPTCHA / desafio | Página de verificação detectada | `status="needs_auth"`, escalar para operador |
| Resultado legitimamente vazio | Mensagem de 0 resultados presente | `status="empty"`, `decisions=[]`, `evidence` preenchida |
| Seletor não encontrado | Mudança de interface | Falha de locator → tentar recuperação CLEF → se falhar, `status="error"` |
| Parse falhou em todos os itens | HTML mudou estruturalmente | `status="error"`, bundle de falha para diagnóstico |

**Regra crítica:** `status="empty"` só pode ser retornado se a página **confirmou explicitamente** a ausência de resultados.
Timeout ou falha de parser **não são** resultado vazio.
