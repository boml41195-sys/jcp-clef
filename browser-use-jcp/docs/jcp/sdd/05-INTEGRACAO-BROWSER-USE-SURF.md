# Integração com Browser Use e Surf

## 1. Estratégia de fork

Basear a primeira branch de implementação no commit Browser Use `7be96ed8bafa8dfe1eef228b59cf5c884b8b2431`. Adicionar `jcp/`, testes e configuração de empacotamento. Não editar os checkouts de pesquisa para confundi-los com implementação. Atualizações do upstream passam pela matriz de compatibilidade do adaptador.

O pacote `jcp` pode expor API própria, mantendo importações do Browser Use concentradas em `jcp/runtime/browser_use/`. Não depender diretamente de métodos privados do Agent em cada claw. Se um método privado for indispensável, envolvê-lo em um adaptador, registrar commit e adicionar teste de contrato sobre assinatura/comportamento.

## 2. Pontos concretos de integração

| Arquivo do Browser Use | Componente observado | Aplicação no JCP |
|---|---|---|
| `browser_use/browser/session.py` | BrowserSession, estado e páginas | Posse de sessão, observação e anexação. |
| `browser_use/actor/page.py` | Navegação e busca de elementos | Execução determinística. |
| `browser_use/actor/element.py` | Interações com elemento | Click, fill, atributos e seleção. |
| `browser_use/tools/service.py` | Tools e act | Ferramentas do agente de descoberta. |
| `browser_use/tools/registry/service.py` | Registry, action, execute_action | Registro tipado e ponte de ações. |
| `browser_use/agent/service.py` | Agent, histórico e replay | Descoberta e material para converter em receita. |
| `browser_use/dom/views.py` | Elementos e níveis de correspondência | Referência para localizar elementos novamente. |
| `browser_use/browser/events.py` | Eventos de navegador | Integração com estado e observabilidade. |
| `browser_use/browser/watchdogs/` | DOM, downloads, storage, segurança | Reaproveitamento do runtime, com testes por função. |
| `browser_use/mcp/` | Integração MCP existente | Referência; gateway semântico JCP separado. |

Os links fixados estão no documento 09. As interfaces acima existem no código inspecionado; a camada JCP descrita a seguir ainda será implementada.

## 3. BrowserUseAdapter

Interface proposta:

```python
class BrowserUseAdapter:
    async def acquire(self, session_ref, context): ...
    async def observe(self, scope): ...
    async def locate(self, locator_spec, observation): ...
    async def perform(self, allowed_action, target_ref, binding): ...
    async def capture(self, evidence_spec): ...
    async def release(self, lease): ...
```

`perform` recebe uma ação já autorizada pelo broker. `target_ref` contém identidade da página, frame, observação e referência efêmera ao elemento. A função revalida antes da interação. A liberação respeita a posse do navegador e a política da sessão.

No Actor, `page.get_elements_by_css_selector` retorna elementos, não uma promessa de unicidade ou espera por visibilidade. O adaptador deve exigir cardinalidade, estado interagível e contexto. O JCP implementa suas esperas explícitas sobre condições observadas; não atribuir ao Actor automaticamente APIs do Playwright.

O executor determinístico não instancia Agent para cada tarefa. Ele usa a sessão e as primitivas. Operações que chamam LLM, como extração por prompt, são explicitamente classificadas como inferência e ficam fora da receita de zero inferência.

## 4. Ferramentas de descoberta

O Agent pode receber `Tools` customizado. Excluir ferramentas desnecessárias de arquivo, JavaScript genérico e navegação fora do escopo. Registrar wrappers que chamam o broker JCP. O parâmetro de injeção deve corresponder à interface do Registry, incluindo `browser_session` quando utilizado.

Restrição por domínio no registro de ferramenta ajuda, mas não é fronteira suficiente para todo acesso: navegação, redirects, downloads e transporte HTTP também devem aplicar política. Chamadas diretas a CDP/Actor devem permanecer internas ao adaptador.

Configurar limites do Agent coerentes com o orçamento JCP. O resultado `ActionResult.error` precisa ser convertido em falha tipada; retorno de uma função Python não prova que a operação foi bem-sucedida.

## 5. Captura e conversão de trajetória

Extrair do histórico ações, parâmetros, elementos interagidos e resultados. Acrescentar observações JCP com contexto do recurso e verificadores. Converter o percurso em DSL, em vez de simplesmente armazenar os índices usados pelo modelo.

A conversão identifica três tipos de valor: entrada do usuário, informação obtida da fonte e segredo/estado efêmero. Os dois últimos não são substituídos por literais genéricos sem regra de aquisição. Após remover passos de exploração, testar novamente a receita consolidada.

O replay do Browser Use continua útil para investigação e comparação. Não é a API de produção escolhida para prometer zero inferência e verificação jurídica completa.

## 6. Surf como transporte especializado

### 6.1 O que aproveitar

Do código Surf: cliente persistente e pools; cookie jar; contextos de cancelamento; configuração de timeout; middleware; resposta com metadados; leitura limitada/streaming; políticas de redirect; perfis de transporte e interoperabilidade com `net/http`.

O valor para JCP é executar de maneira econômica uma requisição que já foi compreendida e certificada. O mesmo verificador da função deve avaliar o resultado obtido por navegador e por HTTP.

### 6.2 Fronteira Python e Go

Primeira integração proposta: processo worker Go iniciado por um supervisor e comunicação JSON Lines sobre stdin/stdout, com tamanho máximo por mensagem e IDs de correlação. Stderr transporta logs sanitizados. Sem servidor HTTP público obrigatório e sem FFI no primeiro ciclo.

