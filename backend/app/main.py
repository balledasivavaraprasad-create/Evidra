"""FastAPI entrypoint declaring all health and /api/v1 contract endpoints."""
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.contracts.enums import (
    EffectiveDecisionState,
)
from app.contracts.models import (
    AssistantProposal,
    AssistantRequest,
    ConflictResolveRequest,
    CorpusDiffResponse,
    CorpusRevisionResponse,
    CriteriaVersionCreate,
    CriteriaVersionResponse,
    DecisionCommand,
    DedupOverrideRequest,
    ErrorDetail,
    ErrorEnvelope,
    ExportRequest,
    ExportResponse,
    ImportJobCreate,
    JobResponse,
    PaperGroupDetail,
    PaperGroupSummary,
    PicoOverrideRequest,
    QueryVersionCreate,
    QueryVersionResponse,
    ReviewEventResponse,
    SearchExecutionCreate,
    SearchExecutionResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)
from app.db.models import WorkspaceModel
from app.db.session import get_db
from app.settings import settings

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="Deterministic and AI-augmented systematic literature review engine REST API.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

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
        200: {"description": "Service and database ready"},
        503: {"model": ErrorEnvelope, "description": "Database connection unavailable"},
    },
)
def health_ready(db: Session = Depends(get_db)) -> JSONResponse:  # noqa: B008
    """Check if the application and business SQLite database are ready to serve."""
    try:
        db.execute(text("SELECT 1")).scalar()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "database": "connected"},
        )
    except Exception as exc:  # noqa: BLE001
        envelope = ErrorEnvelope(
            code="DATABASE_UNAVAILABLE",
            message=f"Database readiness check failed: {exc}",
            retryable=True,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=envelope.model_dump(),
        )


# ============================================================================
# API v1 Endpoints (Declared Contracts & Stubs)
# ============================================================================

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
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)) -> WorkspaceResponse:  # noqa: B008
    """Create a new review workspace."""
    workspace = WorkspaceModel(
        title=payload.title,
        description=payload.description,
        created_by="reviewer_local",
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace)


