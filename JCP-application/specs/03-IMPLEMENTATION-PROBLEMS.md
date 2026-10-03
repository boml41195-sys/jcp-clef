# 03 — Problemas de implementação identificados

**JCP-application | browser-use + CLEF | PoC**

Este documento lista os problemas concretos que a implementação vai enfrentar.
Cada problema tem origem rastreável na pesquisa já realizada.
**Leia antes de escrever qualquer código.**

---

## PROBLEMA 1 — CLEF não é um LLM generativo e não pode ser plugado diretamente no Agent

**Severidade:** BLOQUEANTE

**Descrição:**
O Agent do Browser Use espera um objeto que satisfaz `BaseChatModel.ainvoke` — uma interface de geração de texto.
O CLEF expõe `systemone(state, questions)` que retorna uma distribuição de probabilidades sobre opções.
Esses dois contratos são diferentes. Tentar passar CLEF como `llm=ClefProvider()` no Agent vai:
- Falhar com `AttributeError` ou produzir resposta malformada
- Ou fazer o Agent tratar o JSON de distribuição como texto gerado — comportamento indefinido

**Fonte:** `APLICABILIDADE-CLEF.md §conclusão`, `MAPA-DO-CODIGO.md §código Clef`

**Solução especificada:**
CLEF só pode ser chamado como `DecisionProvider.decide(state, questions)` dentro do módulo M5.
O executor JCP chama CLEF diretamente — nunca via `Agent.run()`.
O Agent (com LLM generativa real) continua existindo apenas para descoberta e reparo.

**Critério de aceitação:** nenhum trecho de código instancia `Agent(llm=ClefProvider(...))`.

---

## PROBLEMA 2 — `rerun_history` chama LLM — replay não é zero inferência

**Severidade:** BLOQUEANTE

**Descrição:**
O método `_execute_history_step` (linha 3398 de `agent/service.py`) e `rerun_history` (linha 3103)
invocam `extract` que faz chamadas ao modelo para reinterpretar o estado do DOM.
Usar replay do Agent como substituto de receita determinística vai:
- Gerar chamadas de LLM silenciosas que não aparecem no log superficial
- Invalidar o critério de `llm_calls=0`

**Fonte:** `MAPA-DO-CODIGO.md §2`, `PENDENCIAS.md #2`

**Solução especificada:**
O runtime JCP implementa seu próprio interpretador da DSL de receita.
O interpretador usa `BrowserSession` e `Actor` diretamente — nunca `Agent.run()` nem `rerun_history`.
O caminho estável não instancia o Agent.

**Critério de aceitação:** segunda execução com parâmetros diferentes não chama nenhum dos providers LLM instrumentados.

---

## PROBLEMA 3 — `_update_action_indices` usa índices DOM efêmeros

**Severidade:** ALTO

**Descrição:**
O mecanismo de relocalização do Agent usa índices numéricos do DOM atual (`_update_action_indices`, linha 3529).
Esses índices mudam a cada carregamento de página e entre sessões.
Persistir uma receita como "clique no elemento de índice 42" produz receita que quebra na próxima execução.

**Fonte:** `MAPA-DO-CODIGO.md §2`

**Solução especificada:**
A DSL de receita usa **seletores semânticos estáveis**: CSS selector, XPath, atributo `data-*`, texto visível ou role ARIA.
Índices DOM aparecem apenas como candidatos transitórios durante a recuperação de locator — nunca são persistidos.

**Critério de aceitação:** T20 — receita não contém literais de índice DOM, cookie de sessão nem data fixa da descoberta.

---

## PROBLEMA 4 — CJPG: inteiro teor e paginação ao vivo ainda pendentes

**Severidade:** MÉDIO (limitação de escopo, não bug)

**Descrição:**
Durante a pesquisa, o percurso de busca inicial do CJPG foi observado mas:
- Paginação completa (além da primeira página) não foi validada
- Abertura de inteiro teor e download de documento não foram confirmados

**Fonte:** `PENDENCIAS.md P03`

**Solução especificada:**
O MVP certifica apenas:
- Busca com filtros → primeira página de resultados → extração de lista
- Detecção de resultado vazio
- Detecção de página de login/desafio (não confundir com resultado vazio)

Inteiro teor e paginação completa são capacidades separadas, fora do escopo do MVP.
A receita deve declarar `max_pages=1` e `full_text=false` explicitamente.

**Critério de aceitação:** T08 — paginação não avança além do limite declarado.

---

## PROBLEMA 5 — Estado do DOM não pode ser enviado integralmente ao CLEF

**Severidade:** ALTO

**Descrição:**
`get_browser_state_summary` (linha 1597 de `browser/session.py`) produz um resumo do DOM completo.
O CLEF tem limite local de 16.384 tokens (`encode_record` na linha 103 do `joint_schema_model.py`).
Enviar o DOM completo de uma página TJSP pode truncar o estado silenciosamente.
O modelo então decide com informação incompleta — sem avisar.

