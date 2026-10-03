# JCP-application — MVP

**Judicial Communication Protocol — Prova de Conceito**

> Tornar a web jurídica visível para agentes de IA.

Esta pasta contém o plano executável, as especificações e o código do MVP do JCP.
O escopo é deliberadamente restrito: **browser-use + CLEF**, sem Surf, sem Go, sem abstrações extras.
O objetivo é provar o circuito mínimo e determinar os requisitos reais de máquina e ambiente.

## Estrutura

```
JCP-application/
  README.md                        <- este arquivo
  specs/
    00-MVP-SCOPE.md                <- o que entra e o que fica fora do MVP
    01-REQUIREMENTS.md             <- requisitos de máquina e ambiente
    02-SPEC-CJPG.md                <- especificação da única claw do MVP
    03-IMPLEMENTATION-PROBLEMS.md  <- problemas reais de implementação
    04-SPEC-CLEF-ADAPTER.md        <- contrato do adapter Clef
    05-ACCEPTANCE-TESTS.md         <- testes de aceitação do MVP
  runtime/
    jcp/                           <- código a ser escrito (ver specs)
  fixtures/
    cjpg_result_page.html          <- fixture HTML para testes offline
    cjpg_empty_page.html           <- fixture resultado vazio
    cjpg_auth_page.html            <- fixture página de login/desafio
```

## O que o MVP prova

1. Uma função jurídica tipada (`search_decisions`) executa via BrowserSession/Actor
2. O caminho estável roda **zero chamadas de LLM**
3. CLEF é chamado apenas na recuperação de locator — nunca no caminho principal
4. O verificador é independente e não pode ser alterado pelo executor
5. A segunda execução reutiliza a receita salva sem inferência

## O que o MVP não inclui

- Surf / Go / HTTP direto
- Autenticação (PJe, eproc)
- Mais de um portal
- Autorreparo generativo completo
- Cobertura nacional

## Ordem de leitura

1. `specs/00-MVP-SCOPE.md`
2. `specs/01-REQUIREMENTS.md`
3. `specs/03-IMPLEMENTATION-PROBLEMS.md`
4. `specs/02-SPEC-CJPG.md`
5. `specs/04-SPEC-CLEF-ADAPTER.md`
6. `specs/05-ACCEPTANCE-TESTS.md`
