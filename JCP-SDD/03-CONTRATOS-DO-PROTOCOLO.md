# Contratos do protocolo

Esta é a definição proposta do JCP 0.1. Modelos de implementação devem usar Pydantic v2 e exportar JSON Schema. Os exemplos são exemplos de contrato; não representam uma execução real já concluída. A revisão documental 0.2 complementa este desenho com um perfil CJPG executável em [10 — Contratos validáveis](10-CONTRATOS-VALIDAVEIS.md). Para esse perfil, os tipos e as invariantes detalhadas de 10 prevalecem sobre enumerações conceituais abreviadas deste documento.

## 1. Identidades e versões

`claw_id` identifica uma integração lógica. `installation_id` identifica a implantação real de um sistema. `capability_id` identifica uma função semântica. `recipe_id` e `recipe_version` identificam a implementação imutável. `run_id` identifica uma execução. `evidence_id` identifica um artefato ou observação com política de acesso.

Formato recomendado de capacidade: `tjsp.cjpg.search_decisions`, `tjsp.cpopg.get_case`, `stj.scon.search_decisions`, `pje.trt2.list_documents`, `eproc.jfrs.get_document`. A versão é campo explícito; não extrair versão do nome.

## 2. Invocation

```json
{
  "protocol_version": "0.1",
  "request_id": "req_20261003_001",
  "capability_id": "tjsp.cjpg.search_decisions",
  "capability_version": "1.0.0",
  "installation_id": "tjsp-esaj-cjpg",
  "arguments": {
    "query": "dano moral",
    "date_from": "2026-09-01",
    "date_to": "2026-09-02",
    "date_kind": "availability",
    "limit": 10
  },
  "session_ref": null,
  "options": {
    "freshness": "live",
    "max_age_ms": 0,
    "transport": "auto",
    "allow_partial": true,
    "allow_repair": true
  },
  "budget": {
    "deadline_ms": 120000,
    "max_pages": 2,
    "max_documents": 10,
    "max_model_calls": 6,
    "max_repair_candidates": 1,
    "max_download_bytes": 20000000
  },
  "idempotency_key": "caller-operation-001"
}
```

Os valores de orçamento acima são configurações iniciais propostas, não limites medidos dos portais. A política do servidor pode estreitá-los. A sessão é opcional para uma capacidade pública; seu uso não transforma a chamada em autorização para acessar recursos privados.

Campos de identidade de usuário/organização não são controlados por argumentos do modelo. O gateway acrescenta um `ExecutionContext` confiável contendo principal, tenant, papéis, política, trace e referências de segredo.

Validações obrigatórias: rejeitar campos desconhecidos no envelope; validar `arguments` pelo schema exato da capacidade; verificar intervalo de datas; limitar tamanho de texto e listas; impedir URL livre em campos que deveriam ser referências de recurso. O resultado da negociação deve informar a versão efetivamente selecionada.

Idempotency key associa principal, tenant e chave a uma execução. O fingerprint da chamada normalizada inclui capacidade/versão, instalação, argumentos, referência de sessão, opções e orçamento; exclui request_id e a própria chave. Reutilizar a mesma chave com conteúdo diferente retorna conflito. Reenviar a mesma requisição consulta o mesmo run. Uma nova consulta com frescor atual usa nova chave; idempotência não é cache de resultados. Defaults e concorrência estão definidos em [13 — API e estados](13-API-ESTADOS-E-CONCORRENCIA.md).

## 3. Resultado de execução

```json
{
  "protocol_version": "0.1",
  "run_id": "run_example_001",
  "status": "running",
  "capability_id": "tjsp.cjpg.search_decisions",
  "capability_version": "1.0.0",
  "installation_id": "tjsp-esaj-cjpg",
  "data": {"items": []},
  "coverage": {
    "sources_requested": ["tjsp-esaj-cjpg"],
    "sources_completed": [],
    "pages_visited": 0,
    "items_returned": 0,
    "total_reported": null,
    "complete": false,
    "source_exhausted": null,
    "stop_reason": null
  },
  "verification": {
    "status": "not_run",
    "checks": [],
    "evidence_refs": []
  },
  "execution": {
    "recipe_id": "tjsp-cjpg-search",
    "recipe_version": "0.1.0",
    "transport": "browser",
    "model_calls": 0,
    "repaired": false
  },
  "errors": [],
  "continuation": null
}
```

O exemplo representa uma execução ainda em andamento: os resultados e as verificações ainda não estão disponíveis. `success` exige verificação aprovada e cobertura completa do escopo solicitado. `partial` exige dados efetivamente úteis, verificações aplicáveis e motivo de incompletude; sem dados úteis e sem conclusão válida, retornar erro ou espera, não fabricar sucesso parcial.

Estados públicos: `accepted`, `running`, `needs_input`, `needs_auth`, `suspended`, `success`, `partial`, `failed`, `cancelled`, `uncertain_effect`. Estados de execução detalhados estão no documento 04.

