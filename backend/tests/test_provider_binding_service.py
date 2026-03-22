from app.modules.provider_bindings.service import ProviderBindingService


def test_provider_binding_transition_rules() -> None:
    assert ProviderBindingService.is_transition_allowed("draft", "enabled") is True
    assert ProviderBindingService.is_transition_allowed("enabled", "quarantined") is True
    assert ProviderBindingService.is_transition_allowed("quarantined", "enabled") is True
    assert ProviderBindingService.is_transition_allowed("draft", "quarantined") is False
