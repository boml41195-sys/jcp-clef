# Contrato de decisão e avaliação Clef

## 1. Interface interna proposta

`DecisionProvider` recebe `DecisionRequest` e devolve `DecisionResult`, ambos modelos Pydantic v2 fechados. A interface é distinta de `BaseChatModel`: seu objetivo é escolher dentro de uma gramática, não produzir texto ou `AgentOutput` genérico.

Campos internos do pedido: `run_id`, `step_id`, `observation_id`, `observation_generation`, `capability_id`, `decision_kind`, `candidates`, `known_bindings`, `deadline_at`, `remaining_model_calls`, `state_policy_version`. O adapter converte apenas o conteúdo necessário ao payload externo.

Campos internos da resposta: decisão/abstenção, operação, candidato, geração da observação, variante/modelo, probabilidades relevantes, uso observado, duração e referência ao relatório do gate. Esses metadados são associados pelo runtime; não confiar no modelo para devolver identidade de tenant ou prazo.

## 2. Payload ilustrativo para escolha de alvo

O exemplo usa candidatos sintéticos. As strings `candidate_01` e `candidate_02` são referências locais, não seletores descobertos em tribunal.

```json
{
  "model": "clef",
  "state": {
    "task": "Localizar o campo de pesquisa livre da consulta autorizada",
    "page_state": "search_form",
    "observation_id": "obs_fixture_001",
    "candidates": [
      {"id": "candidate_01", "role": "textbox", "label": "Pesquisa livre", "form": "Consulta de decisões"},
      {"id": "candidate_02", "role": "textbox", "label": "Pesquisar no site", "form": "Cabeçalho"}
    ]
  },
  "questions": {
    "target": {
      "type": "choice",
      "instructions": "Escolha o campo da consulta de decisões. Se os dados não permitirem escolher, use abstain.",
      "criteria": {
        "candidate_01": "Campo observado na consulta de decisões",
        "candidate_02": "Campo observado no cabeçalho do site",
        "abstain": "Não há candidato adequado ou há ambiguidade"
      }
    }
  }
}
```

O binding da query já está nos argumentos da função e pode permanecer fora do payload: não é necessário enviar o conteúdo jurídico para decidir qual textbox corresponde a um formulário.

## 3. Transporte e normalização

