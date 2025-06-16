# Scripts

This directory contains utility scripts for version management and development setup.

## Version Management

### `bump_version.py`
Main version management script that replaces hatch-vcs.

```bash
# Show current version
python scripts/bump_version.py --current

# Bump version
python scripts/bump_version.py --bump patch|minor|major

# Set specific version
python scripts/bump_version.py --set 2.0.4

# Create git tag and push
python scripts/bump_version.py --set 2.0.4 --tag --push
```

## Development Setup

### `setup_conventional_commits.sh`
Configures git for conventional commits and automatic version management.

```bash
./scripts/setup_conventional_commits.sh
```

This script:
- Sets up git commit message template
- Provides guidance for conventional commit format
- Explains how commits trigger automatic version bumps

## Automatic Version Management

The project uses GitHub Actions to automatically:
1. Analyze commit messages for conventional commit patterns
2. Determine appropriate version bump (patch/minor/major)
3. Update VERSION file and create git tag
4. Create GitHub release
5. Trigger PyPI and Docker publishing

See `../VERSION_MANAGEMENT.md` for complete documentation. 