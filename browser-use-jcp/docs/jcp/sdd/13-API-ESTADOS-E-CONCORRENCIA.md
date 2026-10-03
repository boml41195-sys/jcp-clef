# API, estados, retomada e concorrência

Este documento fecha comportamentos de controle necessários para implementar a especificação. Os endpoints são propostos para o JCP; não existem como endpoints do Browser Use. O perfil de dados executável está no documento 10. A API admite múltiplos perfis de capacidade, cada qual com schema próprio.

## 1. Admissão de uma chamada

`POST /v1/runs` recebe Invocation. O gateway autentica principal e tenant, aplica limite ao tamanho do corpo, rejeita JSON malformado ou chaves duplicadas, resolve a versão da capacidade, valida argumentos e autoriza a execução.

Se a chamada for aceita, o servidor persiste o run antes de retornar `202 Accepted`, com `run_id`, `status=accepted`, `revision`, URL de consulta, prazo absoluto e orçamento efetivo. Esses metadados pertencem a `RunView`; o perfil de Result do documento 10 é outro objeto. `request_id` é correlação do chamador; `run_id` é criado pelo servidor.

### 1.1 Idempotência do pedido

A identidade de deduplicação é `(tenant, principal, idempotency_key)`. O fingerprint compara a chamada normalizada, incluindo capacidade/versão, instalação, argumentos, referência de sessão, opções e orçamento. Excluir `request_id` e a própria chave do conteúdo comparado. Aplicar defaults antes de calcular o fingerprint.

Mesma chave e mesmo fingerprint: devolver o mesmo run, sem nova navegação. Mesma chave e conteúdo diferente: `409 Conflict`. Inserção de chave e run ocorre numa transação com constraint única; uma consulta prévia seguida de insert sem constraint não evita corridas.

A autorização atual deve ser reavaliada antes de expor estado ou resultado de um run antigo. Idempotência não mantém permissões revogadas. Não colocar cookie bruto ou segredo no fingerprint.

Uma consulta atual exige nova chave quando a anterior já foi concluída. Um retry de rede do POST original conserva a chave. Tokens de continuação e retomada têm regras próprias e não são intercambiáveis com idempotency key.

### 1.2 Erros da API versus erros da fonte

| Condição | Resposta de controle |
|---|---|
| JSON malformado, chaves duplicadas ou corpo excessivo | `400` ou `413`, sem criar execução. |
| Chamador não autenticado | `401`, sem tocar na sessão do portal. |
| Chamador autenticado, operação proibida | `403`, sem execução. |
| Argumentos/versão de capacidade incompatíveis | `422`, com erro de contrato sanitizado. |
| Conflito de chave, revisão ou comando | `409`. |
| Admissão excede cota local | `429`, com orientação limitada de repetição. |
| Runtime indisponível antes da admissão | `503`; nenhuma execução iniciada. |
| Portal falha depois de aceitar o run | Estado/erro tipado no run, consultável por API. |

Um HTTP 200 ao consultar o estado significa que a consulta de estado funcionou. O cliente precisa ler o status do run; isso não significa que a consulta judicial teve sucesso.

## 2. Superfície de controle

| Endpoint | Entrada | Saída e comportamento |
|---|---|---|
| `GET /v1/capabilities` | Filtros opcionais aprovados | Capacidades visíveis, versões, instalações, efeitos, autenticação, schemas e certificação. |
| `POST /v1/runs` | Invocation | `202` com RunView ou erro de admissão. |
| `GET /v1/runs/{id}` | Identidade do run | RunView autorizado, status, revision, progresso e ação necessária. |
| `GET /v1/runs/{id}/result` | Identidade do run | `200` com Result final; `202` com marcador de indisponibilidade enquanto não houver resultado publicável. |
| `POST /v1/runs/{id}/cancel` | Command ID e revisão esperada | Pedido de cancelamento idempotente; resposta distingue solicitado de concluído. |
| `POST /v1/runs/{id}/resume` | Command ID, revisão, token de retomada e session_ref quando aplicável | Retomada condicional ou `409`/erro de autorização. |
| `GET /v1/runs/{id}/events` | Cursor do último evento visto | Eventos autorizados por SSE ou formato equivalente versionado; deduplicação por sequência. |

