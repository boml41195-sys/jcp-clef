# Mapa do código e pontos de integração

## 1. Base exata

Browser Use: commit `7be96ed8bafa8dfe1eef228b59cf5c884b8b2431`, versão 0.13.10. A clonagem desta entrega retornou a mesma revisão usada no estudo anterior. Os links abaixo apontam ao código fixado, enquanto os caminhos relativos permitem abrir o clone.

## 2. O que reaproveitar do Browser Use

| Arquivo e símbolo observado | Papel no JCP | Limite/alteração necessária |
|---|---|---|
| [llm/base.py](../../browser_use/llm/base.py), `BaseChatModel.ainvoke` | Explica o contrato generativo do Agent. | Clef `systemone` não satisfaz automaticamente esse contrato. |
| [browser/session.py](../../browser_use/browser/session.py), `new_page` (1346), `get_current_page` (1360) | Ciclo de vida e obtenção de páginas. | Broker de sessão, posse e isolamento são responsabilidades JCP. |
| Mesmo arquivo, `get_browser_state_summary` (1597) | Estado do navegador para construir observação. | Selecionar e sanitizar conteúdo; não enviar o DOM inteiro por padrão. |
| [actor/page.py](../../browser_use/actor/page.py), `goto` (324), `get_elements_by_css_selector` (382) | Caminho determinístico de navegação e localização. | Condições de espera, cardinalidade e pós-condição ficam no adapter. |
| [actor/element.py](../../browser_use/actor/element.py), `click` (92), `fill` (352), `select_option` (446) | Execução das ações aprovadas. | Revalidar alvo/estado e classificar efeito antes de agir. |
| [tools/service.py](../../browser_use/tools/service.py), `Tools.__init__` (442), `act` (2178) | Ferramentas do agente generativo e execução de ações registradas. | Conferir `ActionResult.error` e limitar a superfície final de ferramentas. |
| [tools/registry/service.py](../../browser_use/tools/registry/service.py), `action` (291), `execute_action` (331), `create_action_model` (519) | Registro tipado de wrappers que passam pelo ActionBroker. | Anotação de domínio não substitui política em redirects/downloads. |
| [agent/service.py](../../browser_use/agent/service.py), Agent | Descoberta e geração de reparos com LLM generativa. | Usar contratos, orçamento e verificador do JCP. |
| Mesmo arquivo, `rerun_history` (3103), `_execute_history_step` (3398) | Referência para histórico e relocalização. | `extract` no replay chama caminho com IA; replay não comprova zero inferência. |
| Mesmo arquivo, `_update_action_indices` (3529) | Cascata de correspondência de elementos. | Reutilizar ideias; persistir receita semântica, não índice efêmero. |

Os caminhos desta tabela são relativos à pasta `docs/jcp`; apontam para a base clonada. Os números são de revisão fixada e podem mudar em atualizações.

## 3. Fronteiras propostas

```text
jcp/
  decisions/
    views.py       DecisionRequest, DecisionResult, Candidate
    service.py     DecisionProvider e aplicação do gate
    clef.py        CloudflareClefProvider; adapter local futuro
  runtime/
    browser_use/   BrowserUseAdapter: único consumidor direto de Actor/CDP
    actions.py     ActionBroker
  repair/
    discovery.py   Agent Browser Use + LLM generativa
    compiler.py    trajetória/patch -> receita candidata
  pescache/        DSL, seleção e versões
  verification/   verificadores que os modelos não podem reescrever
```

Esses diretórios são proposta de implementação, não módulos adicionados ao runtime por esta PR documental. O primeiro passo é desenvolver o adapter e seu contrato, sem modificar internals de `Agent` para fingir uma interface chat sobre o Clef.

## 4. Código Clef inspecionado

Revisões: Clef `2f3de3dd85f379784083b0814d997ab627200f0c`; Clef-flash `17f0b0ad64efb65d273590632833508766b2aae6`. O arquivo `joint_schema_model.py` tem o mesmo hash nas duas revisões inspecionadas. Pesos e configurações diferem.

| Símbolo | Linha | Achado | Consequência no JCP |
|---|---:|---|---|
| `question_options` | 46 | `choice` ordena IDs; `score` usa níveis numerados; `noul` usa verdadeiro/falso. | Não vincular ação à posição acidental de um array. |
| `encode_record` | 103 | Monta estado e schema; limite local padrão de 16.384; corta o estado quando necessário. | Compactar antes da chamada e testar ausência de informação crítica. |
| `EvidenceRoutingLayer` | 242 | Atenção das consultas ao contexto. | O modelo usa conteúdo e opções em conjunto; descrição de candidato influencia a decisão. |
| `JointSchemaHead` | 281 | Combina representações de campos e opções e produz scores. | Não substituir a cabeça por geração de texto genérica. |
| `ClefModel.forward` | 462 | Backbone e cabeça conjunta; `use_cache=False`. | Não inferir comportamento de decode autoregressivo ou cache a partir de um servidor de chat. |
| `load_release_model` | 494 | Carrega backbone, `joint_head.safetensors` e processor. | Self-host precisa dos componentes e versões compatíveis. |
| `systemone_answer` | 523 | Converte probabilidades; arredonda quatro casas; score é média ponderada. | Validação com tolerância ao arredondamento e tipos distintos. |
| `systemone` | 547 | Executa forward, aplica softmax e devolve respostas e uso. | Trata-se do contrato de decisão, não de `AgentOutput` do Browser Use. |

Fonte: [joint_schema_model.py fixado](https://huggingface.co/Cloudflare/clef/blob/2f3de3dd85f379784083b0814d997ab627200f0c/joint_schema_model.py). O carregador local devolve o campo `model` fornecido no pedido; esse rótulo sozinho não comprova quais pesos estão carregados. O serviço local deve vincular configuração, revisão e telemetria de modo confiável.

## 5. O que fica fora do patch inicial

Não alterar o loop generativo upstream, não adicionar pesos ao Git, não mudar a biblioteca Surf nem copiar seu cliente para dentro do decisor. Browser/HTTP são executores de transporte; Clef é provedor de escolha. A migração de Jev é uma alteração do módulo M5 e de sua configuração, acompanhada de avaliação.

O runtime deverá registrar decisões, IDs de observação, modelo, versão do schema de perguntas, resultado de gate e custo observado. O log não inclui credenciais ou conteúdo jurídico integral por padrão.
