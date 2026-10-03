# Módulos e componentes

Os caminhos abaixo são a estrutura proposta dentro do fork. Cada componente descreve responsabilidade, contrato e condição de correção. São novos módulos JCP, salvo quando identificado um componente herdado do Browser Use.

```text
jcp/
  contracts/       protocol, legal, capabilities, errors, versioning
  catalog/         claws, installations, coverage, discovery
  orchestration/  runs, retrieval, budgets, scheduling, recovery
  runtime/        browser_use, actions, observation, sessions, transport
  pescache/       recipes, matching, binding, execution, persistence
  decisions/      clef, candidates, calibration
  repair/         diagnosis, discovery, patching, compilation
  verification/   checks, evidence, regression, promotion
  governance/     policy, isolation, secrets, audit, telemetry
  claws/          tjsp_cjpg, tjsp_cpopg, stj_scon, pje_trt2, eproc_jfrs
workers/surf/     serviço de transporte opcional em Go
tests/           contracts, fixtures, integration, fault_injection, evaluations
```

## M1 — Contratos e catálogo de claws

### M1.1 — Registro de capacidades

#### M1.1.1 — Manifesto da claw

`ClawManifest` declara ID, versão, responsáveis técnicos, famílias de sistema, instalações e funções. O carregador DEVE validar referências a esquemas, verificadores e políticas antes de disponibilizar a claw. Um manifesto não concede acesso por si só. Erros de manifesto desabilitam somente o pacote afetado.

#### M1.1.2 — Registro da função

`CapabilitySpec` contém nome estável, entrada, saída, efeitos, perfil de acesso, critérios de sucesso, limites e transportes certificados. `get_case` não compartilha o mesmo contrato de `search_cases`. A função fornece um resumo curto ao agente e uma definição completa ao runtime. O nome público inclui instalação quando não existir seleção explícita de instalação.

#### M1.1.3 — Instalação e matriz de compatibilidade

`InstallationSpec` identifica tribunal/organização, grau, URL inicial, origens permitidas, mecanismo de autenticação e variantes conhecidas. Versões de PJe, e-SAJ e eproc não são inferidas somente pela marca visual. A matriz cruza instalação, capacidade, papel do usuário, receita e situação de certificação.

### M1.2 — Tipos jurídicos

#### M1.2.1 — Identidade e normalização

Normalizar número CNJ preservando zeros, máscara original e origem. Validar formato e dígito quando aplicável; aceitar identificadores legados em tipo separado. Nunca tratar todo identificador STJ como número CNJ. Mapear tribunal/grau com diretório versionado e confirmar a instalação efetiva, inclusive migrações entre sistemas.

#### M1.2.2 — Processo e andamento

`CaseRecord` e `MovementRecord` preservam campos originais, nomes normalizados, número exibido, data e identificador do evento quando disponível. Descrição ausente não vira string inventada. Ordem de eventos deve usar a ordem/identidade da fonte; timestamps iguais não autorizam deduplicação indiscriminada.

#### M1.2.3 — Decisão e documento

`DecisionRecord` distingue sentença, acórdão, decisão monocrática e outros tipos quando a fonte informa. `DocumentArtifact` identifica bytes, MIME, hash, origem e vínculo. Ementa e inteiro teor são campos distintos. A classificação inferida é marcada como tal e não substitui o valor da fonte.

### M1.3 — Exposição aos consumidores

#### M1.3.1 — Gateway MCP

Exporta funções JCP com input/output schemas e descrições de efeito. Não exporta primitivas irrestritas de navegador ao agente de negócio. Anotações MCP são informativas; autorização é aplicada pelo runtime. Listagem pode ser filtrada pelas capacidades disponíveis ao principal autenticado.

#### M1.3.2 — API de execução

Recebe `Invocation`, devolve `run_id` e permite consultar status, resultado, cancelar e retomar condições pendentes. O servidor preenche identidade e organização a partir da autenticação; não confia em `tenant_id` sugerido pelo modelo. Chamadas longas não dependem de manter uma conexão aberta.

