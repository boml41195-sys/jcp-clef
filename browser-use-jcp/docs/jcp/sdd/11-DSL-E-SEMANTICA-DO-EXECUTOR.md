# DSL, interpretação determinística e pontos de integração

Este documento aprofunda os módulos M3, M4, M5 e M6. É uma especificação de implementação; o interpretador descrito ainda não foi executado contra portais. As interfaces de referência do Browser Use e Jev foram conferidas nos commits fixados em [09](09-FONTES-E-CONCLUSOES.md).

## 1. Três níveis que o código deve manter separados

1. **Capacidade:** a operação jurídica contratada, com entrada, saída, instalação, efeito e verificador. Exemplo: buscar decisões por termos e período.
2. **Receita:** o procedimento parametrizado que implementa a capacidade em uma variante da fonte. Contém passos, referências de parser e condições.
3. **Tentativa:** a execução concreta de um passo, com observação, valores resolvidos, autorização, envio e recibo.

Um reparo pode mudar a receita sem mudar a capacidade. Uma tentativa pode falhar sem provar que a receita está quebrada. Misturar esses níveis transforma expiração de sessão em reparo de seletor e transforma sucesso em uma tela em certificação geral.

## 2. Modelo fechado de Recipe

Campos obrigatórios propostos:

| Campo | Tipo e interpretação |
|---|---|
| `dsl_version` | Versão da gramática, inicialmente `0.1`. |
| `recipe_id`, `recipe_version` | Identidade estável e versão imutável. |
| `capability_id`, `capability_version`, `installation_id` | Contrato implementado. |
| `variant` | Papel de acesso, variante da UI, transporte e faixa de compatibilidade do runtime. |
| `certification` | `candidate`, `experimental`, `certified`, `degraded` ou `disabled` para a receita. |
| `input_schema_ref` | Schema do catálogo, resolvido e fixado na admissão do run. |
| `origin_policy_ref` | Política de destinos aprovada; não editável pelo reparador. |
| `parameters` | Nomes, tipos e bindings admitidos. |
| `locators` | Estratégias nomeadas com escopo e cardinalidade. |
| `conditions` | Predicados nomeados e versionados. |
| `steps` | Lista ordenada de passos; IDs únicos. |
| `verifier_ref` | Verificador da capacidade, protegido. |
| `limits` | Limites locais, intersectados com os limites do run. |
| `provenance` | Origem manual/descoberta/reparo, revisão-base e referências de evidência. |
| `content_hash` | Hash da representação canônica do conteúdo operacional. |

`candidate` é estado de receita, não nível público de capacidade. Os níveis do catálogo de capacidades continuam os do documento 01. Nunca selecionar candidato como receita estável apenas porque o nome da capacidade está marcado como certificado.

A forma canônica exclui o próprio `content_hash` e timestamps administrativos, mas inclui passos, condições, locators, referências e versões dos parsers/verificadores, parâmetros e política de origem. A implementação deve fixar a serialização canônica antes de usar o hash como identidade. Hash de `repr(dict)` ou de YAML formatado não é um identificador interoperável.

## 3. Gramática dos bindings

Um valor dinâmico usa exatamente um dos discriminadores:

```json
{"input": "query"}
```

```json
{"state": "current_document_ref"}
```

```json
{"const": "DESC"}
```

```json
{"secret_ref": "portal_session"}
```

`input` lê uma propriedade conhecida dos argumentos validados. `state` lê uma saída declarada de passo anterior. `const` admite literal validado pelo schema daquela operação. `secret_ref` resolve uma referência autorizada no broker e só pode ser usado em posições explicitamente sensíveis; seu valor não vai para log, prompt nem hash da receita.

Não há interpolação de Python, JavaScript, shell ou templates que executem expressões. Um campo `query` contendo caracteres de código continua sendo texto do formulário. Transformações necessárias, como formato de data, são funções puras de um registro fechado, por exemplo `date_to_ddmmyyyy.v1`, testadas separadamente. Não usar LLM para formatar uma data já conhecida.

