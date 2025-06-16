# Version Management

This project uses a simple file-based version management system instead of the complex `hatch-vcs` system to avoid issues with git history and merge commits.

## How It Works

- **VERSION file**: Contains the current version number (e.g., `2.0.3`)
- **pyproject.toml**: Configured to read version from the VERSION file
- **CI/CD workflows**: Read version directly from the VERSION file
- **No git dependencies**: Version is independent of git tags and commit history

## Managing Versions

### Using the Script (Recommended)

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

## Release Process

1. **Update version**: Use the script or edit VERSION file
2. **Commit changes**: `git commit -am "Bump version to 2.0.4"`
3. **Create tag**: `git tag 2.0.4`
4. **Push tag**: `git push origin 2.0.4`
5. **Create GitHub release**: This triggers the publishing workflows

## Workflow Integration

Both PyPI and Docker publishing workflows:
- Read version from the VERSION file
- Verify the version matches the git tag
- Use the version for building and publishing

## Benefits

- ✅ **Simple and reliable**: No complex git history parsing
- ✅ **No merge commit issues**: Version is independent of git structure
- ✅ **Easy to debug**: Version source is always clear
- ✅ **Manual control**: You decide when to bump versions
- ✅ **CI/CD friendly**: Workflows are simpler and more predictable

## Migration from hatch-vcs

The previous system used `hatch-vcs` which automatically detected versions from git tags. This caused issues with:
- Merge commits creating development versions
- Complex git history causing version detection failures
- Dependency on git repository state

The new system eliminates these issues by using a simple file-based approach. 