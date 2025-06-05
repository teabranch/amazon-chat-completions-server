# Documentation

This directory contains the Jekyll-based documentation for the Amazon Chat Completions Server, designed for deployment to GitHub Pages.

## 🚀 Quick Setup

### Local Development

1. **Install Ruby and Bundler** (if not already installed):
   ```bash
   # On macOS with Homebrew
   brew install ruby
   
   # On Ubuntu/Debian
   sudo apt-get install ruby-full build-essential zlib1g-dev
   ```

2. **Install Jekyll dependencies**:
   ```bash
   cd docs
   bundle install
   ```

3. **Serve locally**:
   ```bash
   bundle exec jekyll serve
   ```
   
   The site will be available at `http://localhost:4000/open-amazon-chat-completions-server/`

### GitHub Pages Deployment

The documentation is automatically deployed to GitHub Pages via GitHub Actions when changes are pushed to the `main` branch in the `docs/` directory.

**Setup Requirements:**
1. Enable GitHub Pages in repository settings
2. Set source to "GitHub Actions"
3. The workflow in `.github/workflows/pages.yml` will handle the rest

## 📁 Structure

```
docs/
├── _config.yml              # Jekyll configuration
├── Gemfile                  # Ruby dependencies
├── index.md                 # Homepage
├── getting-started.md       # Setup guide
├── api-reference.md         # API documentation
├── cli-reference.md         # CLI documentation
├── development.md           # Development guide
└── guides/                  # Specialized guides
    ├── index.md            # Guide navigation
    ├── usage.md            # Programming examples
    ├── aws-authentication.md # AWS setup
    ├── architecture.md     # System design
    ├── core-components.md  # Technical details
    ├── testing.md          # Testing guide
    └── packaging.md        # Distribution guide
```

## 🎨 Theme and Styling

- **Theme**: Minimal theme optimized for technical documentation
- **Features**: 
  - Responsive design
  - Syntax highlighting
  - Table of contents generation
  - SEO optimization
  - Search functionality

## 📝 Writing Documentation

### Front Matter

All pages should include Jekyll front matter:

```yaml
---
layout: default
title: Page Title
nav_order: 1
description: "Page description for SEO"
parent: Parent Page (if applicable)
---
```

### Table of Contents

Add automatic table of contents with:

```markdown
## Table of Contents
{:toc}
```

### Code Blocks

Use fenced code blocks with language specification:

````markdown
```bash
# Example command
amazon-chat serve --port 8000
```
````

### Navigation

Pages are automatically included in navigation based on:
- `nav_order`: Controls ordering
- `parent`: Creates hierarchical structure
- `header_pages`: Defined in `_config.yml`

## 🔧 Configuration

Key configuration files:

- **`_config.yml`**: Jekyll site configuration
- **`Gemfile`**: Ruby gem dependencies
- **`.github/workflows/pages.yml`**: GitHub Actions deployment

## 🌐 Live Site

The documentation is available at: https://teabranch.github.io/open-amazon-chat-completions-server/

## 📚 Resources

- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Minimal Theme](https://github.com/pages-themes/minimal) 