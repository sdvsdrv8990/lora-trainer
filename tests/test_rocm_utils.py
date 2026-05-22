from src.rocm_utils import hsa_override_for


def test_rdna2_hsa_override() -> None:
    assert hsa_override_for("rdna2") == "10.3.0"


def test_rdna3_hsa_override() -> None:
    assert hsa_override_for("rdna3") == "11.0.0"