Referência inexistente é erro de compilação estática quando detectável; ausência de estado adquirido dinamicamente é falha de pré-condição. Nenhuma das duas vira string vazia silenciosamente.

## 4. Locators persistentes e referências efêmeras

`LocatorSpec` contém ID, estratégia, valor, contexto, cardinalidade esperada, papel semântico, requisitos de visibilidade e política de recuperação. O MVP admite CSS e alternativas nomeadas. Outras estratégias só entram quando o adapter as suportar e testar.

Uma localização produz `TargetRef` efêmero: sessão, página, frame, geração da observação, elemento/backend node, origem e instante. Esse objeto nunca é serializado como solução reutilizável entre sessões.

### 4.1 Regras de cardinalidade

- Nenhum elemento: aguardar somente se a condição admite carregamento; depois `SELECTOR_NOT_FOUND`.
- Um elemento adequado: permitir que o broker avalie a ação.
- Vários elementos: desambiguar por contexto determinístico certificado ou retornar `AMBIGUOUS_TARGET`.
- Elemento invisível, desabilitado ou em frame inesperado: não clicar apenas porque houve correspondência de CSS.

Não selecionar automaticamente o primeiro elemento quando o contrato exige unicidade. Não converter nome acessível genérico em identidade jurídica do recurso.

### 4.2 Frames, abas e mudanças de DOM

O locator deve declarar escopo de página/frame. Novas abas são capturadas por correlação com a ação e por destino aprovado. Um seletor na página principal não é presumido válido dentro de iframe, shadow root ou componente desenhado em canvas.

Revalidar o alvo perto do envio reduz a janela entre observar e agir, mas não elimina todas as corridas da interface. A pós-condição e o verificador precisam detectar seleção errada. Operações com efeito maior exigem confirmação e reconciliação específicas; fingerprint não oferece atomicidade com o servidor do portal.

## 5. Semântica de cada operação

| Operação | Semântica | Saída persistível | Condição para prosseguir |
|---|---|---|---|
| `navigate` | Abrir referência de URL aprovada pelo broker | Origem/URL sanitizada e observação | Destino e estado esperados após espera explícita. |
| `locate` | Resolver locator na observação atual | Metadados do achado; TargetRef fica efêmero | Cardinalidade e contexto válidos. |
| `fill` | Resolver binding, preencher alvo e reler | Confirmação, sem expor segredo | Valor observado equivalente ao valor solicitado. |
| `click` | Enviar interação em alvo autorizado | Intenção, envio e recibo | Pós-condição específica; retorno de click não basta. |
| `select` | Escolher opção realmente observada | Opção e estado posterior | Valor selecionado conferido. |
| `wait_for` | Observar predicado até limite | Última observação e duração | Predicado satisfeito; timeout tipado caso contrário. |
| `extract` | Aplicar parser registrado à observação/resposta | Objetos candidatos e relatório de extração | Estrutura reconhecida; nada publicado antes de verificar. |
| `paginate` | Percorrer próximo cursor/controle sob limites | Itens, páginas, progresso e deduplicação | Fim, limite ou falha explícita; sem loop silencioso. |
| `download` | Obter recurso observado e vinculado | ArtifactRef, hash, MIME e tamanho | Conteúdo, identidade e limites aprovados. |
| `http_request` | Executar template HTTP certificado | Metadados e ArtifactRef de resposta | Identidade de sessão, destino e corpo esperados. |
| `verify` | Executar verificador protegido | Relatório e referências de evidência | Resultado aceito ou falha diagnosticável. |
| `checkpoint` | Guardar progresso semântico | Identidades, passos confirmados, orçamento restante | Estado persistido de modo durável. |

`extract`, `paginate` e `verify` podem ter código Python próprio da claw. Esse código é extensão de desenvolvimento versionada, não texto arbitrário gerado e executado em produção. `paginate` executa suas ações filhas através do mesmo broker, sem acesso lateral ao navegador.

## 6. Interpretador: ordem de execução

O algoritmo abaixo é pseudocódigo de orquestração. Cada serviço citado é componente JCP a implementar.

