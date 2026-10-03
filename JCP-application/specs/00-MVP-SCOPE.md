# 00 — Escopo do MVP

**JCP-application | browser-use + CLEF | PoC**

Data: 2026-10-03. Esta especificação define o que entra e o que fica fora da primeira prova de conceito.
O critério é simples: se não for necessário para provar o circuito `função jurídica → navegador → resultado verificado`, fica fora.

---

## 1. O que entra no MVP

| # | Componente | Justificativa de inclusão |
|---|---|---|
| 1 | **Browser Use** (fork, commit `7be96ed`) | Base de execução já inspecionada. BrowserSession e Actor são o único runtime de navegador. |
| 2 | **CLEF via Workers AI** | Substitui Jev como provedor de decisões delimitadas. Chamado apenas em recuperação de locator. |
| 3 | **Claw CJPG** (TJSP, consulta pública) | Único portal com percurso público observado durante a pesquisa. |
| 4 | **DSL de receita mínima** | Sequência de passos tipados: navegar, preencher, clicar, aguardar, extrair. |
| 5 | **Verificador de identidade** | Confirma que o resultado pertence à consulta enviada. Independente do executor. |
| 6 | **Pescache básico** | Salva receita versionada; segunda chamada não usa LLM. |
| 7 | **Fixtures HTML offline** | Permite rodar todos os testes sem acesso à internet. |

---

## 2. O que fica fora — e por quê

| Componente | Decisão | Motivo concreto |
|---|---|---|
| **Surf / Go** | Fora | Requer Go 1.27+ e toolchain separada; não bloqueia provar o circuito base. ADR 04 já diz: primeiro provar correção, depois otimizar com HTTP. |
| **Jev** | Fora | Substituído por CLEF. Código Ultrafast mantido apenas como referência de design. |
| **Scrapling** | Fora | Abstração de seleção adaptativa; agrega dependência antes de medir ganho. Ver P13 nas pendências. |
| **LangChain / frameworks de agent** | Fora | Browser Use já tem seu Agent. Não adicionar camada sobre camada. |
| **Reparo generativo completo** | Fora da v1 | O MVP só faz recuperação de locator via CLEF. Reparo com LLM generativa é PR-07 no backlog original. |
| **PJe / eproc / STJ SCON** | Fora | Dependem de autenticação ou de resolver acesso bloqueado por desafio. Ver pendências P05/P06/P07. |
| **Múltiplos portais** | Fora | Um portal certifica a arquitetura. Dois portais certificam a generalização — essa é a próxima fase. |
| **API REST externa** | Fora | O MVP é uma biblioteca Python chamada diretamente. FastAPI/servidor vem depois do ciclo estável. |
| **MCP server** | Fora | Só faz sentido depois que o circuito base funciona sem erros. |
| **Sessões autenticadas** | Fora | CJPG é consulta pública; não precisa de login para o MVP. |
| **Inteiro teor de decisões** | Fora | Paginação básica entra; download de PDF/HTML completo fica para depois de P03 estar encerrada. |

---

## 3. Circuito mínimo a provar

```
search_decisions(tribunal="TJSP", texto="dano moral", data_inicio="2024-01-01")
        │
        ▼
   Pescache: existe receita para CJPG?
        │ NÃO → executor cria receita mínima
        │ SIM ↓
        ▼
   BrowserSession.new_page("https://esaj.tjsp.jus.br/cjpg/...")
        │
        ▼
   Actor: fill(campo_texto, "dano moral"), click(buscar), aguardar resultados
        │
        ▼
   Parser: extrair decisões com número, data, ementa, URL
        │
        ▼
   Verificador: filtros aplicados? resultado não vazio? origem correta?
        │
        ▼
   Result(decisions=[...], evidence={...}, recipe_version="1.0", llm_calls=0)
```

**Critério de sucesso do MVP:** `llm_calls == 0` na segunda execução com parâmetros diferentes.

---

## 4. Informações já obtidas que não podem ter outro runtime

As informações abaixo são **conclusões fixadas** da pesquisa anterior. Não devem ser reescritas ou contraditas sem nova evidência técnica.

| Conclusão | Fonte | Status |
|---|---|---|
| Browser Use commit `7be96ed8` é a base fixada | MAPA-DO-CODIGO.md | **Fixada** |
| `rerun_history` / `_execute_history_step` do Agent chama LLM — não é zero inferência | MAPA-DO-CODIGO.md, PENDENCIAS.md #2 | **Fixada** |
| `systemone` do CLEF não implementa `BaseChatModel.ainvoke` — não pode ser plug-in direto no Agent | APLICABILIDADE-CLEF.md, MAPA-DO-CODIGO.md | **Fixada** |
| CLEF encaixa no módulo M5 como `DecisionProvider`, não no loop generativo | APLICABILIDADE-CLEF.md | **Fixada** |
| CLEF self-hosted exige ~54 GB BF16 (27B params) — Workers AI é o caminho do MVP | APLICABILIDADE-CLEF.md §3 | **Fixada** |
| Surf tem TLS inicial que requer endurecimento; não é production-ready sem trabalho extra | PENDENCIAS.md #7, SDD 05 | **Fixada** |
| Jev Ultrafast benchmark não é benchmark do JCP nem dos tribunais brasileiros | 08-IMPLEMENTACAO-E-ACEITACAO.md §5 | **Fixada** |
| CJPG: percurso público observado, inteiro teor pendente | PENDENCIAS.md P03 | **Fixada** |
| CPOPG: entrada observada, detalhe final não confirmado | PENDENCIAS.md P04 | **Fixada** |
| STJ SCON: bloqueado por desafio, estado de resultado não observado | PENDENCIAS.md P05 | **Fixada** |
| PJe TRT2 / eproc JFRS: área privada não acessada | PENDENCIAS.md P06/P07 | **Fixada** |

**Regra:** nenhum documento futuro pode usar a palavra "implementado", "certificado" ou "testado ponta a ponta" para qualquer um dos itens acima marcados como pendência.