@app.post(
    "/api/v1/workspaces/{workspace_id}/criteria",
    tags=["Criteria"],
    summary="Save a new criteria version",
    response_model=CriteriaVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_criteria_version(workspace_id: str, payload: CriteriaVersionCreate) -> CriteriaVersionResponse:
    """Save immutable review question and inclusion/exclusion criteria version (Implemented in D02/B02)."""
    stub_not_implemented("create_criteria_version")
    raise NotImplementedError


@app.post(
    "/api/v1/workspaces/{workspace_id}/queries",
    tags=["Queries"],
    summary="Save a new query version",
    response_model=QueryVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_query_version(workspace_id: str, payload: QueryVersionCreate) -> QueryVersionResponse:
    """Save an immutable structured search query version (Implemented in D02)."""
    stub_not_implemented("create_query_version")
    raise NotImplementedError


@app.post(
    "/api/v1/queries/{query_id}/searches",
    tags=["Queries"],
    summary="Execute search count acquisition",
    response_model=SearchExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def execute_search_count(query_id: str, payload: SearchExecutionCreate) -> SearchExecutionResponse:
    """Trigger count-only query acquisition from literature provider (Implemented in D02)."""
    stub_not_implemented("execute_search_count")
    raise NotImplementedError


@app.post(
    "/api/v1/workspaces/{workspace_id}/imports",
    tags=["Ingestion"],
    summary="Trigger approved record import job",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_import_job(workspace_id: str, payload: ImportJobCreate) -> JobResponse:
    """Queue durable literature import job for approved search executions (Implemented in D02)."""
    stub_not_implemented("trigger_import_job")
    raise NotImplementedError


@app.get(
    "/api/v1/jobs/{job_id}",
    tags=["Jobs"],
    summary="Get background job status",
    response_model=JobResponse,
)
def get_job_status(job_id: str) -> JobResponse:
    """Poll status, stage, progress, and errors for a background job (Implemented in D02)."""
    stub_not_implemented("get_job_status")
    raise NotImplementedError


@app.get(
    "/api/v1/workspaces/{workspace_id}/revisions",
    tags=["Corpus"],
    summary="List published corpus revisions",
    response_model=list[CorpusRevisionResponse],
)
def list_corpus_revisions(workspace_id: str) -> list[CorpusRevisionResponse]:
    """List historical immutable corpus snapshots (Implemented in D04/D05)."""
    stub_not_implemented("list_corpus_revisions")
    raise NotImplementedError


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
) -> list[PaperGroupSummary]:
    """List paginated deduplicated paper groups for screening workbench (Implemented in D03)."""
    stub_not_implemented("list_paper_groups")
    raise NotImplementedError


@app.get(
    "/api/v1/groups/{group_id}",
    tags=["Review"],
    summary="Get paper group detail with members and evidence",
    response_model=PaperGroupDetail,
)
def get_paper_group(group_id: str, revision_id: str | None = None) -> PaperGroupDetail:
    """Retrieve full group detail, member revisions, screening evidence, and PICO spans (Implemented in D03)."""
    stub_not_implemented("get_paper_group")
    raise NotImplementedError


@app.post(
    "/api/v1/groups/{group_id}/decisions",
    tags=["Review"],
    summary="Record reviewer eligibility decision",
    response_model=ReviewEventResponse,
)
def record_screening_decision(group_id: str, payload: DecisionCommand) -> ReviewEventResponse:
    """Append a human include/exclude/maybe decision event with optimistic concurrency (Implemented in D03)."""
    stub_not_implemented("record_screening_decision")
    raise NotImplementedError


@app.post(
    "/api/v1/groups/{group_id}/pico",
    tags=["Review"],
    summary="Override or save verified PICO spans",
    response_model=ReviewEventResponse,
)
def save_pico_annotations(group_id: str, payload: PicoOverrideRequest) -> ReviewEventResponse:
    """Save verified PICO offsets bound to immutable text revision (Implemented in D03)."""
    stub_not_implemented("save_pico_annotations")
    raise NotImplementedError


@app.post(
    "/api/v1/workspaces/{workspace_id}/dedup-decisions",
    tags=["Review"],
    summary="Confirm or reject deduplication candidate pair",
    response_model=ReviewEventResponse,
)
def record_dedup_override(workspace_id: str, payload: DedupOverrideRequest) -> ReviewEventResponse:
    """Confirm duplicate group merge or record cannot-link constraint (Implemented in D03)."""
    stub_not_implemented("record_dedup_override")
    raise NotImplementedError


@app.post(
    "/api/v1/conflicts/{conflict_id}/resolve",
    tags=["Review"],
    summary="Resolve group merge conflict",
    response_model=ReviewEventResponse,
)
def resolve_group_conflict(conflict_id: str, payload: ConflictResolveRequest) -> ReviewEventResponse:
    """Manually resolve an inherited screening divergence on merged groups (Implemented in D05)."""
    stub_not_implemented("resolve_group_conflict")
    raise NotImplementedError


@app.get(
    "/api/v1/revisions/{revision_id}/diff",
    tags=["Corpus"],
    summary="Diff two corpus snapshots",
    response_model=CorpusDiffResponse,
)
def diff_corpus_revisions(revision_id: str, base_revision_id: str) -> CorpusDiffResponse:
    """Calculate diff between two corpus snapshots (Implemented in D05)."""
    stub_not_implemented("diff_corpus_revisions")
    raise NotImplementedError


@app.post(
    "/api/v1/workspaces/{workspace_id}/restore",
    tags=["Corpus"],
    summary="Restore exact historical snapshot",
    response_model=CorpusRevisionResponse,
)
def restore_corpus_snapshot(workspace_id: str, snapshot_id: str) -> CorpusRevisionResponse:
    """Restore exact historical corpus snapshot without re-fetching APIs (Implemented in D05)."""
    stub_not_implemented("restore_corpus_snapshot")
    raise NotImplementedError


@app.post(
    "/api/v1/revisions/{revision_id}/exports",
    tags=["Export"],
    summary="Export included studies",
    response_model=ExportResponse,
)
def export_included_studies(revision_id: str, payload: ExportRequest) -> ExportResponse:
    """Generate sanitized CSV/RIS export of included studies with audit provenance (Implemented in D04)."""
    stub_not_implemented("export_included_studies")
    raise NotImplementedError


@app.post(
    "/api/v1/workspaces/{workspace_id}/assistant",
    tags=["Assistant"],
    summary="Query bounded RAG assistant",
    response_model=AssistantProposal,
)
def query_assistant(workspace_id: str, payload: AssistantRequest) -> AssistantProposal:
    """Query bounded corpus assistant for explainable screening or PICO proposals (Implemented in C06)."""
    stub_not_implemented("query_assistant")
    raise NotImplementedError