**Fonte:** `MAPA-DO-CODIGO.md §4`

**Solução especificada:**
O adapter CLEF recebe apenas:
- Lista de candidatos já filtrados pelo papel semântico (inputs, buttons, links relevantes)
- Contexto da operação em andamento (ex: "buscando campo de texto para 'dano moral'")
- Schema da pergunta (qual candidato é o campo de busca?)

O estado nunca inclui: credenciais, histórico de sessão, DOM completo, cookies.

**Critério de aceitação:** T17 — segredos sentinela ausentes no payload enviado ao CLEF.

---

## PROBLEMA 6 — Clef `score` e `noul` têm semântica diferente e não são intercambiáveis

**Severidade:** MÉDIO

**Descrição:**
O `joint_schema_model.py` produz dois tipos de saída:
- `score`: expectativa numérica (média ponderada). Não é probabilidade direta.
- `noul`: probabilidade de "verdadeiro" para campos booleanos.

Usar `score` como limiar direto de confiança (ex: `if score > 0.9: executar`) é matematicamente incorreto.
A escala de `score` varia por questão e não equivale a percentual de acerto.

**Fonte:** `MAPA-DO-CODIGO.md §4 — systemone_answer linha 523`

**Solução especificada:**
O gate de ação após CLEF é **sempre determinístico**:
1. A opção escolhida deve estar na lista original de candidatos (validação por ID, não por posição)
2. Se `abstain` foi retornado → não agir, escalar para regra ou LLM generativa
3. Threshold de abstenção é configurável por classe de decisão, não hardcoded
4. `score` é registrado para análise mas não é critério de go/no-go

**Critério de aceitação:** T18 — resposta fora da lista de candidatos é rejeitada; abstain não vira clique de fallback.

---

## PROBLEMA 7 — Browser Use tem telemetria ativa por padrão

**Severidade:** BAIXO (privacidade e compliance)

**Descrição:**
O `pyproject.toml` inclui `posthog==7.7.0` e o código referencia telemetria de uso.
Em ambiente de produção com dados jurídicos, envio silencioso de telemetria é inaceitável.

**Fonte:** `browser-use-jcp/pyproject.toml`

**Solução especificada:**
Configurar `ANONYMIZED_TELEMETRY=false` no `.env` antes de qualquer execução.
Verificar que nenhum dado de sessão, URL de portal ou resultado jurídico é transmitido.

**Critério de aceitação:** primeira linha do `smoke_test.py` verifica a variável de ambiente.

---

## PROBLEMA 8 — Windows com caminho contendo espaços

**Severidade:** BAIXO (ambiente de desenvolvimento)

**Descrição:**
O workspace atual está em `C:\Users\100OS\Downloads\LOPS OS DEFINITIVO` — caminho com espaços.
Algumas ferramentas Python (Playwright, uv) têm comportamento instável com espaços em caminhos no Windows.

**Fonte:** observação do ambiente atual

**Solução especificada:**
Para desenvolvimento no Windows, clonar o repositório para um caminho sem espaços:
```
C:\dev\jcp-clef\
```
O caminho atual pode ser usado para leitura de documentação, não para execução do runtime.

---

## PROBLEMA 9 — `clef-flash` tem CLINC150+OOS macro-F1 de 66,77 vs 97,43 do clef

**Severidade:** MÉDIO (risco de qualidade)

**Descrição:**
Os benchmarks publicados pela Cloudflare mostram que clef-flash tem desempenho muito inferior
em classificação fora da distribuição (OOS). Decisões de recuperação de locator em portais
jurídicos brasileiros (domínio não visto) têm alto risco de cair nessa categoria.

**Fonte:** `APLICABILIDADE-CLEF.md §2`

**Solução especificada:**
MVP usa `clef` (padrão) em todas as decisões.
`clef-flash` só pode ser habilitado por classe de decisão após avaliação com observações reais dos portais.
Nenhum benchmark externo substitui esse teste.

**Critério de aceitação:** variável `CLEF_MODEL` default aponta para `clef`, não `clef-flash`.

---

## Resumo de riscos

| # | Problema | Severidade | Bloqueante para MVP? |
|---|---|---|---|
| 1 | CLEF ≠ BaseChatModel | BLOQUEANTE | Sim |
| 2 | rerun_history chama LLM | BLOQUEANTE | Sim |
| 3 | Índices DOM efêmeros | ALTO | Sim |
| 4 | CJPG paginação/inteiro teor | MÉDIO | Não (limitação de escopo) |
| 5 | DOM completo → truncamento CLEF | ALTO | Sim |
| 6 | score ≠ probabilidade | MÉDIO | Sim |
| 7 | Telemetria posthog | BAIXO | Não (configurável) |
| 8 | Caminhos Windows com espaços | BAIXO | Não (ambiente) |
| 9 | clef-flash OOS inferior | MÉDIO | Não (configuração) |