```text
admit(invocation, authenticated_context):
    validate input and capability version
    authorize capability and installation
    canonicalize request identity and persist ACCEPTED
    intersect budgets and reserve execution capacity

execute(run):
    acquire session lease and verify ownership/health
    select compatible recipe; pin version and dependencies
    statically validate bindings, operations and protected refs
    for step in recipe.steps:
        check cancellation, deadline and all shared budgets
        evaluate preconditions against a current observation
        resolve typed bindings
        prepare action and persist intended effect
        authorize the concrete action and destination
        refresh/revalidate target if this action requires a target
        record dispatch boundary conservatively
        execute through adapter with bounded timeout
        persist receipt or uncertain state
        evaluate postconditions
        emit step result; persist safe checkpoint if declared
    verify candidate data against invocation and source evidence
    publish a result only through the verified-result gate
    release lease according to session ownership policy

on failure:
    classify error with dispatch/receipt information
    reconcile uncertain effects before any retry
    select bounded recovery, repair candidate, suspension or failure
```

O registro durável e o envio para um portal externo não compartilham uma transação. Se o processo cair entre registrar intenção e comprovar envio, o sistema deve assumir a ambiguidade pertinente ao efeito. Registrar `dispatched` antes da chamada é conservador, mas não prova recebimento; registrar depois pode perder a prova de um envio ocorrido. A reconciliação é indispensável.

## 7. Condições e controle de fluxo

Condições usam operadores fechados: `exists`, `equals`, `count_between`, `member_of`, `url_matches_policy`, `document_type_is`, `resource_identity_matches`, `page_state_is`, `no_progress`.

O MVP usa sequência, espera limitada, paginação limitada e encaminhamento de falha. Não precisa de `while` genérico, recursão, importação dinâmica ou execução de expressões livres. Variações de interface podem ser representadas por receitas distintas selecionadas por pré-condições.

`on_failure` referencia uma classe de encaminhamento do núcleo, como `diagnose` ou `stop`; não aponta para uma sequência arbitrária capaz de remover o verificador. O classificador decide quais níveis de recuperação são pertinentes. Uma exceção de transporte não exige passar por Scrapling e Clef antes de reconhecer indisponibilidade.

O timeout do passo é o menor entre limite do passo, tempo restante do run e limite do transporte. O prazo total inclui o tempo esperando recursos. Uma suspensão para autenticação tem expiração própria; retomada não cria orçamento infinito. O documento 13 define sua contabilidade.

## 8. Exemplo de receita integral para um ambiente de teste

Este exemplo usa uma instalação **sintética**, `fixture-cjpg`. Os seletores e predicados abaixo pertencem a fixtures que o desenvolvedor deve implementar. Não são apresentados como seletores certificados de TJSP. O objetivo é fixar a forma do contrato e todas as dependências necessárias ao executor.

