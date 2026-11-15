import sys
import types
from unittest.mock import MagicMock, patch

from services.base_model import clear_mlx_cache, clear_mps_cache


def test_clear_mps_cache_skips_when_mps_unavailable():
    """Verify C++ torch.mps bindings are never called when is_available() is False."""
    mock_mps = MagicMock()
    mock_backends_mps = MagicMock()
    mock_backends_mps.is_available.return_value = False
    mock_torch = types.SimpleNamespace(
        backends=types.SimpleNamespace(mps=mock_backends_mps),
        mps=mock_mps,
    )

    with patch.dict(sys.modules, {"torch": mock_torch}):
        did_clear = clear_mps_cache(synchronize=True)

    assert did_clear is False
    mock_mps.synchronize.assert_not_called()
    mock_mps.empty_cache.assert_not_called()


def test_clear_mps_cache_skips_when_backends_missing():
    """Verify clear_mps_cache fails closed when torch.backends.mps is absent."""
    mock_mps = MagicMock()
    mock_torch = types.SimpleNamespace(mps=mock_mps)

    with patch.dict(sys.modules, {"torch": mock_torch}):
        did_clear = clear_mps_cache(synchronize=True)

    assert did_clear is False
    mock_mps.synchronize.assert_not_called()
    mock_mps.empty_cache.assert_not_called()


def test_clear_mps_cache_clears_when_mps_available():
    """Verify clear_mps_cache triggers empty_cache and optional synchronize when available."""
    mock_mps = MagicMock()
    mock_backends_mps = MagicMock()
    mock_backends_mps.is_available.return_value = True
    mock_torch = types.SimpleNamespace(
        backends=types.SimpleNamespace(mps=mock_backends_mps),
        mps=mock_mps,
    )

    with patch.dict(sys.modules, {"torch": mock_torch}):
        did_clear_no_sync = clear_mps_cache(synchronize=False)
        assert did_clear_no_sync is True
        mock_mps.synchronize.assert_not_called()
        mock_mps.empty_cache.assert_called_once()

        did_clear_with_sync = clear_mps_cache(synchronize=True)
        assert did_clear_with_sync is True
        mock_mps.synchronize.assert_called_once()
        assert mock_mps.empty_cache.call_count == 2


def test_clear_mps_cache_real_environment_no_segfault():
    """Verify calling clear_mps_cache against real torch never segfaults in headless environments."""
    import torch

    result = clear_mps_cache(synchronize=True)
    expected = bool(hasattr(torch, "backends") and hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
    assert result is expected


def test_clear_mlx_cache_handles_unavailable_and_runtime_error():
    """Verify clear_mlx_cache catches headless RuntimeError safely without propagating."""
    failing_mx = MagicMock()
    failing_mx.clear_cache.side_effect = RuntimeError("No Metal device available")
    mlx_pkg = types.ModuleType("mlx")
    mlx_pkg.core = failing_mx

    with patch.dict(sys.modules, {"mlx": mlx_pkg, "mlx.core": failing_mx}):
        assert clear_mlx_cache() is False
        failing_mx.clear_cache.assert_called_once()