`complete` é relativo ao escopo solicitado: retornar 10 decisões pedidas pode satisfazer o pedido, embora não esgote a fonte. Registrar separadamente `source_exhausted`. `total_reported` é o total anunciado pela fonte naquele momento, não uma garantia de contagem estável durante paginação.

O snapshot acima é um estado intermediário, não a resposta final da consulta. A API de controle usa RunView para progresso e mantém `/result` explicitamente indisponível enquanto não houver resposta publicável, conforme documento 13. Resultados sintéticos completos de sucesso, vazio, parcial, autenticação e falha estão em [12 — Exemplos](12-EXEMPLOS-E-TESTES-DE-CONTRATO.md).

## 4. Objetos jurídicos

### 4.1 CaseRecord

Campos: `case_ref`, `source_id`, `installation_id`, `case_number_raw`, `case_number_normalized`, `number_kind`, `court`, `level`, `class_raw`, `subject_raw`, `status_raw`, `movements`, `document_refs`, `observed_at`, `evidence_refs`.

`number_kind` admite `cnj`, `legacy`, `source_internal`. O normalizado pode ser nulo quando não houver conversão confiável. O identificador interno da fonte complementa o número processual, não o substitui silenciosamente.

### 4.2 MovementRecord

Campos: `movement_ref`, `case_ref`, `source_event_id`, `sequence_in_source`, `occurred_at`, `date_precision`, `title_raw`, `description_raw`, `document_refs`, `evidence_refs`. Data sem horário mantém precisão de dia; não inventar meia-noite como horário real do movimento.

### 4.3 DecisionRecord

Campos: `decision_ref`, `source_id`, `source_document_id`, `case_number_raw`, `decision_kind`, `decision_kind_basis`, `court`, `panel_raw`, `judge_raw`, `judgment_date`, `publication_date`, `availability_date`, `summary`, `full_text_ref`, `source_url`, `observed_at`, `evidence_refs`.

`decision_kind_basis` distingue informado pela fonte de classificação derivada. Campos ausentes são nulos com razão opcional. `summary` identifica se é ementa da fonte ou resumo produzido. Nunca preencher `full_text_ref` com link de ementa sem rotular corretamente.

### 4.4 DocumentArtifact

Campos: `artifact_id`, `resource_ref`, `source_url_canonical`, `retrieved_at`, `media_type_declared`, `media_type_detected`, `byte_length`, `sha256`, `storage_ref`, `access_scope`, `expires_at`, `text_derivative_ref`, `extraction_method`.

`storage_ref` é referência autorizada, não caminho arbitrário fornecido pelo modelo. URL com token é sanitizada no registro geral; uma referência protegida conserva o necessário para reprodução enquanto válida. Retenção e acesso são aplicados também às derivações OCR/texto.

### 4.5 EvidenceRecord

Campos: `evidence_id`, `run_id`, `step_id`, `kind`, `observed_at`, `source_origin`, `resource_ref`, `artifact_ref`, `locator`, `content_hash`, `redaction_policy`, `access_scope`.

Tipos: `page_observation`, `response_metadata`, `document`, `extracted_fragment`, `verification_report`. `locator` pode identificar página de PDF ou trecho DOM; só registrar localizador realmente disponível. Não inventar página ou linha de fonte.

## 5. ClawManifest e CapabilitySpec

```yaml
claw_id: tjsp.cjpg
version: 0.1.0
installations:
  - id: tjsp-esaj-cjpg
    entry_url: https://esaj.tjsp.jus.br/cjpg/
    allowed_origins:
      - https://esaj.tjsp.jus.br
capabilities:
  - id: tjsp.cjpg.search_decisions
    version: 1.0.0
    effect: read
    access: public
    input_schema_ref: schemas/search_decisions.json
    output_schema_ref: schemas/decision_search_result.json
    verifier_ref: tjsp.cjpg.search.v1
    certification: experimental
    transports: [browser]
```

Os paths de schemas do exemplo representam arquivos a gerar durante a implementação; não são arquivos ausentes deste pacote documental. A especificação de campos está neste documento.

`effect`: `read`, `download`, `draft_write`, `external_write`, `legal_acknowledgment`, `signature`, `submission`. O manifesto declara o efeito mais alto do percurso. Ações intermediárias podem elevar a classificação e exigir política correspondente.

## 6. Receita e DSL

Campos obrigatórios de `Recipe`: ID, versão, capacidade/versão, instalação, variante, transporte, estado de certificação, parâmetros, pré-condições, passos, verificadores, limites, origem e hash de conteúdo.

Cada passo contém `step_id`, `operation`, `arguments`, `preconditions`, `postconditions`, `timeout_ms`, `effect`, `retry_policy`, `on_failure`. A lista de operações é fechada e versionada.

