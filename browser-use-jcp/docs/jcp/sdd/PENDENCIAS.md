# Pendências e continuidade

## Estado desta entrega

A especificação documental foi entregue com arquitetura, módulos e submódulos, contratos, ciclo de execução e reparo, integração com código existente, cinco superfícies jurídicas, governança e plano de implementação. A revisão 0.2 acrescenta modelos de contrato CJPG executados em 34 casos locais, dois JSON Schemas, exemplos sintéticos, semântica de DSL, API detalhada e backlog de 11 PRs. O runtime JCP ainda precisa ser construído. Este arquivo registra as validações abertas para evitar que uma próxima sessão repita a pesquisa ou trate hipóteses como funcionalidades prontas.

## Conclusões que devem ser preservadas

1. O JCP é uma camada semântica de capacidades jurídicas sobre Browser Use, com funções independentes das interfaces dos portais.
2. O caminho estável executa receita parametrizada e verificação sem inferência. O estado transitório do DOM e os índices do agente não são receita persistente suficiente.
3. O histórico/replay do Browser Use não deve ser presumido como garantia de execução sem LLM; o JCP precisa de seu próprio interpretador e de extração determinística.
4. Clef entra em decisões pequenas e tipadas. Não substitui a verificação de identidade jurídica e não produz automaticamente código seguro para produção.
5. O agente Browser Use descobre e repara percursos. A correção é candidata; a promoção exige testes e um verificador que o reparador não controla.
6. O Surf indicado pelo usuário é um cliente HTTP em Go. Sua contribuição é transporte eficiente para templates certificados, especialmente depois de provar equivalência com o percurso do navegador.
7. A configuração TLS inicial encontrada no Surf precisa de endurecimento explícito. Cookies, redirects, CSRF, cancelamento e retry são requisitos da integração, não detalhes dispensáveis.
8. Aprendizado de procedimento, cache de resultado e evidência são armazenamentos diferentes. A proposta não depende de ingerir antecipadamente o acervo jurídico nacional.
9. Login existente é uma premissa válida de produto. Sessão expirada, desafio e autorização de recurso continuam sendo estados que o runtime precisa distinguir.
10. A cobertura cresce por capacidade, instalação e variante certificada. Cinco superfícies pesquisadas não equivalem a cinco conectores prontos.

## Ordem de continuidade

Começar pelo incremento I0 e depois I1–I4 do [plano de implementação](08-IMPLEMENTACAO-E-ACEITACAO.md), usando as PRs 01–04 do [backlog](14-BACKLOG-E-RASTREABILIDADE.md). Extrair os contratos e executar os testes conforme [12](12-EXEMPLOS-E-TESTES-DE-CONTRATO.md). Não iniciar por mais uma pesquisa ampla de frameworks. Reabrir fontes apenas para confirmar comportamento que afete o incremento em desenvolvimento ou resolver uma pendência específica abaixo.

## Validações técnicas abertas

| ID | Pendência | Evidência já disponível | Próximo trabalho concreto | Critério de encerramento |
|---|---|---|---|---|
| P01 | Compatibilidade do ambiente Browser Use | Commit, versão e arquivos inspecionados em 09 | Instalar dependências fixadas e rodar smoke test Actor | Ações e encerramento de sessão testados no ambiente do produto. |
| P02 | Receitas sem inferência implícita | Diferença entre Actor e replay/extração do agente documentada | Implementar adapter/interpreter e instrumentar todos os clientes LLM | Segunda execução parametrizada registra zero chamadas de modelo. |
| P03 | CJPG: inteiro teor e paginação ao vivo | Busca inicial e resultados observados; código Juscraper analisado | Validar avanço, resultado vazio e abertura/download de um documento público | Contrato preenchido com origem, identidade, cobertura e artefato correto. |
| P04 | CPOPG: detalhe processual | Formulário e submissão observados; resultado final não confirmado | Completar consulta pública autorizada e mapear detalhe/movimentos | Fixture redigido e verificador de identidade aprovados. |
| P05 | STJ SCON: acesso real ao percurso | Desafio observado; automação de terceiro analisada | Validar caminho permitido de acesso e estado pós-desafio | Busca e documento confirmados no portal; sem presumir que endpoint antigo funciona. |
| P06 | PJe TRT2: área autenticada | Entrada, PDPJ e versões observadas; sem login realizado | Sessão de teste autorizada, uma função de leitura, expiração e retomada | Resultado e identidade verificados no escopo da conta. |
| P07 | eproc JFRS: área autenticada | Redirecionamento SSO e controles de login observados | Sessão autorizada e percurso específico de consulta/download | Capacidade individual certificada; efeitos intermediários mapeados. |
| P08 | Serviço Clef no ambiente do produto | Código Clef/Clef-flash fixado; 18 checks locais sem inferência | Implementar adapter REST e executar chamada real autorizada | Respostas válidas/abstenção, medição local e gate testados. |
| P09 | Build do Surf | Commit e declaração Go 1.27 inspecionados | Confirmar toolchain e compilar worker mínimo | Build reproduzível com versões registradas. |
| P10 | TLS e redirects do Surf | Defaults e builder analisados | Testar certificado válido/inválido e redirects entre origens | Verificação TLS efetiva e credenciais restritas ao destino permitido. |
| P11 | Sessão compartilhada browser/HTTP | Limitações de cookies e outros armazenamentos registradas | Implementar lease/bridge para um template compatível | Identidade preservada; expiração e CSRF tratados sem vazamento. |
| P12 | Equivalência Surf/browser | Método proposto, ainda sem benchmark integrado | Comparar consultas idênticas com verificação independente | Dados, encoding, filtros e cobertura equivalentes no conjunto testado. |
| P13 | Scrapling como recuperação estrutural | Código de seleção adaptativa inspecionado | Benchmark de fixtures contra alternativa simples de locators | Adotar somente se ganho medido justificar dependência. |
| P14 | Licenças e redistribuição do fork | Repositórios e commits registrados | Conferir licença dos arquivos efetivamente incorporados e dependências | Inventário e avisos no repositório de implementação. |
| P15 | Política de retenção e autorização do produto | Modelo técnico proposto no documento 07 | Definir configuração com responsáveis do produto e ambientes | Valores explícitos, aplicados e testados; sem prazo presumido. |
| P16 | Desempenho real e custo | Benchmark externo qualificado, sem números JCP | Executar modos A/B/C/D do documento 08 | Relatório reproduzível com verificação, amostra e falhas. |
| P17 | Interpretador DSL e fixture completa | Semântica e receita proposta em 11 | Implementar registries, passos, broker e fixture | Executar receita e falhas controladas sem inferência. |
| P18 | API, idempotência e concorrência | Contratos de controle e regras em 13 | Implementar ledger, leases e operações condicionais | Testes de corrida, retomada e cancelamento aprovados. |
| P19 | Schemas em clientes de outras linguagens | Dois schemas gerados e modelos testados em Python | Validar dialeto com ferramenta independente no CI | Compatibilidade estrutural comprovada; regras relacionais mantidas no servidor. |
| P20 | Outros perfis de capacidade | Perfil CJPG executável de referência | Criar modelos de processo/movimento/documento para a próxima claw | Schemas, fixtures e verificadores específicos aprovados. |

