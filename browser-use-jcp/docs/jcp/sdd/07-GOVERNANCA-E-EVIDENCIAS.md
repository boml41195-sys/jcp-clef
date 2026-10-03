# Governança, evidências e qualidade da informação

Este documento especifica os controles do próprio JCP. Não pretende declarar conformidade jurídica automática. A política é parte executável do runtime: ela limita a receita, as decisões de Clef, o agente de reparo e o worker HTTP da mesma forma.

## 1. Identidade e escopo de uma execução

O gateway autentica o chamador e cria `ExecutionContext`. A aplicação, o modelo e a receita não podem sobrescrever `tenant_id`, `principal_id`, `roles`, `policy_version` ou o proprietário de `session_ref`.

Toda operação depende de quatro verificações:

1. O principal pode chamar a capacidade naquela instalação?
2. A sessão pertence ao principal ou foi explicitamente delegada para ele?
3. O recurso solicitado está no escopo autorizado?
4. O efeito concreto da próxima ação está permitido?

Ter login satisfaz uma pré-condição de acesso, não comprova que a sessão ainda está válida. Sessão expirada gera `needs_auth`; esse estado não deve consumir o orçamento de reconstrução de seletores. Uma delegação registra concedente, destinatário, instalação, capacidades, validade e revogação. Compartilhar cookies entre tenants é proibido.

### 1.1 Enforcement no ponto de ação

O `ActionBroker` verifica a política imediatamente antes de cada ação e registra o resultado. O agente recebe somente ferramentas vinculadas ao broker. Expor ao reparador um navegador irrestrito em paralelo invalidaria esse controle.

A política contém origens permitidas, classes de efeito, limites por instalação, escopo de recursos, permissão de retenção e orçamento. Um motor externo como OPA é opcional; no MVP, funções Python determinísticas e testadas implementam a mesma interface `authorize(context, proposed_action) -> Decision`.

Redirecionamentos de autenticação são cadastrados por instalação, com relação explícita ao provedor de identidade. Uma origem vista em um redirect não entra automaticamente na lista permitida. O worker Surf e o navegador usam o mesmo conjunto aprovado de destinos e regras de envio de credenciais.

### 1.2 Efeitos jurídicos

Uma ação visualmente parecida com leitura pode produzir ciência, confirmação ou outro efeito na plataforma. O manifesto declara a classe de efeito conhecida; o adaptador acrescenta guardas para operações intermediárias. Se não for possível determinar o efeito de um caminho, a capacidade permanece experimental ou é suspensa nesse ponto.

| Classe | Condição de execução | Comportamento após timeout |
|---|---|---|
| `read` | Capacidade e recurso autorizados | Repetir apenas quando o percurso estiver classificado como seguro para repetição. |
| `download` | Documento autorizado e limite de bytes | Verificar se o artefato já foi recebido antes de baixar outra vez. |
| `draft_write` | Permissão explícita para editar rascunho | Consultar estado e reconciliar. |
| `external_write` | Política e autorização para a alteração concreta | Não reenviar sem comprovar estado. |
| `legal_acknowledgment` | Autorização específica e identificação do ato | `uncertain_effect` quando o resultado não puder ser confirmado. |
| `signature` / `submission` | Fluxo específico fora do MVP de consulta | Recibo e reconciliação; nunca repetição cega. |

Essas classes são categorias técnicas propostas. Cada instalação precisa mapear seus próprios atos. O MVP certifica apenas percursos de consulta e download cujo efeito tenha sido verificado.

## 2. Sessões, segredos e intervenções

### 2.1 Propriedade e ciclo de vida

Estados internos de sessão: `absent`, `authenticating`, `active`, `expired`, `challenged`, `revoked`. Uma sessão `active` ainda passa por um teste de identidade antes de uma operação sensível. A validação usa indicadores próprios da instalação; HTTP 200 ou a presença de qualquer cookie não bastam.

