import shutil

import pytest


@pytest.mark.integration
def test_anvil_test_environment_is_explicit() -> None:
    if shutil.which("anvil") is None:
        pytest.skip("Install Foundry/Anvil to run local-EVM integration tests")
    assert shutil.which("anvil") is not None
