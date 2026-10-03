# Contratos validáveis e schemas de referência

Revisão documental 0.2. O protocolo proposto continua em 0.1 e a capacidade de referência em 1.0.0: ainda não existe uma implementação pública lançada cuja compatibilidade precise ser migrada.

Este documento entrega um perfil executável de contrato para `tjsp.cjpg.search_decisions`. Ele formaliza o primeiro caso vertical; não pretende fingir que schemas de todos os portais foram implementados. A arquitetura dos demais objetos está no documento 03. Cada nova capacidade precisa de seus próprios modelos e verificadores.

## 1. O que foi executado

O código Python abaixo foi executado localmente com Python 3.12.14 e Pydantic 2.13.5. Os 34 casos de contrato do documento 12 passaram. Isso verifica comportamento dos modelos, consistência entre chamada e resposta e exportação de schemas. Não é teste de navegação, de autenticidade de evidência, de integração Browser Use ou de consulta judicial real.

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

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


Id = Annotated[str, StringConstraints(min_length=1, max_length=200, pattern=r'^[A-Za-z0-9_.:-]+$')]
Version = Annotated[str, StringConstraints(pattern=r'^\d+\.\d+\.\d+$')]
NonEmpty = Annotated[str, StringConstraints(min_length=1, max_length=4096)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, validate_default=True)