```yaml
dsl_version: '0.1'
recipe_id: fixture-decisions-search
recipe_version: 0.1.0
capability_id: fixture.decisions.search
capability_version: 1.0.0
installation_id: fixture-cjpg
variant:
  access_role: public
  ui: fixture-v1
  transport: browser
  runtime: browser-use-pinned-adapter-v1
certification: candidate
input_schema_ref: fixture.search_input.v1
origin_policy_ref: fixture.origin_policy.v1
parameters:
  query: {type: string, required: true}
  date_from: {type: date, required: true}
  date_to: {type: date, required: true}
  limit: {type: integer, required: true}
locators:
  query: {strategy: css, value: '#query', scope: main, cardinality: 1, role: textbox}
  from: {strategy: css, value: '#date-from', scope: main, cardinality: 1, role: textbox}
  to: {strategy: css, value: '#date-to', scope: main, cardinality: 1, role: textbox}
  submit: {strategy: css, value: '#search', scope: main, cardinality: 1, role: button}
  next: {strategy: css, value: '#next', scope: main, cardinality: 1, role: button}
conditions:
  form_ready: {registry_ref: fixture.form_ready.v1}
  query_confirmed: {registry_ref: fixture.query_confirmed.v1}
  from_confirmed: {registry_ref: fixture.from_confirmed.v1}
  to_confirmed: {registry_ref: fixture.to_confirmed.v1}
  results_or_empty: {registry_ref: fixture.results_or_empty.v1}
  verified: {registry_ref: core.verification_passed.v1}
steps:
  - step_id: open
    operation: navigate
    arguments: {url: {const: 'https://fixture.invalid/search'}}
    preconditions: []
    postconditions: []
    timeout_ms: 10000
    effect: read
    retry_policy: read_before_dispatch_only
    on_failure: diagnose
  - step_id: ready
    operation: wait_for
    arguments: {condition: form_ready}
    preconditions: []
    postconditions: [form_ready]
    timeout_ms: 10000
    effect: read
    retry_policy: bounded_observation
    on_failure: diagnose
  - step_id: query
    operation: fill
    arguments: {locator_ref: query, value: {input: query}}
    preconditions: [form_ready]
    postconditions: [query_confirmed]
    timeout_ms: 5000
    effect: read
    retry_policy: reconcile_field_then_retry
    on_failure: diagnose
  - step_id: from
    operation: fill
    arguments: {locator_ref: from, value: {input: date_from}, transform_ref: fixture.date_format.v1}
    preconditions: [form_ready]
    postconditions: [from_confirmed]
    timeout_ms: 5000
    effect: read
    retry_policy: reconcile_field_then_retry
    on_failure: diagnose
  - step_id: to
    operation: fill
    arguments: {locator_ref: to, value: {input: date_to}, transform_ref: fixture.date_format.v1}
    preconditions: [form_ready]
    postconditions: [to_confirmed]
    timeout_ms: 5000
    effect: read
    retry_policy: reconcile_field_then_retry
    on_failure: diagnose
  - step_id: search
    operation: click
    arguments: {locator_ref: submit}
    preconditions: [query_confirmed, from_confirmed, to_confirmed]
    postconditions: []
    timeout_ms: 5000
    effect: read
    retry_policy: diagnose_after_dispatch
    on_failure: diagnose
  - step_id: results
    operation: wait_for
    arguments: {condition: results_or_empty}
    preconditions: []
    postconditions: [results_or_empty]
    timeout_ms: 10000
    effect: read
    retry_policy: bounded_observation
    on_failure: diagnose
  - step_id: collect
    operation: paginate
    arguments:
      parser_ref: fixture.decisions_parser.v1
      next_locator_ref: next
      limit: {input: limit}
      output_state: candidate_results
    preconditions: [results_or_empty]
    postconditions: []
    timeout_ms: 30000
    effect: read
    retry_policy: reconcile_page_then_retry
    on_failure: diagnose
  - step_id: verify
    operation: verify
    arguments: {verifier_ref: fixture.decisions_verifier.v1, data: {state: candidate_results}}
    preconditions: []
    postconditions: [verified]
    timeout_ms: 5000
    effect: read
    retry_policy: no_retry
    on_failure: diagnose
  - step_id: checkpoint
    operation: checkpoint
    arguments: {state: verified_results}
    preconditions: [verified]
    postconditions: []
    timeout_ms: 5000
    effect: read
    retry_policy: idempotent_local_commit
    on_failure: stop
verifier_ref: fixture.decisions_verifier.v1
limits: {max_steps: 10, max_pages: 2, max_recovery_attempts: 2}
provenance: {kind: manual, base_recipe_version: null, evidence_refs: []}
content_hash: GENERATED_AFTER_CANONICALIZATION
```

`content_hash` é marcador de preparação, não hash válido. O compilador da receita deve substituí-lo antes da admissão. O `verify` grava `verified_results` somente após aprovação; `paginate` grava candidatos, preservando a separação entre extraído e publicado. A instalação de teste precisa de resolução local controlada para seu domínio e não pode ser usada em produção.

Os nomes de `retry_policy` acima são políticas a implementar no núcleo. O carregador rejeita nome não registrado. A compatibilidade da gramática é coberta por testes do carregador; YAML aqui é representação legível, não autorização para carregamento inseguro ou resolução automática de objetos Python.

