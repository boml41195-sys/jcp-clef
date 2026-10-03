from __future__ import annotations

from copy import deepcopy
import json

from pydantic import ValidationError
from contracts import CjpgInvocation, CjpgResult, validate_against_invocation


INVOCATION = {
    'protocol_version': '0.1', 'request_id': 'req_fixture_001',
    'capability_id': 'tjsp.cjpg.search_decisions', 'capability_version': '1.0.0',
    'installation_id': 'tjsp-esaj-cjpg',
    'arguments': {'query': 'termo de teste sintetico', 'date_from': '2026-09-01',
                  'date_to': '2026-09-02', 'date_kind': 'availability', 'limit': 1},
    'session_ref': None,
    'options': {'freshness': 'live', 'max_age_ms': 0, 'transport': 'auto',
                'allow_partial': True, 'allow_repair': True},
    'budget': {'deadline_ms': 120000, 'max_pages': 2, 'max_documents': 10,
               'max_model_calls': 6, 'max_repair_candidates': 1, 'max_download_bytes': 20000000},
    'idempotency_key': 'fixture-operation-001',
}

ITEM = {
    'decision_ref': 'decision_fixture_001', 'source_id': 'tjsp-esaj-cjpg',
    'source_document_id': 'document_fixture_001', 'case_number_raw': 'PROCESSO-SINTETICO-001',
    'decision_kind': 'unknown', 'decision_kind_basis': 'unknown', 'court': 'TJSP',
    'panel_raw': None, 'judge_raw': None, 'judgment_date': None,
    'publication_date': None, 'availability_date': '2026-09-01',
    'summary': {'kind': 'source_excerpt', 'text': 'Texto sintetico usado somente para testar o contrato.'},
    'full_text_ref': None, 'source_url': 'https://fixture.invalid/decisao/001',
    'observed_at': '2026-10-03T12:00:00-03:00', 'evidence_refs': ['evidence_fixture_001'],
}

SUCCESS = {
    'protocol_version': '0.1', 'run_id': 'run_fixture_001', 'status': 'success',
    'capability_id': 'tjsp.cjpg.search_decisions', 'capability_version': '1.0.0',
    'installation_id': 'tjsp-esaj-cjpg', 'data': {'items': [ITEM]},
    'coverage': {'sources_requested': ['tjsp-esaj-cjpg'], 'sources_completed': ['tjsp-esaj-cjpg'],
                 'pages_visited': 1, 'items_returned': 1, 'total_reported': 3,
                 'complete': True, 'source_exhausted': False, 'stop_reason': None},
    'verification': {'status': 'passed',
                     'checks': [{'check_id': c, 'status': 'passed', 'evidence_refs': ['evidence_fixture_001']}
                                for c in ['schema', 'identity', 'filters', 'coverage', 'provenance']],
                     'evidence_refs': ['evidence_fixture_001']},
    'execution': {'recipe_id': 'cjpg-fixture-search', 'recipe_version': '0.1.0',
                  'transport': 'browser', 'model_calls': 0, 'repaired': False},
    'errors': [], 'continuation': None,
}


def example_cases():
    empty = deepcopy(SUCCESS)
    empty['data']['items'] = []
    empty['coverage'].update(items_returned=0, total_reported=0, source_exhausted=True)
    partial_invocation = deepcopy(INVOCATION)
    partial_invocation['arguments']['limit'] = 10
    partial = deepcopy(SUCCESS)
    partial.update(status='partial', continuation='continuation_fixture_opaque')
    partial['coverage'].update(complete=False, sources_completed=[], stop_reason='page_limit', pages_visited=2)
    running = deepcopy(SUCCESS)
    running.update(status='running', data={'items': []}, verification={'status': 'not_run', 'checks': [], 'evidence_refs': []})
    running['coverage'].update(sources_completed=[], pages_visited=0, items_returned=0, total_reported=None, complete=False, source_exhausted=None)
    needs_auth = deepcopy(running)
    needs_auth.update(status='needs_auth', errors=[{'code': 'AUTH_EXPIRED', 'message': 'Sessao de teste expirada.',
        'stage': 'acquiring_session', 'retryable': False, 'effect_state': 'not_dispatched',
        'evidence_refs': ['auth_evidence_fixture'], 'next_action': 'authenticate', 'cause_ref': None}])
    failed = deepcopy(running)
    failed.update(status='failed', errors=[{'code': 'PARSER_DRIFT', 'message': 'Estrutura de teste nao reconhecida.',
        'stage': 'extract', 'retryable': False, 'effect_state': 'not_dispatched',
        'evidence_refs': ['parser_evidence_fixture'], 'next_action': 'repair', 'cause_ref': None}])
    return [
        ('C01', 'Sucesso com limite solicitado satisfeito, sem esgotar a fonte', INVOCATION, SUCCESS),
        ('C02', 'Sucesso vazio com fonte esgotada', INVOCATION, empty),
        ('C03', 'Parcial util ao atingir limite de paginas', partial_invocation, partial),
        ('C04', 'Execucao em andamento sem dados publicados', INVOCATION, running),
        ('C05', 'Sessao expirada, sem disfarcar o estado como vazio', INVOCATION, needs_auth),
        ('C06', 'Falha de parser, sem publicar itens rejeitados', INVOCATION, failed),
    ]


def set_path(obj, path, value):
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value