Cada sessão tem um lease exclusivo para operações que possam alterar sua navegação ou seus tokens. Consultas independentes podem usar contextos distintos quando a instalação permitir. O JCP não abre vários workers com a mesma sessão e presume que os tokens continuarão coerentes.

Credenciais, cookies, armazenamento do navegador e certificados ficam em armazenamento protegido, com referências opacas no banco do JCP. O worker recebe apenas o material necessário durante o lease. O término da execução limpa buffers transitórios conforme a política e libera o lease. Revogação impede novas ações e invalida credenciais derivadas sob controle do JCP.

### 2.2 Login, MFA, certificado e desafios

O fluxo parte da premissa do produto: o usuário possui acesso à ferramenta. Quando houver login, MFA, certificado ou desafio interativo, o runtime oferece uma sessão assistida e depois revalida a identidade. A integração com provedores de navegador ou serviços de desafio usa a interface `ChallengeResolver`; disponibilidade e compatibilidade precisam ser testadas por instalação.

A existência de watchdogs no Browser Use não é evidência de que qualquer CAPTCHA será resolvido. `challenged` é um estado operacional explícito. O protocolo não deve converter um bloqueio persistente em um loop de reconstrução, troca de identidade ou aumento de tráfego. Ao terminar o orçamento, retorna o motivo e o próximo passo necessário.

### 2.3 Credenciais fora do contexto do modelo

O modelo recebe que existe uma sessão válida e quais ações estão disponíveis. Não recebe a senha, o cookie bruto ou a chave privada. Quando a página contém campos com material sensível, o construtor de observação mascara o valor antes de enviar DOM, screenshot ou logs a um provedor de inferência. Caso não seja possível produzir uma observação adequada, o fluxo deve recorrer à operação determinística ou à intervenção assistida.

## 3. Conteúdo da fonte é dado, não instrução

Páginas jurídicas, documentos, PDFs, títulos e mensagens de erro são entradas não confiáveis para o controlador. Uma página que manda ignorar regras, executar comandos, instalar bibliotecas ou enviar arquivos não altera o contrato da chamada.

O isolamento deve ser estrutural:

- O modelo escolhe ações de um conjunto finito associado à capacidade e ao estado observado.
- URLs são derivadas de referências validadas, não de instruções em texto de documentos.
- O reparador pode propor passos e seletores; não pode alterar política, verificador, orçamento ou destino de exportação.
- Código Python ou Go sugerido por modelo não é executado diretamente no worker de produção.
- Ferramentas de shell e acesso ao filesystem geral não fazem parte da superfície do reparador.
- Conteúdo retornado ao assistente é rotulado como material da fonte, com origem e escopo; não é concatenado como mensagem de sistema.

Um reparo que exija novo parser ou nova dependência gera uma alteração de código para o fluxo de desenvolvimento, com testes e revisão. O autorreparo em produção opera dentro da DSL admitida.

## 4. Verificar significado, não apenas formato

O verificador é independente do agente que propôs a extração ou o reparo. Ele combina regras genéricas e regras da capacidade. Schema válido é condição necessária, mas insuficiente.

| Camada | Pergunta verificada | Falha típica |
|---|---|---|
| Transporte | A resposta é do destino e tipo esperados? | HTML de login recebido como PDF. |
| Estado | A tela corresponde à operação solicitada? | Resultado antigo após submit que falhou. |
| Identidade | O processo/documento é o solicitado? | Processo homônimo, número parcial ou seleção errada. |
| Filtros | Os filtros aplicados correspondem à chamada? | Data interpretada como publicação quando era disponibilização. |
| Extração | Campos preservam o conteúdo e a precisão da fonte? | Ementa apresentada como inteiro teor. |
| Cobertura | O escopo percorrido satisfaz o pedido? | Primeira página tratada como busca nacional completa. |
| Evidência | Há referência verificável para o resultado? | Texto sem origem ou documento sem vínculo com o processo. |

