# 04 — Especificação do Adapter CLEF

**JCP-application | browser-use + CLEF | PoC**

Esta especificação define o contrato do `CloudflareClefProvider` — o único ponto de integração
com o modelo CLEF no MVP. Tudo o que o CLEF pode receber e o que pode retornar está aqui.

---

## 1. Posição na arquitetura

```
Executor JCP (caminho estável)
    │
    ├── [locator encontrado] → Actor.click() / Actor.fill()
    │
    └── [locator falhou] → RelocalizationResolver
                               │
                               ├── Regra determinística resolveu? → ActionBroker
                               │
                               └── Candidatos ambíguos? → CloudflareClefProvider.decide()
                                                               │
                                                               ├── opção escolhida → gate → ActionBroker
                                                               │
                                                               └── abstain → escalar ou falhar
```

**CLEF não é chamado:**
- No caminho estável (receita funcionando)
- Para interpretar texto livre
- Para decidir sobre permissões ou autenticação
- Para validar o resultado jurídico
- Para decidir se uma receita está correta

---

## 2. Interface do provider

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class Candidate:
    id: str           # ID estável — NÃO é posição no array
    description: str  # descrição legível do candidato (ex: "campo de busca por texto")
    selector: str     # seletor CSS ou XPath do elemento

@dataclass
class DecisionRequest:
    operation_id: str             # ID único da decisão (para log)
    question: str                 # ex: "Qual elemento é o campo de busca de texto?"
    question_type: str            # "choice" | "noul"
    candidates: list[Candidate]   # DEVE ter pelo menos 2 e no máximo 8 no MVP
    context: str                  # descrição compacta do estado atual da página
    observation_id: str           # ID do estado DOM que gerou os candidatos
    observation_timestamp: datetime

@dataclass
class DecisionResult:
    chosen_id: str | None         # None = abstain
    score: float | None           # registrar, não usar como critério de go
    provider: str                 # "cloudflare/clef" ou "cloudflare/clef-flash"
    latency_ms: int
    abstained: bool

class DecisionProvider(ABC):
    @abstractmethod
    async def decide(self, request: DecisionRequest) -> DecisionResult: ...
```

---

## 3. CloudflareClefProvider — implementação

### 3.1 Configuração

```python
class CloudflareClefProvider(DecisionProvider):
    def __init__(
        self,
        account_id: str,          # de CLOUDFLARE_ACCOUNT_ID
        api_token: str,           # de CLOUDFLARE_API_TOKEN
        model: str = "@cf/cloudflare/clef",  # nunca clef-flash por padrão
        timeout_ms: int = 5000,
        max_candidates: int = 8,
    ): ...
```

### 3.2 Construção do payload

O payload enviado ao Workers AI **só pode conter**:
- A pergunta (`question`)
- Os candidatos como opções com IDs estáveis
- O contexto compacto da operação

**O payload NÃO pode conter:**
- Cookies ou tokens de sessão
- URL completa com parâmetros de busca
- Conteúdo jurídico dos resultados
- Histórico de ações anteriores
- Credenciais de qualquer tipo

```python
# Exemplo de payload permitido
payload = {
    "model": self.model,
    "messages": [],           # CLEF não usa chat — estrutura depende da API Workers AI
    "schema": {
        "question": request.question,
        "options": [
            {"id": c.id, "text": c.description}
            for c in request.candidates
        ]
    },
    "context": request.context[:2000]  # limite explícito de tamanho
}
```

> **Nota de implementação:** o endpoint exato e o formato do payload do Workers AI para CLEF
> precisam ser confirmados com a documentação atual da Cloudflare antes da implementação.
> A estrutura acima é baseada na inspeção do `joint_schema_model.py` e pode diferir da API REST.

### 3.3 Gate pós-decisão (determinístico)

```python
def apply_gate(self, request: DecisionRequest, result: DecisionResult) -> Candidate | None:
    # 1. Abstain → retornar None (escalar)
    if result.abstained or result.chosen_id is None:
        return None

    # 2. ID escolhido deve estar na lista original
    valid_ids = {c.id for c in request.candidates}
    if result.chosen_id not in valid_ids:
        raise DecisionGateError(f"CLEF retornou ID inválido: {result.chosen_id}")

    # 3. Observação não pode ser mais velha que o estado atual
    age = datetime.utcnow() - request.observation_timestamp
    if age.total_seconds() > 10:
        raise StaleObservationError("Observação expirada — não executar decisão")

    return next(c for c in request.candidates if c.id == result.chosen_id)
```

**Regra:** o gate nunca pode ser removido ou contornado, mesmo em modo de desenvolvimento.

---

## 4. Logging obrigatório

Toda chamada ao CLEF deve registrar:

```python
@dataclass
class ClefCallLog:
    operation_id: str
    model: str
    question_type: str
    num_candidates: int
    chosen_id: str | None
    abstained: bool
    gate_passed: bool
    latency_ms: int
    timestamp: datetime
    # NÃO registrar: descrições dos candidatos, contexto, seletores CSS
```

Os logs de decisão são **separados** dos logs de execução de ações.
Os logs não devem incluir conteúdo que possa identificar o usuário ou o processo consultado.

---

## 5. Tratamento de falha do provider

| Cenário | Comportamento |
|---|---|
| Timeout (> `timeout_ms`) | Retornar `abstained=True`, escalar para regra ou falha |
| HTTP 4xx (auth/config) | Levantar `ProviderConfigError` — parar execução |
| HTTP 5xx (serviço fora) | Retornar `abstained=True` após 1 retry com backoff mínimo |
| Resposta malformada | Levantar `ProviderProtocolError` — não inventar uma escolha |
| ID fora da lista | Gate rejeita — `DecisionGateError` |
| Observação expirada | Gate rejeita — `StaleObservationError` |

**Em nenhum cenário** o fallback é clicar em um elemento aleatório ou continuar sem ação.

---

## 6. Pendências a confirmar antes de implementar

1. **Formato exato da API Workers AI para CLEF** — a documentação da Cloudflare deve ser consultada
   para confirmar o endpoint, headers e estrutura de request/response
2. **Limite de tokens na chamada REST** — confirmar se o limite de 16.384 do loader local aplica-se também à API
3. **Disponibilidade regional** — confirmar latência do Workers AI a partir do Brasil
4. **Rate limits** — definir limite de chamadas por execução antes de implementar

Estas pendências **não bloqueiam** a escrita dos contratos e fixtures, mas bloqueiam a implementação do adapter HTTP real.
