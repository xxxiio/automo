from automo.integrations.getdone import GetDoneCapabilityWorkflow


def test_getdone_integration_status_is_lazy() -> None:
    status = GetDoneCapabilityWorkflow(enabled=False).status()
    assert status.provider == "getdone"
    assert not status.enabled
    assert status.detail
