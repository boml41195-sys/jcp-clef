# Implementação, critérios de aceite e ordem de entrega

Este plano transforma a especificação em incrementos verificáveis. Os componentes JCP citados aqui são propostos. O pacote não contém uma implementação pronta nem atribui ao Browser Use APIs que ainda precisam ser criadas pelo projeto.

## 1. Primeiro resultado que o desenvolvedor deve construir

Receber uma chamada tipada de busca CJPG, executar uma receita pelo navegador do Browser Use, extrair decisões, comprovar filtros e origem e retornar JSON. Repetir com parâmetros diferentes sem chamar LLM. Depois introduzir uma mudança de seletor em uma réplica de teste, produzir um reparo candidato e demonstrar que o verificador aceita a correção correta e rejeita a incorreta.

Esse circuito comprova o núcleo do produto: função jurídica estável, reutilização determinística, contexto recuperado na hora e autorreparo verificável. O segundo portal testa se a arquitetura generaliza. Surf e Jev entram em pontos mensuráveis desse circuito, sem bloquear a primeira entrega funcional.

## 2. Organização do fork e das mudanças

Partir do commit do Browser Use registrado em [09](09-FONTES-E-CONCLUSOES.md), fixar dependências em lockfile e executar os testes relevantes do upstream antes de alterar a biblioteca. Não usar a branch principal flutuante como dependência de produção.

Manter o núcleo JCP em pacote próprio no fork. O primeiro conjunto de mudanças deve caber nos adaptadores e no registro de ferramentas; editar internals do Browser Use somente quando o ponto de extensão existente não suportar o contrato. Cada alteração upstream mantém uma nota curta sobre o motivo e um teste de compatibilidade.

Estrutura sugerida:

```text
jcp/
  contracts/          # modelos Pydantic, schemas, erros, versões
  catalog/            # manifests, installations, capabilities
  orchestration/      # runs, budgets, policy gates, leases
  runtime/            # browser adapter, actions, sessions, transports
  pescache/           # DSL, interpreter, immutable recipes, promotions
  decisions/          # Jev adapter, action candidates, deterministic gate
  repair/             # failure bundle, discovery, candidate builder
  verification/       # identity, filters, coverage, evidence
  governance/         # tenant scope, audit, retention
  claws/tjsp/cjpg/     # primeiro parser, manifesto, receitas e verificadores
workers/surf/         # worker Go opcional após baseline browser
tests/
  fixtures/           # HTML/PDF sintéticos ou redigidos, sem sessões reais
  contract/
  integration/
  acceptance/
  benchmarks/
```

Esse layout complementa a decomposição de [02](02-MODULOS-E-COMPONENTES.md). Não é uma listagem de diretórios já implementados neste pacote documental.

## 3. Incrementos e dependências

| ID | Incremento | Entrega concreta | Dependência | Condição para encerrar |
|---|---|---|---|---|
| I0 | Base reproduzível | Fork fixado, lockfile, smoke test Browser Use, inventário de licenças | Nenhuma | Abrir página de fixture e executar ação Actor com sucesso. |
| I1 | Contratos e catálogo | Invocation, Result, Manifest, Recipe, erros e schemas | I0 | Validar chamadas positivas e rejeitar argumentos incompatíveis. |
| I2 | Runtime determinístico | Browser adapter, ActionBroker, interpreter, deadline e eventos | I1 | Fluxo de fixture completo, sem LLM e sem ações fora da política. |
| I3 | Claw CJPG | Busca, parser, paginação limitada, evidência e verificador | I2 | Consulta real verificada no escopo testado, mais regressão offline. |
| I4 | Pescache persistente | Seleção, versões, ativação atômica, checkpoint e rollback | I3 | Segunda execução parametrizada reutiliza receita sem inferência. |
| I5 | Recuperação estrutural e Jev | Candidatos, gate, decisão de uso único, budgets | I4 | Resolver mudança conhecida ou recusar candidato ambíguo. |
| I6 | Reparo generativo | Agente Browser Use restrito, trace-to-recipe, testes e promoção | I4; I5 opcional | Corrigir fluxo quebrado e rejeitar reparo semanticamente incorreto. |
| I7 | Segunda instalação pública | CPOPG ou SCON conforme validação de acesso | I3, I6 | Reusar núcleo e acrescentar apenas pacote de capacidade/adaptação. |
| I8 | Sessão autenticada | Lease, retomada, identidade, expiração e primeira capacidade privada | I2, I4, I6 | Testar com conta autorizada e retornar resultado verificado. |
| I9 | Surf certificado | Worker Go, templates, bridge de sessão e comparação de transporte | I3, baseline de medição | Equivalência semântica e TLS efetivo comprovados por template. |
| I10 | Piloto operável | Métricas, limites por fonte, rollback, retenção e matriz publicada | I6, I7; I8 se escopo privado | Operação dentro dos critérios de lançamento abaixo. |