P06 e P07 dependem de acesso de teste autorizado. Não é necessário resolver essas duas pendências para construir o primeiro circuito público CJPG. P08 e P09 não bloqueiam uma primeira versão do interpretador Browser Use.

## Evidência de pesquisa e onde encontrá-la

Os commits e links permanentes estão em [09 — Fontes e conclusões](09-FONTES-E-CONCLUSOES.md). As observações por portal estão em [06 — Mapeamento](06-MAPEAMENTO-DOS-PORTAIS.md). As cópias de pesquisa usadas nesta sessão estão no diretório `tmp/research/` do workspace, fora do ZIP. O ZIP contém apenas a documentação solicitada e pode ser usado independentemente dessas cópias.

Não foram executados nesta pesquisa os scrapers de terceiros contra os portais, nem foi compilado o worker Surf integrado, nem foi construído um fork funcional JCP. A leitura de código serve para especificar pontos de integração reais; não substitui o aceite de cada incremento. Os 34 testes executados na revisão 0.2 pertencem somente ao perfil de contratos de referência; não mudam essas limitações de integração.

## Limites da inspeção dos cinco portais

- CJPG: consulta pública e lista inicial observadas; inteiro teor e paginação completa ainda pendentes.
- CPOPG: entrada e submissão observadas; detalhe final não confirmado.
- SCON: acesso interrompido por desafio; estado de resultado não observado.
- PJe TRT2: superfície pública e entrada de autenticação; área privada não acessada.
- eproc JFRS: entrada, SSO e controles públicos; área privada não acessada.

Esses limites fazem parte do mapa entregue e devem permanecer visíveis nas apresentações técnicas. Não converter a palavra “mapeado” em “implementado”, “testado ponta a ponta” ou “certificado”.

## Decisões de produto ainda ajustáveis

O nome expandido oficial do JCP, os nomes finais das claws, os limites padrão, os prazos de retenção e a primeira instalação autenticada podem mudar sem redesenhar o núcleo. A expansão usada neste pacote é Judicial Communication Protocol. Pescache denomina o registro de receitas.

A escolha de banco, object store e provedor de segredos depende do ambiente de implantação. O contrato exige transações, isolamento e retenção, mas não obriga um fornecedor. O fork Browser Use e os contratos semânticos são decisões centrais; adicionar mais infra antes de demonstrar o ciclo de reutilização e reparo não é pré-requisito.

## Como continuar em uma próxima sessão

Ler README, este arquivo e o incremento atual do documento 08. Consultar o documento 05 para os pontos de integração e 09 para a origem de cada conclusão. Escolher uma pendência concreta, produzir implementação/teste e registrar o resultado. Atualizar estado, evidência e versão dos documentos quando uma hipótese for validada ou refutada. Não apagar a distinção entre proposta e comportamento observado.

## Pivot da revisão 0.3

O provedor de decisão passa a ser Clef. A LLM generativa continua para código e reparos. [Estudo atual](../README.md). Os checks de preparação/conversão do Clef não encerram pendências de inferência, runtime ou portal.
