# JCP sobre Browser Use — revisão 0.3 com Clef

3 de outubro de 2026. Esta pasta é a entrada do estudo de aplicabilidade solicitado para o código clonado. O MVP passa a usar Cloudflare Clef no lugar do provedor Jev para decisões delimitadas. A arquitetura mantém as funções jurídicas, o executor determinístico, o Pescache, a verificação independente e o reparo versionado.

## Decisão central

Clef cabe no módulo M5, como `DecisionProvider`. Ele recebe um estado limitado e opções válidas; o JCP transforma a opção escolhida em uma ação já autorizada. O código de Clef não implementa a interface generativa `BaseChatModel` esperada pelo Agent do Browser Use. Portanto, a integração proposta chama Clef fora do loop de geração de texto e usa BrowserSession/Actor para executar.

Para o primeiro MVP, a configuração proposta usa `clef` como padrão de qualidade; `clef-flash` fica habilitável por classe de decisão depois de avaliação. A disponibilidade de duas variantes não obriga duas chamadas em cada passo. Código salvo continua executando sem inferência no caminho estável.

## Conteúdo

1. [Estudo de aplicabilidade](APLICABILIDADE-CLEF.md): conclusões, arquitetura, escolhas de MVP e limites.
2. [Mapa do código](MAPA-DO-CODIGO.md): arquivos, símbolos e pontos concretos de integração.
3. [Contrato e avaliação](CONTRATO-E-AVALIACAO-CLEF.md): formato de decisão, semântica, testes locais e critérios de validação com o modelo.
4. [Plano do pivot](PIVOT-E-IMPLEMENTACAO.md): mudanças por módulo, ordem de trabalho e pendências.
5. [Fontes e evidências](FONTES-E-EVIDENCIAS.md): commits, revisões dos modelos, origem dos números e resultados da inspeção.
6. [SDD consolidada](sdd/README.md): especificação anterior revisada para a decisão de produto atual.

## Como ler o status

**Observado**: comportamento encontrado no código fixado. **Proposto**: implementação nova do JCP. **Testado localmente**: ensaio especificado e executado sem inferência real. **Pendente**: teste que exige runtime, credenciais, pesos ou acesso ao portal.

O benchmark anexado coincide com a publicação da Cloudflare. Ele orienta hipóteses, mas não mede os portais brasileiros ou o runtime JCP. Os resultados variam por tarefa; não há conclusão de superioridade em todo cenário.
