#!/usr/bin/env python3
"""
Simple version management script for the project.
This replaces the complex hatch-vcs system with a straightforward approach.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    """Get the current version from the VERSION file."""
    version_file = Path("VERSION")
    if not version_file.exists():
        print("ERROR: VERSION file not found")
        sys.exit(1)
    return version_file.read_text().strip()


def set_version(version):
    """Set the version in the VERSION file."""
    version_file = Path("VERSION")
    version_file.write_text(version + "\n")
    print(f"✅ Updated VERSION file to: {version}")


def validate_version(version):
    """Validate that the version follows semantic versioning."""
    pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?(?:\+[a-zA-Z0-9.-]+)?$"
    if not re.match(pattern, version):
        print(f"ERROR: Invalid version format: {version}")
        print("Version must follow semantic versioning (e.g., 1.0.0, 1.0.0-alpha.1)")
        sys.exit(1)


def bump_version(current_version, bump_type):
    """Bump the version based on the type (major, minor, patch)."""
    # Parse current version
    parts = current_version.split(".")
    if len(parts) != 3:
        print(f"ERROR: Current version {current_version} is not in major.minor.patch format")
        sys.exit(1)
    
    try:
        major, minor, patch = map(int, parts)
    except ValueError:
        print(f"ERROR: Current version {current_version} contains non-numeric parts")
        sys.exit(1)
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        print(f"ERROR: Invalid bump type: {bump_type}")
        sys.exit(1)
    
    return f"{major}.{minor}.{patch}"


def create_git_tag(version, push=False):
    """Create a git tag for the version."""
    try:
        subprocess.run(["git", "tag", version], check=True)
        print(f"✅ Created git tag: {version}")
        
        if push:
            subprocess.run(["git", "push", "origin", version], check=True)
            print(f"✅ Pushed tag {version} to origin")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create/push git tag: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Manage project version")
    parser.add_argument("--current", action="store_true", help="Show current version")
    parser.add_argument("--set", help="Set specific version")
    parser.add_argument("--bump", choices=["major", "minor", "patch"], help="Bump version")
    parser.add_argument("--tag", action="store_true", help="Create git tag after setting version")
    parser.add_argument("--push", action="store_true", help="Push git tag to origin (requires --tag)")
    
    args = parser.parse_args()
    
    if args.current:
        print(get_current_version())
        return
    
    if args.set:
        validate_version(args.set)
        set_version(args.set)
        new_version = args.set
    elif args.bump:
        current = get_current_version()
        new_version = bump_version(current, args.bump)
        print(f"Bumping version from {current} to {new_version}")
        set_version(new_version)
    else:
        parser.print_help()
        return
    
    if args.tag:
        create_git_tag(new_version, push=args.push)
        
        if args.push:
            print(f"\n🚀 Ready for release! Version {new_version} has been tagged and pushed.")
            print("You can now create a GitHub release to trigger the publishing workflows.")


if __name__ == "__main__":
    main() 