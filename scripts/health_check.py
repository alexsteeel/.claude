#!/usr/bin/env python3
"""
API Health Check

Lightweight check if Claude API is responding.

Exit codes:
    0 - API healthy (got valid response)
    1 - Auth error (401)
    2 - Rate limited (429)
    3 - Other error
    4 - Overloaded (529)

Usage:
    python health_check.py
    python health_check.py --verbose
"""

import json
import subprocess
import sys
from typing import NamedTuple


class HealthResult(NamedTuple):
    """Health check result."""
    code: int
    status: str
    message: str


# Exit codes
EXIT_HEALTHY = 0
EXIT_AUTH_ERROR = 1
EXIT_RATE_LIMITED = 2
EXIT_OTHER_ERROR = 3
EXIT_OVERLOADED = 4


def check_health(verbose: bool = False) -> HealthResult:
    """Run health check against Claude API.

    Returns HealthResult with exit code, status name, and message.
    """
    try:
        result = subprocess.run(
            ["claude", "-p", "Reply with OK", "--max-turns", "1", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout + result.stderr

        if verbose:
            print(f"Raw output: {output[:500]}", file=sys.stderr)

        # Try to parse as JSON (may be multiple JSON objects, take last one)
        lines = output.strip().split('\n')
        data = None

        for line in reversed(lines):
            try:
                data = json.loads(line)
                if data.get("type") == "result":
                    break
            except json.JSONDecodeError:
                continue

        if data is None:
            # No valid JSON found, check raw output for errors
            if "401" in output or "Unauthorized" in output.lower():
                return HealthResult(EXIT_AUTH_ERROR, "AUTH_ERROR", "Authentication failed (401)")
            if "429" in output or "rate" in output.lower():
                return HealthResult(EXIT_RATE_LIMITED, "RATE_LIMITED", "Rate limited (429)")
            if "529" in output or "overloaded" in output.lower():
                return HealthResult(EXIT_OVERLOADED, "OVERLOADED", "API overloaded (529)")
            return HealthResult(EXIT_OTHER_ERROR, "PARSE_ERROR", f"Could not parse response: {output[:200]}")

        # Check for result type
        if data.get("type") == "result":
            if data.get("is_error"):
                error_code = data.get("error_code", "")
                errors = data.get("errors", [])
                error_msg = "; ".join(str(e) for e in errors) if errors else str(data.get("result", ""))

                # Check specific error codes
                if "401" in str(error_code) or "401" in error_msg:
                    return HealthResult(EXIT_AUTH_ERROR, "AUTH_ERROR", f"Authentication error: {error_msg}")
                if "429" in str(error_code) or "429" in error_msg or "rate" in error_msg.lower():
                    return HealthResult(EXIT_RATE_LIMITED, "RATE_LIMITED", f"Rate limited: {error_msg}")
                if "529" in str(error_code) or "529" in error_msg or "overloaded" in error_msg.lower():
                    return HealthResult(EXIT_OVERLOADED, "OVERLOADED", f"API overloaded: {error_msg}")

                return HealthResult(EXIT_OTHER_ERROR, "API_ERROR", f"API error: {error_msg}")

            # Success - check if we got valid response
            result_text = data.get("result", "")
            if "OK" in result_text.upper() or result_text:
                return HealthResult(EXIT_HEALTHY, "HEALTHY", "API is responding")

        # Check usage - if we got tokens, API is working
        usage = data.get("usage", {})
        if usage.get("output_tokens", 0) > 0:
            return HealthResult(EXIT_HEALTHY, "HEALTHY", "API is responding (got tokens)")

        return HealthResult(EXIT_OTHER_ERROR, "NO_RESPONSE", "No valid response from API")

    except subprocess.TimeoutExpired:
        return HealthResult(EXIT_OTHER_ERROR, "TIMEOUT", "Health check timed out after 60s")
    except FileNotFoundError:
        return HealthResult(EXIT_OTHER_ERROR, "NOT_FOUND", "Claude CLI not found")
    except Exception as e:
        return HealthResult(EXIT_OTHER_ERROR, "EXCEPTION", f"Health check failed: {e}")


def main():
    """Run health check and exit with appropriate code."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    result = check_health(verbose=verbose)

    if verbose or result.code != EXIT_HEALTHY:
        print(f"{result.status}: {result.message}")

    sys.exit(result.code)


if __name__ == "__main__":
    main()