Para REST, usar `POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/cloudflare/clef`, com Bearer obtido por referência protegida. `clef-flash` muda o identificador da rota e o campo `model` em conjunto. Endpoint e conta vêm da configuração, não do conteúdo de páginas. O [guia REST](https://developers.cloudflare.com/workers-ai/get-started/rest-api/) documenta o envelope `result/success/errors/messages`.

O adapter REST primeiro valida status HTTP e envelope de serviço; só depois interpreta `result.answers`. `env.AI.run` e a função Python local são superfícies diferentes, portanto possuem normalização explícita. Uma resposta `200` com erro de serviço não pode produzir ação.

A [ficha Clef](https://developers.cloudflare.com/workers-ai/models/clef/) descreve `model`, `state` e `questions`, até 64 perguntas, e o contexto hospedado de 65.536 tokens. O perfil inicial JCP usa `choice` com poucas perguntas; não depende do limite máximo. A rota hospedada documenta imagens embutidas, não URLs remotas. Suporte a vídeo do código local não deve ser presumido como campo disponível nessa rota.

Timeout, 401/403, 429, 5xx e payload inesperado produzem falha tipada de provedor. Repetir uma inferência não repete uma ação do navegador; ainda assim consome prazo e possível custo. O envio de ação depende de uma nova decisão válida e do gate. Retries ficam limitados pelo orçamento global.

## 4. Interpretação dos tipos

| Tipo | Semântica encontrada no código local | Uso inicial |
|---|---|---|
| `choice` | ID vencedor, confiança associada e probabilidades por opção. | Alvo, classe de estado ou recuperação permitida. |
| `noul` | Probabilidade de verdadeiro, não um booleano. | Sinal auxiliar opcional com regra de decisão explícita. |
| `score` | Média ponderada de níveis ordenados, com legenda. | Priorização opcional; não usar como índice de ação. |

Fonte: `systemone_answer`, linha 523 do [código fixado](https://huggingface.co/Cloudflare/clef/blob/2f3de3dd85f379784083b0814d997ab627200f0c/joint_schema_model.py). Probabilidades são arredondadas para quatro casas. O gate aceita tolerância de soma coerente com esse arredondamento, mas rejeita números não finitos, opções ausentes/desconhecidas e valores fora de [0,1].

Para `choice`, confirmar que o escolhido está no conjunto enviado e é compatível com a distribuição, admitindo apenas a tolerância de arredondamento. IDs de perguntas devem corresponder aos esperados. Em múltiplas cabeças de operação/alvo, somente a cabeça da operação selecionada pode gerar uma ação.

Empates e pequena margem entre candidatos exigem uma política explícita de abstenção. O código local escolhe o primeiro critério na ordem original em empate; essa convenção não é evidência de que aquele alvo seja mais seguro. Thresholds de confiança e margem serão calibrados por tarefa, não definidos como garantia universal.

## 5. Gate antes de executar

1. A resposta pertence ao pedido ainda ativo e chegou dentro do prazo?
2. Os campos e a distribuição são válidos para as opções enviadas?
3. A observação ainda é atual e o candidato continua presente, no frame e origem corretos?
4. A operação pertence à capacidade autorizada e seu efeito está permitido?
5. Os bindings necessários existem sem geração ou adivinhação de valores?
6. A decisão já foi consumida? Consumi-la antes do envio impede reuso acidental.
7. Há pós-condição observável e verificador independente para confirmar o resultado?

Nenhuma resposta do modelo altera filtros, identidade do processo, política, orçamento ou o verificador. Um resultado `abstain` encaminha para reobservação, LLM generativa ou suspensão conforme a causa; não é substituído pelo primeiro candidato.

## 6. Preparação do estado e truncamento

O `encode_record` local inspecionado usa `max_length=16384` por padrão, reserva espaço para schema e corta o estado para caber. Um limite hospedado maior não muda esse default do arquivo local. O JCP deve construir um estado compacto e medir seu tamanho antes da chamada.

Preservar objetivo da etapa, papel dos candidatos, contexto de formulário e sinais necessários de página. Excluir scripts, conteúdo repetido, texto jurídico desnecessário e segredos. Quando não couber, reduzir candidatos por regras e escopo, e não cortar arbitrariamente o final de uma observação completa.

O controlador mantém a identidade jurídica e as autorizações fora do modelo. Assim, mesmo uma decisão sobre contexto incompleto não pode autorizar uma operação fora do contrato. Essa proteção não resolve perda de qualidade; a avaliação ainda precisa testar truncamento e estados ambíguos.

## 7. Ensaios executados nesta entrega

Foram extraídas por AST somente funções e estruturas de preparação/conversão do código fixado e executados **18 checks**. Não houve importação de Torch, download de pesos, GPU nem chamada à API. Um tokenizer sintético de caracteres foi usado apenas para exercitar os ramos do encoder; não mede tokens ou qualidade do tokenizer real.

| Grupo | Checks | Resultado |
|---|---:|---|
| IDs/opções de choice, noul e score | 3 | Passaram. |
| Escolha, confiança, arredondamento, score, legenda, noul e empate | 7 | Passaram. |
| Unicode e identidade da pergunta | 2 | Passaram. |
| Estado completo, truncamento e preservação do schema | 3 | Passaram. |
| Limite explícito de estado, schema grande e perguntas vazias | 3 | Passaram. |

Isso confirma detalhes de integração do código lido. Não é benchmark de Clef, nem demonstração de precisão em português ou de navegação jurídica. Os hashes e o relatório resumido estão em [Fontes e evidências](FONTES-E-EVIDENCIAS.md).

## 8. Avaliação necessária com inferência real

Construir um conjunto inicial de estados de teste com: formulário reconhecido; campo renomeado; campo parecido incorreto; múltiplos frames; login expirado; resultado vazio; tela de erro; paginação repetida; popup; operação com efeito fora do escopo; observação envelhecida; instrução maliciosa na página; ausência de candidato correto.

Para cada caso, registrar conjunto de ações aceitáveis e quando abstenção é obrigatória. Avaliar Clef e Flash separadamente, com o mesmo estado, perguntas e gate. A execução generativa continua disponível como etapa posterior; não misturar seu resultado com a acurácia de uma única decisão do Clef.

Métricas: acerto entre opções, ação incorreta executada, abstenção apropriada, recuperação verificada, chamadas por tarefa, input tokens observados, custo, tempo do provedor e tempo total. Separar preparação, rede, inferência, execução de portal e verificação. Avaliar português jurídico e layouts reais; benchmarks externos não substituem esse conjunto.

Critério de liberação inicial: nenhum ato fora de escopo nos casos de aceite, nenhum falso sucesso de identidade, preservação do caminho estável sem inferência e reparo validado. Metas estatísticas e thresholds dependem da amostra e do risco de cada capacidade.
