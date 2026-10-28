import hashlib
import json
import logging
import os
import shutil
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.contracts.enums import (
    CorpusRevisionState,
    JobKind,
    EffectiveDecisionState,
    SourceNamespace,
)
from app.contracts.models import (
    DashboardReviewSummary,
    SearchExecutionSelectionUpdate,
    ArticleRadarResponse,
    AssistantProposal,
    AssistantRequest,
    CapabilitiesResponse,
    ConflictResolveRequest,
    CorpusDiffResponse,
    CorpusRevisionResponse,
    CriteriaSuggestRequest,
    CriteriaSuggestResponse,
    CriteriaVersionCreate,
    CriteriaVersionResponse,
    CriterionDefinition,
    DecisionCommand,
    DedupOverrideRequest,
    ErrorDetail,
    ErrorEnvelope,
    EvidenceCorrectionRequest,
    EvidenceCoverageResponse,
    EvidenceItemCreateRequest,
    EvidenceItemResponse,
    EvidencePassportBundle,
    EvidenceRevalidateResponse,
    ExportRequest,
    ExportResponse,
    ImportJobCreate,
    JobResponse,
    MLRankingRequest,
    MLRankingResponse,
    PaperGroupDetail,
    PaperGroupSummary,
    PicoOverrideRequest,
    QueryASTNode,
    QueryVersionCreate,
    QueryVersionResponse,
    RadarConfirmRequest,
    RadarCorrectRequest,
    DevilsAdvocateChallengeResponse,
    DevilsAdvocateDashboardResponse,
    DevilsAdvocateDispositionRequest,
    DevilsAdvocateGenerateRequest,
    DuplicateGroupGenealogyResponse,
    DuplicateReconcileRequest,
    DuplicateReverseMergeRequest,
    DuplicateSplitRequest,
    DuplicateWorkspaceSummaryResponse,
    RadarFlagConflictRequest,
    RadarFlagUncertainRequest,
    ReviewEventResponse,
    ReviewRadarResponse,
    ScreeningRankRequest,
    ScreeningRankResponse,
    SearchEvolutionDiffResponse,
    SearchEvolutionVersionSummary,
    SearchExecutionCreate,
    SearchExecutionResponse,
    SearchRestoreRequest,
    SearchRestoreResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)
from app.db.models import (
    CorpusRevisionModel,
    CriteriaVersionModel,
    ExportModel,
    QueryVersionModel,
    SearchExecutionModel,
    WorkspaceModel,
)
from app.db.session import get_db
from app.ml_feature.service import execute_ml_ranking
from app.services.workspace_state import (
    dashboard_summaries,
    latest_query_version,
    list_executions,
    list_jobs,
    set_execution_selection,
)
from app.services.corpus import (
    get_paper_group_detail,
    list_paper_groups_in_revision,
)
from app.services.evidence_passport import (
    apply_reviewer_correction,
    create_manual_evidence_item,
    export_evidence_passport_csv,
    get_paper_group_evidence_bundle,
    get_workspace_evidence_coverage,
    revalidate_group_evidence,
)
from app.services.exports import export_corpus_studies
from app.services.imports import trigger_import
from app.services.jobs import (
    cancel_job,
    get_job_by_id,
    queue_corpus_processing,
    recover_stuck_jobs,
    to_job_response,
)
from app.worker import _get_worker_session, run_worker_daemon
from app.services.genealogy import (
    get_duplicate_group_genealogy,
    get_workspace_duplicate_overview,
    reconcile_duplicate_conflict,
    reverse_merge_event,
    split_duplicate_group,
)
from app.services.devils_advocate import (
    get_or_generate_challenge,
    get_workspace_challenge_dashboard,
    record_challenge_disposition,
)
from app.services.radar import (
    confirm_radar_field,
    correct_radar_field,
    flag_conflict_radar_field,
    flag_uncertain_radar_field,
    get_or_sync_article_radar,
    get_review_level_radar,
    revalidate_radar_field,
)
from app.services.review_decisions import (
    record_dedup_override,
    record_screening_decision,
    resolve_group_conflict,
    save_pico_annotations,
)
from app.services.screening_rank import rank_screening_groups
from app.services.search_evolution import (
    compute_search_evolution_diff,
    get_search_version_detail,
    list_search_versions,
    restore_search_configuration,
)
from app.services.snapshots import (
    compute_corpus_diff,
)
from app.services.snapshots import (
    restore_corpus_snapshot as svc_restore_corpus_snapshot,
)
from app.auth import (
    LOCAL_USER_ID,
    SessionAuthMiddleware,
    accounts_enabled,
    auth_router,
    current_user_id,
    get_or_create_local_user,
)
from app.services.access import enforce_review_access
from app.settings import settings
from app.sources.errors import SourceUnavailableError, describe_source_error
from app.sources.europepmc import EuropePMCAdapter
from app.sources.pubmed import PubMedAdapter
from app.sources.translator import translate_query

logger = logging.getLogger(__name__)

_worker_thread: threading.Thread | None = None
_worker_stop_event: threading.Event | None = None
_worker_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_thread, _worker_stop_event
    if settings.run_worker_in_process:
        try:
            workers_count = int(os.environ.get("WORKERS", "1"))
        except ValueError:
            workers_count = 1

        if workers_count > 1:
            logger.warning(
                "WORKERS is set to %d (> 1). In-process worker is active; "
                "in-process mode requires WORKERS=1 for a single worker instance.",
                workers_count,
            )

        with _worker_lock:
            if _worker_thread is None or not _worker_thread.is_alive():
                # 1. Recover any stuck RUNNING jobs after container/worker restart
                session, should_close = _get_worker_session()
                try:
                    recovered = recover_stuck_jobs(session)
                    if recovered > 0:
                        logger.info("Recovered %d stuck RUNNING jobs on startup", recovered)
                except Exception:
                    logger.exception("Failed to recover stuck jobs on startup")
                finally:
                    if should_close:
                        session.close()

                # 2. Start worker daemon in background thread
                _worker_stop_event = threading.Event()
                _worker_thread = threading.Thread(
                    target=run_worker_daemon,
                    kwargs={"poll_interval": 0.5, "stop_event": _worker_stop_event},
                    name="evidra-in-process-worker",
                    daemon=True,
                )
                _worker_thread.start()
                logger.info("Started in-process background worker thread")

    yield

    with _worker_lock:
        if _worker_stop_event is not None:
            logger.info("Signaling in-process background worker to stop...")
            _worker_stop_event.set()
        if _worker_thread is not None and _worker_thread.is_alive():
            _worker_thread.join(timeout=5.0)
            if _worker_thread.is_alive():
                logger.warning("In-process background worker thread did not stop within 5s timeout")
            else:
                logger.info("In-process background worker thread stopped cleanly")
        _worker_thread = None
        _worker_stop_event = None


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Deterministic and AI-augmented systematic literature review engine REST API.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    dependencies=[Depends(enforce_review_access)],
)

