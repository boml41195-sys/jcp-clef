# Mapeamento de cinco superfícies jurídicas

Esta amostra foi escolhida para representar busca de sentenças, pesquisa de decisões, consulta processual e áreas autenticadas. Ela não é inventário de todos os tribunais. A observação ocorreu em 2 e 3 de outubro de 2026; interfaces podem mudar. Não foram fornecidas credenciais de teste, portanto fluxos internos autenticados não foram executados.

## 1. Matriz de evidência

| Superfície | Evidência obtida | Resultado da inspeção | Primeira função proposta |
|---|---|---|---|
| TJSP CJPG | Formulário vivo, busca executada e resultados; código Juscraper | Consulta pública comprovada nessa sessão | search_decisions |
| TJSP CPOPG | Formulário vivo e envio de consulta; código Juscraper | Resposta final do processo não confirmada | get_case |
| STJ SCON | Acesso vivo interrompido por verificação automática; parser JurisMCP | Fluxo completo não validado nessa sessão | search_decisions |
| PJe TRT2 | Portal oficial, login e consulta pública vivos | Fronteira de autenticação e campo público observados | get_case e list_documents |
| eproc JFRS na 4ª Região | Entrada e SSO vivos, menu público expandido | Login e rotas públicas observados; área interna não acessada | get_case e get_document |

O caso mais simples efetivamente executado foi a busca pública de sentenças no CJPG. A existência de consulta pública não implica acesso irrestrito a todo documento de um processo.

## 2. TJSP CJPG — sentenças e julgados de primeiro grau