Protocolo do worker: `hello`, `open_session`, `execute_template`, `cancel`, `close_session`. A primeira versão pode processar uma requisição por worker; o pool fornece concorrência. Um processo supervisor detecta queda e marca requests pendentes segundo seu estado de envio.

Não passar arquivos grandes em base64 no canal de controle. O worker grava artefatos na raiz atribuída pelo supervisor e retorna referência, tamanho, MIME e hash. O supervisor valida que o caminho resolvido permanece nessa raiz.

### 6.3 Template HTTP

```json
{
  "type": "execute_template",
  "request_id": "http_example_001",
  "session_ref": "transport_session_opaque",
  "template_id": "tjsp.cjpg.search.v1",
  "arguments": {"query": "dano moral", "date_from": "2026-09-01"},
  "deadline_ms": 30000,
  "max_response_bytes": 10000000,
  "trace_id": "trace_example"
}
```

O template está registrado e validado no worker; ele contém origem, path, método, codificação, parâmetros permitidos, obtenção de tokens e expectativa de resposta. O consumidor não envia URL, headers de autorização ou código Go arbitrários. Credenciais são injetadas por referência de sessão, fora dos argumentos de negócio.

### 6.4 Sessão e cookies

O SessionBroker é autoridade sobre o ciclo de vida. A ponte exporta apenas cookies elegíveis para a origem, preservando domínio, path, expiração e flags suportadas. Cookies particionados ou semânticas não representáveis no cookie jar exigem execução no navegador ou adaptador específico validado.

LocalStorage, IndexedDB, CSRF, nonce, state de OIDC e certificado não são cookies intercambiáveis. A simples cópia de cookies não prova equivalência de sessão. Mudança de IP, agente ou contexto também pode invalidar o acesso.

Uma sessão em fase HTTP recebe lease exclusivo quando a fonte altera seu estado. Atualizações de cookies retornam sob controle de versão; não sincronizar cegamente dois jars concorrentes. Renovação ocorre no mecanismo original autorizado. Nunca guardar token dinâmico dentro da receita compartilhada.

### 6.5 Defaults que precisam ser alterados

No commit inspecionado, o default TLS desativa verificação de certificado. Construir cliente com `SecureTLS()` e testar o transporte final, inclusive depois da configuração de perfil. Falha de certificado termina como erro de transporte; o JCP não deve tentar recuperar reduzindo essa validação.

Desabilitar retries genéricos do Surf no início. O orquestrador decide repetição segundo efeito e estágio. Se habilitados para leitura certificada, os retries precisam compartilhar o mesmo orçamento/deadline e produzir métricas. O código observado respeita `Retry-After` para status configurados, mas não conhece idempotência jurídica.

Configurar redirects explicitamente. Em SSO, origens adicionais são registradas como origens de autenticação e não como permissão para enviar qualquer conteúdo jurídico. Authorization e cookies não devem ser encaminhados indiscriminadamente a outra origem.

### 6.6 Robustez de rede e resposta

Aplicar deadline total, limite de conexão, headers e corpo. Limitar bytes descomprimidos, rejeitar resposta truncada como completa e testar compressão excessiva. Conferir tipo real de conteúdo antes de parsear. Um 200 pode conter login, aviso ou desafio.

Verificar DNS e destino de cada conexão/redirect conforme a política de origens e redes da implantação. Templates de fontes públicas não podem ser usados como proxy para recursos internos. Instalações jurídicas internas têm allowlist específica e workers na rede autorizada.

Pools devem respeitar tenant, sessão, proxy e perfil de transporte. Não compartilhar cookie jar global. Limites conservadores por origem vêm do orquestrador; os defaults de conexão do Surf não são limites adequados automaticamente para tribunais.

### 6.7 Perfis, HTTP2 e HTTP3

Manter perfil consistente com a sessão e testar benefícios reais. Perfis TLS/HTTP não substituem navegador nem garantem ausência de desafios. HTTP/3 só entra se compatível com proxy, rede e fonte e se melhorar o benchmark. Começar com caminho estável e observável é suficiente.

### 6.8 Dependência e build

O repositório solicitado declara módulo `github.com/enetx/surf` e Go 1.27. A equipe deve fixar o fork/commit em `go.mod` por estratégia de replace ou publicação controlada e confirmar a toolchain disponível. Não foi compilado durante esta pesquisa; essa é uma pendência explícita.

## 7. Certificar uma otimização HTTP

1. Executar a capacidade pelo navegador e registrar entradas, filtros, estado e identidade dos resultados.
2. Identificar formulário/endpoint observado ou documentado e sua semântica. HAR/telemetria de rede pode auxiliar, com segredos protegidos.
3. Criar template HTTP parametrizado, com tokens efêmeros obtidos em runtime.
4. Executar as duas implementações em casos diferentes, incluindo vazio e paginação.
5. Comparar identidade, campos, filtros, cobertura e acesso. Contagens podem variar com atualização da fonte; tratar essa diferença explicitamente.
6. Certificar o transporte por instalação/versão e acompanhar divergências.

Não copiar todo HAR como receita e não supor que um endpoint observado é uma API pública estável. Se a equivalência falhar, manter Browser Use para aquela operação.

## 8. Papel do Scrapling

Usar seu parser sobre conteúdo já obtido pelo runtime, evitando introduzir um segundo navegador independente no fluxo principal. Ativar o mecanismo adaptativo conforme a API do parser e manter armazenamento separado por receita/instalação. Os candidatos extraídos devem passar pelo verificador JCP.

Os fetchers do Scrapling podem ser avaliados no futuro como outro transporte. Na primeira integração, Browser Use mantém posse do navegador e Surf possui apenas as requisições certificadas. Isso reduz divergência de cookies, estados e diagnósticos.