`RunView` contém no mínimo `run_id`, `request_id`, `status`, `revision`, `created_at`, `deadline_at`, `effective_budget`, `progress`, `result_available`, `action_required`, `links`. `action_required` pode apontar para um fluxo assistido protegido. Não incluir senha, cookie ou certificado no objeto.

Estados `needs_auth`, `needs_input`, `suspended` e `uncertain_effect` continuam consultáveis por RunView. Um snapshot diagnóstico pode usar o formato Result do documento 10 internamente, mas o endpoint `/result` só entrega resultado final/publicável; não apresentar coleção vazia em andamento como resposta conclusiva.

## 3. Máquina de estados implementável

Estados internos detalham o trabalho; o cliente recebe estados públicos estáveis.

| Estado interno | Estado público | Transições relevantes e guardas |
|---|---|---|
| `ACCEPTED`, `VALIDATING` | `accepted` | Validar, admitir ou falhar. |
| `ACQUIRING_SESSION`, `SELECTING_RECIPE` | `running` | Sessão pronta e receita elegível, ou suspensão/descoberta. |
| `EXECUTING`, `VERIFYING` | `running` | Progredir por recibo e pós-condição; publicar só após verificação. |
| `DIAGNOSING`, `RECOVERING`, `DISCOVERING`, `REPAIRING`, `CANDIDATE_VALIDATION` | `running` | Orçamento compartilhado e escopo preservado. |
| `NEEDS_AUTH` | `needs_auth` | Retomar com sessão válida e token ligado à suspensão; prazo não expande. |
| `NEEDS_INPUT` | `needs_input` | Retomar só com informação admitida; mudança de contrato exige novo run. |
| `SUSPENDED` | `suspended` | Causa e condição de retorno explícitas. |
| `UNCERTAIN_EFFECT` | `uncertain_effect` | Reconciliar; nunca reenviar automaticamente ato incerto. |
| `SUCCEEDED` | `success` | Terminal; resultado imutável dentro da política de retenção. |
| `PARTIAL` | `partial` | Terminal para esse run; continuidade usa novo pedido. |
| `FAILED` | `failed` | Terminal; nova tentativa é novo run, salvo leitura idempotente do histórico. |
| `CANCELLED` | `cancelled` | Terminal somente quando não houver efeito incerto ocultado. |

Entrada inválida detectada antes da criação não precisa virar `needs_input`; recebe erro de admissão. Esse estado é útil para informação requerida durante um plano ou autenticação assistida. Não usar retomada para trocar silenciosamente query, processo ou origem de uma chamada existente.

### 3.1 Contagem de tempo

Para o perfil inicial, `deadline_ms` é prazo total contínuo desde a admissão, incluindo fila, sessão, inferência, navegação e verificação. O servidor fixa `deadline_at` e usa relógio monotônico para medir intervalos dentro de cada processo. Recuperação depois de restart conserva o prazo absoluto e aplica uma política conservadora diante de inconsistência de relógio.

Autenticação assistida tem TTL próprio, limitado pelo prazo restante do run. A pausa não estende o prazo. Se o usuário concluir login depois de expirar o pedido, a sessão pronta pode servir a um novo run com nova chave; a execução expirada não ressuscita. Isso mantém orçamento previsível e evita sessões suspensas indefinidamente.

### 3.2 Orçamento e contadores

Contabilizar páginas efetivamente visitadas para coleta, downloads, bytes recebidos, chamadas de modelo, candidatos de reparo e tentativas conforme definição da capacidade. Falhas também consomem os recursos usados. Uma chamada iniciada cujo custo não pode ser confirmado permanece reservada/conservadoramente contada até reconciliação.

O orçamento efetivo é a interseção entre o solicitado e a política. Se um limite menor impedir satisfazer o escopo original, informar parcial permitido ou recusar a admissão. Não reduzir silenciosamente `arguments.limit` e depois declarar que o pedido maior foi concluído.

Uma chamada ao modelo auxiliar para preencher texto também conta. O JCP não herda do demo Ultrafast um orçamento que exclua helpers e depois anuncia zero inferência.

