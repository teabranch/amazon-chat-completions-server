# Version Management

This project uses a simple file-based version management system with **automatic version bumping** based on conventional commits.

## How It Works

- **VERSION file**: Contains the current version number (e.g., `2.0.3`)
- **pyproject.toml**: Configured to read version from the VERSION file
- **Auto-version workflow**: Automatically bumps versions on push to main
- **CI/CD workflows**: Read version directly from the VERSION file
- **No git dependencies**: Version is independent of git tags and commit history

## Automatic Version Management

### Conventional Commits (Recommended)

The system automatically detects version bump type based on your commit messages:

```bash
# Patch version bump (2.0.3 -> 2.0.4)
git commit -m "fix: resolve authentication bug"
git commit -m "perf: improve query performance"

# Minor version bump (2.0.3 -> 2.1.0) 
git commit -m "feat: add new chat completion endpoint"
git commit -m "feat(api): implement streaming responses"

# Major version bump (2.0.3 -> 3.0.0)
git commit -m "feat!: redesign API with breaking changes"
git commit -m "feat: new feature

BREAKING CHANGE: removes old API endpoints"
```

### Automatic Workflow Triggers

1. **Push to main**: Automatically analyzes commits and bumps version
2. **Manual dispatch**: Trigger manually via GitHub Actions with specific bump type

### Manual Override

You can manually trigger version bumps via GitHub Actions:
1. Go to Actions tab → "Auto Version Management"
2. Click "Run workflow" 
3. Choose bump type: `auto`, `patch`, `minor`, or `major`
4. Optionally skip GitHub release creation

## Manual Version Management

### Using the Script

```bash
# Show current version
python scripts/bump_version.py --current

# Set a specific version
python scripts/bump_version.py --set 2.0.4

# Bump version automatically
python scripts/bump_version.py --bump patch    # 2.0.3 -> 2.0.4
python scripts/bump_version.py --bump minor    # 2.0.3 -> 2.1.0  
python scripts/bump_version.py --bump major    # 2.0.3 -> 3.0.0

# Set version and create git tag
python scripts/bump_version.py --set 2.0.4 --tag

# Set version, create tag, and push to origin
python scripts/bump_version.py --set 2.0.4 --tag --push
```

### Manual Method

1. Edit the `VERSION` file directly
2. Commit the change
3. Create a git tag: `git tag 2.0.4`
4. Push the tag: `git push origin 2.0.4`

## Fully Automatic Release Process

1. **Make changes** with conventional commit messages
2. **Push to main** - Auto-version workflow triggers
3. **Version auto-bumped** based on commit analysis
4. **GitHub release created** automatically
5. **PyPI & Docker publish** triggered by the release

### Example Workflow:

```bash
# Work on feature
git checkout -b feature/new-endpoint
# ... make changes ...
git commit -m "feat: add new streaming endpoint"
git push origin feature/new-endpoint

# Create PR and merge to main
# -> Auto-version workflow runs
# -> Version bumped from 2.0.3 to 2.1.0
# -> GitHub release created
# -> PyPI and Docker publishing triggered
```

## Workflow Integration

The automatic version management integrates with:
- **PyPI publishing**: Triggered when GitHub release is created
- **Docker publishing**: Triggered when GitHub release is created
- **Version verification**: All workflows verify VERSION file matches git tag

## Benefits

- ✅ **Fully automatic**: No manual version management needed
- ✅ **Conventional commits**: Industry-standard commit message format
- ✅ **Flexible**: Auto-detect or manual override available
- ✅ **Simple and reliable**: No complex git history parsing
- ✅ **No merge commit issues**: Version is independent of git structure
- ✅ **Easy to debug**: Version source is always clear
- ✅ **CI/CD friendly**: Workflows are simpler and more predictable

## Conventional Commit Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: A new feature (minor bump)
- `fix`: A bug fix (patch bump)
- `perf`: Performance improvement (patch bump)
- `docs`: Documentation changes (no bump)
- `style`: Code style changes (no bump)
- `refactor`: Code refactoring (no bump)
- `test`: Test changes (no bump)
- `chore`: Maintenance tasks (no bump)

**Breaking changes:** Add `!` after type or include `BREAKING CHANGE:` in footer (major bump)

## Migration from hatch-vcs

The previous system used `hatch-vcs` which automatically detected versions from git tags. This caused issues with:
- Merge commits creating development versions
- Complex git history causing version detection failures
- Dependency on git repository state

The new system eliminates these issues with a file-based approach and intelligent commit analysis. 