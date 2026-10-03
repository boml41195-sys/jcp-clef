# JCP — Especificação de desenvolvimento

Revisão documental 0.2 • 3 de outubro de 2026 • LopsOS

Este pacote especifica o Judicial Communication Protocol, uma camada de capacidades jurídicas construída sobre um fork do Browser Use. O objetivo é permitir que um agente obtenha informações e opere ferramentas jurídicas na hora em que precisa delas, por meio de funções estáveis, receitas determinísticas e recuperação controlada quando as interfaces mudam.

O desenvolvedor deve conseguir transformar os documentos em implementação sem reconstruir a discussão original. As decisões propostas estão separadas dos comportamentos encontrados nos repositórios e das observações feitas nos portais. O pacote é uma especificação: não declara que o runtime JCP ou as cinco integrações já estejam implementados ou certificados. A revisão 0.2 acrescenta modelos de contrato executados localmente, schemas, exemplos, semântica de execução e um backlog rastreável. A versão proposta do protocolo permanece 0.1.

## Ordem de leitura

1. [Visão e decisões de arquitetura](01-VISAO-E-ARQUITETURA.md): problema, limites, diferencial e estrutura do sistema.
2. [Módulos e componentes](02-MODULOS-E-COMPONENTES.md): responsabilidades até o terceiro nível, interfaces e invariantes.
3. [Contratos do protocolo](03-CONTRATOS-DO-PROTOCOLO.md): chamadas, respostas, objetos jurídicos, receitas e eventos.
4. [Execução e autorreparo](04-EXECUCAO-E-AUTORREPARO.md): máquina de estados, Pescache, Jev e promoção de receitas.
5. [Integração com Browser Use e Surf](05-INTEGRACAO-BROWSER-USE-SURF.md): pontos concretos do código, fronteira Python/Go e transporte HTTP.
6. [Cinco superfícies jurídicas](06-MAPEAMENTO-DOS-PORTAIS.md): observações reais, funções propostas, automações existentes e limites da pesquisa.
7. [Governança e evidências](07-GOVERNANCA-E-EVIDENCIAS.md): isolamento, permissões, qualidade de informação e retenção.
8. [Plano de implementação e testes](08-IMPLEMENTACAO-E-ACEITACAO.md): fatias de entrega, testes e condições de lançamento.
9. [Fontes e conclusões do código](09-FONTES-E-CONCLUSOES.md): versões inspecionadas, arquivos e decisões derivadas.
10. [Contratos validáveis](10-CONTRATOS-VALIDAVEIS.md): código Python completo do perfil CJPG e dois JSON Schemas gerados.
11. [DSL e semântica do executor](11-DSL-E-SEMANTICA-DO-EXECUTOR.md): bindings, locators, passos, execução e integração de decisões.
12. [Exemplos e testes de contrato](12-EXEMPLOS-E-TESTES-DE-CONTRATO.md): seis cenários sintéticos e suíte reproduzível de 34 casos.
13. [API, estados e concorrência](13-API-ESTADOS-E-CONCORRENCIA.md): admissão, idempotência, retomada, cancelamento, locks e contexto.
14. [Backlog e rastreabilidade](14-BACKLOG-E-RASTREABILIDADE.md): 11 PRs sugeridas e requisitos ligados a provas de aceite.
15. [Pendências e continuidade](PENDENCIAS.md): o que falta validar e como continuar sem repetir a pesquisa.

## Como começar a implementar

Ler 01 e 05 para entender a base técnica. Usar 10 e 12 para extrair e testar os contratos. Seguir PR-01 a PR-04 do documento 14 para construir o primeiro circuito Browser Use → receita → parser → verificador. A DSL do documento 11 define o comportamento do interpretador; os testes de contrato não implementam esse runtime.

## Validação desta revisão

Os modelos embutidos foram executados com 34 casos locais, cobrindo respostas válidas e rejeições esperadas. Dois schemas foram gerados desses modelos. Links internos, blocos JSON e conteúdo do ZIP foram conferidos no empacotamento. As invariantes relacionais dos modelos não são todas expressas em JSON Schema; essa diferença está documentada em 10. Nenhum teste de contrato é apresentado como consulta real a tribunal.

## A ideia em uma página

Uma aplicação chama `tjsp.cjpg.search_decisions` com termos e filtros. O JCP valida a chamada e seleciona uma receita já certificada para aquela instalação. A receita executa no navegador do Browser Use ou, quando houver equivalência comprovada, por HTTP. A extração produz objetos jurídicos com origem e horário de coleta. O verificador confirma identidade, filtros e escopo percorrido. O resultado retorna ao agente como contexto atual.

Quando uma receita deixa de funcionar, o sistema primeiro distingue demora, sessão expirada, bloqueio e mudança de interface. Regras determinísticas resolvem casos conhecidos. Jev ajuda em escolhas pequenas entre alternativas observadas. O agente Browser Use descobre um novo percurso quando necessário. Uma correção vira candidata e somente é reutilizada após passar pelos verificadores e testes da capacidade.

O aprendizado persistente é o conhecimento de como operar a fonte. O conteúdo jurídico é recuperado sob demanda; a evidência necessária à tarefa tem retenção explícita. Isso reduz a necessidade de construir uma cópia nacional antecipada dos documentos, mas não elimina armazenamento operacional nem garante a disponibilidade das fontes.

## Convenções

- **DEVE** indica requisito necessário à conformidade com esta especificação.
- **DEVERIA** indica preferência que admite exceção documentada.
- **PODE** indica extensão opcional.
- **Observado** significa visto no código ou no navegador durante esta pesquisa.
- **Proposto** significa decisão de projeto JCP ainda a implementar.
- **Pendente** significa que falta validação identificada.

As versões de protocolo e de capacidade são independentes. O nome Pescache é usado aqui para o registro de receitas; pode ser alterado sem mudar a arquitetura. Os exemplos de contratos são propostas normativas, não APIs já existentes do Browser Use.