## 4. Retomada sem duplicar ações

O token de retomada é opaco, gerado pelo servidor, vinculado ao run, principal, tenant, razão da suspensão, revisão e vencimento. Um comando de retomada registra seu próprio ID para tolerar repetição de rede. Token usado com revisão anterior é recusado.

Procedimento:

1. Autenticar e autorizar o principal atual.
2. Validar token, revisão, prazo e estado suspenso.
3. Confirmar propriedade e identidade da nova sessão quando houver.
4. Reconciliar a última tentativa; não inferir que uma ação deixou de acontecer porque o cliente perdeu conexão.
5. Adquirir lease e avançar estado via compare-and-swap.
6. Retomar de um checkpoint semântico ou reiniciar uma leitura segura com os mesmos argumentos.

Checkpoint preserva identidade de recurso, etapas confirmadas, versão da receita, orçamento e evidências. Não preserva índice de elemento como referência válida para uma página recarregada.

## 5. Cancelamento e corrida com a última ação

O sinal de cancelamento impede novas ações assim que observado. Um click ou POST já enviado pode não ser revertível. Se o efeito for incerto, manter `uncertain_effect` até reconciliação, em vez de prometer `cancelled`.

Depois de marcar intenção de cancelamento, interromper waits e chamadas que aceitem cancelamento, fechar o lease conforme a política e registrar o estado final. BrowserSession compartilhada com o usuário não deve ser destruída como se o worker fosse dono exclusivo do navegador.

Se o resultado já foi finalizado, cancelar é uma operação idempotente sem desfazer o ato. A API informa o estado final existente. O sistema deve testar cancelamento concorrente com finalização, promoção e expiração.

## 6. Concorrência, locks e publicação

### 6.1 Lease da sessão

Chave inclui tenant, dono, instalação e sessão. O lease usa fencing token crescente, prazo e proprietário do worker. Persistência rejeita escrita de um proprietário antigo depois de o lease ser transferido. Expiração do lease não prova que um navegador antigo parou; o supervisor precisa isolá-lo/encerrá-lo antes de permitir ações conflitantes.

Dados do portal podem mudar independentemente do lease. O lease controla concorrência do JCP, não implementa bloqueio no tribunal.

### 6.2 Lease de reparo

Chave inclui capacidade, versão, instalação, variante e versão-base da receita. Um worker produz candidato; os demais aguardam de forma limitada ou retornam degradação. Lease de reparo não deve monopolizar a sessão de todos os usuários.

### 6.3 Promoção e resultado

Resultado do run, relatório de verificação e evento de finalização são persistidos atomicamente quando pertencem ao mesmo banco. Publicação em fila usa outbox. A promoção usa compare-and-swap sobre o ponteiro de receita ativa e registra revisão-base.

Um run fixa sua receita e dependências ao começar. Promoção não troca o procedimento no meio de uma execução. O candidato pode resolver o run corrente após verificação e ainda permanecer não promovido para uso geral.

### 6.4 Eventos

Eventos possuem sequência monotônica por run. Entrega pode ocorrer mais de uma vez; consumidores deduplicam por `(run_id, sequence)`. A API de eventos não é autoridade para reexecutar ações. Estado persistido e recibos são a autoridade operacional.

Evitar corpos enormes: eventos apontam para evidências autorizadas. Retenção pode expirar o conteúdo de um artefato sem apagar a existência histórica do evento, conforme a política definida.

## 7. Cursor de busca e continuidade

`Result.continuation` referencia um checkpoint de consulta. Uma nova Invocation envia esse token em `arguments.cursor`. O token é vinculado a principal/tenant, capacidade/versão, instalação, filtros canônicos, estado de paginação, ordenação observada, deduplicação necessária e vencimento.

A nova chamada pode pedir outro `limit` e orçamento, mas deve manter query e filtros vinculados ao token. `limit` vale para os novos itens desse run, não soma silenciosamente itens publicados antes. Alterar origem ou filtros invalida o cursor e exige uma nova busca sem token.

