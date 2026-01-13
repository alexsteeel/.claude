"""Health check command."""

from ..health import check_health
from ..logging import console


def run_health(verbose: bool = False) -> int:
    """Run health check and return exit code."""
    result = check_health(verbose=verbose)

    if verbose or not result.is_healthy:
        if result.is_healthy:
            console.success(result.message)
        else:
            console.error(f"{result.error_type.value}: {result.message}")

    return result.exit_code