Não há prazo fechado neste documento: acesso às instalações e estabilidade dos portais afetam a duração. Cada incremento termina em evidência executável, não em quantidade de arquivos criados.

### 3.1 I0–I2: fundamentos

1. Instalar a versão fixada em ambiente isolado. Registrar versões efetivas de Python, navegador e dependências.
2. Criar um pequeno `BrowserUseAdapter` que abra sessão, obtenha página, observe, encontre alvo, preencha, clique e feche. Usar as APIs reais do Actor apontadas no documento 05.
3. Implementar espera explícita e limitada. Não pressupor auto-wait do Playwright em métodos do Actor.
4. Modelar operações da DSL como união discriminada. Rejeitar operações desconhecidas e bindings ausentes antes de iniciar o navegador.
5. Construir `ActionBroker` como única rota de ação e `VerifierRegistry` separado do construtor de receitas.
6. Registrar tentativas e recibos. Tratar erro contido em `ActionResult`, além de exceções Python.
7. Provar cancelamento e deadline mesmo quando a página não termina de carregar.

### 3.2 I3–I4: caminho determinístico real

Começar com CJPG, pois a consulta pública foi observada durante a pesquisa e há automação existente útil para entender parâmetros e estrutura. Os seletores observados são ponto de partida, não garantia futura. O manifesto começa em `experimental`.

O primeiro parser deve preservar número bruto do processo, tipo e origem do trecho, datas disponíveis e URL. Cobrir resultado vazio e paginação desde o início para não consolidar uma receita que só entende a primeira página de sucesso. Inteiro teor pode ficar em uma capacidade separada até sua navegação ser validada.

A receita inicial pode ser escrita manualmente pelo desenvolvedor. O autorreparo deve ser avaliado contra um fluxo conhecido e correto; não há vantagem em exigir descoberta generativa para provar o caminho básico.

Persistir uma versão imutável e repetir o teste com consulta e datas diferentes. Esse teste deve encontrar parâmetros indevidamente gravados, datas fixas, cookies incorporados e índices DOM reaproveitados entre execuções.

### 3.3 I5: Jev onde ele produz diferença

Integrar o cliente de decisão tipada observado em Jev Ultrafast atrás de `DecisionProvider`. A disponibilidade do serviço, credenciais e modelo exato entram na configuração; não cristalizar `jev-latest` como garantia de modelo ou desempenho.

Primeiras decisões admitidas:

- Escolher o campo de busca entre candidatos presentes e já filtrados por papel e contexto.
- Escolher o controle de continuação entre opções observadas.
- Classificar estado entre opções fechadas como resultado, autenticação, desafio, carregamento ou erro.
- Decidir entre duas ações de recuperação previamente autorizadas.

Jev não recebe a tarefa de produzir Python arbitrário, relaxar verificador, adivinhar um endpoint ou afirmar que um resultado jurídico está correto. A resposta é validada pelo conjunto oferecido e pela política antes de agir. `abstain` é resposta válida.

Reutilizar a ideia mais útil do código Ultrafast: observação pequena, ação tipada e decisão consumida uma única vez. Não reutilizar cegamente uma escolha tomada sobre estado anterior depois de navegar ou mudar a página.

### 3.4 I6: ciclo completo de reparo

O teste de aceitação principal usa três versões controladas da mesma página: A funciona, B muda a estrutura mantendo o significado, C inclui um alvo plausível que leva a resultado errado. A versão B deve gerar correção verificável; C deve demonstrar que o sistema recusa o caminho incorreto.

O bundle de falha contém observação sanitizada, contrato, passos anteriores, erro, evidências e orçamento restante. O agente Browser Use explora somente as ações da capacidade. O trace é compilado em DSL declarativa; não copiar o histórico do agente como se isso garantisse replay sem inferência.

Executar candidato com verificador fixo. Em seguida, rodar regressão nos filtros suportados e em pelo menos um caso negativo. Só então promover a versão. Um segundo worker tentando reparar a mesma variante deve aguardar o lease ou usar a versão estável, sem criar uma disputa de promoções.