Quando a fonte não fornece snapshot estável, continuidade pode perder estabilidade por inserções/remoções concorrentes. Declarar essa limitação e detectar repetição/ausência de progresso. Cursor expirado não autoriza fabricar paginação equivalente: retornar erro de entrada contextual e oferecer reinício explícito.

O suporte ao campo no schema não significa que a receita CJPG já implementa retomada. Até certificar a função, o catálogo declara `supports_continuation=false`, recusa cursor não nulo e emite `continuation=null`.

## 8. Ponte Surf: cancelamento precisa continuar legível

O protocolo JSON Lines sugerido em 05 admite um request de execução ativo por worker. Isso não significa bloquear o leitor de controle dentro de `Request.Do`: manter a leitura de stdin responsiva e despachar a execução em tarefa/goroutine cancelável, associada ao ID da requisição.

`cancel` referencia o request ativo; o worker confirma recebimento e depois informa estado final. O supervisor distingue confirmação de cancelamento recebido de prova de que nenhuma requisição saiu. Em caso de processo morto, classifica o efeito com base na última fronteira confirmada.

`hello` negocia versão, templates instalados e limites. `execute_template` recusa template desconhecido ou versão divergente antes da rede. `close_session` espera ou cancela de modo explícito o trabalho ativo. Logs vão para stderr; stdout só carrega mensagens do protocolo.

O canal de controle possui limite de mensagem, schema fechado e correlação. Artefatos grandes ficam em diretório atribuído pelo supervisor; não retornam base64 em mensagens. O supervisor valida raiz, tamanho, tipo e hash antes de registrar a referência.

Essas são obrigações do wrapper JCP. O pacote Surf oferece transporte HTTP, não esse protocolo de worker pronto.

## 9. Contexto entregue ao agente consumidor

O resultado verificado é a unidade primária. Um montador opcional cria `ContextPack` com pedido original, fontes consultadas, itens selecionados, trechos, datas, evidências, cobertura e limitações. Ele deve ser determinístico quando apenas selecionar e formatar campos. Síntese por modelo é etapa separada, contabilizada e marcada como derivada.

O catálogo pode oferecer famílias como `search_decisions`, `get_case`, `list_movements` e `get_document`. O roteador procura capacidades certificadas compatíveis com necessidade, instalação, acesso e filtros; não pesquisa toda a internet a cada chamada.

Fluxo mínimo de recuperação de contexto:

1. Receber uma necessidade explícita ou uma função conhecida.
2. Se necessário, resolver um plano finito com fontes, filtros, limite e critério de parada.
3. Executar chamadas independentes até o orçamento do plano, compartilhando limites por fonte e principal.
4. Agregar apenas resultados verificados, preservando origem e erro por fonte.
5. Cortar trechos segundo orçamento de contexto, mantendo referências aos documentos completos e indicando cortes.
6. Entregar ao modelo material da fonte como dados, sem promover instruções presentes nos documentos a comandos do sistema.

O agregado não declara sucesso nacional porque uma fonte respondeu. Se uma das fontes essenciais falha, registra cobertura parcial do plano mesmo que outra chamada tenha `success`. “Fonte esgotada” é relativo aos filtros e ao instante observado.

Deduplicação entre portais deve preservar as múltiplas proveniências. Mesmo número de processo não implica mesma decisão; documento republicado pode ter texto ou data distintos. Priorizar IDs fornecidos pela fonte, relações documentais e conteúdo observado, sem colapsar decisões diferentes por semelhança textual superficial.

O contexto de trabalho pode ser descartado ao final da tarefa conforme política. Pescache mantém como buscar, não precisa reter todos os conteúdos que já passaram pelo runtime.

## 10. Testes de controle obrigatórios

Adicionar testes de corrida para: dois POSTs com a mesma chave; mesma chave com corpo diferente; dois resumes com revisão antiga; worker com lease expirado; cancelamento durante envio; deadline durante login; promoção concorrente; resultado persistido com evento ainda não publicado; reconexão a eventos com duplicatas; cursor usado por outro principal.

Os testes locais do documento 12 validam os envelopes. Estes ensaios requerem um runtime e persistência reais ou simulados de modo controlado; permanecem como critérios de implementação.
