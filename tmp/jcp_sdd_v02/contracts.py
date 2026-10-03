from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


Id = Annotated[str, StringConstraints(min_length=1, max_length=200, pattern=r'^[A-Za-z0-9_.:-]+$')]
Version = Annotated[str, StringConstraints(pattern=r'^\d+\.\d+\.\d+$')]
NonEmpty = Annotated[str, StringConstraints(min_length=1, max_length=4096)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, validate_default=True)


class CjpgSearchArguments(StrictModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    date_from: date
    date_to: date
    date_kind: Literal['availability']
    limit: int = Field(ge=1, le=100)
    cursor: Id | None = None

    @model_validator(mode='after')
    def chronological(self) -> Self:
        if self.date_from > self.date_to:
            raise ValueError('date_from must not exceed date_to')
        return self


class Options(StrictModel):
    freshness: Literal['live', 'cached_if_fresh'] = 'live'
    max_age_ms: int = Field(default=0, ge=0, le=86400000)
    transport: Literal['auto', 'browser', 'http'] = 'auto'
    allow_partial: bool = True
    allow_repair: bool = True

    @model_validator(mode='after')
    def freshness_bounds(self) -> Self:
        if self.freshness == 'live' and self.max_age_ms != 0:
            raise ValueError('live requires max_age_ms=0')
        if self.freshness == 'cached_if_fresh' and self.max_age_ms <= 0:
            raise ValueError('cached_if_fresh requires a positive max_age_ms')
        return self


class Budget(StrictModel):
    deadline_ms: int = Field(ge=1, le=600000)
    max_pages: int = Field(ge=1, le=100)
    max_documents: int = Field(ge=0, le=100)
    max_model_calls: int = Field(ge=0, le=30)
    max_repair_candidates: int = Field(ge=0, le=3)
    max_download_bytes: int = Field(ge=0, le=100000000)


class CjpgInvocation(StrictModel):
    protocol_version: Literal['0.1']
    request_id: Id
    capability_id: Literal['tjsp.cjpg.search_decisions']
    capability_version: Literal['1.0.0']
    installation_id: Literal['tjsp-esaj-cjpg']
    arguments: CjpgSearchArguments
    session_ref: Id | None
    options: Options
    budget: Budget
    idempotency_key: Id


CheckId = Literal['schema', 'identity', 'filters', 'coverage', 'provenance']


class Check(StrictModel):
    check_id: CheckId
    status: Literal['passed', 'failed']
    evidence_refs: list[Id] = Field(min_length=1, max_length=100)


class Verification(StrictModel):
    status: Literal['not_run', 'passed', 'failed']
    checks: list[Check] = Field(max_length=5)
    evidence_refs: list[Id] = Field(max_length=100)

    @model_validator(mode='after')
    def consistent_report(self) -> Self:
        ids = [c.check_id for c in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate verification check')
        known_refs = set(self.evidence_refs)
        if any(not set(c.evidence_refs) <= known_refs for c in self.checks):
            raise ValueError('check evidence must be listed in the report')
        if self.status == 'not_run' and (self.checks or self.evidence_refs):
            raise ValueError('not_run has no completed checks or evidence report')
        if self.status == 'passed':
            required = {'schema', 'identity', 'filters', 'coverage', 'provenance'}
            if set(ids) != required or any(c.status != 'passed' for c in self.checks):
                raise ValueError('passed requires all five successful checks')
        if self.status == 'failed' and not any(c.status == 'failed' for c in self.checks):
            raise ValueError('failed report requires a failed check')
        return self


class Coverage(StrictModel):
    sources_requested: list[Id] = Field(min_length=1, max_length=10)
    sources_completed: list[Id] = Field(max_length=10)
    pages_visited: int = Field(ge=0)
    items_returned: int = Field(ge=0)
    total_reported: int | None = Field(ge=0)
    complete: bool
    source_exhausted: bool | None
    stop_reason: Literal['page_limit', 'item_limit', 'document_limit', 'deadline', 'model_budget', 'source_unavailable', 'cancelled', 'access_challenge', 'no_progress'] | None

    @model_validator(mode='after')
    def coherent_sources(self) -> Self:
        if len(set(self.sources_requested)) != len(self.sources_requested):
            raise ValueError('duplicate requested source')
        if len(set(self.sources_completed)) != len(self.sources_completed):
            raise ValueError('duplicate completed source')
        if not set(self.sources_completed) <= set(self.sources_requested):
            raise ValueError('completed source was not requested')
        if self.complete and set(self.sources_completed) != set(self.sources_requested):
            raise ValueError('complete scope requires all requested sources completed')
        return self


class DecisionSummary(StrictModel):
    kind: Literal['source_excerpt', 'source_headnote', 'model_summary']
    text: NonEmpty


class DecisionRecord(StrictModel):
    decision_ref: Id
    source_id: Literal['tjsp-esaj-cjpg']
    source_document_id: Id | None
    case_number_raw: NonEmpty | None
    decision_kind: Literal['sentence', 'interlocutory', 'judgment', 'other', 'unknown']
    decision_kind_basis: Literal['source', 'derived', 'unknown']
    court: NonEmpty
    panel_raw: NonEmpty | None
    judge_raw: NonEmpty | None
    judgment_date: date | None
    publication_date: date | None
    availability_date: date | None
    summary: DecisionSummary | None
    full_text_ref: Id | None
    source_url: Annotated[str, StringConstraints(pattern=r'^https://[^\s]+$', max_length=4096)]
    observed_at: datetime
    evidence_refs: list[Id] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def aware_timestamp(self) -> Self:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError('observed_at must contain timezone information')
        return self


class SearchData(StrictModel):
    items: list[DecisionRecord] = Field(max_length=100)


ErrorCode = Literal['INVALID_INPUT', 'UNSUPPORTED_CAPABILITY', 'POLICY_DENIED', 'ACCESS_DENIED', 'AUTH_REQUIRED', 'AUTH_EXPIRED', 'ACCESS_CHALLENGE', 'RATE_LIMITED', 'PORTAL_UNAVAILABLE', 'TRANSPORT_ERROR', 'SELECTOR_NOT_FOUND', 'AMBIGUOUS_TARGET', 'PAGE_STATE_MISMATCH', 'PARSER_DRIFT', 'TRUNCATED_RESPONSE', 'VERIFICATION_FAILED', 'REPAIR_FAILED', 'RECIPE_CONFLICT', 'BUDGET_EXHAUSTED', 'DEADLINE_EXCEEDED', 'UNCERTAIN_EFFECT']


class JcpError(StrictModel):
    code: ErrorCode
    message: NonEmpty
    stage: Id
    retryable: bool
    effect_state: Literal['not_dispatched', 'confirmed', 'uncertain']
    evidence_refs: list[Id] = Field(max_length=100)
    next_action: Literal['none', 'correct_input', 'authenticate', 'wait', 'repair', 'reconcile', 'contact_operator']
    cause_ref: Id | None


class Execution(StrictModel):
    recipe_id: Id | None
    recipe_version: Version | None
    transport: Literal['browser', 'http'] | None
    model_calls: int = Field(ge=0)
    repaired: bool

    @model_validator(mode='after')
    def recipe_pair(self) -> Self:
        if (self.recipe_id is None) != (self.recipe_version is None):
            raise ValueError('recipe_id and recipe_version must be present together')
        return self


RunStatus = Literal['accepted', 'running', 'needs_input', 'needs_auth', 'suspended', 'success', 'partial', 'failed', 'cancelled', 'uncertain_effect']


class CjpgResult(StrictModel):
    protocol_version: Literal['0.1']
    run_id: Id
    status: RunStatus
    capability_id: Literal['tjsp.cjpg.search_decisions']
    capability_version: Literal['1.0.0']
    installation_id: Literal['tjsp-esaj-cjpg']
    data: SearchData
    coverage: Coverage
    verification: Verification
    execution: Execution
    errors: list[JcpError] = Field(max_length=20)
    continuation: Id | None

    @model_validator(mode='after')
    def consistent_result(self) -> Self:
        items = self.data.items
        if self.coverage.items_returned != len(items):
            raise ValueError('items_returned must equal the number of published items')
        if self.coverage.sources_requested != [self.installation_id]:
            raise ValueError('this vertical profile supports exactly its declared installation')
        if len({i.decision_ref for i in items}) != len(items):
            raise ValueError('duplicate decision_ref')
        if self.status in {'success', 'partial'}:
            if self.verification.status != 'passed' or self.coverage.pages_visited < 1:
                raise ValueError('published result requires verification and a visited page')
            refs = set(self.verification.evidence_refs)
            if any(not set(i.evidence_refs) <= refs for i in items):
                raise ValueError('published item requires evidence in verification report')
            if self.execution.recipe_id is None or self.execution.transport is None:
                raise ValueError('published result requires execution provenance')
        elif items:
            raise ValueError('this profile publishes items only in success/partial')
        if self.status == 'success' and (not self.coverage.complete or self.errors or self.coverage.stop_reason is not None):
            raise ValueError('success requires complete scope, no error and no interruption')
        if self.status == 'success' and not items and self.coverage.source_exhausted is not True:
            raise ValueError('empty success requires confirmation that the source is exhausted')
        if self.status == 'partial' and (not items or self.coverage.complete or self.coverage.stop_reason is None):
            raise ValueError('partial requires useful items and a stated incomplete scope')
        if self.status == 'failed' and not self.errors:
            raise ValueError('failed requires a typed error')
        if self.status == 'needs_auth' and not any(e.code in {'AUTH_REQUIRED', 'AUTH_EXPIRED'} for e in self.errors):
            raise ValueError('needs_auth requires an authentication error')
        if self.status == 'uncertain_effect' and not any(e.code == 'UNCERTAIN_EFFECT' and e.effect_state == 'uncertain' for e in self.errors):
            raise ValueError('uncertain_effect requires its corresponding error')
        return self


def validate_against_invocation(invocation: CjpgInvocation, result: CjpgResult) -> None:
    """Checks requiring both envelopes; this does not verify the source itself."""
    if (result.capability_id, result.capability_version, result.installation_id) != (
        invocation.capability_id, invocation.capability_version, invocation.installation_id
    ):
        raise ValueError('result does not belong to the requested capability')
    if result.execution.model_calls > invocation.budget.max_model_calls:
        raise ValueError('model budget exceeded')
    if result.coverage.pages_visited > invocation.budget.max_pages:
        raise ValueError('page budget exceeded')
    if len(result.data.items) > invocation.arguments.limit:
        raise ValueError('requested item limit exceeded')
    if result.status == 'partial' and not invocation.options.allow_partial:
        raise ValueError('partial result was not requested')
    if result.execution.repaired and not invocation.options.allow_repair:
        raise ValueError('repair was not allowed')
    if invocation.options.transport != 'auto' and result.execution.transport not in (None, invocation.options.transport):
        raise ValueError('explicit transport was not respected')
    if result.status == 'success' and len(result.data.items) < invocation.arguments.limit and result.coverage.source_exhausted is not True:
        raise ValueError('fewer items than requested requires source exhaustion')
    for item in result.data.items:
        if item.availability_date is not None and not (invocation.arguments.date_from <= item.availability_date <= invocation.arguments.date_to):
            raise ValueError('known availability date violates the requested filter')
