# Pivot do MVP e implementação

## 1. Decisão registrada

Clef passa a ser o provedor de decisões delimitadas do MVP. Jev deixa de ser dependência de produção prevista; seu código Ultrafast permanece uma referência histórica de desenho de loop, validação e consumo de decisões. **A LLM generativa não foi excluída:** continua responsável por geração de código e reparos que a gramática de ações não resolve.

Configuração inicial proposta: `clef` hospedado em Workers AI; `clef-flash` como variante avaliada por tipo de decisão; Agent Browser Use com modelo generativo configurável para descoberta/reparo. O `ChatBrowserUse` é uma opção de integração nativa do fork; a escolha do modelo generativo não é o objeto deste pivot e não exige trocar o restante da arquitetura.

## 2. Mudança por módulo

| Módulo | O que muda | O que precisa ser implementado |
|---|---|---|
| M1 Contratos/catálogo | Capacidade continua sem referência obrigatória ao provedor de IA. | Catálogo pode declarar suporte a recuperação e perfis avaliados. |
| M2 Orquestrador | Orçamento distingue decisões Clef e chamadas generativas, conservando total global. | Diagnóstico, roteamento e deadlines compartilhados. |
| M3 Runtime/sessões | Browser Use continua a executar; Clef não recebe controle direto de CDP. | Adapter e ActionBroker, sessões e política de dados enviados. |
| M4 Pescache | Receitas continuam independentes do modelo que as descobriu. | Proveniência registra variante e schema de perguntas usados no reparo. |
| M5 Decisão | `CloudflareClefProvider` substitui cliente Jev. | Conversão de estado, transporte, normalização, validação e gate. |
| M6 Descoberta/reparo | Decisão delimitada e geração de código continuam caminhos distintos e combináveis. | Trace-to-recipe, patches, testes e escalonamento para Agent generativo. |
| M7 Verificação/promoção | Não delegar certificação ao Clef. | Ensaios positivos/negativos, comparação por variante e promoção versionada. |
| M8 Governança | Registrar provedor/modelo e envio de contexto com política explícita. | Redaction, uso, isolamento, evidências e avaliação de implantação. |

## 3. Ordem de entrega para o desenvolvedor

### Etapa A — Contrato e caminho estável

Extrair os modelos da SDD, executar os 34 casos locais e implementar uma receita de consulta em fixture com BrowserSession/Actor. Instrumentar os clientes de inferência para provar zero chamadas no caminho estável. Esta etapa não depende de credencial Cloudflare.

### Etapa B — Adapter Clef

Implementar `views.py` e `clef.py`, normalizar REST versus resposta local/binding e aplicar os gates do contrato. Testar respostas do provedor com erro, opções inválidas, empate, observação antiga e cancelamento. A primeira chamada real usa somente um estado sintético e verifica formato/latência; acesso ao serviço deve estar configurado no ambiente, fora do repositório.

### Etapa C — Recuperação delimitada

Introduzir mudança de locator em fixture, oferecer candidatos corretos/incorretos e medir decisão seguida de pós-condição. Guardar patch como candidato. Não promover um seletor apenas porque o modelo lhe atribuiu confiança alta.

### Etapa D — LLM generativa e autorreconstrução

Provocar uma mudança que exceda a recuperação de locator: novo percurso, parser ou transformação. Usar Agent/LLM para produzir a proposta dentro do escopo. Validar contrato, efeitos, testes, evidência e regressão antes de promover. Código novo de parser segue o fluxo de desenvolvimento; não executar código arbitrário gerado dentro da sessão de produção.

### Etapa E — Primeiro portal e avaliação de Flash

Certificar CJPG no escopo já definido, respeitando as pendências de inteiro teor/paginação. Comparar Clef e Flash nas mesmas observações e liberar Flash apenas para classes em que a avaliação justifique. Surf permanece otimização posterior por template equivalente.

## 4. Critérios de aceite do pivot

- Chamadas jurídicas externas não precisam conhecer nomes de modelos.
- Nenhum código tenta tratar `systemone` como substituição automática de `BaseChatModel.ainvoke`.
- Valor de query/data fornecido pelo chamador usa binding determinístico.
- Clef escolhe somente entre candidatos observados e ações autorizadas.
- Abstenção, timeout e erro não causam clique de fallback arbitrário.
- O Agent generativo continua acessível quando for necessário construir reparo/código.
- Toda correção passa por verificador protegido e testes antes de uso geral.
- Modelo e variante efetivos aparecem na proveniência e na medição de custo.
- Reuso de receita continua com zero inferência quando o fluxo funciona.

## 5. Entrega desta revisão

Foi clonado o Browser Use, lido seu código e inspecionado o código público de Clef/Clef-flash com revisões fixadas. Foram executados 18 checks de preparação/conversão, e a SDD foi consolidada para o pivot. Não foram baixados pesos, configuradas credenciais de inferência ou implementado o runtime completo.

O escopo desta PR é o estudo de aplicabilidade e a documentação de construção sobre a base real. As PRs de implementação seguem a ordem acima e o backlog consolidado; não confundir a especificação de uma função com sua implementação.

## 6. Pendências específicas

1. Implementar e testar o adapter Workers AI no ambiente escolhido.
2. Confirmar chamada real, envelope e medição de uso com a conta do produto.
3. Avaliar desempenho em português e observações de portais jurídicos.
4. Definir classes liberadas para Clef-flash e thresholds de abstenção.
5. Medir limites de contexto com tokenizer/modelo reais.
6. Certificar o circuito completo incluindo LLM generativa, parser e promoção.
7. Avaliar hospedagem própria somente se necessária ao produto; o loader exige backbone e cabeça conjunta.

As limitações de acesso e certificação dos portais permanecem as registradas na SDD. O pivot de provedor não resolve login, CAPTCHA, disponibilidade, autorização ou identidade documental por si só.
