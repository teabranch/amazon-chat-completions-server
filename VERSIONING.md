# Versioning Strategy

This project uses **semantic versioning** (SemVer) to ensure consistency across all release channels: PyPI packages and Docker images.

## Current Version
- **Latest Release**: 1.0.0 (to be tagged)
- **Next Release**: 1.0.1 (example)

## Semantic Versioning Format
We follow the `MAJOR.MINOR.PATCH` format:
- **MAJOR**: Breaking changes that are not backward compatible
- **MINOR**: New features that are backward compatible  
- **PATCH**: Bug fixes that are backward compatible

## Version Consistency Across Platforms

### 1. Git Tags
- All releases start with creating a git tag: `v{VERSION}` (e.g., `v1.0.1`)
- Tags are the single source of truth for version numbers

### 2. PyPI Package
- Uses `setuptools-scm` to automatically detect version from git tags
- Published to: https://pypi.org/project/open-amazon-chat-completions-server
- Version verification step in CI ensures tag matches package version

### 3. Docker Images
- Uses `docker/metadata-action` with semver patterns
- Published to: `ghcr.io/teabranch/open-amazon-chat-completions-server`
- Creates multiple tags per release:
  - `ghcr.io/teabranch/open-amazon-chat-completions-server:1.0.1` (exact version)
  - `ghcr.io/teabranch/open-amazon-chat-completions-server:1.0` (major.minor)
  - `ghcr.io/teabranch/open-amazon-chat-completions-server:1` (major)

## Release Process

### Automated Release (Recommended)
Use the provided release script:

```bash
# For the next patch version (1.0.1)
./scripts/release.sh 1.0.1

# For a minor version (1.1.0)  
./scripts/release.sh 1.1.0

# For a major version (2.0.0)
./scripts/release.sh 2.0.0
```

### Manual Release Process
1. **Create and push git tag**:
   ```bash
   git tag -a v1.0.1 -m "Release version 1.0.1"
   git push origin v1.0.1
   ```

2. **Create GitHub Release**:
   - Go to GitHub releases page
   - Click "Create a new release"
   - Select the tag `v1.0.1`
   - Add release notes
   - Click "Publish release"

3. **Automatic CI/CD**:
   - PyPI workflow triggers on release publication
   - Docker workflow triggers on release publication  
   - Both use the same version from the git tag

## Workflow Details

### PyPI Workflow (`.github/workflows/pypi_publish.yml`)
- **Trigger**: `release.published`
- **Version Source**: `setuptools-scm` reads from git tag
- **Verification**: Compares git tag with package version
- **Output**: Package published to PyPI

### Docker Workflow (`.github/workflows/docker-publish.yml`) 
- **Trigger**: `release.published` (among others)
- **Version Source**: `docker/metadata-action` reads from git tag
- **Tags Created**: 
  - Exact version (e.g., `1.0.1`)
  - Major.minor (e.g., `1.0`)
  - Major only (e.g., `1`)
- **Output**: Images published to GitHub Container Registry

## Version Verification

Both workflows include verification steps to ensure version consistency:

1. **PyPI workflow**: Verifies that the Python package version matches the git tag
2. **Docker workflow**: Uses semver patterns that are only enabled for release events

## Example Release Cycle

Starting from version 1.0.0:

1. **Patch Release (1.0.1)**: Bug fixes
   - Git tag: `v1.0.1`
   - PyPI: `open-amazon-chat-completions-server==1.0.1`
   - Docker: `ghcr.io/teabranch/open-amazon-chat-completions-server:1.0.1`

2. **Minor Release (1.1.0)**: New backward-compatible features  
   - Git tag: `v1.1.0`
   - PyPI: `open-amazon-chat-completions-server==1.1.0`
   - Docker: `ghcr.io/teabranch/open-amazon-chat-completions-server:1.1.0`

3. **Major Release (2.0.0)**: Breaking changes
   - Git tag: `v2.0.0` 
   - PyPI: `open-amazon-chat-completions-server==2.0.0`
   - Docker: `ghcr.io/teabranch/open-amazon-chat-completions-server:2.0.0`

## Best Practices

1. **Always use the release script** for consistency
2. **Write meaningful release notes** for each version
3. **Test thoroughly** before creating releases
4. **Follow semantic versioning** rules strictly
5. **Never delete or modify existing tags** once published 