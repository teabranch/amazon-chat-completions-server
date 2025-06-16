#!/bin/bash
# Setup script for conventional commits and automatic version management

echo "🔧 Setting up conventional commits for automatic version management..."

# Set git commit template
git config commit.template .gitmessage
echo "✅ Git commit template configured"

# Optional: Set up git hooks for commit message validation (requires pre-commit)
if command -v pre-commit &> /dev/null; then
    echo "📝 pre-commit detected - you can add conventional commit validation"
    echo "   Add this to your .pre-commit-config.yaml:"
    echo ""
    echo "  - repo: https://github.com/compilerla/conventional-pre-commit"
    echo "    rev: v3.0.0"
    echo "    hooks:"
    echo "      - id: conventional-pre-commit"
    echo "        stages: [commit-msg]"
else
    echo "💡 Consider installing pre-commit for commit message validation:"
    echo "   pip install pre-commit"
    echo "   pre-commit install --hook-type commit-msg"
fi

echo ""
echo "🚀 Setup complete! Your commits will now trigger automatic version management:"
echo ""
echo "   feat: new feature      → minor version bump (2.0.3 → 2.1.0)"
echo "   fix: bug fix          → patch version bump (2.0.3 → 2.0.4)" 
echo "   feat!: breaking change → major version bump (2.0.3 → 3.0.0)"
echo ""
echo "📖 See VERSION_MANAGEMENT.md for complete documentation" 