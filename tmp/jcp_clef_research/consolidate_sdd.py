from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'JCP-SDD'
TARGET = ROOT / 'browser-use-jcp' / 'docs' / 'jcp' / 'sdd'
TARGET.mkdir(parents=True, exist_ok=True)

for path in sorted(SOURCE.glob('*.md')):
    text = path.read_text(encoding='utf-8')
    if path.name != '09-FONTES-E-CONCLUSOES.md':
        protected = ['Jev Ultrafast', 'benchmark Jev externo', 'Browser Use e Jev foram conferidas']
        for i, phrase in enumerate(protected):
            text = text.replace(phrase, f'__HISTORICAL_JEV_{i}__')
        text = text.replace('JevDecisionClient', 'CloudflareClefProvider').replace('Jev', 'Clef')
        text = text.replace('decisions/      jev, candidates, calibration', 'decisions/      clef, candidates, calibration')
        for i, phrase in enumerate(protected):
            text = text.replace(f'__HISTORICAL_JEV_{i}__', phrase)
    if path.name == 'README.md':
        text = text.replace('Revisão documental 0.2', 'Revisão documental 0.3', 1)
        text = text.replace('## Ordem de leitura', '## Pivot Clef\n\nEsta é a cópia consolidada para o MVP com Clef. A LLM generativa continua no projeto para geração de código e reparos. [Estudo de aplicabilidade e fontes atuais](../README.md). As referências a Jev Ultrafast em fontes e benchmarks são históricas. Os modelos de contrato CJPG e seus 34 testes não mudaram neste pivot.\n\n## Ordem de leitura', 1)
    if path.name == '08-IMPLEMENTACAO-E-ACEITACAO.md':
        old = 'Integrar o cliente de decisão tipada observado em Jev Ultrafast atrás de `DecisionProvider`. A disponibilidade do serviço, credenciais e modelo exato entram na configuração; não cristalizar `jev-latest` como garantia de modelo ou desempenho.'
        new = 'Implementar `CloudflareClefProvider` atrás de `DecisionProvider`, com `clef` como configuração inicial e `clef-flash` sujeito a avaliação. A LLM generativa permanece no módulo de descoberta/reparo. Jev Ultrafast é referência histórica de controle, não dependência de inferência do MVP. O estudo atual define o adapter e suas verificações em [Clef](../CONTRATO-E-AVALIACAO-CLEF.md).'
        if old not in text:
            raise AssertionError('Expected migration paragraph not found')
        text = text.replace(old, new)
    if path.name == 'PENDENCIAS.md':
        text = text.replace('| P08 | Serviço Clef no ambiente do produto | Código e benchmark Ultrafast inspecionados | Confirmar SDK/API, modelo, credenciais e executar escolha tipada | Respostas válidas/abstenção, medição local e gate testados. |', '| P08 | Serviço Clef no ambiente do produto | Código Clef/Clef-flash fixado; 18 checks locais sem inferência | Implementar adapter REST e executar chamada real autorizada | Respostas válidas/abstenção, medição local e gate testados. |')
        text += '\n## Pivot da revisão 0.3\n\nO provedor de decisão passa a ser Clef. A LLM generativa continua para código e reparos. [Estudo atual](../README.md). Os checks de preparação/conversão do Clef não encerram pendências de inferência, runtime ou portal.\n'
    if path.name == '09-FONTES-E-CONCLUSOES.md':
        text = text.replace('# Fontes inspecionadas e conclusões', '# Fontes inspecionadas e conclusões\n\nNota da revisão 0.3: este documento preserva fontes históricas do desenho anterior. O provedor corrente do MVP é Clef, mantendo a LLM generativa para código e reparos. As revisões e conclusões do novo provedor estão em [Fontes Clef](../FONTES-E-EVIDENCIAS.md).', 1)
    if path.name == '02-MODULOS-E-COMPONENTES.md':
        text = text.replace('`CloudflareClefProvider` chama perguntas Choice e valida domínio, campos e distribuições.', '`CloudflareClefProvider` chama perguntas Choice do Clef e valida domínio, campos e distribuições. A normalização do envelope Workers AI fica neste adapter.')
    (TARGET / path.name).write_text(text, encoding='utf-8')

print(f'Consolidated {len(list(TARGET.glob("*.md")))} documents into {TARGET}')