class CjpgSearchArguments(StrictModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    date_from: date
    date_to: date
    date_kind: Literal['availability']
    limit: int = Field(ge=1, le=100)
    cursor: Id | None = None

    @model_validator(mode='after')
    def chronological(self) -> Self:
        if self.date_from > self.date_to:
            raise ValueError('date_from must not exceed date_to')
        return self


class Options(StrictModel):
    freshness: Literal['live', 'cached_if_fresh'] = 'live'
    max_age_ms: int = Field(default=0, ge=0, le=86400000)
    transport: Literal['auto', 'browser', 'http'] = 'auto'
    allow_partial: bool = True
    allow_repair: bool = True

    @model_validator(mode='after')
    def freshness_bounds(self) -> Self:
        if self.freshness == 'live' and self.max_age_ms != 0:
            raise ValueError('live requires max_age_ms=0')
        if self.freshness == 'cached_if_fresh' and self.max_age_ms <= 0:
            raise ValueError('cached_if_fresh requires a positive max_age_ms')
        return self


class Budget(StrictModel):
    deadline_ms: int = Field(ge=1, le=600000)
    max_pages: int = Field(ge=1, le=100)
    max_documents: int = Field(ge=0, le=100)
    max_model_calls: int = Field(ge=0, le=30)
    max_repair_candidates: int = Field(ge=0, le=3)
    max_download_bytes: int = Field(ge=0, le=100000000)


class CjpgInvocation(StrictModel):
    protocol_version: Literal['0.1']
    request_id: Id
    capability_id: Literal['tjsp.cjpg.search_decisions']
    capability_version: Literal['1.0.0']
    installation_id: Literal['tjsp-esaj-cjpg']
    arguments: CjpgSearchArguments
    session_ref: Id | None
    options: Options
    budget: Budget
    idempotency_key: Id


CheckId = Literal['schema', 'identity', 'filters', 'coverage', 'provenance']


class Check(StrictModel):
    check_id: CheckId
    status: Literal['passed', 'failed']
    evidence_refs: list[Id] = Field(min_length=1, max_length=100)


class Verification(StrictModel):
    status: Literal['not_run', 'passed', 'failed']
    checks: list[Check] = Field(max_length=5)
    evidence_refs: list[Id] = Field(max_length=100)

    @model_validator(mode='after')
    def consistent_report(self) -> Self:
        ids = [c.check_id for c in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate verification check')
        known_refs = set(self.evidence_refs)
        if any(not set(c.evidence_refs) <= known_refs for c in self.checks):
            raise ValueError('check evidence must be listed in the report')
        if self.status == 'not_run' and (self.checks or self.evidence_refs):
            raise ValueError('not_run has no completed checks or evidence report')
        if self.status == 'passed':
            required = {'schema', 'identity', 'filters', 'coverage', 'provenance'}
            if set(ids) != required or any(c.status != 'passed' for c in self.checks):
                raise ValueError('passed requires all five successful checks')
        if self.status == 'failed' and not any(c.status == 'failed' for c in self.checks):
            raise ValueError('failed report requires a failed check')
        return self


class Coverage(StrictModel):
    sources_requested: list[Id] = Field(min_length=1, max_length=10)
    sources_completed: list[Id] = Field(max_length=10)
    pages_visited: int = Field(ge=0)
    items_returned: int = Field(ge=0)
    total_reported: int | None = Field(ge=0)
    complete: bool
    source_exhausted: bool | None
    stop_reason: Literal['page_limit', 'item_limit', 'document_limit', 'deadline', 'model_budget', 'source_unavailable', 'cancelled', 'access_challenge', 'no_progress'] | None

    @model_validator(mode='after')
    def coherent_sources(self) -> Self:
        if len(set(self.sources_requested)) != len(self.sources_requested):
            raise ValueError('duplicate requested source')
        if len(set(self.sources_completed)) != len(self.sources_completed):
            raise ValueError('duplicate completed source')
        if not set(self.sources_completed) <= set(self.sources_requested):
            raise ValueError('completed source was not requested')
        if self.complete and set(self.sources_completed) != set(self.sources_requested):
            raise ValueError('complete scope requires all requested sources completed')
        return self


class DecisionSummary(StrictModel):
    kind: Literal['source_excerpt', 'source_headnote', 'model_summary']
    text: NonEmpty


class DecisionRecord(StrictModel):
    decision_ref: Id
    source_id: Literal['tjsp-esaj-cjpg']
    source_document_id: Id | None
    case_number_raw: NonEmpty | None
    decision_kind: Literal['sentence', 'interlocutory', 'judgment', 'other', 'unknown']
    decision_kind_basis: Literal['source', 'derived', 'unknown']
    court: NonEmpty
    panel_raw: NonEmpty | None
    judge_raw: NonEmpty | None
    judgment_date: date | None
    publication_date: date | None
    availability_date: date | None
    summary: DecisionSummary | None
    full_text_ref: Id | None
    source_url: Annotated[str, StringConstraints(pattern=r'^https://[^\s]+$', max_length=4096)]
    observed_at: datetime
    evidence_refs: list[Id] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def aware_timestamp(self) -> Self:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError('observed_at must contain timezone information')
        return self


class SearchData(StrictModel):
    items: list[DecisionRecord] = Field(max_length=100)


ErrorCode = Literal['INVALID_INPUT', 'UNSUPPORTED_CAPABILITY', 'POLICY_DENIED', 'ACCESS_DENIED', 'AUTH_REQUIRED', 'AUTH_EXPIRED', 'ACCESS_CHALLENGE', 'RATE_LIMITED', 'PORTAL_UNAVAILABLE', 'TRANSPORT_ERROR', 'SELECTOR_NOT_FOUND', 'AMBIGUOUS_TARGET', 'PAGE_STATE_MISMATCH', 'PARSER_DRIFT', 'TRUNCATED_RESPONSE', 'VERIFICATION_FAILED', 'REPAIR_FAILED', 'RECIPE_CONFLICT', 'BUDGET_EXHAUSTED', 'DEADLINE_EXCEEDED', 'UNCERTAIN_EFFECT']


class JcpError(StrictModel):
    code: ErrorCode
    message: NonEmpty
    stage: Id
    retryable: bool
    effect_state: Literal['not_dispatched', 'confirmed', 'uncertain']
    evidence_refs: list[Id] = Field(max_length=100)
    next_action: Literal['none', 'correct_input', 'authenticate', 'wait', 'repair', 'reconcile', 'contact_operator']
    cause_ref: Id | None


class Execution(StrictModel):
    recipe_id: Id | None
    recipe_version: Version | None
    transport: Literal['browser', 'http'] | None
    model_calls: int = Field(ge=0)
    repaired: bool

    @model_validator(mode='after')
    def recipe_pair(self) -> Self:
        if (self.recipe_id is None) != (self.recipe_version is None):
            raise ValueError('recipe_id and recipe_version must be present together')
        return self


RunStatus = Literal['accepted', 'running', 'needs_input', 'needs_auth', 'suspended', 'success', 'partial', 'failed', 'cancelled', 'uncertain_effect']


class CjpgResult(StrictModel):
    protocol_version: Literal['0.1']
    run_id: Id
    status: RunStatus
    capability_id: Literal['tjsp.cjpg.search_decisions']
    capability_version: Literal['1.0.0']
    installation_id: Literal['tjsp-esaj-cjpg']
    data: SearchData
    coverage: Coverage
    verification: Verification
    execution: Execution
    errors: list[JcpError] = Field(max_length=20)
    continuation: Id | None

    @model_validator(mode='after')
    def consistent_result(self) -> Self:
        items = self.data.items
        if self.coverage.items_returned != len(items):
            raise ValueError('items_returned must equal the number of published items')
        if self.coverage.sources_requested != [self.installation_id]:
            raise ValueError('this vertical profile supports exactly its declared installation')
        if len({i.decision_ref for i in items}) != len(items):
            raise ValueError('duplicate decision_ref')
        if self.status in {'success', 'partial'}:
            if self.verification.status != 'passed' or self.coverage.pages_visited < 1:
                raise ValueError('published result requires verification and a visited page')
            refs = set(self.verification.evidence_refs)
            if any(not set(i.evidence_refs) <= refs for i in items):
                raise ValueError('published item requires evidence in verification report')
            if self.execution.recipe_id is None or self.execution.transport is None:
                raise ValueError('published result requires execution provenance')
        elif items:
            raise ValueError('this profile publishes items only in success/partial')
        if self.status == 'success' and (not self.coverage.complete or self.errors or self.coverage.stop_reason is not None):
            raise ValueError('success requires complete scope, no error and no interruption')
        if self.status == 'success' and not items and self.coverage.source_exhausted is not True:
            raise ValueError('empty success requires confirmation that the source is exhausted')
        if self.status == 'partial' and (not items or self.coverage.complete or self.coverage.stop_reason is None):
            raise ValueError('partial requires useful items and a stated incomplete scope')
        if self.status == 'failed' and not self.errors:
            raise ValueError('failed requires a typed error')
        if self.status == 'needs_auth' and not any(e.code in {'AUTH_REQUIRED', 'AUTH_EXPIRED'} for e in self.errors):
            raise ValueError('needs_auth requires an authentication error')
        if self.status == 'uncertain_effect' and not any(e.code == 'UNCERTAIN_EFFECT' and e.effect_state == 'uncertain' for e in self.errors):
            raise ValueError('uncertain_effect requires its corresponding error')
        return self


def validate_against_invocation(invocation: CjpgInvocation, result: CjpgResult) -> None:
    """Checks requiring both envelopes; this does not verify the source itself."""
    if (result.capability_id, result.capability_version, result.installation_id) != (
        invocation.capability_id, invocation.capability_version, invocation.installation_id
    ):
        raise ValueError('result does not belong to the requested capability')
    if result.execution.model_calls > invocation.budget.max_model_calls:
        raise ValueError('model budget exceeded')
    if result.coverage.pages_visited > invocation.budget.max_pages:
        raise ValueError('page budget exceeded')
    if len(result.data.items) > invocation.arguments.limit:
        raise ValueError('requested item limit exceeded')
    if result.status == 'partial' and not invocation.options.allow_partial:
        raise ValueError('partial result was not requested')
    if result.execution.repaired and not invocation.options.allow_repair:
        raise ValueError('repair was not allowed')
    if invocation.options.transport != 'auto' and result.execution.transport not in (None, invocation.options.transport):
        raise ValueError('explicit transport was not respected')
    if result.status == 'success' and len(result.data.items) < invocation.arguments.limit and result.coverage.source_exhausted is not True:
        raise ValueError('fewer items than requested requires source exhaustion')
    for item in result.data.items:
        if item.availability_date is not None and not (invocation.arguments.date_from <= item.availability_date <= invocation.arguments.date_to):
            raise ValueError('known availability date violates the requested filter')
```

## 5. JSON Schema da chamada

Schema gerado a partir de `CjpgInvocation.model_json_schema(mode="validation")`, com declaração do dialeto 2020-12. Referências `$defs` são locais; não há downloads durante a resolução. As invariantes relacionais continuam sendo as do código acima.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Budget": {
      "additionalProperties": false,
      "properties": {
        "deadline_ms": {
          "maximum": 600000,
          "minimum": 1,
          "title": "Deadline Ms",
          "type": "integer"
        },
        "max_pages": {
          "maximum": 100,
          "minimum": 1,
          "title": "Max Pages",
          "type": "integer"
        },
        "max_documents": {
          "maximum": 100,
          "minimum": 0,
          "title": "Max Documents",
          "type": "integer"
        },
        "max_model_calls": {
          "maximum": 30,
          "minimum": 0,
          "title": "Max Model Calls",
          "type": "integer"
        },
        "max_repair_candidates": {
          "maximum": 3,
          "minimum": 0,
          "title": "Max Repair Candidates",
          "type": "integer"
        },
        "max_download_bytes": {
          "maximum": 100000000,
          "minimum": 0,
          "title": "Max Download Bytes",
          "type": "integer"
        }
      },
      "required": [
        "deadline_ms",
        "max_pages",
        "max_documents",
        "max_model_calls",
        "max_repair_candidates",
        "max_download_bytes"
      ],
      "title": "Budget",
      "type": "object"
    },
    "CjpgSearchArguments": {
      "additionalProperties": false,
      "properties": {
        "query": {
          "maxLength": 2000,
          "minLength": 1,
          "title": "Query",
          "type": "string"
        },
        "date_from": {
          "format": "date",
          "title": "Date From",
          "type": "string"
        },
        "date_to": {
          "format": "date",
          "title": "Date To",
          "type": "string"
        },
        "date_kind": {
          "const": "availability",
          "title": "Date Kind",
          "type": "string"
        },
        "limit": {
          "maximum": 100,
          "minimum": 1,
          "title": "Limit",
          "type": "integer"
        },
        "cursor": {
          "anyOf": [
            {
              "maxLength": 200,
              "minLength": 1,
              "pattern": "^[A-Za-z0-9_.:-]+$",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Cursor"
        }
      },
      "required": [
        "query",
        "date_from",
        "date_to",
        "date_kind",
        "limit"
      ],
      "title": "CjpgSearchArguments",
      "type": "object"
    },
    "Options": {
      "additionalProperties": false,
      "properties": {
        "freshness": {
          "default": "live",
          "enum": [
            "live",
            "cached_if_fresh"
          ],
          "title": "Freshness",
          "type": "string"
        },
        "max_age_ms": {
          "default": 0,
          "maximum": 86400000,
          "minimum": 0,
          "title": "Max Age Ms",
          "type": "integer"
        },
        "transport": {
          "default": "auto",
          "enum": [
            "auto",
            "browser",
            "http"
          ],
          "title": "Transport",
          "type": "string"
        },
        "allow_partial": {
          "default": true,
          "title": "Allow Partial",
          "type": "boolean"
        },
        "allow_repair": {
          "default": true,
          "title": "Allow Repair",
          "type": "boolean"
        }
      },
      "title": "Options",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "properties": {
    "protocol_version": {
      "const": "0.1",
      "title": "Protocol Version",
      "type": "string"
    },
    "request_id": {
      "maxLength": 200,
      "minLength": 1,
      "pattern": "^[A-Za-z0-9_.:-]+$",
      "title": "Request Id",
      "type": "string"
    },
    "capability_id": {
      "const": "tjsp.cjpg.search_decisions",
      "title": "Capability Id",
      "type": "string"
    },
    "capability_version": {
      "const": "1.0.0",
      "title": "Capability Version",
      "type": "string"
    },
    "installation_id": {
      "const": "tjsp-esaj-cjpg",
      "title": "Installation Id",
      "type": "string"
    },
    "arguments": {
      "$ref": "#/$defs/CjpgSearchArguments"
    },
    "session_ref": {
      "anyOf": [
        {
          "maxLength": 200,
          "minLength": 1,
          "pattern": "^[A-Za-z0-9_.:-]+$",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Session Ref"
    },
    "options": {
      "$ref": "#/$defs/Options"
    },
    "budget": {
      "$ref": "#/$defs/Budget"
    },
    "idempotency_key": {
      "maxLength": 200,
      "minLength": 1,
      "pattern": "^[A-Za-z0-9_.:-]+$",
      "title": "Idempotency Key",
      "type": "string"
    }
  },
  "required": [
    "protocol_version",
    "request_id",
    "capability_id",
    "capability_version",
    "installation_id",
    "arguments",
    "session_ref",
    "options",
    "budget",
    "idempotency_key"
  ],
  "title": "CjpgInvocation",
  "type": "object"
}
```

## 6. JSON Schema da resposta

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Check": {
      "additionalProperties": false,
      "properties": {
        "check_id": {
          "enum": [
            "schema",
            "identity",
            "filters",
            "coverage",
            "provenance"
          ],
          "title": "Check Id",
          "type": "string"
        },
        "status": {
          "enum": [
            "passed",
            "failed"
          ],
          "title": "Status",
          "type": "string"
        },
        "evidence_refs": {
          "items": {
            "maxLength": 200,
            "minLength": 1,
            "pattern": "^[A-Za-z0-9_.:-]+$",
            "type": "string"
          },
          "maxItems": 100,
          "minItems": 1,
          "title": "Evidence Refs",
          "type": "array"
        }
      },
      "required": [
        "check_id",
        "status",
        "evidence_refs"
      ],
      "title": "Check",
      "type": "object"
    },
    "Coverage": {
      "additionalProperties": false,
      "properties": {
        "sources_requested": {
          "items": {
            "maxLength": 200,
            "minLength": 1,
            "pattern": "^[A-Za-z0-9_.:-]+$",
            "type": "string"
          },
          "maxItems": 10,
          "minItems": 1,
          "title": "Sources Requested",
          "type": "array"
        },
        "sources_completed": {
          "items": {
            "maxLength": 200,
            "minLength": 1,
            "pattern": "^[A-Za-z0-9_.:-]+$",
            "type": "string"
          },
          "maxItems": 10,
          "title": "Sources Completed",
          "type": "array"
        },
        "pages_visited": {
          "minimum": 0,
          "title": "Pages Visited",
          "type": "integer"
        },
        "items_returned": {
          "minimum": 0,
          "title": "Items Returned",
          "type": "integer"
        },
        "total_reported": {
          "anyOf": [
            {
              "minimum": 0,
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "title": "Total Reported"
        },
        "complete": {
          "title": "Complete",
          "type": "boolean"
        },
        "source_exhausted": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "title": "Source Exhausted"
        },
        "stop_reason": {
          "anyOf": [
            {
              "enum": [
                "page_limit",
                "item_limit",
                "document_limit",
                "deadline",
                "model_budget",
                "source_unavailable",
                "cancelled",
                "access_challenge",
                "no_progress"
              ],
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Stop Reason"
        }
      },
      "required": [
        "sources_requested",
        "sources_completed",
        "pages_visited",
        "items_returned",
        "total_reported",
        "complete",
        "source_exhausted",
        "stop_reason"
      ],
      "title": "Coverage",
      "type": "object"
    },
    "DecisionRecord": {
      "additionalProperties": false,
      "properties": {
        "decision_ref": {
          "maxLength": 200,
          "minLength": 1,
          "pattern": "^[A-Za-z0-9_.:-]+$",
          "title": "Decision Ref",
          "type": "string"
        },
        "source_id": {
          "const": "tjsp-esaj-cjpg",
          "title": "Source Id",
          "type": "string"
        },
        "source_document_id": {
          "anyOf": [
            {
              "maxLength": 200,
              "minLength": 1,
              "pattern": "^[A-Za-z0-9_.:-]+$",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Source Document Id"
        },
        "case_number_raw": {
          "anyOf": [
            {
              "maxLength": 4096,
              "minLength": 1,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Case Number Raw"
        },
        "decision_kind": {
          "enum": [
            "sentence",
            "interlocutory",
            "judgment",
            "other",
            "unknown"
          ],
          "title": "Decision Kind",
          "type": "string"
        },
        "decision_kind_basis": {
          "enum": [
            "source",
            "derived",
            "unknown"
          ],
          "title": "Decision Kind Basis",
          "type": "string"
        },
        "court": {
          "maxLength": 4096,
          "minLength": 1,
          "title": "Court",
          "type": "string"
        },
        "panel_raw": {
          "anyOf": [
            {
              "maxLength": 4096,
              "minLength": 1,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Panel Raw"
        },
        "judge_raw": {
          "anyOf": [
            {
              "maxLength": 4096,
              "minLength": 1,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Judge Raw"
        },
        "judgment_date": {
          "anyOf": [
            {
              "format": "date",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Judgment Date"
        },
        "publication_date": {
          "anyOf": [
            {
              "format": "date",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Publication Date"
        },
        "availability_date": {
          "anyOf": [
            {
              "format": "date",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Availability Date"
        },
        "summary": {
          "anyOf": [
            {
              "$ref": "#/$defs/DecisionSummary"
            },
            {
              "type": "null"
            }
          ]
        },
        "full_text_ref": {
          "anyOf": [
            {
              "maxLength": 200,
              "minLength": 1,
              "pattern": "^[A-Za-z0-9_.:-]+$",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Full Text Ref"
        },
        "source_url": {
          "maxLength": 4096,
          "pattern": "^https://[^\\s]+$",
          "title": "Source Url",
          "type": "string"
        },
        "observed_at": {
          "format": "date-time",
          "title": "Observed At",
          "type": "string"
        },
        "evidence_refs": {
          "items": {
            "maxLength": 200,
            "minLength": 1,
            "pattern": "^[A-Za-z0-9_.:-]+$",
            "type": "string"
          },
          "maxItems": 100,
          "minItems": 1,
          "title": "Evidence Refs",
          "type": "array"
        }
      },
      "required": [
        "decision_ref",
        "source_id",
        "source_document_id",
        "case_number_raw",
        "decision_kind",
        "decision_kind_basis",
        "court",
        "panel_raw",
        "judge_raw",
        "judgment_date",
        "publication_date",
        "availability_date",
        "summary",
        "full_text_ref",
        "source_url",
        "observed_at",
        "evidence_refs"
      ],
      "title": "DecisionRecord",
      "type": "object"
    },
    "DecisionSummary": {
      "additionalProperties": false,
      "properties": {
        "kind": {
          "enum": [
            "source_excerpt",
            "source_headnote",
            "model_summary"
          ],
          "title": "Kind",
          "type": "string"
        },
        "text": {
          "maxLength": 4096,
          "minLength": 1,
          "title": "Text",
          "type": "string"
        }
      },
      "required": [
        "kind",
        "text"
      ],
      "title": "DecisionSummary",
      "type": "object"
    },
    "Execution": {
      "additionalProperties": false,
      "properties": {
        "recipe_id": {
          "anyOf": [
            {
              "maxLength": 200,
              "minLength": 1,
              "pattern": "^[A-Za-z0-9_.:-]+$",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Recipe Id"
        },
        "recipe_version": {
          "anyOf": [
            {
              "pattern": "^\\d+\\.\\d+\\.\\d+$",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Recipe Version"
        },
        "transport": {
          "anyOf": [
            {
              "enum": [
                "browser",
                "http"
              ],
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Transport"
        },
        "model_calls": {
          "minimum": 0,
          "title": "Model Calls",
          "type": "integer"
        },
        "repaired": {
          "title": "Repaired",
          "type": "boolean"
        }
      },
      "required": [
        "recipe_id",
        "recipe_version",
        "transport",
        "model_calls",
        "repaired"
      ],
      "title": "Execution",
      "type": "object"
    },
    "JcpError": {
      "additionalProperties": false,
      "properties": {
        "code": {
          "enum": [
            "INVALID_INPUT",
            "UNSUPPORTED_CAPABILITY",
            "POLICY_DENIED",
            "ACCESS_DENIED",
            "AUTH_REQUIRED",
            "AUTH_EXPIRED",
            "ACCESS_CHALLENGE",
            "RATE_LIMITED",
            "PORTAL_UNAVAILABLE",
            "TRANSPORT_ERROR",
            "SELECTOR_NOT_FOUND",
            "AMBIGUOUS_TARGET",
            "PAGE_STATE_MISMATCH",
            "PARSER_DRIFT",
            "TRUNCATED_RESPONSE",
            "VERIFICATION_FAILED",
            "REPAIR_FAILED",
            "RECIPE_CONFLICT",
            "BUDGET_EXHAUSTED",
            "DEADLINE_EXCEEDED",
            "UNCERTAIN_EFFECT"
          ],
          "title": "Code",
          "type": "string"
        },
        "message": {
          "maxLength": 4096,
          "minLength": 1,
          "title": "Message",
          "type": "string"
        },
        "stage": {
          "maxLength": 200,
          "minLength": 1,
          "pattern": "^[A-Za-z0-9_.:-]+$",
          "title": "Stage",
          "type": "string"
        },
        "retryable": {
          "title": "Retryable",
          "type": "boolean"
        },
        "effect_state": {
          "enum": [
            "not_dispatched",
            "confirmed",
            "uncertain"
          ],
          "title": "Effect State",
          "type": "string"
        },
        "evidence_refs": {
          "items": {
            "maxLength": 200,
            "minLength": 1,
            "pattern": "^[A-Za-z0-9_.:-]+$",
            "type": "string"
          },
          "maxItems": 100,
          "title": "Evidence Refs",
          "type": "array"
        },
        "next_action": {
          "enum": [
            "none",
            "correct_input",
            "authenticate",
            "wait",
            "repair",
            "reconcile",
            "contact_operator"
          ],
          "title": "Next Action",
          "type": "string"
        },
        "cause_ref": {
          "anyOf": [
            {
              "maxLength": 200,
              "minLength": 1,
              "pattern": "^[A-Za-z0-9_.:-]+$",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Cause Ref"
        }
      },
      "required": [
        "code",
        "message",
        "stage",
        "retryable",
        "effect_state",
        "evidence_refs",
        "next_action",
        "cause_ref"
      ],
      "title": "JcpError",
      "type": "object"
    },
    "SearchData": {
      "additionalProperties": false,
      "properties": {
        "items": {
          "items": {
            "$ref": "#/$defs/DecisionRecord"
          },
          "maxItems": 100,
          "title": "Items",
          "type": "array"
        }
      },
      "required": [
        "items"
      ],
      "title": "SearchData",
      "type": "object"
    },
    "Verification": {
      "additionalProperties": false,
      "properties": {
        "status": {
          "enum": [
            "not_run",
            "passed",
            "failed"
          ],
          "title": "Status",
          "type": "string"
        },
        "checks": {
          "items": {
            "$ref": "#/$defs/Check"
          },
          "maxItems": 5,
          "title": "Checks",
          "type": "array"
        },
        "evidence_refs": {
          "items": {
            "maxLength": 200,
            "minLength": 1,
            "pattern": "^[A-Za-z0-9_.:-]+$",
            "type": "string"
          },
          "maxItems": 100,
          "title": "Evidence Refs",
          "type": "array"
        }
      },
      "required": [
        "status",
        "checks",
        "evidence_refs"
      ],
      "title": "Verification",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "properties": {
    "protocol_version": {
      "const": "0.1",
      "title": "Protocol Version",
      "type": "string"
    },
    "run_id": {
      "maxLength": 200,
      "minLength": 1,
      "pattern": "^[A-Za-z0-9_.:-]+$",
      "title": "Run Id",
      "type": "string"
    },
    "status": {
      "enum": [
        "accepted",
        "running",
        "needs_input",
        "needs_auth",
        "suspended",
        "success",
        "partial",
        "failed",
        "cancelled",
        "uncertain_effect"
      ],
      "title": "Status",
      "type": "string"
    },
    "capability_id": {
      "const": "tjsp.cjpg.search_decisions",
      "title": "Capability Id",
      "type": "string"
    },
    "capability_version": {
      "const": "1.0.0",
      "title": "Capability Version",
      "type": "string"
    },
    "installation_id": {
      "const": "tjsp-esaj-cjpg",
      "title": "Installation Id",
      "type": "string"
    },
    "data": {
      "$ref": "#/$defs/SearchData"
    },
    "coverage": {
      "$ref": "#/$defs/Coverage"
    },
    "verification": {
      "$ref": "#/$defs/Verification"
    },
    "execution": {
      "$ref": "#/$defs/Execution"
    },
    "errors": {
      "items": {
        "$ref": "#/$defs/JcpError"
      },
      "maxItems": 20,
      "title": "Errors",
      "type": "array"
    },
    "continuation": {
      "anyOf": [
        {
          "maxLength": 200,
          "minLength": 1,
          "pattern": "^[A-Za-z0-9_.:-]+$",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Continuation"
    }
  },
  "required": [
    "protocol_version",
    "run_id",
    "status",
    "capability_id",
    "capability_version",
    "installation_id",
    "data",
    "coverage",
    "verification",
    "execution",
    "errors",
    "continuation"
  ],
  "title": "CjpgResult",
  "type": "object"
}
```

## 7. Evolução

Adicionar outro tribunal não significa trocar os Literals desta classe por strings livres e perder validação. O gateway seleciona um perfil pelo par capacidade/versão. Cada perfil usa schema fechado e seu verificador; o envelope comum pode ser extraído para uma base compartilhada na implementação.

Mudança compatível de documentação não é nova versão de protocolo. Mudança de significado de campo, filtro ou efeito exige nova versão de capacidade e matriz de compatibilidade. Receitas fixam essa versão. O cliente deve receber a versão selecionada, sem fallback silencioso para interpretação diferente.

Referências: [contrato conceitual](03-CONTRATOS-DO-PROTOCOLO.md), [semântica do executor](11-DSL-E-SEMANTICA-DO-EXECUTOR.md), [exemplos e testes](12-EXEMPLOS-E-TESTES-DE-CONTRATO.md), [API e estados](13-API-ESTADOS-E-CONCORRENCIA.md).