# User sessions (AUTH_MODE=accounts; no-op in local mode). Added before CORS so CORS stays outermost.
app.add_middleware(SessionAuthMiddleware)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Standardized error envelope for HTTP exceptions."""
    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
    elif exc.status_code == status.HTTP_409_CONFLICT:
        code = "STALE_VERSION_CONFLICT"
    elif exc.status_code == status.HTTP_501_NOT_IMPLEMENTED:
        code = "NOT_IMPLEMENTED"

    envelope = ErrorEnvelope(
        code=code,
        message=str(exc.detail),
        retryable=exc.status_code >= 500 and exc.status_code != 501,
        details=None,
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())


@app.exception_handler(SourceUnavailableError)
async def source_unavailable_handler(request: Request, exc: SourceUnavailableError) -> JSONResponse:
    """A literature source is down or slow: a plain 502 the reviewer can read, safe to retry."""
    envelope = ErrorEnvelope(code="SOURCE_UNAVAILABLE", message=str(exc), retryable=True, details=None)
    return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=envelope.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Standardized error envelope for Pydantic validation failures."""
    details = []
    for err in exc.errors():
        loc = " -> ".join(str(x) for x in err.get("loc", []))
        details.append(ErrorDetail(field=loc, message=err.get("msg", "Invalid value"), type=err.get("type")))

    envelope = ErrorEnvelope(
        code="VALIDATION_ERROR",
        message="Request payload failed contract schema validation",
        retryable=False,
        details=details,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=envelope.model_dump())


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get(
    "/health/live",
    tags=["Health"],
    summary="Liveness probe",
    response_model=dict[str, Any],
)
def health_live() -> dict[str, Any]:
    """Check if the process is alive."""
    return {
        "status": "ok",
        "app": settings.app_title,
        "version": settings.app_version,
        "env": settings.app_env,
    }


@app.get(
    "/health/ready",
    tags=["Health"],
    summary="Readiness probe",
    response_model=dict[str, Any],
    responses={
        200: {"description": "Service, database, migrations, and disk ready"},
        503: {"model": ErrorEnvelope, "description": "Service readiness check failed"},
    },
)
def health_ready(db: Session = Depends(get_db)) -> JSONResponse:  # noqa: B008
    """Check if the application, SQLite database, migrations, and storage are ready to serve."""
    try:
        # 1. Database connectivity
        db.execute(text("SELECT 1")).scalar()

        # 2. Migration version verification
        migration_version = None
        try:
            row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            if row:
                migration_version = row[0]
        except Exception:  # noqa: BLE001
            migration_version = None

        # 3. Disk space check (ensure at least 10MB free)
        target_path = settings.data_dir if settings.data_dir.exists() else Path(".")
        disk = shutil.disk_usage(target_path)
        min_required_bytes = 10 * 1024 * 1024  # 10 MB
        if disk.free < min_required_bytes:
            envelope = ErrorEnvelope(
                code="DISK_SPACE_EXHAUSTED",
                message=f"Insufficient free disk space: {disk.free} bytes available (minimum required: {min_required_bytes})",
                retryable=True,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=envelope.model_dump(),
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "database": "connected",
                "migration_version": migration_version,
                "disk_free_bytes": disk.free,
                "llm_enabled": settings.llm_enabled,
                "rag_enabled": settings.rag_enabled,
            },
        )
    except Exception as exc:  # noqa: BLE001
        envelope = ErrorEnvelope(
            code="SERVICE_UNAVAILABLE",
            message=f"Service readiness check failed: {exc}",
            retryable=True,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=envelope.model_dump(),
        )


# ============================================================================
# API v1 Endpoints (Declared Contracts & Stubs)
# ============================================================================


@app.get(
    "/api/v1/capabilities",
    tags=["Capabilities"],
    summary="Get runtime system capabilities and feature flags",
    response_model=CapabilitiesResponse,
    responses={
        200: {"model": CapabilitiesResponse, "description": "Runtime system capabilities"},
    },
)
def get_capabilities() -> CapabilitiesResponse:
    """Return runtime system capabilities (safe public boolean flags from settings)."""
    from app.gateway.adapter import HTTPXModelAdapter

    return CapabilitiesResponse(
        # On only when it is switched on AND a key is set; otherwise the UI says it is off
        llm_enabled=bool(settings.llm_enabled) and HTTPXModelAdapter(default_model=settings.llm_model_alias).is_enabled(),
        rag_enabled=bool(settings.rag_enabled),
    )


def stub_not_implemented(operation_name: str) -> None:
    """Raise structured 501 for endpoints planned in future developer tasks."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Operation '{operation_name}' is declared in contracts and will be implemented in a subsequent merge.",
    )


@app.post(
    "/api/v1/workspaces",
    tags=["Workspaces"],
    summary="Create a review workspace",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    payload: WorkspaceCreate,
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
) -> WorkspaceResponse:
    """Create a new review workspace owned by the signed-in user."""
    user_id = current_user_id(request)
    if user_id == LOCAL_USER_ID:
        get_or_create_local_user(db)
    workspace = WorkspaceModel(
        title=payload.title,
        description=payload.description,
        created_by=user_id or "reviewer_local",
        owner_user_id=user_id,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace)


@app.get(
    "/api/v1/workspaces",
    tags=["Workspaces"],
    summary="List review workspaces",
    response_model=list[WorkspaceResponse],
)
def list_workspaces(request: Request, db: Session = Depends(get_db)) -> list[WorkspaceResponse]:  # noqa: B008
    """List the signed-in user's reviews, newest first (every review in local mode)."""
    query = db.query(WorkspaceModel)
    if accounts_enabled():
        query = query.filter(WorkspaceModel.owner_user_id == current_user_id(request))
    workspaces = query.order_by(WorkspaceModel.created_at.desc()).all()
    return [WorkspaceResponse.model_validate(ws) for ws in workspaces]


