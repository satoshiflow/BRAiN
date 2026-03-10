from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.course_factory.schemas import (
    CourseGenerationRequest,
    CourseLanguage,
    CourseTargetAudience,
)
from app.modules.course_factory.service import CourseFactoryService


@pytest.mark.asyncio
async def test_deploy_to_staging_dispatches_opencode_job_contract() -> None:
    service = CourseFactoryService(event_stream=None)
    service.opencode_dispatcher = SimpleNamespace(
        dispatch_job_contract=AsyncMock(return_value=SimpleNamespace(job_id="job_123"))
    )

    request = CourseGenerationRequest(
        tenant_id="tenant-1",
        title="Test Course Dispatch",
        description="Dispatch test for OpenCode job contract",
        language=CourseLanguage.DE,
        target_audiences=[CourseTargetAudience.PRIVATE_INDIVIDUALS],
        deploy_to_staging=True,
        staging_domain="course-dispatch.staging",
        dry_run=False,
    )
    outline = SimpleNamespace(metadata=SimpleNamespace(course_id="course-123"))

    url = await service._deploy_to_staging(request, outline, landing_page=None)

    assert url == "https://course-dispatch.staging"
    assert service.opencode_dispatcher.dispatch_job_contract.await_count == 1