### 4.1 Identidade processual e documental

Preservar sempre o identificador bruto. A normalização de número CNJ é implementada e testada separadamente; não significa que todo número de uma plataforma possa ser reduzido ao padrão CNJ. Identificadores legados e internos permanecem representáveis.

Quando a fonte publica número completo, comparar o valor extraído com o solicitado. Quando ela usa identificador interno, vincular esse ID ao registro observado durante a execução. Downloads exigem confirmação do vínculo com processo, movimento ou decisão; nome do arquivo isolado não prova identidade.

### 4.2 Datas, resumos e ausência de resultados

Datas de julgamento, publicação e disponibilização são campos distintos. A extração não preenche um com o outro sem informação explícita. Datas sem horário mantêm precisão de dia. Transformações de encoding, espaços ou Unicode registram versão do parser e preservam o artefato de origem enquanto a política permitir.

Resultado vazio válido exige evidência de que a busca foi submetida e a fonte mostrou ausência de itens para os filtros. Timeout, desafio, parser quebrado e login não são resultados vazios. O texto retornado deve dizer “nenhum resultado nessa fonte e nesses filtros”, sem extrapolar para inexistência de precedentes ou processos no Brasil.

Resumos produzidos por LLM são derivados opcionais, marcados como tal. A resposta estruturada mantém a ementa e os trechos originais disponíveis separadamente. Uma inferência de classificação jurídica não vira fato informado pelo tribunal.

### 4.3 Paginação e completude

O parser registra página/cursor, quantidade, chaves de deduplicação e sinais de próxima página. Repetição de página, ausência de progresso e alteração de total durante a execução entram no relatório. `complete` refere-se ao limite solicitado, enquanto `source_exhausted` indica que a fonte não mostrou continuação.

Ao alcançar um limite, retornar os itens verificados com `partial` quando o escopo solicitado não foi satisfeito. Se o próprio pedido era obter até dez itens e os dez foram obtidos, pode haver `success` sem esgotar a fonte. Cursor de continuação é opaco, vinculado a principal, filtros e versão da capacidade, com validade explícita. Ele não garante snapshot estável de um portal que não oferece essa propriedade.

## 5. Evidências e retenção

Persistir receita não exige persistir indefinidamente os documentos consultados. Há quatro classes diferentes de armazenamento:

| Classe | Conteúdo | Política proposta |
|---|---|---|
| Operacional | Estado, orçamento, erros, versões e eventos | Retenção configurada por organização, com mínimo para reconciliação de runs ativos. |
| Receita | DSL, metadados e testes sintéticos/redigidos | Versões imutáveis; sem credenciais nem conteúdo privado usado como parâmetro fixo. |
| Evidência | Fragmentos, documentos, metadados de resposta | Escopo e vencimento explícitos; acesso igual ou mais restrito que o resultado. |
| Resultado | Objetos e derivados de uma consulta | Cache opcional por tenant e principal, respeitando frescor e autorização. |

Nenhum prazo deste documento constitui prazo legal. Os valores são definidos na configuração do produto e nos contratos aplicáveis. O MVP deve iniciar com cache de conteúdo privado desativado entre execuções; a evidência necessária ao run tem prazo explícito. Documentos guardados pelo usuário podem ter política própria, fora do Pescache.

`sha256` permite conferir integridade de bytes, não comprova sozinho autoria, autenticidade jurídica ou validade de assinatura. Registrar separadamente qualquer verificação de assinatura realizada por ferramenta apropriada, incluindo seu resultado e suas limitações.

Excluir um artefato remove também seus derivados, salvo retenção explicitamente aplicável. Um tombstone pode manter apenas ID, data de expiração e motivo, sem reconstruir o conteúdo. A execução antiga continua auditável quanto ao que fez, mas pode perder a possibilidade de reproduzir a extração; isso deve aparecer na consulta do histórico.

