# Fontes, revisões e evidências

Pesquisa e consolidação: 3 de outubro de 2026. O código do Browser Use foi clonado do upstream; os arquivos de modelo foram lidos nas revisões abaixo. Não foi executada inferência real nesta entrega.

## 1. Revisões fixadas

| Base | Revisão | Material inspecionado |
|---|---|---|
| [Browser Use](https://github.com/browser-use/browser-use/tree/7be96ed8bafa8dfe1eef228b59cf5c884b8b2431) | `7be96ed8bafa8dfe1eef228b59cf5c884b8b2431` | Agent, protocolo LLM, sessão, Actor, Tools e Registry; versão 0.13.10. |
| [Cloudflare Clef](https://huggingface.co/Cloudflare/clef/tree/2f3de3dd85f379784083b0814d997ab627200f0c) | `2f3de3dd85f379784083b0814d997ab627200f0c` | Model card, `joint_schema_model.py`, configs e licença. |
| [Cloudflare Clef-flash](https://huggingface.co/Cloudflare/clef-flash/tree/17f0b0ad64efb65d273590632833508766b2aae6) | `17f0b0ad64efb65d273590632833508766b2aae6` | Mesmo conjunto de arquivos, sem baixar pesos. |

SHA-256 de `joint_schema_model.py`, idêntico nas duas revisões: `0e304cf7c6500e8bb59bef7e2afd2c6373f82596dfb3b57d1aa93c175e2dc3a3`.

As licenças das publicações Clef consultadas são Apache 2.0. A licença do Browser Use permanece no repositório. Esta documentação não redistribui os pesos nem incorpora o código de modelo como dependência instalada do runtime.

## 2. Fontes oficiais adicionais

- [Anúncio Clef](https://blog.cloudflare.com/clef-decision-models/): lançamento e avaliação divulgada pela Cloudflare.
- [Ficha Workers AI Clef](https://developers.cloudflare.com/workers-ai/models/clef/): identificação e superfície hospedada.
- [Ficha Clef-flash](https://developers.cloudflare.com/ai/models/%40cf/cloudflare/clef-flash/): variante hospedada.
- [REST API Workers AI](https://developers.cloudflare.com/workers-ai/get-started/rest-api/): autenticação e envelope de resposta.
- [Changelog AI](https://developers.cloudflare.com/changelog/product-group/ai/): compatibilidade declarada com System One e tipos de pergunta.

A imagem anexada pelo usuário foi usada para a comparação de quatro métricas no estudo. Os números coincidem com a tabela do anúncio. O benchmark é evidência publicada pelo fornecedor; não foi reproduzido neste ambiente.

## 3. Verificações executadas

Dezoito checks locais exercitaram funções do arquivo de modelo: enumeração de opções, transformação de respostas e ramos de montagem/truncamento de entrada. Foram carregados somente os nós AST necessários; o módulo completo, Torch e os pesos não foram importados. O tokenizer sintético não estima custo real de tokens.

O conjunto confirma: IDs de opções e perguntas preservados, semântica de `choice`/`noul`/`score`, arredondamento, comportamento de empate, preservação do schema e truncamento de estado. Detalhes em [Contrato e avaliação](CONTRATO-E-AVALIACAO-CLEF.md).

Os 34 testes da SDD consolidada pertencem aos contratos jurídicos de referência, não ao modelo. A verificação documental confere links locais, JSON, sintaxe dos blocos Python, consistência dos schemas e integridade do pacote. Não é execução do runtime Browser Use.

## 4. Conclusões preservadas para continuidade

1. Clef entra no módulo M5 por interface de decisão; não substitui por configuração a interface chat do Agent.
2. A LLM generativa continua no MVP para gerar código e construir reparos.
3. O executor de receita continua determinístico e independente do provedor de decisão.
4. IDs de candidatos são efêmeros e vinculados à observação; receitas não armazenam posições DOM como identidade durável.
5. A distribuição de probabilidades não autoriza ação nem certifica resultado jurídico.
6. O caminho local exige a cabeça de decisão; não basta carregar apenas o backbone com pipeline genérico.
7. Limites e formatos de mídia diferem entre código local e superfície hospedada; não transferir pressupostos sem teste.
8. A primeira decisão de implantação favorece REST hospedado para validar o MVP; self-host permanece alternativa a avaliar.
9. A qualidade e a latência precisam ser medidas nas tarefas jurídicas antes de promover variantes.
10. As pendências de cada portal permanecem válidas; o pivot de modelo não as encerra.

## 5. Reprodução dos checks

No workspace original, `tmp/jcp_clef_research/manifest.json` registra URLs, revisões e hashes dos arquivos consultados. `probe_semantics.py` e `semantics_report.json` registram o ensaio local. Esses arquivos são de pesquisa e não fazem parte do runtime clonado. Os links fixados acima permitem recuperar os arquivos sem depender do workspace.

Para repetir o ensaio em outro ambiente, selecionar as funções puras identificadas no mapa, conferir os hashes, construir casos de choice/noul/score e exercitar o encoder com tokenizer controlado. Antes de afirmar compatibilidade de inferência, executar também uma chamada real e a avaliação da seção 8 do contrato; os checks desta entrega não cobrem esses itens.
