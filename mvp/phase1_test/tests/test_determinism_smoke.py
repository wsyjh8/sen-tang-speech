"""Smoke test for determinism runner - validates no drift with 3 replays."""

from eval.run_determinism import run_determinism


def test_determinism_smoke() -> None:
    """
    Run determinism test with 3 replays (smoke test).
    
    Asserts no AssertionError is raised.
    """
    run_determinism(replays=3)
