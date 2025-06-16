# Release Process

This project uses standard git flow for releases. Versions are determined by git tags, and releases are published automatically when GitHub releases are created.

## Release Workflow

1. **Create a Release on GitHub**
   - Go to the GitHub repository
   - Click "Releases" → "Create a new release"
   - Choose or create a new tag (e.g., `v1.2.3` or `1.2.3`)
   - Fill in the release title and description
   - Click "Publish release"

2. **Automatic Publishing**
   - The release workflow will automatically trigger
   - PyPI package will be published with the version from the git tag
   - Docker image will be built and pushed with the same version
   - Both jobs run in parallel for faster publishing

## Version Format

- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Git tags can have `v` prefix (`v1.2.3`) or not (`1.2.3`) - both work
- The published packages will use the clean version number (without `v`)

## Development Builds

- Pushes to `main` and `develop` branches trigger build workflows
- Docker images are built but not published (for testing)
- Python packages are built but not published

## Tag Examples

```bash
# Create and push a tag manually (if needed)
git tag v1.2.3
git push origin v1.2.3

# Or create a release directly on GitHub (recommended)
```

## What Gets Published

When you create a GitHub release:

- **PyPI**: `open-bedrock-server==1.2.3`
- **Docker**: `ghcr.io/username/repo:1.2.3`, `ghcr.io/username/repo:1.2`, `ghcr.io/username/repo:1`

## Previous Workflows Removed

The following files have been removed as they conflicted with standard git flow:

- `auto-version.yml` - Automatic version bumping
- `VERSION` file - Manual version tracking
- `scripts/bump_version.py` - Version bump script

Now versioning is purely based on git tags and GitHub releases. 