@app.get(
    "/api/v1/dashboard",
    tags=["Workspaces"],
    summary="The signed-in user's reviews with screening progress",
    response_model=list[DashboardReviewSummary],
)
def get_dashboard(request: Request, db: Session = Depends(get_db)) -> list[DashboardReviewSummary]:  # noqa: B008
    """Dashboard cards: each review's question, record counts and decision progress."""
    query = db.query(WorkspaceModel)
    if accounts_enabled():
        query = query.filter(WorkspaceModel.owner_user_id == current_user_id(request))
    return dashboard_summaries(db, query.order_by(WorkspaceModel.created_at.desc()).all())


@app.get(
    "/api/v1/workspaces/{workspace_id}/queries/latest",
    tags=["Queries"],
    summary="Latest saved query version",
    response_model=QueryVersionResponse,
)
def get_latest_query_version(workspace_id: str, db: Session = Depends(get_db)) -> QueryVersionResponse:  # noqa: B008
    """Return the most recently saved search so the query builder can resume it."""
    return latest_query_version(db, workspace_id)


@app.get(
    "/api/v1/workspaces/{workspace_id}/executions",
    tags=["Queries"],
    summary="Search counts for a query version",
    response_model=list[SearchExecutionResponse],
)
def list_workspace_executions(
    workspace_id: str,
    query_version_id: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[SearchExecutionResponse]:
    """Search counts (with import ticks) for the given or latest query version, newest first."""
    return list_executions(db, workspace_id, query_version_id)


@app.patch(
    "/api/v1/executions/{execution_id}",
    tags=["Queries"],
    summary="Tick or untick a search count for import",
    response_model=SearchExecutionResponse,
)
def update_execution_selection(
    execution_id: str,
    payload: SearchExecutionSelectionUpdate,
    db: Session = Depends(get_db),  # noqa: B008
) -> SearchExecutionResponse:
    """Persist whether this search count is selected for the next import."""
    return set_execution_selection(db, execution_id, payload.selected_for_import)


@app.get(
    "/api/v1/workspaces/{workspace_id}/jobs",
    tags=["Jobs"],
    summary="Recent background jobs for a review",
    response_model=list[JobResponse],
)
def list_workspace_jobs(
    workspace_id: str,
    kind: JobKind | None = None,
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),  # noqa: B008
) -> list[JobResponse]:
    """Newest jobs first, optionally of one kind, so progress survives a reload."""
    return list_jobs(db, workspace_id, kind, limit)