#### M1.3.3 — Compatibilidade de versões

Mudança incompatível de campo ou semântica exige nova versão major da capacidade. Mudança de seletor sem alterar o contrato gera versão de receita. Versão de protocolo negocia formatos. Receitas antigas permanecem associadas ao contrato para o qual foram certificadas.

## M2 — Orquestrador

### M2.1 — Coordenação de execução

#### M2.1.1 — Máquina de estados

`RunCoordinator` controla transições persistidas. Cada transição tem sequência, causa e revisão esperada. Atualizações concorrentes usam compare-and-swap. O estado terminal não é reaberto; uma repetição deliberada cria outra execução vinculada.

#### M2.1.2 — Escalonador e exclusão

`Scheduler` aplica limites por instalação, organização e sessão. Uma sessão de navegador admite um fluxo que altera estado por vez, salvo suporte explícito de isolamento em contextos independentes. Navegação e cookies compartilhados tornam paralelismo por abas insuficiente como garantia.

#### M2.1.3 — Cancelamento e retomada

O cancelamento impede novas ações e tenta interromper trabalho em andamento. Se uma ação com efeito já foi enviada, o resultado permanece incerto até reconciliação. A retomada parte de checkpoint verificável, não de índice DOM armazenado.

### M2.2 — Planejamento de recuperação de informação

#### M2.2.1 — Resolução de necessidade

`NeedResolver` é opcional: transforma intenção em capacidades registradas e argumentos. A aplicação pode enviar diretamente a função desejada. Uma escolha de fontes registra justificativa e restrições, mas não cria URLs arbitrárias.

#### M2.2.2 — Plano limitado de busca

`RetrievalPlanner` define fontes, filtros, documentos máximos, páginas máximas, prazo e critérios de parada. Pesquisa temática usa vocabulário da instalação e preserva a expressão original. Expansão de sinônimos é rastreável. Não percorrer todo o acervo por ausência de limite.

#### M2.2.3 — Agregação e contexto

`ContextAssembler` recebe itens verificados, deduplica por identidade da fonte/documento e compõe referências. Distribui orçamento de tokens entre fontes e pode retornar resumos com links aos trechos. Documento completo continua distinguível de recorte. Falha em uma fonte aparece na cobertura do resultado agregado.

### M2.3 — Limites e encaminhamento

#### M2.3.1 — Reserva de orçamento

`BudgetLedger` reserva capacidade antes de modelo, navegação, download ou reparo. Mantém tempo, chamadas, tokens e bytes. Preço desconhecido não vira custo zero. Orçamento esgotado termina com resultado parcial explicitamente permitido ou `BUDGET_EXHAUSTED`.

#### M2.3.2 — Classificação de falha

`FailureRouter` primeiro usa sinais determinísticos: status, URL, marcadores de login, erro de conexão, página esperada e invariantes. Clef entra apenas em ambiguidades. `RATE_LIMITED`, `AUTH_EXPIRED` e `PORTAL_UNAVAILABLE` não iniciam alteração de receita.

#### M2.3.3 — Circuit breaker

Agrupa falhas por instalação e causa. Uma falha compartilhada não deve disparar reparo para todos os usuários. Define pausa e sondagem limitada após backoff. Falha de um usuário não deve invalidar sessões de todos os demais.

## M3 — Runtime e sessões

### M3.1 — Adaptador Browser Use

#### M3.1.1 — Ciclo de vida

`BrowserUseAdapter` recebe uma sessão existente ou cria um BrowserSession configurado. Controla posse: encerrar a execução não deve fechar o navegador pessoal do usuário se o worker apenas o anexou. Usa APIs públicas sempre que possível e concentra acessos internos num único módulo.

#### M3.1.2 — Broker de ações

`ActionBroker.execute(step, context)` aplica política, registra intenção, resolve alvo fresco, executa e registra confirmação/erro. Tanto receitas quanto ferramentas do agente de reparo passam por esse broker. Uma chamada direta ao Actor fora da fronteira seria uma violação de arquitetura.