## 6. Persistência e recuperação operacional

Estrutura inicial proposta em banco transacional:

- `capabilities` e `installations`: versões e políticas de catálogo.
- `recipe_versions`: conteúdo imutável, hash, estado e verificador associado.
- `recipe_promotions`: versão ativa por capacidade/instalação/variante, com histórico.
- `runs`: principal, tenant, invocação canônica, estado, deadline e contadores.
- `run_events`: eventos ordenados por run, com chave de deduplicação.
- `action_attempts`: intenção, efeito, início e recibo, necessários à reconciliação.
- `session_refs`: metadados de propriedade e validade; segredos em serviço separado.
- `artifact_refs` e `evidence_records`: referências, escopo, hashes e vencimento.
- `repair_leases`: exclusão e prazo para reconstruções concorrentes da mesma variante.

Atualizar estado do run e publicar evento usa transação/outbox quando o processo for separado em workers. Consumidores são idempotentes. Um evento de ação iniciada sem recibo depois de uma queda não é evidência de que a ação deixou de acontecer.

Armazenamento local é suficiente para desenvolvimento isolado. Produção com concorrência deve usar backend que ofereça transações e locks adequados; não implementar exclusão distribuída por convenção em arquivos JSON. O desenho não exige uma plataforma de filas complexa no primeiro incremento.

## 7. Observabilidade e controle de custo

Todos os passos carregam `run_id`, `step_id`, capacidade, instalação, transporte, versão da receita e política. Traces registram duração e categoria de erro; logs não contêm cookies, senhas nem o texto integral de processos por padrão. Métricas evitam números de processo ou nomes de pessoas como labels.

Métricas mínimas:

1. Sucesso verificado, parcial, erro e intervenção por capacidade/instalação.
2. Taxa de reutilização de receita e chamadas de modelo por execução.
3. Duração p50/p95, separando espera da fonte, autenticação, inferência e verificação.
4. Reparos tentados, candidatos rejeitados, promoções, rollback e recaída de erro.
5. Respostas vazias confirmadas versus falhas de extração.
6. Requisições, bytes, 429, desafios e ocupação de sessão por instalação.
7. Custo observado quando o provedor disponibilizar medição; nunca inferir custo real apenas por contagem de chamadas.

O orçamento é compartilhado por toda a execução e seus subfluxos. Reabrir o agente de reparo não zera contadores. Os limites de tráfego são aplicados por instalação e por identidade, incluindo navegador e Surf. Circuit breaker evita que várias consultas repitam a mesma falha estrutural ou bloqueio.

## 8. Condições para promover uma receita

Uma receita só se torna ativa quando: passa nos verificadores imutáveis da capacidade; satisfaz casos positivos e negativos relevantes; respeita política e orçamento; não incorpora dados da sessão de descoberta; e tem rollback para a versão anterior. A promoção é atômica. Runs em andamento conservam a versão selecionada, salvo cancelamento por risco identificado.

O sucesso de uma consulta após reparo pode autorizar o retorno daquele resultado verificado. Não autoriza, sozinho, certificar o reparo para todos os filtros, perfis e instalações. A certificação é sempre associada ao conjunto de variantes efetivamente testado.

## 9. Critérios de aceite deste módulo

Uma tentativa de cruzar tenant, reutilizar sessão revogada, seguir destino não aprovado, baixar HTML como PDF, retornar processo diferente ou trocar verificador durante reparo deve falhar em teste automatizado. Logs e traces de teste devem demonstrar ausência dos segredos sentinela inseridos nos fixtures. Uma consulta vazia legítima deve passar, enquanto um login com status 200 deve falhar como consulta.

As fontes técnicas e os commits que fundamentam as decisões estão em [09 — Fontes e conclusões](09-FONTES-E-CONCLUSOES.md). Os ensaios de implementação estão em [08 — Implementação e aceitação](08-IMPLEMENTACAO-E-ACEITACAO.md).
