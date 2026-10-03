# 05 — Testes de aceitação do MVP

**JCP-application | browser-use + CLEF | PoC**

O MVP está pronto quando **todos** estes testes passam.
Os marcados com `[LIVE]` exigem acesso real ao portal CJPG.
Os marcados com `[FIXTURE]` rodam offline com HTML sintético.
Os marcados com `[UNIT]` não abrem navegador.

**Regra:** nenhum teste pode ser marcado como "passou" sem evidência executável (log + output).

---

## Grupo A — Contratos e validação de entrada [UNIT]

### A01 — Invocation inválida é rejeitada antes do navegador
```
Dado: CJPGInvocation(tribunal="TJSP", texto="")
Quando: search_decisions() é chamado
Então: levanta INVALID_ARGUMENT
  E: nenhuma sessão de browser foi aberta
  E: llm_calls == 0
```

### A02 — data_fim anterior a data_inicio é rejeitada
```
Dado: CJPGInvocation(texto="dano moral", data_inicio="2024-06-01", data_fim="2024-01-01")
Quando: search_decisions() é chamado
Então: levanta INVALID_ARGUMENT com mensagem explicativa
  E: nenhuma sessão de browser foi aberta
```

### A03 — max_pages > 1 retorna NOT_SUPPORTED
```
Dado: CJPGInvocation(texto="dano moral", max_pages=3)
Quando: search_decisions() é chamado
Então: levanta NOT_SUPPORTED
  E: nenhuma sessão de browser foi aberta
```

### A04 — Result só é criado com campos obrigatórios preenchidos
```
Dado: um dict JSON sem o campo "status"
Quando: CJPGResult(**dict) é chamado
Então: levanta ValidationError do Pydantic
```

---

## Grupo B — Caminho estável offline [FIXTURE]

### B01 — Receita funciona com fixture de resultado
```
Dado: fixture "cjpg_result_page.html" com 5 decisões sobre "dano moral"
  E: CJPGInvocation(texto="dano moral", data_inicio="2024-01-01")
  E: receita tjsp-cjpg-search-v0.1 carregada no Pescache
Quando: search_decisions() é executado contra a fixture
Então: result.status == "ok"
  E: len(result.decisions) == 5
  E: result.llm_calls == 0
  E: result.evidence.verification_passed == True
  E: result.recipe_version == "0.1.0"
```

### B02 — Segunda execução com parâmetros diferentes reutiliza receita sem inferência
```
Dado: receita já presente no Pescache após B01
  E: CJPGInvocation(texto="responsabilidade civil", data_inicio="2023-01-01")
Quando: search_decisions() é executado novamente
Então: result.llm_calls == 0
  E: Pescache não chamou nenhum LLM para selecionar receita
  E: mesma recipe_version
```

### B03 — Resultado vazio é distinguido de erro
```
Dado: fixture "cjpg_empty_page.html" com mensagem "Nenhum documento encontrado"
  E: CJPGInvocation(texto="xyzzy_inexistente_123")
Quando: search_decisions() é executado contra a fixture
Então: result.status == "empty"
  E: result.decisions == []
  E: result.evidence.verification_passed == True
  E: result.llm_calls == 0
```

### B04 — Página de login não é confundida com resultado vazio
```
Dado: fixture "cjpg_auth_page.html" com formulário de autenticação
  E: CJPGInvocation(texto="dano moral")
Quando: search_decisions() é executado contra a fixture
Então: result.status == "needs_auth"
  E: result.decisions == []
  E: result.status != "empty"
  E: result.status != "error"
```

### B05 — Seletor errado aciona recuperação CLEF — candidato correto é escolhido
```
Dado: fixture "cjpg_result_page.html" com seletor de campo de busca alterado
  E: mock do CloudflareClefProvider configurado para retornar o candidato correto
Quando: search_decisions() é executado
Então: CLEF.decide() é chamado uma vez
  E: o candidato escolhido está na lista original
  E: o gate confirma o ID
  E: result.status == "ok"
  E: result.llm_calls == 0 (CLEF não conta como LLM generativo)
```

### B06 — Candidato enganoso (alvo errado) é rejeitado pelo verificador
```
Dado: fixture com seletor alterado
  E: mock do CloudflareClefProvider configurado para retornar ID de candidato errado
  E: candidato errado leva a campo de assunto em vez de campo de texto
Quando: search_decisions() é executado
Então: verificador.verify() retorna passed == False
  E: result.status == "error"
  E: o erro documenta qual verificação falhou
```

### B07 — Paginação não avança além de max_pages=1
```
Dado: fixture com botão "próxima página" presente
  E: CJPGInvocation(texto="dano moral", max_pages=1)
Quando: search_decisions() é executado
Então: result.pages_fetched == 1
  E: nenhum clique em "próxima página" foi registrado no ActionBroker
  E: scope_declared menciona "primeira página"
```