#### M3.1.3 — Observação

`ObservationService` produz URL canônica, origem, título, estado reconhecido, elementos candidatos, identidade de página e horário. Captura screenshots apenas quando úteis. Não depender de screenshot no caminho estável se DOM basta. Mudança irrelevante de animação não invalida automaticamente toda observação.

### M3.2 — Sessões autenticadas

#### M3.2.1 — Cofre e referência de sessão

`SessionBroker` mapeia referências opacas para perfil, principal, organização, instalação e estado. Segredos ficam fora das receitas e prompts. A sessão obtida é conferida contra o papel esperado; página com texto genérico de conta não prova autenticação.

#### M3.2.2 — Saúde e renovação

`SessionHealth` distingue anônima, pronta, expirada, autenticação pendente e acesso negado. A renovação preserva escopo. Cookies válidos em uma origem não provam que a etapa de SSO finalizou. O retorno de autenticação deve confirmar origem e contexto esperado antes de retomar.

#### M3.2.3 — Interação assistida e desafios

`AccessChallengeAdapter` integra mecanismos disponíveis no provedor e passagem temporária de controle ao usuário. A execução fica suspensa com prazo e token de retomada. Certificados, PJeOffice, MFA e CAPTCHA não são delegados ao gerador de receitas como se fossem seletores quebrados.

### M3.3 — Transporte e conteúdo

#### M3.3.1 — Seleção de transporte

`TransportRouter` escolhe browser ou HTTP entre implementações certificadas. Mudança de transporte não muda autorização nem critérios de sucesso. `transport=auto` usa preferência de custo/latência por capacidade com fallback documentado.

#### M3.3.2 — Extração determinística

`ExtractorRegistry` oferece parsers versionados para HTML, tabelas, JSON e documentos. Cada parser recebe artefato e contexto e retorna objetos mais um relatório de campos ausentes/ambíguos. Saída vazia sem marcador de zero resultados é falha de interpretação.

#### M3.3.3 — Aquisição de documentos

`DocumentFetcher` associa download à ação/origem, espera conclusão, verifica tipo real e limites e calcula hash. PDF com HTML de login dentro não passa. OCR é fallback explícito, com página e qualidade registradas; não alterar o arquivo original para acomodar a extração.

## M4 — Pescache

### M4.1 — Registro

#### M4.1.1 — Repositório de receitas

`RecipeStore` armazena versões imutáveis da DSL, verificadores referenciados, parâmetros e matriz de compatibilidade. O ponteiro de produção é atualizado atomicamente. Conteúdo de uma receita publicada não é editado no lugar.

#### M4.1.2 — Índice de compatibilidade

`RecipeMatcher` considera capacidade, instalação, contrato, papel, transporte e variante de interface. Uma assinatura estrutural serve como sinal; não deve incluir todo texto dinâmico da página nem ser o único critério de seleção.

#### M4.1.3 — Ciclo de vida

Estados: draft, candidate, certified, degraded, retired. Guardar origem, execução de descoberta, testes e motivo de substituição. Rollback aponta para versão anterior compatível; não restaura cookies nem desfaz atos no portal.

### M4.2 — Execução

#### M4.2.1 — Binding de parâmetros

`ParameterBinder` substitui referências tipadas por valores validados. Datas são formatadas pelo adaptador da instalação; número CNJ é dividido corretamente por campos. Referências de segredo são resolvidas somente no worker autorizado.

#### M4.2.2 — Interpretador

`RecipeExecutor` executa operações declaradas e condições limitadas. Laços exigem limites e prova de progresso. Não usar `eval` de expressões fornecidas por modelo. Elementos são localizados novamente no estado atual.

#### M4.2.3 — Checkpoints e efeitos

Checkpoint registra etapa semântica, identidade de recurso e observação mínima. Uma ação é registrada como planejada, enviada, confirmada ou incerta. Queda entre envio e confirmação impede repetição cega de ações com efeito.

### M4.3 — Reuso seguro

#### M4.3.1 — Cache operacional