@app.post(
    "/api/v1/workspaces/{workspace_id}/criteria",
    tags=["Criteria"],
    summary="Save a new criteria version",
    response_model=CriteriaVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_criteria_version(
    workspace_id: str,
    payload: CriteriaVersionCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> CriteriaVersionResponse:
    """Save immutable review question and inclusion/exclusion criteria version."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    last_crit = (
        db.query(CriteriaVersionModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(CriteriaVersionModel.sequence.desc())
        .first()
    )
    seq = (last_crit.sequence + 1) if last_crit else 1

    pico_json = json.dumps(payload.pico_description, sort_keys=True)
    criteria_json = json.dumps([c.model_dump() for c in payload.criteria], sort_keys=True)
    content_hash = hashlib.sha256(f"{payload.question}\n{pico_json}\n{criteria_json}".encode()).hexdigest()

    crit_model = CriteriaVersionModel(
        workspace_id=workspace_id,
        sequence=seq,
        question=payload.question,
        pico_json=pico_json,
        criteria_json=criteria_json,
        content_hash=content_hash,
    )
    db.add(crit_model)
    db.commit()
    db.refresh(crit_model)

    return CriteriaVersionResponse(
        id=crit_model.id,
        workspace_id=crit_model.workspace_id,
        sequence=crit_model.sequence,
        question=crit_model.question,
        pico_description=payload.pico_description,
        criteria=payload.criteria,
        content_hash=crit_model.content_hash,
        created_at=crit_model.created_at,
    )


@app.get(
    "/api/v1/workspaces/{workspace_id}/criteria",
    tags=["Criteria"],
    summary="Get the latest saved criteria version",
    response_model=CriteriaVersionResponse,
)
def get_latest_criteria_version(
    workspace_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> CriteriaVersionResponse:
    """Return the newest saved criteria version so the UI can resume without re-saving."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    crit = (
        db.query(CriteriaVersionModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(CriteriaVersionModel.sequence.desc())
        .first()
    )
    if not crit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No criteria version saved yet for workspace '{workspace_id}'",
        )

    return CriteriaVersionResponse(
        id=crit.id,
        workspace_id=crit.workspace_id,
        sequence=crit.sequence,
        question=crit.question,
        pico_description=json.loads(crit.pico_json),
        criteria=[CriterionDefinition(**c) for c in json.loads(crit.criteria_json)],
        content_hash=crit.content_hash,
        created_at=crit.created_at,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/criteria/suggest",
    tags=["Criteria"],
    summary="Suggest screening rules from the review question and PICO",
    response_model=CriteriaSuggestResponse,
)
def suggest_criteria(
    workspace_id: str,
    payload: CriteriaSuggestRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> CriteriaSuggestResponse:
    """Build screening rules from the PICO. Nothing is saved; the reviewer edits and saves them.

    Fully deterministic unless AI is enabled, in which case synonym keywords may be added to the
    population and intervention rules (marked as AI-suggested). AI failure never blocks the rules.
    """
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    from app.gateway.synonyms import build_synonym_provider
    from app.screening.generate import rules_from_pico

    provider, _ = build_synonym_provider()
    rules = rules_from_pico(ws.title, payload.question, payload.pico, synonyms=provider)
    used = any(r.ai_suggested_keywords for r in rules)
    notice = None
    if provider is not None and not used and provider.problems:
        notice = f"AI synonyms were skipped: {provider.problems[0]}"
    return CriteriaSuggestResponse(criteria=rules, ai_synonyms_used=used, notice=notice)


@app.post(
    "/api/v1/workspaces/{workspace_id}/queries",
    tags=["Queries"],
    summary="Save a new query version",
    response_model=QueryVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_query_version(
    workspace_id: str,
    payload: QueryVersionCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> QueryVersionResponse:
    """Save an immutable structured search query version."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    crit = db.query(CriteriaVersionModel).filter_by(id=payload.criteria_version_id, workspace_id=workspace_id).first()
    if not crit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Associated criteria version '{payload.criteria_version_id}' not found in workspace",
        )

    last_q = (
        db.query(QueryVersionModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(QueryVersionModel.sequence.desc())
        .first()
    )
    seq = (last_q.sequence + 1) if last_q else 1

    ast_json = json.dumps(payload.ast.model_dump(), sort_keys=True)
    sources_json = json.dumps([s.value for s in payload.sources], sort_keys=True)
    content_hash = hashlib.sha256(
        f"{ast_json}\n{payload.start_date}\n{payload.end_date}\n{sources_json}".encode()
    ).hexdigest()

    query_model = QueryVersionModel(
        workspace_id=workspace_id,
        parent_id=payload.parent_id,
        sequence=seq,
        ast_json=ast_json,
        start_date=payload.start_date,
        end_date=payload.end_date,
        sources_json=sources_json,
        criteria_version_id=payload.criteria_version_id,
        content_hash=content_hash,
        change_description=payload.change_description,
        restored_from_version_id=payload.restored_from_version_id,
    )
    db.add(query_model)
    db.commit()
    db.refresh(query_model)

    return QueryVersionResponse(
        id=query_model.id,
        workspace_id=query_model.workspace_id,
        parent_id=query_model.parent_id,
        sequence=query_model.sequence,
        ast=payload.ast,
        start_date=query_model.start_date,
        end_date=query_model.end_date,
        sources=payload.sources,
        criteria_version_id=query_model.criteria_version_id,
        content_hash=query_model.content_hash,
        change_description=query_model.change_description,
        restored_from_version_id=query_model.restored_from_version_id,
        created_at=query_model.created_at,
    )


@app.post(
    "/api/v1/queries/{query_id}/searches",
    tags=["Queries"],
    summary="Execute search count acquisition",
    response_model=SearchExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def execute_search_count(
    query_id: str,
    payload: SearchExecutionCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> SearchExecutionResponse:
    """Trigger count-only query acquisition from literature provider."""
    q_row = db.query(QueryVersionModel).filter_by(id=query_id).first()
    if not q_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query version '{query_id}' not found",
        )

    ast_node = QueryASTNode.model_validate_json(q_row.ast_json)
    exact_query = translate_query(
        source=payload.source,
        ast=ast_node,
        start_date=q_row.start_date,
        end_date=q_row.end_date,
        synonym_expansion=payload.synonym_expansion,
    )

    if payload.source in (SourceNamespace.PUBMED, SourceNamespace.EUROPEPMC):
        try:
            if payload.source == SourceNamespace.PUBMED:
                res = PubMedAdapter().search_count(q_row.id, exact_query, payload.cap)
            else:
                res = EuropePMCAdapter().search_count(q_row.id, exact_query, payload.synonym_expansion, payload.cap)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("Count on %s failed: %s", payload.source.value, type(exc).__name__)
            raise SourceUnavailableError(payload.source.value, describe_source_error(exc)) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported source namespace '{payload.source}'",
        )

    # Execution ids are deterministic per query version and translated query, so counting the
    # same saved query again returns the recorded execution instead of failing on a duplicate id.
    existing = db.get(SearchExecutionModel, res.id)
    if existing is not None:
        return SearchExecutionResponse.model_validate(existing)

    exec_model = SearchExecutionModel(
        id=res.id,
        query_version_id=q_row.id,
        source=res.source.value,
        exact_query=res.exact_query,
        synonym_setting=res.synonym_setting,
        hit_count=res.hit_count,
        counted_at=res.counted_at,
        status=res.status.value,
        partial=res.partial,
        cap=res.cap,
        raw_hash=res.raw_hash,
        # Nothing found means nothing to import: never tick a 0-hit count
        selected_for_import=res.hit_count > 0,
    )
    db.add(exec_model)
    db.commit()
    db.refresh(exec_model)
    return res.model_copy(update={"selected_for_import": exec_model.selected_for_import})


@app.post(
    "/api/v1/workspaces/{workspace_id}/imports",
    tags=["Ingestion"],
    summary="Trigger approved record import job",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_import_job(
    workspace_id: str,
    payload: ImportJobCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> JobResponse:
    """Queue durable literature import job for approved search executions."""
    return trigger_import(db, workspace_id, payload)


@app.get(
    "/api/v1/jobs/{job_id}",
    tags=["Jobs"],
    summary="Get background job status",
    response_model=JobResponse,
)
def get_job_status(job_id: str, db: Session = Depends(get_db)) -> JobResponse:  # noqa: B008
    """Poll status, stage, progress, and errors for a background job."""
    job = get_job_by_id(db, job_id)
    return to_job_response(job)


@app.post(
    "/api/v1/jobs/{job_id}/cancel",
    tags=["Jobs"],
    summary="Cancel running or queued background job",
    response_model=JobResponse,
)
def cancel_job_endpoint(job_id: str, db: Session = Depends(get_db)) -> JobResponse:  # noqa: B008
    """Cancel background job execution safely."""
    job = cancel_job(db, job_id)
    return to_job_response(job)


@app.get(
    "/api/v1/workspaces/{workspace_id}/revisions",
    tags=["Corpus"],
    summary="List published corpus revisions",
    response_model=list[CorpusRevisionResponse],
)
def list_corpus_revisions(workspace_id: str, db: Session = Depends(get_db)) -> list[CorpusRevisionResponse]:  # noqa: B008
    """List historical immutable corpus snapshots."""
    revs = (
        db.query(CorpusRevisionModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(CorpusRevisionModel.created_at.desc())
        .all()
    )
    return [
        CorpusRevisionResponse(
            id=r.id,
            workspace_id=r.workspace_id,
            parent_id=r.parent_id,
            criteria_version_id=r.criteria_version_id,
            dedup_version=r.dedup_version,
            state=CorpusRevisionState(r.state),
            published_at=r.published_at,
            decision_seq_cutoff=r.decision_seq_cutoff,
            fingerprint=r.fingerprint,
            group_count=r.group_count,
            record_count=r.record_count,
        )
        for r in revs
    ]


@app.post(
    "/api/v1/workspaces/{workspace_id}/process-corpus",
    tags=["Corpus"],
    summary="Queue deduplication, screening, and PICO extraction",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_process_corpus(
    workspace_id: str,
    criteria_version_id: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008
) -> JobResponse:
    """Queue processing of the imported records and return the job to poll (GET /jobs/{id}).

    Screens with ``criteria_version_id`` when given, else the newest saved criteria version.
    The job's stage reads "queued", "processing", then "done".
    """
    if not db.query(WorkspaceModel.id).filter_by(id=workspace_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workspace '{workspace_id}' not found")
    if criteria_version_id and not db.query(CriteriaVersionModel.id).filter_by(
        id=criteria_version_id, workspace_id=workspace_id
    ).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Criteria version '{criteria_version_id}' not found",
        )
    job = queue_corpus_processing(db, workspace_id, criteria_version_id=criteria_version_id, trigger="manual")
    return to_job_response(job)


@app.get(
    "/api/v1/revisions/{revision_id}/groups",
    tags=["Review"],
    summary="List deduplicated paper groups in revision",
    response_model=list[PaperGroupSummary],
)
def list_paper_groups(
    revision_id: str,
    status_filter: EffectiveDecisionState | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[PaperGroupSummary]:
    """List paginated deduplicated paper groups for screening workbench (Implemented in D03)."""
    return list_paper_groups_in_revision(
        db=db,
        revision_id=revision_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/v1/groups/{group_id}",
    tags=["Review"],
    summary="Get paper group detail with members and evidence",
    response_model=PaperGroupDetail,
)
def get_paper_group(
    group_id: str,
    revision_id: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008
) -> PaperGroupDetail:
    """Retrieve full group detail, member revisions, screening evidence, and PICO spans (Implemented in D03)."""
    return get_paper_group_detail(db=db, group_id=group_id, revision_id=revision_id)


@app.post(
    "/api/v1/groups/{group_id}/decisions",
    tags=["Review"],
    summary="Record reviewer eligibility decision",
    response_model=ReviewEventResponse,
)
def record_screening_decision_route(
    group_id: str,
    payload: DecisionCommand,
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewEventResponse:
    """Append a human include/exclude/maybe decision event with optimistic concurrency (Implemented in D03)."""
    return record_screening_decision(db=db, group_id=group_id, command=payload)


@app.post(
    "/api/v1/groups/{group_id}/pico",
    tags=["Review"],
    summary="Override or save verified PICO spans",
    response_model=ReviewEventResponse,
)
def save_pico_annotations_route(
    group_id: str,
    payload: PicoOverrideRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewEventResponse:
    """Save verified PICO offsets bound to immutable text revision (Implemented in D03)."""
    return save_pico_annotations(db=db, group_id=group_id, request=payload)


@app.post(
    "/api/v1/workspaces/{workspace_id}/dedup-decisions",
    tags=["Review"],
    summary="Confirm or reject deduplication candidate pair",
    response_model=ReviewEventResponse,
)
def record_dedup_override_route(
    workspace_id: str,
    payload: DedupOverrideRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewEventResponse:
    """Confirm duplicate group merge or record cannot-link constraint (Implemented in D03)."""
    return record_dedup_override(db=db, workspace_id=workspace_id, request=payload)


@app.post(
    "/api/v1/conflicts/{conflict_id}/resolve",
    tags=["Review"],
    summary="Resolve group merge conflict",
    response_model=ReviewEventResponse,
)
def resolve_group_conflict_route(
    conflict_id: str,
    payload: ConflictResolveRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewEventResponse:
    """Manually resolve an inherited screening divergence on merged groups (Implemented in D03/D05)."""
    return resolve_group_conflict(db=db, conflict_id=conflict_id, request=payload)


@app.get(
    "/api/v1/revisions/{revision_id}/diff",
    tags=["Corpus"],
    summary="Diff two corpus snapshots",
    response_model=CorpusDiffResponse,
)
def diff_corpus_revisions(
    revision_id: str,
    base_revision_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> CorpusDiffResponse:
    """Calculate diff between two corpus snapshots (Implemented in D05)."""
    return compute_corpus_diff(db=db, base_revision_id=base_revision_id, target_revision_id=revision_id)


@app.post(
    "/api/v1/workspaces/{workspace_id}/restore",
    tags=["Corpus"],
    summary="Restore exact historical snapshot",
    response_model=CorpusRevisionResponse,
)
def restore_corpus_snapshot(
    workspace_id: str,
    snapshot_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> CorpusRevisionResponse:
    """Restore exact historical corpus snapshot without re-fetching APIs (Implemented in D05)."""
    return svc_restore_corpus_snapshot(
        db=db,
        workspace_id=workspace_id,
        snapshot_id=snapshot_id,
    )


@app.post(
    "/api/v1/revisions/{revision_id}/exports",
    tags=["Export"],
    summary="Export included studies",
    response_model=ExportResponse,
)
def export_included_studies_route(
    revision_id: str,
    payload: ExportRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ExportResponse:
    """Generate sanitized CSV/RIS export of included studies with audit provenance (Implemented in D03/D04)."""
    return export_corpus_studies(db=db, revision_id=revision_id, export_format=payload.format)


@app.get(
    "/api/v1/exports/{export_id}/download",
    tags=["Export"],
    summary="Download sanitized export file",
)
def download_export_file(export_id: str, db: Session = Depends(get_db)):  # noqa: B008
    """Download generated sanitized export CSV file."""
    exp = db.query(ExportModel).filter_by(id=export_id).first()
    if not exp or not os.path.exists(exp.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")
    return FileResponse(
        path=exp.file_path,
        media_type="text/csv",
        filename=f"evidra_export_{export_id}.csv",
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/screening/rank",
    tags=["Screening"],
    summary="Compute ML-prioritized screening order",
    response_model=ScreeningRankResponse,
)
def get_screening_rank(
    workspace_id: str,
    payload: ScreeningRankRequest | None = None,
    db: Session = Depends(get_db),  # noqa: B008
) -> ScreeningRankResponse:
    """Compute ML-prioritized screening order for workbench triage without automatic exclusions."""
    req = payload or ScreeningRankRequest()
    return rank_screening_groups(db=db, workspace_id=workspace_id, request=req)


@app.post(
    "/api/v1/workspaces/{workspace_id}/revisions/{revision_id}/ml-ranking",
    tags=["Machine Learning"],
    summary="Compute ML review prioritization for corpus revision",
    response_model=MLRankingResponse,
    responses={
        200: {"model": MLRankingResponse, "description": "Computed or cached ML prioritized ranking"},
        404: {"model": ErrorEnvelope, "description": "Workspace or corpus revision not found"},
        413: {"model": ErrorEnvelope, "description": "Corpus revision too large"},
    },
)
def compute_ml_ranking(
    workspace_id: str,
    revision_id: str,
    payload: MLRankingRequest | None = None,
    db: Session = Depends(get_db),  # noqa: B008
) -> MLRankingResponse:
    """Compute, cache, or retrieve prioritized screening queue using verified scikit-learn model."""
    req = payload or MLRankingRequest()
    return execute_ml_ranking(
        db=db,
        workspace_id=workspace_id,
        revision_id=revision_id,
        request=req,
    )


@app.get(
    "/api/v1/workspaces/{workspace_id}/revisions/{revision_id}/ml-ranking",
    tags=["Machine Learning"],
    summary="Get ML review prioritization for corpus revision",
    response_model=MLRankingResponse,
    responses={
        200: {"model": MLRankingResponse, "description": "Prioritized ranking order"},
        404: {"model": ErrorEnvelope, "description": "Workspace or corpus revision not found"},
    },
)
def get_ml_ranking(
    workspace_id: str,
    revision_id: str,
    limit: int = 100,
    offset: int = 0,
    force_recompute: bool = False,
    db: Session = Depends(get_db),  # noqa: B008
) -> MLRankingResponse:
    """Get paginated ML-prioritized queue for a corpus revision."""
    req = MLRankingRequest(limit=limit, offset=offset, force_recompute=force_recompute)
    return execute_ml_ranking(
        db=db,
        workspace_id=workspace_id,
        revision_id=revision_id,
        request=req,
    )



@app.post(
    "/api/v1/workspaces/{workspace_id}/assistant",
    tags=["Assistant"],
    summary="Query bounded RAG assistant",
    response_model=AssistantProposal,
    responses={
        200: {"model": AssistantProposal, "description": "Structured assistant proposal with citations"},
        503: {"model": ErrorEnvelope, "description": "Assistant feature disabled by runtime configuration"},
    },
)
def query_assistant(
    workspace_id: str,
    payload: AssistantRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> AssistantProposal:
    """Query bounded corpus assistant for explainable screening or PICO proposals (Implemented in C06)."""
    if not settings.llm_enabled and not settings.rag_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Operation 'query_assistant' is disabled by default runtime configuration. Configure LLM_ENABLED=true to activate.",
        )

    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # Resolve latest published corpus revision for workspace
    rev = (
        db.query(CorpusRevisionModel)
        .filter_by(workspace_id=workspace_id, state=CorpusRevisionState.PUBLISHED.value)
        .order_by(CorpusRevisionModel.created_at.desc())
        .first()
    )
    if not rev:
        rev = (
            db.query(CorpusRevisionModel)
            .filter_by(workspace_id=workspace_id)
            .order_by(CorpusRevisionModel.created_at.desc())
            .first()
        )
    if not rev:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace '{workspace_id}' has no corpus revision to query",
        )

    from app.gateway.adapter import HTTPXModelAdapter
    from app.services.evidence import SqliteEvidenceRepository
    from app.workflows.assistant import BoundedEvidenceAssistant

    # The key and model come from settings (server side only); with no key the adapter reports AI
    # as disabled and the assistant answers from the paper's own text.
    assistant = BoundedEvidenceAssistant(
        retrieval_repo=SqliteEvidenceRepository(db),
        gateway=HTTPXModelAdapter(default_model=settings.llm_model_alias),
        model_alias=settings.llm_model_alias,
    )
    return assistant.answer_query(
        workspace_id=workspace_id,
        corpus_revision_id=rev.id,
        request=payload,
    )


# ============================================================================
# Single-Host Production SPA Static Files Mount (A06 Packaging)
# ============================================================================



# ============================================================================
# Evidence Passport Routes
# ============================================================================

@app.get(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/evidence",
    tags=["Evidence Passport"],
    summary="Get complete Evidence Passport for paper group",
    response_model=EvidencePassportBundle,
)
def get_group_evidence_passport_route(
    workspace_id: str,
    group_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> EvidencePassportBundle:
    """Retrieve all evidence-backed claims, quotations, offsets, and summary metrics for a study."""
    return get_paper_group_evidence_bundle(db=db, workspace_id=workspace_id, group_id=group_id)


@app.post(
    "/api/v1/workspaces/{workspace_id}/evidence/{evidence_id}/correct",
    tags=["Evidence Passport"],
    summary="Submit reviewer correction for evidence claim",
    response_model=EvidenceItemResponse,
)
def correct_evidence_item_route(
    workspace_id: str,
    evidence_id: str,
    payload: EvidenceCorrectionRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> EvidenceItemResponse:
    """Correct claim or evidence passage with backend verification and audit trail preservation."""
    return apply_reviewer_correction(db=db, workspace_id=workspace_id, evidence_id=evidence_id, payload=payload)


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/evidence",
    tags=["Evidence Passport"],
    summary="Create manual evidence claim",
    response_model=EvidenceItemResponse,
)
def create_evidence_item_route(
    workspace_id: str,
    group_id: str,
    payload: EvidenceItemCreateRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> EvidenceItemResponse:
    """Add a new evidence-backed claim with deterministic quote validation."""
    return create_manual_evidence_item(db=db, workspace_id=workspace_id, group_id=group_id, payload=payload)


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/evidence/revalidate",
    tags=["Evidence Passport"],
    summary="Revalidate all evidence claims for a paper group",
    response_model=EvidenceRevalidateResponse,
)
def revalidate_paper_evidence_route(
    workspace_id: str,
    group_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> EvidenceRevalidateResponse:
    """Revalidate quotations and offsets against current source text revision."""
    return revalidate_group_evidence(db=db, workspace_id=workspace_id, group_id=group_id)


@app.get(
    "/api/v1/workspaces/{workspace_id}/evidence/summary",
    tags=["Evidence Passport"],
    summary="Get review-wide evidence transparency metrics",
    response_model=EvidenceCoverageResponse,
)
def get_evidence_summary_route(
    workspace_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> EvidenceCoverageResponse:
    """Retrieve workspace-wide evidence coverage, verified quote rates, and review workload."""
    return get_workspace_evidence_coverage(db=db, workspace_id=workspace_id)


@app.get(
    "/api/v1/workspaces/{workspace_id}/evidence/export",
    tags=["Evidence Passport"],
    summary="Export Evidence Passport as formula-injection-safe CSV",
)
def export_evidence_csv_route(
    workspace_id: str,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Download formula-injection sanitized CSV of all workspace evidence claims."""
    from fastapi.responses import Response
    csv_data = export_evidence_passport_csv(db=db, workspace_id=workspace_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=evidence_passport_{workspace_id}.csv",
        },
    )


@app.get(
    "/api/v1/workspaces/{workspace_id}/search-versions",
    tags=["Search Evolution"],
    summary="List workspace search versions with timeline summaries and executed provider counts",
    response_model=list[SearchEvolutionVersionSummary],
)
def list_workspace_search_versions(
    workspace_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[SearchEvolutionVersionSummary]:
    """Retrieve versioned timeline of search strategies, counts, and screening metrics."""
    return list_search_versions(db=db, workspace_id=workspace_id)


@app.get(
    "/api/v1/workspaces/{workspace_id}/search-versions/{version_id}",
    tags=["Search Evolution"],
    summary="Get detailed summary and execution history for a single search version",
    response_model=SearchEvolutionVersionSummary,
)
def get_workspace_search_version(
    workspace_id: str,
    version_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> SearchEvolutionVersionSummary:
    """Get detailed execution metadata and counts for a specific search version."""
    return get_search_version_detail(db=db, workspace_id=workspace_id, version_id=version_id)


@app.get(
    "/api/v1/workspaces/{workspace_id}/search-versions/{target_version_id}/diff",
    tags=["Search Evolution"],
    summary="Compute 6-way diff between base search version and target search version",
    response_model=SearchEvolutionDiffResponse,
)
def diff_workspace_search_versions(
    workspace_id: str,
    target_version_id: str,
    base_version_id: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008
) -> SearchEvolutionDiffResponse:
    """Compare search versions across new, repeated, missing, changed, and conflicting records."""
    return compute_search_evolution_diff(
        db=db,
        workspace_id=workspace_id,
        target_version_id=target_version_id,
        base_version_id=base_version_id,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/search-versions/{version_id}/restore",
    tags=["Search Evolution"],
    summary="Safely restore a prior search query configuration into a new active version",
    response_model=SearchRestoreResponse,
    status_code=status.HTTP_201_CREATED,
)
def restore_workspace_search_version(
    workspace_id: str,
    version_id: str,
    payload: SearchRestoreRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> SearchRestoreResponse:
    """Restore historical search query strategy non-destructively without erasing reviewer decisions."""
    return restore_search_configuration(
        db=db,
        workspace_id=workspace_id,
        target_version_id=version_id,
        reason=payload.reason,
        actor_id=payload.actor_id,
    )


@app.get(
    "/api/v1/workspaces/{workspace_id}/pico-radar",
    tags=["Missing-Evidence Radar"],
    summary="Review-level PICO evidence coverage matrix and dimension metrics",
    response_model=ReviewRadarResponse,
)
def get_workspace_radar_overview(
    workspace_id: str,
    dimension_filter: str | None = None,
    status_filter: str | None = None,
    needs_review_only: bool = False,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewRadarResponse:
    """Retrieve comprehensive review-level PICO evidence matrix and dimension metrics."""
    return get_review_level_radar(
        db=db,
        workspace_id=workspace_id,
        dimension_filter=dimension_filter,
        status_filter=status_filter,
        needs_review_only=needs_review_only,
        query=query,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar",
    tags=["Missing-Evidence Radar"],
    summary="Article-level Missing-Evidence Radar for a paper group",
    response_model=ArticleRadarResponse,
)
def get_group_radar_detail(
    workspace_id: str,
    group_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> ArticleRadarResponse:
    """Get detailed 4-dimensional PICO evidence coverage, quotes, offsets, and review status."""
    return get_or_sync_article_radar(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        persist=False,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/confirm",
    tags=["Missing-Evidence Radar"],
    summary="Confirm an extracted PICO value as verified",
    response_model=ArticleRadarResponse,
)
def confirm_group_radar_field(
    workspace_id: str,
    group_id: str,
    field_type: str,
    payload: RadarConfirmRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ArticleRadarResponse:
    """Confirm extracted PICO value without changing study eligibility or screening decision."""
    return confirm_radar_field(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        field_type=field_type,
        payload=payload,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/correct",
    tags=["Missing-Evidence Radar"],
    summary="Submit human correction for a PICO element with audit history",
    response_model=ArticleRadarResponse,
)
def correct_group_radar_field(
    workspace_id: str,
    group_id: str,
    field_type: str,
    payload: RadarCorrectRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ArticleRadarResponse:
    """Record human correction with mandatory rationale while preserving original extraction."""
    return correct_radar_field(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        field_type=field_type,
        payload=payload,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/flag-uncertain",
    tags=["Missing-Evidence Radar"],
    summary="Flag a PICO field as uncertain or ambiguous",
    response_model=ArticleRadarResponse,
)
def flag_uncertain_group_radar_field(
    workspace_id: str,
    group_id: str,
    field_type: str,
    payload: RadarFlagUncertainRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ArticleRadarResponse:
    """Flag ambiguous or insufficient evidence to prioritize for human review."""
    return flag_uncertain_radar_field(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        field_type=field_type,
        payload=payload,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/flag-conflict",
    tags=["Missing-Evidence Radar"],
    summary="Flag conflicting evidence for a PICO field",
    response_model=ArticleRadarResponse,
)
def flag_conflict_group_radar_field(
    workspace_id: str,
    group_id: str,
    field_type: str,
    payload: RadarFlagConflictRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ArticleRadarResponse:
    """Flag conflicting evidence passages and route to reviewer conflict queue."""
    return flag_conflict_radar_field(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        field_type=field_type,
        payload=payload,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/pico-radar/{field_type}/revalidate",
    tags=["Missing-Evidence Radar"],
    summary="Revalidate an evidence field against current source text",
    response_model=ArticleRadarResponse,
)
def revalidate_group_radar_field(
    workspace_id: str,
    group_id: str,
    field_type: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> ArticleRadarResponse:
    """Check supporting quote and fingerprint against current stored text."""
    return revalidate_radar_field(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        field_type=field_type,
    )



# ============================================================================
# Devil's Advocate Reviewer Endpoints
# ============================================================================

@app.get(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/devils-advocate",
    response_model=DevilsAdvocateChallengeResponse,
    tags=["Devil's Advocate Reviewer"],
)
def get_group_devils_advocate_challenge(
    workspace_id: str,
    group_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> DevilsAdvocateChallengeResponse:
    """Retrieve the stored Devil's Advocate challenge for a paper group; never saves anything."""
    return get_or_generate_challenge(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        persist=False,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/devils-advocate/generate",
    response_model=DevilsAdvocateChallengeResponse,
    tags=["Devil's Advocate Reviewer"],
)
def generate_group_devils_advocate_challenge(
    workspace_id: str,
    group_id: str,
    payload: DevilsAdvocateGenerateRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> DevilsAdvocateChallengeResponse:
    """Request or force a fresh Devil's Advocate challenge assessment."""
    return get_or_generate_challenge(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        payload=payload,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/devils-advocate/disposition",
    response_model=DevilsAdvocateChallengeResponse,
    tags=["Devil's Advocate Reviewer"],
)
def record_group_challenge_disposition(
    workspace_id: str,
    group_id: str,
    payload: DevilsAdvocateDispositionRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> DevilsAdvocateChallengeResponse:
    """Record human reviewer response to a Devil's Advocate challenge (conceded, upheld, dismissed)."""
    return record_challenge_disposition(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        payload=payload,
    )


@app.get(
    "/api/v1/workspaces/{workspace_id}/devils-advocate",
    response_model=DevilsAdvocateDashboardResponse,
    tags=["Devil's Advocate Reviewer"],
)
def get_workspace_devils_advocate_dashboard(
    workspace_id: str,
    disposition: str | None = None,
    high_vulnerability_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),  # noqa: B008
) -> DevilsAdvocateDashboardResponse:
    """Retrieve review-level Devil's Advocate dashboard metrics and challenged exclusions ledger."""
    return get_workspace_challenge_dashboard(
        db=db,
        workspace_id=workspace_id,
        disposition_filter=disposition,
        high_vulnerability_only=high_vulnerability_only,
        limit=limit,
        offset=offset,
    )




# ============================================================================
# Duplicate Genealogy & Decision Reconciliation Endpoints
# ============================================================================

@app.get(
    "/api/v1/workspaces/{workspace_id}/duplicates",
    response_model=DuplicateWorkspaceSummaryResponse,
    tags=["Duplicate Genealogy & Reconciliation"],
)
def get_workspace_duplicates_overview(
    workspace_id: str,
    conflict_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),  # noqa: B008
) -> DuplicateWorkspaceSummaryResponse:
    """Retrieve workspace-wide overview of duplicate groups, conflicts, and candidate pairs."""
    return get_workspace_duplicate_overview(
        db=db,
        workspace_id=workspace_id,
        conflict_only=conflict_only,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/genealogy",
    response_model=DuplicateGroupGenealogyResponse,
    tags=["Duplicate Genealogy & Reconciliation"],
)
def get_duplicate_group_genealogy_endpoint(
    workspace_id: str,
    group_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> DuplicateGroupGenealogyResponse:
    """Retrieve comprehensive genealogy, pairwise match evidence, conflicts, and field provenance."""
    return get_duplicate_group_genealogy(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/reconcile",
    response_model=DuplicateGroupGenealogyResponse,
    tags=["Duplicate Genealogy & Reconciliation"],
)
def reconcile_duplicate_group_conflict(
    workspace_id: str,
    group_id: str,
    payload: DuplicateReconcileRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> DuplicateGroupGenealogyResponse:
    """Reconcile conflicting screening decisions across duplicate records with audited attribution."""
    return reconcile_duplicate_conflict(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        payload=payload,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/split",
    response_model=DuplicateGroupGenealogyResponse,
    tags=["Duplicate Genealogy & Reconciliation"],
)
def split_duplicate_group_endpoint(
    workspace_id: str,
    group_id: str,
    payload: DuplicateSplitRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> DuplicateGroupGenealogyResponse:
    """Safely split one or more records out of a duplicate group into an independent group."""
    return split_duplicate_group(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        payload=payload,
    )


@app.post(
    "/api/v1/workspaces/{workspace_id}/groups/{group_id}/reverse-merge",
    response_model=DuplicateGroupGenealogyResponse,
    tags=["Duplicate Genealogy & Reconciliation"],
)
def reverse_merge_event_endpoint(
    workspace_id: str,
    group_id: str,
    payload: DuplicateReverseMergeRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> DuplicateGroupGenealogyResponse:
    """Safely reverse an earlier merge operation without erasing historical audit records."""
    return reverse_merge_event(
        db=db,
        workspace_id=workspace_id,
        group_id=group_id,
        payload=payload,
    )


frontend_dist = os.environ.get("FRONTEND_DIST")
dist_path = (
    Path(frontend_dist)
    if frontend_dist
    else (Path(__file__).resolve().parents[2] / "frontend" / "dist")
)

if dist_path.is_dir() and (dist_path / "index.html").is_file():
    from starlette.staticfiles import StaticFiles

    assets_dir = dist_path / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="spa_assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_route(full_path: str):
        # Do not swallow API, health, docs, or OpenAPI errors as SPA html
        if (
            full_path.startswith(("api/", "health/"))
            or full_path in ("docs", "redoc", "openapi.json")
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Endpoint '{full_path}' not found")
        index_file = dist_path / "index.html"
        return FileResponse(index_file)