Entrada: [Consulta de Julgados de Primeiro Grau](https://esaj.tjsp.jus.br/cjpg/).

### Observado na interface

Pesquisa livre; operadores E, OU, NÃO e curingas; opção de sinônimos; número processual dividido; classe; assunto; magistrado; intervalo de datas; vara; ordenação; botões Consultar e Limpar. O link Identificar-se estava disponível, mas a busca realizada não exigiu login.

Locators efetivamente observados: `input[name="dadosConsulta.pesquisaLivre"]`, `#numeroDigitoAnoUnificado`, `#foroNumeroUnificado`, `[id="iddadosConsulta.dtInicio"]`, `[id="iddadosConsulta.dtFim"]`, `#pbSubmit`. Classe, assunto e vara têm seletores compostos; preencher o texto visível pode não selecionar o identificador interno.

Foi enviada pesquisa por `dano moral`, de 01/09/2026 a 02/09/2026. O portal exibiu resultados 1 a 10 de 1021, com paginação, classe, assunto, magistrado, comarca, foro, vara e data de disponibilização. A contagem é uma observação daquela consulta, não métrica permanente. O inteiro teor não foi aberto nem certificado nessa investigação.

### Fluxo a implementar

`FORM_READY → FILTERS_APPLIED → SEARCH_SUBMITTED → RESULTS_READY → PAGE_EXTRACTED → NEXT_PAGE ou DONE`. Estados alternativos: zero resultados, erro de consulta, acesso pendente e layout desconhecido.

Funções: `search_decisions(query, filters, limit)`, `get_decision(decision_ref)` e `get_full_text(decision_ref)`. A primeira é prioridade. Não certificar as outras por dedução a partir da primeira.

O parser deve distinguir resumo de inteiro teor, capturar identidade e separar disponibilização de julgamento/publicação. A paginação deve registrar intervalo exibido e impedir repetir página sem progresso. `limit=10` não precisa coletar os 1021 itens.

### Automação existente e reaproveitamento

Juscraper tem `fetch_cjpg_first_page`, `cjpg_download`, `cjpg_n_results` e `cjpg_parse_single`. O download usa `cjpg/pesquisar.do` e `cjpg/trocarDePagina.do`; o parser trata uma página cheia sem marcador de paginação como ambígua. Esse tratamento é particularmente útil para evitar falsa completude.

O pacote `courtsbr/esaj` também contém módulos `R/cjpg.R` e `R/parse_cjpg.R`. São referências de implementação, sem validação de funcionamento atual durante esta pesquisa.

JCP deve aproveitar o conhecimento de campos e parser, com transporte injetável e sem adotar coleta de todo resultado por padrão. O caminho Surf é candidato forte para comparação, depois que o navegador estiver validado.

### Aceitação específica

Busca com acento; data em formato brasileiro; filtro de classe selecionado de verdade; zero resultados explícito; primeira e última página; interrupção por limite; resumo sem inteiro teor; paginação repetida; renomeação de campo e preservação de filtros após reparo.

## 3. TJSP CPOPG — consulta de processo

Entrada: [Consulta de Processos de Primeiro Grau](https://esaj.tjsp.jus.br/cpopg/open.do).

### Observado na interface

Combobox `#cbPesquisa` com número do processo, parte, documento da parte, advogado, OAB e outros critérios. No modo CNJ, campos `#numeroDigitoAnoUnificado` e `#foroNumeroUnificado`; o segmento 8.26 aparece separado e desabilitado. Botão `#botaoConsultarProcessos`. Há seletor de foro e opção de número antigo.

Foi submetido o número público do primeiro resultado visto no CJPG, mas não foi confirmada a tela final de detalhes antes da interrupção da sessão de pesquisa. Por isso, a evidência deste estudo cobre formulário e envio, não extração de movimentos ou documentos.

### Fluxo a implementar

`SEARCH_FORM → QUERY_SUBMITTED → SINGLE_CASE ou CASE_LIST → CASE_DETAILS → MOVEMENTS → DOCUMENTS`. Lista de incidentes ou múltiplos registros exige escolha por identidade e instância, não pela primeira linha.

Funções: `get_case(case_number)`, `list_movements(case_ref, cursor)` e `list_documents(case_ref)`. Esta última depende do perfil de acesso e do documento específico.

Uma falha em achar movimentos não prova processo inexistente. Consulta bloqueada, redirecionamento, migração de sistema e parser quebrado precisam de estados distintos. O JCP deve preservar a relação entre número CNJ e código interno da instalação.

### Automação existente

Juscraper contém `cpopg_download_html_single`, que monta parâmetros de `cpopg/search.do`, extrai links e trata `processo.codigo`. Há parser separado `cpopg_parse.py`. O downloader existente também verifica arquivos locais já baixados; essa política não deve satisfazer silenciosamente `freshness=live` no JCP.

O pacote R `courtsbr/esaj` contém download e parsing de CPOPG. Ambos demonstram que há automação real aproveitável como referência. Isso não elimina a necessidade de ensaio com sessão e versão atuais.

### Aceitação específica

CNJ com zeros à esquerda; número antigo; caso sem resultado explícito; múltiplos registros; incidente relacionado; sessão expirada; segredo/restrição; movimentos com mesma data; trecho recolhido/expandido e erro de identidade após seleção.

## 4. STJ SCON — decisões e jurisprudência

Entrada: [SCON](https://scon.stj.jus.br/SCON/).

### Observado e limite

O navegador apresentou página de verificação automática de acesso. Não foi concluído desafio nem executada pesquisa ao vivo. Não há base para afirmar que essa sessão conseguiria chegar aos resultados sem etapa adicional.

O código inspecionado do JurisMCP oferece uma implementação concreta em `src/jurismcp/domain/stj.py`, com endpoint `processo.stj.jus.br/SCON/pesquisar.jsp`, envio de formulário e parsing de templates. Esse é um candidato técnico a validar, não uma garantia de acesso atual nem autorização para alterar a fronteira de acesso.

### Fluxo proposto

`ACCESS_READY → QUERY_ENCODED → SEARCH_RESPONSE → TEMPLATE_RECOGNIZED → DECISIONS_EXTRACTED → FULL_TEXT_SELECTED`. Bloqueio, erro de busca e template desconhecido são respostas distintas de vazio.

Funções: `search_decisions(query, filters, limit)`, `get_decision(decision_ref)` e `get_full_text(decision_ref)`. Distinguir número de registro, classe/número do recurso e CNJ quando disponível.

### Automação existente e lições

JurisMCP faz normalização Unicode e codificação de formulário em ISO-8859-1, além de reconhecer templates moderno e legado. O JCP deve manter uma política explícita para caracteres não representáveis: rejeitar/solicitar reformulação ou registrar transformação; não modificar silenciosamente a consulta.

O parser associa campos de processo, relatoria e datas e procura referências de inteiro teor. Ementa e documento completo devem permanecer separados. O comentário do código sobre ausência de bloqueio em um host é uma hipótese histórica da implementação; o status real precisa ser observado.

### Aceitação específica

Acentos compostos/decompostos; expressões booleanas; erro HTTP com corpo; HTTP 200 de desafio; template desconhecido; ementa truncada; ausência de documento; diferença entre data de julgamento e publicação; correlação do inteiro teor com o recurso selecionado.

## 5. PJe TRT2 — acesso público e autenticado

Entradas oficiais: [portal de serviços](https://ww2.trt2.jus.br/servicos/acesso-online/processo-judicial-eletronico-pje/), [login de primeiro grau](https://pje.trt2.jus.br/primeirograu/login.seam) e [consulta pública](https://pje.trt2.jus.br/consultaprocessual/).

### Observado

Login exibiu botão Entrar com PDPJ (`#btnSsoPdpj`) e versão 2.19.10. Consulta pública exibiu campo Número do processo (`#nrProcessoInput`), botão Pesquisar (`#btnPesquisar`) e versão 2.19.7. As versões foram vistas em superfícies diferentes e não devem ser confundidas.

O portal oficial apresenta entradas separadas de primeiro e segundo graus, validação de documentos, consulta pública e acesso restrito. Também referencia PJeOffice e certificado na orientação de acesso. A área interna não foi acessada; suas telas, seletores e permissões continuam pendentes de ensaio com conta autorizada.

### Funções e fronteiras

Primeira etapa: `get_case_public`. Etapa autenticada: `get_case`, `list_documents`, `get_document` e `list_movements` conforme permissões da conta. O manifesto distingue instalação/grau e superfície; não assumir que a tela pública e o PJe interno têm mesmo DOM ou endpoints.

`SESSION_READY → RESOURCE_SELECTED → RESOURCE_IDENTITY_VERIFIED → CONTENT_READ`. Se abrir comunicação produzir ciência, essa operação deve ter capacidade própria e efeito `legal_acknowledgment`, fora da leitura certificada inicial.

### Automação existente

O portal oficial do TRT2 publica link ao maisPJe, extensão de Firefox, como ferramenta adicional. Isso comprova existência de automação integrada ao ambiente, mas não demonstra que seu código é incorporável ou compatível com Browser Use/Chromium. O pacote não foi instalado nem auditado.

Não foi certificado nesta pesquisa um scraper open source do painel autenticado específico do TRT2. Exemplos de outros PJe e MNI não devem ser apresentados como equivalentes. Um endpoint MNI eventualmente disponível é transporte separado, condicionado à instalação e autorização; não é pré-requisito do JCP.

### Aceitação específica

Sessão válida/expirada; redirecionamento SSO; seleção correta de grau e papel; acesso público versus restrito; documento não permitido; nova aba; download; requisição que retorna tela de login; ação com ciência; dependência de certificado fora do DOM.

## 6. eproc JFRS — instalação da Justiça Federal da 4ª Região

Entrada: [eproc JFRS](https://eproc.jfrs.jus.br/eprocV2/), indicada pelo [portal TRF4](https://www.trf4.jus.br/trf4/controlador.php?acao=pagina_visualizar&id_pagina=3939).

### Observado

A entrada levou a autenticação em `eproc-sso.trf4.jus.br`, com fluxo OpenID Connect referenciando o broker `sso.cloud.pje.jus.br`. Foram vistos campos Usuário/Senha, botão Entrar (`#kc-login`), Certificado Digital (`#kc-login-certificate`), opção de autenticação em dois fatores e versão 9.23.2-3.0.8.

O menu Consulta Pública foi expandido e mostrou consulta de documento pela chave, processo por chave e processo sem chave. A entrada de documento por chave aponta a `externo_controlador.php?acao=processo_consulta_publica_chave/consultar`. As consultas processuais também apontam ao portal TRF4. URLs transitórias com state/nonce não foram incorporadas como receita.

Esse achado exige uma lista de origens por papel: origem do recurso, origem de autenticação e broker. Liberar somente o domínio da página inicial quebraria o fluxo; liberar qualquer origem seria amplo demais.

### Funções propostas

`get_case_public`, `get_case`, `list_movements`, `get_document` e `get_document_by_access_key`. Chave é segredo de acesso e usa referência protegida, sem aparecer em logs, prompts gerais ou receita compartilhada.

A autenticação pública observada não prova acesso aos documentos internos. A escolha entre acesso público, chave e perfil autenticado deve ser explícita. O runtime confirma sessão e recurso antes de extrair.

### Automação existente e limitação

O repositório PedroX-dev/Eproc declara automação Python/Playwright, porém o checkout público inspecionado contém somente README. Não há implementação executável para reutilizar a partir dessa referência. A especificação não o trata como dependência.

O caminho real é mapear a instalação com conta autorizada e produzir a primeira receita Browser Use, usando as rotas e estados já observados. HTTP/Surf depende de ensaio de equivalência e compatibilidade de sessão. Não presumir que copiar cookies atravessa toda a federação de login.

### Aceitação específica

Origem SSO permitida; state/nonce nunca persistidos como constantes; usuário/papel correto; chave inválida/expirada; documento fora do escopo; sessão renovada; download parcial; timeout após ato; indisponibilidade de componente de certificado.

## 7. Conclusão para o desenvolvedor

Os cinco casos exigem uma função estável acima de adaptadores específicos. O CJPG oferece a melhor primeira fatia observada; CPOPG testa identidade e estrutura de processo; STJ testa codificação, tipos de documento e acesso; PJe e eproc testam sessão, papéis, SSO e efeitos de ações.

Não há fundamento para exigir uma IA decidindo cada clique. Há fundamento para receitas por capacidade e instalação, com recuperação delimitada e verificadores jurídicos. A universalidade vem da extensão do catálogo e da capacidade de aprender percursos, enquanto a confiança vem da certificação por escopo.