Cache de receita ignora o número específico do processo quando o fluxo é parametrizado, mas respeita compatibilidade de papel e instalação. Cache de resultado inclui parâmetros e fronteira de acesso. Não compartilhar resultados privados entre usuários porque a receita é compartilhada.

#### M4.3.2 — Detecção de deriva

Observar redução de sucesso, divergência de campos, novos estados e falhas de verificação. Um sucesso de clique sem conteúdo esperado também pode indicar deriva. Desativar promoção automática durante incidente compartilhado.

#### M4.3.3 — Recuperação estrutural

Usar cascata determinística de locators e, opcionalmente, Scrapling como gerador de candidatos. Um candidato de parsing deve ser remapeado ao DOM vivo antes de interação. Não clicar em um resultado de similaridade sem confirmar papel, contexto e unicidade.

## M5 — Decisões Clef

### M5.1 — Preparação

#### M5.1.1 — Estado reduzido

`DecisionStateBuilder` envia somente estado necessário, objetivo da etapa, candidatos e histórico recente. Remove segredos e dados de outras tarefas. Texto do portal é entrada não confiável, sem autoridade para modificar o contrato.

#### M5.1.2 — Espaço de ações

`CandidateBuilder` produz IDs efêmeros ligados à observação e separa alvos por operação. Inclui `ABSTAIN`/`BLOCKED` quando nenhuma escolha é sustentada. Alvos de outro frame ou snapshot não podem ser reutilizados implicitamente.

### M5.2 — Escolha

#### M5.2.1 — Cliente TypeSafe

`CloudflareClefProvider` chama perguntas Choice do Clef e valida domínio, campos e distribuições. A normalização do envelope Workers AI fica neste adapter. Usa cliente assíncrono ou execução isolada do código síncrono de referência para não bloquear o event loop. Timeouts e falhas do provedor retornam decisão indisponível.

#### M5.2.2 — Aceitação da decisão

`DecisionGate` combina validade, confiança calibrada por tarefa, risco e estado fresco. O valor de confiança do provedor não é automaticamente probabilidade de acerto jurídico. Limiar inicial é configuração experimental, promovida após avaliação.

### M5.3 — Consumo

#### M5.3.1 — Decisão de uso único

Decisão aceita recebe token ligado ao snapshot, alvo e orçamento. É consumida uma única vez antes da ação. Se o alvo mudou antes do envio, observar novamente; se a mutação foi enviada e o resultado é incerto, reconciliar.

#### M5.3.2 — Escalonamento

Ambiguidade persistente chama descoberta limitada ou devolve bloqueio. Clef não gera o código de reparo. Conteúdo de campo já fornecido pelo contrato não exige modelo de texto auxiliar.

## M6 — Descoberta e autorreparo

### M6.1 — Diagnóstico

#### M6.1.1 — Pacote de falha

`FailureBundle` reúne passo, observação sanitizada, causa, identidade esperada, diferenças estruturais e orçamento. Não enviar histórico integral de navegação nem documentos não necessários.

#### M6.1.2 — Escolha de escopo

Reparar locator antes de parser; parser antes de percurso completo, quando a causa sustentar essa ordem. Falha de autenticação ou infraestrutura não gera patch. A correção não pode ampliar domínios e permissões unilateralmente.

### M6.2 — Descoberta

#### M6.2.1 — Sessão do agente Browser Use

Executar `Agent` com mesma instalação, objetivo concreto e conjunto permitido de ações. Preservar contexto de acesso sem expor segredos. Registrar ações e artefatos suficientes para reconstruir o percurso. Navegações de descoberta seguem o mesmo broker e política.

#### M6.2.2 — Conversão em receita

`TraceToRecipe` transforma a trajetória em passos parametrizados, elimina tentativas descartadas e adiciona pré/pós-condições. Não trocar literais por parâmetros por simples substituição global: preservar quais valores vieram da entrada, do estado e da fonte.

### M6.3 — Patch

#### M6.3.1 — Candidato estruturado