### 3.5 I7–I8: generalização e login

Usar as limitações observadas em [06](06-MAPEAMENTO-DOS-PORTAIS.md) para escolher a próxima fatia. CPOPG exige validar o percurso até detalhe; SCON exige resolver o acesso ao fluxo real antes de certificar seletores. Não lançar nenhuma das duas com base apenas em código de terceiro.

Na fatia autenticada, começar por uma única instalação e uma única função de leitura. Testar identidade, sessão expirada, MFA e retomada no mesmo pedido. PJe e eproc têm contextos e fluxos distintos: o fato de ambos aceitarem login não permite compartilhar automaticamente uma receita.

### 3.6 I9: Surf sem criar um segundo controlador

Compilar o commit inspecionado com toolchain compatível e rodar os testes do worker. O `go.mod` observado declara Go 1.27; sua disponibilidade no ambiente alvo ainda precisa ser verificada. Não reescrever a versão declarada e presumir compatibilidade.

Certificar TLS, política de redirect, limites de bytes, cancelamento e tratamento de retry antes de medir velocidade. O Surf inspecionado tem configuração inicial de TLS que requer endurecimento explícito, conforme documento 05.

Escolher um template de consulta de baixo risco. Obter resultados pelo navegador e por HTTP com filtros e sessão equivalentes. Comparar identidade, campos, cobertura, encoding e documentos. Promover somente esse template. Se a equivalência falhar, a capacidade continua no navegador.

## 4. Suíte de aceitação

Os testes abaixo validam comportamentos do protocolo. Fixtures cobrem regressão sem gerar tráfego repetitivo nos portais; testes ao vivo são limitados e identificados separadamente.

| Teste | Cenário | Resultado obrigatório |
|---|---|---|
| T01 | Invocation com argumento não permitido | Rejeição antes de acessar a fonte. |
| T02 | Receita válida e consulta parametrizada repetida | Zero chamadas de modelo no caminho determinístico. |
| T03 | Mesmo HTML de resultado, processo diferente | Verificação falha; nenhum sucesso. |
| T04 | Busca legitimamente sem resultados | Sucesso vazio com evidência da consulta e do estado vazio. |
| T05 | HTML de login com status 200 | `needs_auth`; não interpretar como resultado vazio. |
| T06 | Mudança de seletor com candidato correto | Reparo validado e versão candidata registrada. |
| T07 | Candidato plausível semanticamente errado | Reparo rejeitado pelo verificador fixo. |
| T08 | Página repete a mesma paginação | Interromper sem progresso e informar cobertura. |
| T09 | Fim de orçamento durante recuperação | Encerrar no limite compartilhado, sem loop de reinício. |
| T10 | Conteúdo da página tenta dar instruções ao agente | Nenhuma ação fora do contrato e da política. |
| T11 | Sessão de outro tenant ou sessão revogada | Acesso negado antes de usar credenciais. |
| T12 | Dois reparos concorrentes da mesma variante | Uma promoção por vez; versões e causalidade preservadas. |
| T13 | Processo cai depois de enviar ação com efeito | Reconciliação ou `uncertain_effect`; sem reenvio cego. |
| T14 | PDF válido, HTML disfarçado e arquivo excessivo | Aceitar apenas artefato permitido e vinculado; rejeitar os demais. |
| T15 | Surf: certificado inválido ou redirect não permitido | Falha de transporte/política, sem vazar credenciais. |
| T16 | Browser e Surf com mesmo contrato | Equivalência de dados e cobertura no conjunto certificado. |
| T17 | Segredos sentinela em página/cookies | Ausência nos prompts, logs e artefatos compartilháveis. |
| T18 | Jev responde alvo fora da lista ou observação vencida | Rejeição e nova observação ou escalonamento dentro do orçamento. |
| T19 | Cancelamento durante paginação/download | Novas ações impedidas e worker encerrado/reconciliado. |
| T20 | Receita com query/data/cookie fixado da descoberta | Falha de teste de parametrização ou sanitização. |
| T21 | Instalação muda fluxo após promoção | Degradação explícita, circuito de reparo e rollback disponíveis. |
| T22 | Cache de resultado com permissões ou frescor diferentes | Não reutilizar resultado incompatível. |

Casos que não fazem parte do MVP permanecem em backlog identificado; não precisam de uma implementação de escrita jurídica para lançar o produto de consulta. Entretanto, classes de efeito desconhecidas devem ser recusadas desde o primeiro runtime.

