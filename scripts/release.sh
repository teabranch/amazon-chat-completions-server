#!/bin/bash

# Release script for open-amazon-chat-completions-server
# This script ensures version consistency between git tags, PyPI, and Docker releases

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if version argument is provided
if [ $# -eq 0 ]; then
    print_error "Please provide a version number (e.g., 1.0.1)"
    echo "Usage: $0 <version>"
    echo "Example: $0 1.0.1"
    exit 1
fi

VERSION=$1

# Validate semantic version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid version format. Please use semantic versioning (e.g., 1.0.1)"
    exit 1
fi

print_info "Starting release process for version $VERSION"

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_warning "You're not on the main branch. Current branch: $CURRENT_BRANCH"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Release cancelled"
        exit 1
    fi
fi

# Check if working directory is clean
if ! git diff-index --quiet HEAD --; then
    print_error "Working directory is not clean. Please commit or stash your changes."
    exit 1
fi

# Check if tag already exists
if git tag --list | grep -q "^v$VERSION$\|^$VERSION$"; then
    print_error "Tag v$VERSION or $VERSION already exists"
    exit 1
fi

# Show current tags
print_info "Current tags:"
git tag --list --sort=-version:refname | head -10

print_info "Creating and pushing tag v$VERSION"

# Create annotated tag
git tag -a "v$VERSION" -m "Release version $VERSION"

# Push the tag
git push origin "v$VERSION"

print_success "Tag v$VERSION created and pushed successfully"

print_info "Next steps:"
echo "1. Go to GitHub and create a release from the tag v$VERSION"
echo "2. The GitHub Actions workflows will automatically:"
echo "   - Build and publish the Python package to PyPI"
echo "   - Build and publish the Docker image to GitHub Container Registry"
echo "3. Both will use the same version: $VERSION"

print_info "GitHub Release URL:"
echo "https://github.com/$(git config --get remote.origin.url | sed 's/.*:\([^.]*\).*/\1/')/releases/new?tag=v$VERSION"

print_success "Release process initiated for version $VERSION" 