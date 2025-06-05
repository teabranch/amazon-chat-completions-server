#!/usr/bin/env python3
"""
Test runner script for the CI/CD pipeline.
Supports different test modes: unit, integration, all-safe, and real-api.
"""

import argparse
import subprocess
import sys
from typing import List


def run_command(cmd: List[str]) -> int:
    """Run a command and return its exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def run_unit_tests(verbose: bool = False) -> int:
    """Run fast unit tests with no external dependencies."""
    cmd = ["uv", "run", "pytest", "-m", "unit"]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_integration_tests(verbose: bool = False) -> int:
    """Run integration tests with mocks (safe, no real API calls)."""
    cmd = ["uv", "run", "pytest", "-m", "integration and not real_api"]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_all_safe_tests(verbose: bool = False) -> int:
    """Run all safe tests (unit + integration, no real API calls)."""
    cmd = ["uv", "run", "pytest", "-m", "not real_api and not external_api"]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_real_api_tests(verbose: bool = False) -> int:
    """Run tests that make real API calls (costs money!)."""
    cmd = ["uv", "run", "pytest", "-m", "real_api or external_api"]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_all_tests(verbose: bool = False) -> int:
    """Run all tests including real API calls."""
    cmd = ["uv", "run", "pytest"]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def main():
    parser = argparse.ArgumentParser(description="Run tests with different modes")
    parser.add_argument(
        "--mode",
        choices=["unit", "integration", "all-safe", "real-api", "all"],
        default="all-safe",
        help="Test mode to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.mode == "unit":
        exit_code = run_unit_tests(args.verbose)
    elif args.mode == "integration":
        exit_code = run_integration_tests(args.verbose)
    elif args.mode == "all-safe":
        exit_code = run_all_safe_tests(args.verbose)
    elif args.mode == "real-api":
        exit_code = run_real_api_tests(args.verbose)
    elif args.mode == "all":
        exit_code = run_all_tests(args.verbose)
    else:
        print(f"Unknown mode: {args.mode}")
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main() 