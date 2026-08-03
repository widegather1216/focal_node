import pytest
from app.services.unipercept_adapter import UniPerceptAdapter, get_unipercept_adapter

def test_unipercept_adapter_singleton():
    adapter1 = get_unipercept_adapter()
    adapter2 = get_unipercept_adapter()
    assert adapter1 is adapter2
    assert adapter1.model is None  # Ensures model is NOT loaded at instantiation (Lazy loading)

def test_unipercept_adapter_initial_state():
    adapter = UniPerceptAdapter()
    assert adapter.model_id == "widegather/unipercept-mirror"
    assert adapter.model is None
    assert adapter.timer_active is False