def run_tests():
    report = []
    for cid, title, invocation, result in example_cases():
        parsed_invocation = CjpgInvocation.model_validate_json(json.dumps(invocation))
        parsed_result = CjpgResult.model_validate_json(json.dumps(result))
        validate_against_invocation(parsed_invocation, parsed_result)
        report.append({'id': cid, 'scenario': title, 'expected': 'accept', 'actual': 'accept'})

    mutations = [
        ('N01', 'Campo extra no envelope', 'invocation', ['tenant_id'], 'invented-tenant'),
        ('N02', 'Tipo booleano usado como limite numerico', 'invocation', ['arguments', 'limit'], True),
        ('N03', 'Intervalo de datas invertido', 'invocation', ['arguments', 'date_from'], '2026-09-03'),
        ('N04', 'Data impossivel', 'invocation', ['arguments', 'date_from'], '2026-02-30'),
        ('N05', 'Filtro de data nao suportado pela capacidade', 'invocation', ['arguments', 'date_kind'], 'judgment'),
        ('N06', 'Consulta composta somente por espacos', 'invocation', ['arguments', 'query'], '   '),
        ('N07', 'Modelo com orcamento negativo', 'invocation', ['budget', 'max_model_calls'], -1),
        ('N08', 'Cache autorizado sem idade maxima positiva', 'invocation', ['options', 'freshness'], 'cached_if_fresh'),
        ('N09', 'Sucesso sem verificacao', 'result', ['verification', 'status'], 'not_run'),
        ('N10', 'Sucesso com escopo incompleto', 'result', ['coverage', 'complete'], False),
        ('N11', 'Quantidade declarada diverge dos itens', 'result', ['coverage', 'items_returned'], 2),
        ('N12', 'Item sem evidencia', 'result', ['data', 'items', 0, 'evidence_refs'], []),
        ('N13', 'Evidencia do item ausente no relatorio', 'result', ['data', 'items', 0, 'evidence_refs'], ['unknown_evidence']),
        ('N14', 'Fonte concluida nao solicitada', 'result', ['coverage', 'sources_completed'], ['other-court']),
        ('N15', 'Timestamp sem fuso', 'result', ['data', 'items', 0, 'observed_at'], '2026-10-03T12:00:00'),
        ('N16', 'Relatorio aprovado com check que falhou', 'result', ['verification', 'checks', 0, 'status'], 'failed'),
        ('N17', 'Check duplicado oculta check ausente', 'result', ['verification', 'checks', 0, 'check_id'], 'identity'),
        ('N18', 'ID de receita sem versao', 'result', ['execution', 'recipe_version'], None),
        ('N19', 'Orcamento de inferencia excedido', 'result', ['execution', 'model_calls'], 7),
        ('N20', 'Orcamento de paginas excedido', 'result', ['coverage', 'pages_visited'], 3),
        ('N21', 'Data conhecida fora do filtro solicitado', 'result', ['data', 'items', 0, 'availability_date'], '2026-08-01'),
        ('N22', 'Menos itens que o pedido sem esgotar a fonte', 'invocation', ['arguments', 'limit'], 2),
        ('N23', 'Transporte explicito desrespeitado', 'invocation', ['options', 'transport'], 'http'),
        ('N24', 'Resultado final tenta publicar HTML como URL de origem', 'result', ['data', 'items', 0, 'source_url'], '<html>login</html>'),
    ]
    for cid, title, target, path, value in mutations:
        invocation, result = deepcopy(INVOCATION), deepcopy(SUCCESS)
        set_path(invocation if target == 'invocation' else result, path, value)
        try:
            parsed_invocation = CjpgInvocation.model_validate_json(json.dumps(invocation))
            parsed_result = CjpgResult.model_validate_json(json.dumps(result))
            validate_against_invocation(parsed_invocation, parsed_result)
        except (ValidationError, ValueError):
            report.append({'id': cid, 'scenario': title, 'expected': 'reject', 'actual': 'reject'})
        else:
            raise AssertionError(f'{cid} was incorrectly accepted')

    extra_negative = []
    partial_invocation, partial = deepcopy(example_cases()[2][2:])
    partial_invocation['options']['allow_partial'] = False
    extra_negative.append(('N25', 'Parcial quando o chamador recusou parcial', partial_invocation, partial))
    empty = deepcopy(example_cases()[1][3])
    empty['coverage']['source_exhausted'] = False
    extra_negative.append(('N26', 'Vazio sem prova de esgotamento', INVOCATION, empty))
    duplicate_inv, duplicate = deepcopy(INVOCATION), deepcopy(SUCCESS)
    duplicate_inv['arguments']['limit'] = 2
    duplicate['data']['items'].append(deepcopy(ITEM))
    duplicate['coverage']['items_returned'] = 2
    extra_negative.append(('N27', 'Identidade de decisao duplicada', duplicate_inv, duplicate))
    repair_inv, repair_result = deepcopy(INVOCATION), deepcopy(SUCCESS)
    repair_inv['options']['allow_repair'] = False
    repair_result['execution']['repaired'] = True
    extra_negative.append(('N28', 'Reparo fora da opcao autorizada', repair_inv, repair_result))
    for cid, title, invocation, result in extra_negative:
        try:
            parsed_invocation = CjpgInvocation.model_validate_json(json.dumps(invocation))
            parsed_result = CjpgResult.model_validate_json(json.dumps(result))
            validate_against_invocation(parsed_invocation, parsed_result)
        except (ValidationError, ValueError):
            report.append({'id': cid, 'scenario': title, 'expected': 'reject', 'actual': 'reject'})
        else:
            raise AssertionError(f'{cid} was incorrectly accepted')
    return report


if __name__ == '__main__':
    report = run_tests()
    print(json.dumps({'passed': len(report), 'failed': 0, 'report': report}, ensure_ascii=False, indent=2))