| Operação | Entrada essencial | Saída | Regra |
|---|---|---|---|
| navigate | URL registrada/referência | nova observação | Verificar origem após redirects. |
| locate | estratégia e escopo | referência efêmera | Cardinalidade e papel esperados. |
| fill | alvo e binding | leitura posterior | Confirmar valor aplicado. |
| click | alvo | recibo de ação | Guardas antes do envio. |
| select | alvo e opção observada | estado selecionado | Não inventar valores de opção. |
| wait_for | condição declarativa | observação | Prazo finito, sem espera infinita. |
| extract | parser versionado | objetos e relatório | Sem chamada LLM implícita. |
| paginate | referência do paginador | páginas/itens | Limite e detecção de progresso. |
| download | referência observada | artefato | Tipo, tamanho e vínculo verificados. |
| http_request | template certificado | resposta/artefato | Mesmo contexto e política. |
| verify | verificador registrado | relatório | Não substituível pelo reparador. |
| checkpoint | identidade semântica | marcador persistido | Não persistir índice DOM como retomada. |

Bindings usam objetos `{"input":"query"}`, `{"const":"DESC"}`, `{"state":"selected_document_ref"}` ou `{"secret_ref":"session_token"}`. A sintaxe não avalia código. Condições permitidas são operadores definidos como igualdade, existência, contagem, pertencimento e correspondência de formato validado. Expressões regulares devem ter limites para evitar execução patológica.

### 6.1 Exemplo do trecho inicial CJPG

```yaml
recipe_id: tjsp-cjpg-search
recipe_version: 0.1.0
certification: candidate
transport: browser
steps:
  - step_id: open
    operation: navigate
    arguments:
      url: {const: "https://esaj.tjsp.jus.br/cjpg/"}
    effect: read
  - step_id: query
    operation: fill
    arguments:
      locator: {css: 'input[name="dadosConsulta.pesquisaLivre"]'}
      value: {input: query}
    effect: read
  - step_id: submit_search
    operation: click
    arguments:
      locator: {css: '#pbSubmit'}
    effect: read
```

Os campos e o botão foram observados no formulário público. Esse trecho não constitui uma receita certificada completa: faltam bindings de filtros, espera de resultados, parser, paginação, verificação e testes. A implementação deve completá-los antes de publicar.

## 7. Falhas tipadas

`JcpError` contém `code`, `message`, `stage`, `retryable`, `effect_state`, `evidence_refs`, `next_action` e `cause_ref`. Não expor stacktrace ou segredos como mensagem pública.

| Código | Tratamento padrão |
|---|---|
| INVALID_INPUT / UNSUPPORTED_CAPABILITY | Corrigir entrada ou escolher capacidade disponível. |
| POLICY_DENIED / ACCESS_DENIED | Encerrar; não iniciar reparo. |
| AUTH_REQUIRED / AUTH_EXPIRED | Suspender e solicitar sessão pronta. |
| ACCESS_CHALLENGE | Encaminhar ao adaptador de desafio. |
| RATE_LIMITED | Backoff limitado e circuit breaker. |
| PORTAL_UNAVAILABLE / TRANSPORT_ERROR | Recuperação de infraestrutura limitada. |
| SELECTOR_NOT_FOUND / AMBIGUOUS_TARGET | Recuperação estrutural ou decisão delimitada. |
| PAGE_STATE_MISMATCH | Reobservar e diagnosticar antes de agir. |
| PARSER_DRIFT / TRUNCATED_RESPONSE | Interromper extração e produzir diagnóstico. |
| VERIFICATION_FAILED | Não publicar sucesso; investigar resultado. |
| REPAIR_FAILED / RECIPE_CONFLICT | Preservar candidato e versão anterior. |
| BUDGET_EXHAUSTED / DEADLINE_EXCEEDED | Encerrar ou retornar parcial permitido. |
| UNCERTAIN_EFFECT | Reconciliar antes de qualquer repetição. |

## 8. Eventos e API de controle

`RunEvent`: `event_id`, `run_id`, `sequence`, `timestamp`, `type`, `step_id`, `recipe_version`, `payload_ref`. Tipos mínimos: accepted, policy_checked, session_ready, recipe_selected, action_prepared, action_dispatched, action_confirmed, action_uncertain, evidence_captured, recovery_started, repair_proposed, verification_completed, recipe_promoted, run_completed.

API proposta: `POST /v1/runs`, `GET /v1/runs/{id}`, `GET /v1/runs/{id}/result`, `POST /v1/runs/{id}/cancel`, `POST /v1/runs/{id}/resume`, `GET /v1/capabilities`. Retomada exige token ligado à suspensão e ao principal. Resultado indisponível antes do fim não deve parecer resposta vazia.

## 9. Extensibilidade

Uma nova claw fornece manifesto, schemas, parsers, verificadores, configuração de instalação e receitas iniciais ou procedimento de descoberta. O núcleo não deve ganhar condições `if tribunal == X` espalhadas por todo o executor. Exceções específicas vivem no adaptador da instalação e são cobertas por testes.