## 9. Adapter mínimo sobre o código real

No commit fixado, `BrowserSession.new_page(url=None)` e `get_current_page()` produzem páginas Actor; a segunda pode retornar `None`. `Page.goto(url)` chama navegação CDP e verifica `errorText`, mas a função não implementa toda a espera de carregamento exigida pela receita. `get_elements_by_css_selector(selector)` consulta o DOM e devolve uma lista de `Element`.

`Element.click(...)`, `fill(value, clear=True)` e `select_option(values)` são as primitivas relevantes. O JCP deve colocar timeout, inspeção de estado e evidência ao redor delas. Métodos de busca por prompt estão em outra categoria porque usam inferência.

Exemplo de fronteira, **incompleto e deliberadamente sem declarar um executor pronto**:

```python
async def locate_one(page, selector):
    elements = await page.get_elements_by_css_selector(selector)
    if len(elements) != 1:
        raise ValueError('expected exactly one element')
    return elements[0]

async def fill_direct(page, selector, value):
    element = await locate_one(page, selector)
    await element.fill(value, clear=True)
```

O exemplo apenas demonstra chamadas reais. Ele ainda não implementa política, visibilidade, frame, leitura posterior, orçamento, persistência ou reconciliação. O código de produção deve percorrer o broker, e os testes não devem confundir ausência de exceção com acerto da tarefa.

A restrição de ferramentas do agente também precisa ser testada: conferir a lista final registrada, após inicialização, e demonstrar que ações padrão não criam um caminho alternativo fora do broker. Uma configuração nominal de exclusão sem conferir a superfície final não fecha essa fronteira.

## 10. Clef como decisão de uso único

`DecisionRequest` proposto: run, etapa, geração da observação, objetivo da etapa, operações permitidas, candidatos por operação, bindings já conhecidos, deadline e orçamento restante. `DecisionResponse`: operação, ID de candidato ou `abstain`, geração, metadados do modelo e uso observado.

O código Ultrafast inspecionado escolhe operação e alvo, valida a cabeça selecionada e consome a decisão antes de agir. Para o JCP:

1. Resolver valores conhecidos diretamente dos bindings. O helper de geração de texto do demo não é necessário para copiar `arguments.query` a um campo.
2. Excluir candidatos incompatíveis por regra antes da inferência.
3. Aceitar somente operação/alvo presentes no conjunto oferecido.
4. Revalidar geração, alvo e política.
5. Consumir a decisão antes de enviar a ação; um retry não pode consumi-la novamente.
6. Registrar tentativa e depois observar o estado posterior.
7. Verificar pós-condição; o retorno `DONE` de um modelo não substitui o verificador.

Probabilidades ou `confidence` retornadas pelo modelo não são probabilidades calibradas de correção jurídica. Um threshold pode ser configurado como heurística após avaliação; não usar um número alto como autorização para ignorar ambiguidade, permissão ou evidência.

## 11. Compilar reparo em receita

O compilador recebe trajetória com ações autorizadas e classifica cada valor como parâmetro, constante estável, estado adquirido ou segredo. Remove exploração redundante e produz referências a parsers/condições já registrados. Se precisar de código novo, abre uma alteração para desenvolvimento e encerra o autorreparo automático naquela fronteira.

Categorias iniciais de patch:

| Categoria | Exemplo | Promoção proposta |
|---|---|---|
| Locator | ID alterado, mesmo formulário e significado | Elegível à automação após regressão e política específica. |
| Espera | Novo estado intermediário reconhecido | Revisão inicial; limite total preservado. |
| Percurso | Novo menu ou nova aba | Revisão do desenvolvedor no início do produto. |
| Parser | Nova estrutura de resultados | Código versionado e testes de dados positivos/negativos. |
| Contrato/efeito | Nova fonte, novo filtro ou ato com efeito | Evolução de capacidade; fora do patch automático. |

Um patch nunca muda conjuntamente o procedimento e a definição do que seria sucesso para fazer a própria correção passar.