`RepairPatch` referencia receita-base, alterações, causa e testes. Só muda campos permitidos pelo tipo de reparo. Verificadores e permissões ficam protegidos contra autoalteração para passar no teste.

#### M6.3.2 — Concorrência e promoção

Uma trava por chave de compatibilidade evita reparos duplicados. Aplicar somente se a receita-base ainda corresponde à revisão esperada. Se outra versão foi promovida, reavaliar o candidato. Um sucesso isolado permite concluir a tarefa atual quando verificada; não basta para certificação geral.

## M7 — Verificação e promoção

### M7.1 — Verificação

#### M7.1.1 — Estrutura e identidade

Validar schema, tipos, identificadores, fonte e recurso esperado. Comparar CNJ consultado com exibido após normalização. Título de página e `DONE` do agente não substituem essa verificação.

#### M7.1.2 — Filtros e completude

Confirmar filtros aplicados, escopo de paginação, contagens e condição de parada. Resultado parcial pode ser válido, mas deve indicar o que faltou. Campos de data sem semântica definida não podem sustentar uma alegação de filtro correto.

#### M7.1.3 — Conteúdo e proveniência

Ligar trechos a artefatos, páginas e localizadores de origem. O verificador de download testa conteúdo real, tamanho e consistência com o item selecionado. Extração por modelo fica identificada como derivação, com referência ao original.

### M7.2 — Regressão

#### M7.2.1 — Casos de referência

Manter fixtures sanitizadas e casos de portal permitidos com estados normais, vazios, parciais e bloqueados. Proteger contra sobreajuste ao primeiro processo usado na descoberta.

#### M7.2.2 — Mutação controlada de interface

Fixtures alteram IDs, ordem, rótulos, overlays, paginação e texto de erro. O teste deve medir recuperação correta e rejeição de candidatos errados, não somente taxa de clique.

### M7.3 — Publicação

#### M7.3.1 — Certificação

Produzir relatório com instalação, papel, cenários, versão de runtime e resultados. Autorizar promoção conforme política do ambiente. Para leituras de baixo risco, critérios automatizados podem ser suficientes após validação do processo.

#### M7.3.2 — Canary e reversão

Aplicar nova versão a fração configurada de execuções, acompanhar falsos sucessos e erros e reverter ponteiro se necessário. Uma execução já iniciada mantém sua versão para evitar mudanças de semântica no meio do percurso.

## M8 — Governança e evidências

### M8.1 — Política

#### M8.1.1 — Autorização de capacidade

Decide principal, organização, instalação, função, recurso e efeito permitido. Autoriza antes da aquisição de sessão e antes de cada ação relevante. OPA pode substituir o avaliador interno atrás da mesma interface.

#### M8.1.2 — Política de execução

Aplica domínios, transporte, orçamento, arquivos e limites. O worker HTTP não recebe autoridade para buscar qualquer URL indicada por um modelo. Permissões são herdadas do contexto autenticado e estreitadas pela tarefa.

### M8.2 — Isolamento

#### M8.2.1 — Sessões e artefatos

Separar perfis, cookies, arquivos e registros por organização e principal. Uma receita compartilhada não contém dados de sessão. Deduplicação de documentos deve preservar ACL; o mesmo hash não autoriza acesso cruzado.

#### M8.2.2 — Código e extensões

Executar extensões em worker com limites de filesystem/rede e segredos mínimos. Confiar em schema não torna código arbitrário seguro. O primeiro MVP evita aceitar Python livre como saída de reparo.

### M8.3 — Registro operacional

#### M8.3.1 — Auditoria

Persistir chamada, política aplicada, versão, transições, passos, evidências e resultado. Sanitizar tokens e URLs transitórias. IDs de correlação conectam registros sem duplicar dados jurídicos sensíveis nos logs.

#### M8.3.2 — Telemetria e avaliação

Medir duração por etapa, inferências, bytes, reparos e motivo de parada. Traces amostrados não substituem registro de execução necessário à reconciliação. Métricas agregadas devem permitir comparar custo e qualidade por instalação e versão.