### B08 — Orçamento de inferência esgotado durante recuperação
```
Dado: fixture com locator falhando
  E: budget de llm_calls configurado para 0 (zero tolerância)
Quando: search_decisions() é executado
Então: ExecutionBudgetExceeded é levantado
  E: nenhuma ação foi executada após o estouro
```

---

## Grupo C — Verificador [UNIT]

### C01 — Número de processo fora do padrão CNJ falha verificação
```
Dado: Decision com numero_processo="123456"  (formato inválido)
Quando: CJPGVerifier.verify() é chamado
Então: VerificationReport.passed == False
  E: check "process_numbers_valid" está no relatório com passed=False
```

### C02 — llm_calls > 0 falha verificação no modo determinístico
```
Dado: CJPGResult com llm_calls=1
Quando: CJPGVerifier.verify() é chamado
Então: VerificationReport.passed == False
  E: check "zero_llm" está no relatório com passed=False
```

### C03 — origin diferente de TJSP/CJPG falha verificação
```
Dado: Decision com origem="STJ/SCON"
Quando: CJPGVerifier.verify() é chamado
Então: VerificationReport.passed == False
```

---

## Grupo D — Adapter CLEF [UNIT com mock]

### D01 — ID fora da lista de candidatos é rejeitado pelo gate
```
Dado: DecisionRequest com candidates=[Candidate(id="a"), Candidate(id="b")]
  E: mock retornando chosen_id="c"
Quando: CloudflareClefProvider.apply_gate() é chamado
Então: DecisionGateError é levantado
```

### D02 — Observação expirada não é executada
```
Dado: DecisionRequest com observation_timestamp = agora - 30 segundos
  E: mock retornando chosen_id="a" (válido)
Quando: CloudflareClefProvider.apply_gate() é chamado
Então: StaleObservationError é levantado
  E: nenhuma ação foi passada ao ActionBroker
```

### D03 — Abstain não vira clique de fallback
```
Dado: DecisionResult com abstained=True
Quando: CloudflareClefProvider.apply_gate() é chamado
Então: retorna None
  E: executor recebe None e escalona para falha, não para clique aleatório
```

### D04 — Timeout no Workers AI retorna abstain
```
Dado: mock HTTP que demora mais que timeout_ms
Quando: CloudflareClefProvider.decide() é chamado
Então: resultado.abstained == True
  E: nenhum erro não tratado é levantado
```

---

## Grupo E — Ao vivo [LIVE] (requer acesso ao portal)

### E01 — Consulta real retorna decisões verificadas
```
Dado: CJPG ao vivo
  E: CJPGInvocation(texto="dano moral", tribunal="TJSP")
Quando: search_decisions() é executado
Então: result.status == "ok"
  E: len(result.decisions) >= 1
  E: result.evidence.verification_passed == True
  E: result.llm_calls == 0
  E: todos os números de processo passam na validação CNJ
```

### E02 — Segunda consulta ao vivo com texto diferente reutiliza receita
```
Dado: E01 foi executado (receita no Pescache)
  E: CJPGInvocation(texto="responsabilidade civil")
Quando: search_decisions() é executado
Então: result.llm_calls == 0
  E: recipe_version é a mesma do E01
```

### E03 — Consulta sem resultados ao vivo
```
Dado: CJPG ao vivo
  E: CJPGInvocation(texto="xyzzyplugh_999_inexistente")
Quando: search_decisions() é executado
Então: result.status == "empty"
  E: result.decisions == []
  E: result.llm_calls == 0
```

---

## Smoke test obrigatório (pré-condição para todos os outros)

### S01 — Ambiente funcional
```
Dado: setup completo (ver specs/01-REQUIREMENTS.md)
Quando: runtime/smoke_test.py é executado
Então: imprime "SMOKE TEST OK — llm_calls=0"
  E: BrowserSession abriu e fechou sem erro
  E: nenhum provider LLM foi instanciado
  E: ANONYMIZED_TELEMETRY=false está configurado
```

---

## Matriz de prioridade para o MVP

| Grupo | Quando implementar |
|---|---|
| S01 (smoke) | **Primeiro** — antes de qualquer outro código |
| A (contratos) | Junto com os modelos Pydantic |
| B01, B03, B04 | Junto com o executor e fixtures |
| C (verificador) | Junto com o verificador |
| D (CLEF mock) | Quando o adapter for escrito |
| B02 | Quando o Pescache for implementado |
| B05, B06 | Quando a recuperação de locator for implementada |
| E (ao vivo) | Por último — só depois de todos os anteriores passarem |
