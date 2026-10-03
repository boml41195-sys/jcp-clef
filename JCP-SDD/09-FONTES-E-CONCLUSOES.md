# Fontes inspecionadas e conclusões

Pesquisa feita em 2 e 3 de outubro de 2026. Os commits abaixo foram obtidos dos checkouts locais. Não foram executadas suítes completas nem benchmarks pagos desses projetos. A inspeção de código fundamenta o desenho; não comprova compatibilidade de produção com portais.

## 1. Versões fixadas para a especificação

| Projeto | Commit inspecionado | Uso proposto |
|---|---|---|
| [Browser Use](https://github.com/browser-use/browser-use) | `7be96ed8bafa8dfe1eef228b59cf5c884b8b2431` | Base Python, navegador, ações e agente. |
| [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) | `1231850a0bf1a0c0341fe408ef1668dbbfdfac46` | Modelo de decisão tipada e guardas de execução. |
| [Surf indicado pelo usuário](https://github.com/lucascardoso-create/surf) | `7da0502899af06f8318f95e632797cb2ac0c6c20` | Transporte HTTP Go opcional. |
| [Juscraper](https://github.com/jtrecenti/juscraper) | `735f36213417a1ae7623b159eb3aea0aef08bd4b` | Referência concreta para e-SAJ e parsing jurídico. |
| [Scrapling](https://github.com/D4Vinci/Scrapling) | `971d5edb9c01f000dd4befcd21742e9b22260dc7` | Seleção adaptativa estrutural. |
| [JurisMCP](https://github.com/ivancaron/jurismcp) | `8138b34ad1e68932b075aa2d5d0041b5b8326702` | Referência para consulta e parsing STJ. |
| [courtsbr/esaj](https://github.com/courtsbr/esaj) | `c1f74ce3f171eb1a90be90451115b9f875a16826` | Histórico de automações de consulta e decisões em R. |
| [PedroX-dev/Eproc](https://github.com/PedroX-dev/Eproc) | `40419af5d58553829f4b3dbe95b1cf6336bb39bb` | Referência declarativa; checkout contém somente README. |

Os fontes completos baixados estão em `tmp/research` no workspace original. O ZIP de especificações contém somente Markdown; os links por commit permitem recuperar as bases sem depender dessa pasta.

## 2. Browser Use — achados que mudam a implementação

[Código do agente no commit inspecionado](https://github.com/browser-use/browser-use/blob/7be96ed8bafa8dfe1eef228b59cf5c884b8b2431/browser_use/agent/service.py).

- Há `rerun_history`, `load_and_rerun`, `save_history`, `_execute_history_step` e `_update_action_indices`.
- O replay remapeia elementos por uma cascata que inclui hash exato, hash estável, XPath, nome acessível e atributos.
- `_execute_history_step` usa inferência para ações `extract`; o replay também contempla resumo por modelo. Portanto, reaproveitar histórico não equivale automaticamente a zero inferência.
- O JCP deve aproveitar esses mecanismos como referência e material para converter execução em receita, mantendo seu executor determinístico separado do loop generativo.

[Actor Page](https://github.com/browser-use/browser-use/blob/7be96ed8bafa8dfe1eef228b59cf5c884b8b2431/browser_use/actor/page.py), [Actor Element](https://github.com/browser-use/browser-use/blob/7be96ed8bafa8dfe1eef228b59cf5c884b8b2431/browser_use/actor/element.py) e [BrowserSession](https://github.com/browser-use/browser-use/blob/7be96ed8bafa8dfe1eef228b59cf5c884b8b2431/browser_use/browser/session.py).

Actor fornece navegação, busca CSS e interação direta. `get_elements_by_css_selector` não deve ser tratado como uma espera automática por visibilidade. O JCP precisa implementar suas condições de espera, cardinalidade e leitura após preenchimento. O índice de um snapshot e o backend node ID não são identificadores persistentes entre execuções.

[Tools](https://github.com/browser-use/browser-use/blob/7be96ed8bafa8dfe1eef228b59cf5c884b8b2431/browser_use/tools/service.py) e [Registry](https://github.com/browser-use/browser-use/blob/7be96ed8bafa8dfe1eef228b59cf5c884b8b2431/browser_use/tools/registry/service.py) oferecem ações tipadas, validação de argumentos e integração com sessão. `Tools.act` possui timeout e pode converter exceções em `ActionResult.error`; o adaptador JCP deve examinar o resultado, não apenas capturar exceções.

O repositório contém watchdogs para DOM, armazenamento de estado, downloads, segurança, popups e CAPTCHA. A existência do arquivo de CAPTCHA não prova solução universal local. Capacidade comercial do Cloud e capacidade disponível no OSS devem ser registradas separadamente.

`browser_use/__init__.py` encaminha `Agent` para `browser_use.agent.service`. Existe também `browser_use/beta/service.py`; esta especificação não mistura as duas implementações. O `pyproject.toml` observado declara versão 0.13.10, Python >=3.11, Pydantic, bubus, cdp-use e browser-harness. Fixar o commit continua necessário porque a versão declarada não identifica sozinha todo o checkout.

## 3. Surf — achados concretos

[Builder](https://github.com/lucascardoso-create/surf/blob/7da0502899af06f8318f95e632797cb2ac0c6c20/builder.go), [Request](https://github.com/lucascardoso-create/surf/blob/7da0502899af06f8318f95e632797cb2ac0c6c20/request.go), [middleware do cliente](https://github.com/lucascardoso-create/surf/blob/7da0502899af06f8318f95e632797cb2ac0c6c20/middleware_client.go) e [adapter](https://github.com/lucascardoso-create/surf/blob/7da0502899af06f8318f95e632797cb2ac0c6c20/adapter.go).

Surf é uma biblioteca HTTP em Go. Seu `go.mod` mantém o caminho `github.com/enetx/surf` e declara Go 1.27. Usar o fork exige fixação/replace ou estratégia equivalente de dependência; importar o upstream flutuante não garante usar o código pesquisado.

O código inspecionado inicializa `InsecureSkipVerify=true`. O JCP DEVE habilitar `SecureTLS()` e testar validação após a construção de todos os transportes/perfis. Isso é uma exigência concreta de integração, não uma preferência opcional.

`Request.Do` oferece repetição por status configurado e respeita `Retry-After`, mas a condição examinada não classifica efeitos jurídicos nem restringe repetição a operações semanticamente idempotentes. O JCP deve controlar as tentativas; não habilitar retry genérico para toda função.

`Session()` cria um cookie jar. Isso não importa automaticamente localStorage, IndexedDB, estado de extensão, certificado ou toda a semântica de cookies do Chrome. A ponte de sessão é parte nova do JCP.

`Std()` adapta o cliente à biblioteca padrão; o README explicita diferenças em retry, cache de corpo e métricas. A implementação deve escolher uma única superfície e testá-la. `Body.Limit` existe, mas o limite deve considerar bytes descomprimidos e sinalizar truncamento no adaptador.

Perfis HTTP/TLS e ordem de headers podem melhorar compatibilidade. Eles não executam JavaScript nem comprovam que qualquer desafio ou vínculo de sessão será superado. HTTP/3 é opcional, condicionado a benefício medido.

## 4. Jev — integração e benchmark

[Loop](https://github.com/browser-use/jev-ultrafast/blob/1231850a0bf1a0c0341fe408ef1668dbbfdfac46/jev_ultrafast/agent.py), [modelo](https://github.com/browser-use/jev-ultrafast/blob/1231850a0bf1a0c0341fe408ef1668dbbfdfac46/jev_ultrafast/model.py), [browser](https://github.com/browser-use/jev-ultrafast/blob/1231850a0bf1a0c0341fe408ef1668dbbfdfac46/jev_ultrafast/browser.py) e [benchmark](https://github.com/browser-use/jev-ultrafast/blob/1231850a0bf1a0c0341fe408ef1668dbbfdfac46/docs/performance.md).

O benchmark reporta mediana de 9,450 para 7,092 segundos em três pares de execuções no Google Flights. Ambas as versões usam Jev; a comparação mede otimizações de runtime. Preparação do navegador, navegação inicial e verificação independente posterior ficam fora do cronômetro. Não é um benchmark jurídico nem uma comparação geral Jev versus outros agentes.

O modelo decide operação e alvo entre candidatos. O loop consome a decisão antes de executar e registra a ação antes da observação seguinte. O leitor DOM do exemplo tem cobertura limitada: frames, shadow roots, canvas, uploads, novas abas e outros controles não são abrangidos pelo MVP. Usar as ideias de decisão e guardas, preservando o runtime Browser Use.

## 5. Scrapers jurídicos e seleção adaptativa

[CJPG download](https://github.com/jtrecenti/juscraper/blob/735f36213417a1ae7623b159eb3aea0aef08bd4b/src/juscraper/courts/tjsp/cjpg_download.py) demonstra formulário GET e paginação. [CJPG parse](https://github.com/jtrecenti/juscraper/blob/735f36213417a1ae7623b159eb3aea0aef08bd4b/src/juscraper/courts/tjsp/cjpg_parse.py) distingue zero resultados de resposta ambígua sem paginação. [CPOPG download](https://github.com/jtrecenti/juscraper/blob/735f36213417a1ae7623b159eb3aea0aef08bd4b/src/juscraper/courts/tjsp/cpopg_download.py) trata parâmetros CNJ e códigos internos. Adaptar por transporte e parser; não importar a política de coleta em lote como comportamento padrão do JCP.

[JurisMCP STJ](https://github.com/ivancaron/jurismcp/blob/8138b34ad1e68932b075aa2d5d0041b5b8326702/src/jurismcp/domain/stj.py) contém formulário, normalização Unicode, codificação ISO-8859-1 e parsers para templates distintos. O comentário de que um endpoint não tem bloqueio não é garantia atual; a própria implementação contempla 403.

[Scrapling parser](https://github.com/D4Vinci/Scrapling/blob/971d5edb9c01f000dd4befcd21742e9b22260dc7/scrapling/parser.py) implementa seleção adaptativa mediante inicialização apropriada e armazenamento anterior. O percentual de similaridade estrutural não representa confiança jurídica. A adoção deve preservar validação semântica e isolar o armazenamento adaptativo por receita/contexto.

## 6. Documentação complementar

- [TypeSafe](https://docs.typesafe.ai/introduction): perguntas Choice, Score e Noul; usar como interface de decisão, não como prova final.
- [Browser Use scripts](https://docs.browser-use.com/cloud/agent/scripts): precedente comercial para reutilização e reparo; não equivale a um módulo JCP OSS pronto.
- [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools): exposição de funções com esquemas; não substitui aplicação de políticas.
- [OPA](https://www.openpolicyagent.org/docs): política como código, extensão futura do mecanismo de autorização.
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/): traces e métricas; complemento do registro operacional persistente.

As licenças devem ser verificadas nos commits antes de copiar código. Browser Use, Surf e JurisMCP foram identificados com licença MIT; Juscraper declara MIT; Scrapling declara BSD no projeto. O inventário de produção deve registrar arquivos efetivamente incorporados e avisos exigidos. Projeto que publica somente demonstração ou README não fornece implementação reutilizável comprovada.

## 7. Complementos da revisão documental 0.2

Foi conferido novamente no checkout fixado que `BrowserSession.new_page` e `get_current_page` expõem páginas Actor, que `Page.goto` usa navegação CDP e que `get_elements_by_css_selector` devolve lista de elementos. No Jev Ultrafast, a escolha de operação/alvo, validação da cabeça selecionada e consumo da decisão antes da ação fundamentam o documento 11. O helper de geração de texto do demo pode ser dispensado quando o valor já existe como parâmetro no JCP.

Os modelos Python do documento 10 são código novo de referência desta especificação, não arquivos encontrados nesses repositórios. Foram executados com Pydantic 2.13.5 disponível no ambiente local, em 34 cenários sintéticos. O relatório e os testes reproduzíveis estão no documento 12. Não foram executados testes de portal como parte desse complemento.