## 5. Medir a tese do produto

Comparar as mesmas tarefas e seus resultados verificados em quatro modos:

| Modo | Execução | O que mede |
|---|---|---|
| A | Agente Browser Use conduzindo a tarefa | Baseline generativo. |
| B | Receita determinística pelo Browser Use | Economia de inferência e repetibilidade. |
| C | Receita quebrada com recuperação estrutural/Jev/agente | Custo e taxa de recuperação correta. |
| D | Template Surf certificado | Ganho de transporte no subconjunto equivalente. |

Fixar versões, hardware, região, sessão, consultas, limites, disponibilidade da fonte e critério de sucesso. Reportar testes frios e quentes separadamente. Medir criação de sessão, navegação, inferência, extração e verificação; deixar claro qualquer custo excluído. Não comparar A com login incluído contra B com sessão pronta sem destacar a diferença.

Guardar tamanho da amostra, distribuição de casos, falhas e taxa de intervenção. Usar p50/p95 e custo observado, além da média. Resultados com identidade errada contam como falha, mesmo que sejam rápidos. Ensaios em fixtures e em portais reais são relatórios diferentes.

O benchmark Jev Ultrafast registrado em [09](09-FONTES-E-CONCLUSOES.md) inspira desenho de controle e hipóteses de desempenho. Não é benchmark do JCP, dos tribunais brasileiros ou do Surf integrado. Nenhuma redução percentual é prometida antes do ensaio acima.

## 6. Rastreabilidade dos requisitos

| Necessidade do produto | Decisão implementável | Módulos | Testes centrais |
|---|---|---|---|
| Buscar quando precisar | Invocation com frescor, execução ao vivo e origem | M1, M2, M3, M7 | T04, T05, T22 |
| LLM chamar função jurídica estável | CapabilitySpec independente da interface | M1, M8 | T01, T03 |
| Repetir sem inferência | DSL parametrizada e Pescache | M3, M4 | T02, T20 |
| Corrigir quando a interface mudar | Diagnóstico, candidato, verificação, promoção | M5, M6, M7 | T06, T07, T12, T21 |
| Usar login existente | Sessão vinculada ao principal e retomada | M3, M8 | T05, T11, T17 |
| Usar Jev de forma útil | Escolha tipada, observação atual e abstinência | M5 | T18, T09 |
| Incorporar Surf | Transporte intercambiável por template certificado | M3, M7 | T15, T16 |
| Cobrir fontes jurídicas diversas | Instalações e certificação por capacidade | M1, M7 | T03, T08, T14 |
| Governança | Broker, política, evidência, auditoria e isolamento | M2, M8 | T10, T11, T13, T19 |

As designações M1–M8 referem-se ao documento 02.

## 7. Condições de lançamento do piloto

O piloto deve publicar a matriz exata de capacidades, instalações, filtros e perfis certificados. “Compatível com PJe” é amplo demais se apenas uma instalação e uma função passaram pelos testes.

Para a primeira capacidade de consulta: contrato validado, consulta real verificada, teste de parametrização sem inferência, evidência de resultado vazio correto, paginação limitada, identidade e filtros checados, erro de autenticação distinto de ausência de dados, orçamento finito, rollback e métricas básicos.

Para anunciar autorreparo: demonstrar recuperação em mudança controlada e recusa em caso adversarial, sem alterar verificador. Para anunciar Surf: adicionar T15/T16. Para anunciar acesso autenticado: adicionar testes reais de identidade, expiração, retomada e isolamento com contas autorizadas.

“Zero erros de identidade nos casos de aceite” é um bloqueio de lançamento desse conjunto de testes, não uma garantia estatística universal. Metas comerciais de latência, disponibilidade e custo serão definidas depois da medição representativa.

## 8. O que deve aparecer na primeira demonstração

Mostrar a chamada de função, a receita e versão escolhidas, o resultado com origem, a contagem de chamadas de modelo e o relatório de verificação. Repetir com novos parâmetros e mostrar zero inferência. Quebrar um seletor na réplica, executar recuperação e mostrar o diff da receita candidata. Por último, oferecer um alvo errado e mostrar a rejeição.

Essa demonstração comunica o diferencial do JCP sem depender de uma alegação de cobertura universal: o agente ganha acesso jurídico sob demanda, enquanto o sistema acumula procedimentos verificáveis e reutilizáveis.
