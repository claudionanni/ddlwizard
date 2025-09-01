#!/bin/bash

# DDL Wizard GitHub Repository Setup Script
# This script helps you create a GitHub repository for the DDL Wizard project

echo "🧙‍♂️ DDL Wizard GitHub Repository Setup"
echo "======================================"
echo

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📋 Initializing git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📋 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
PIPFILE.lock

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
*.log
*.tmp
comparison_demo/
output/
migrations/
backups/
*.sql.bak

# Sensitive configuration files
config.yaml
*.key
*.pem
*.crt

# Database files
*.db
*.sqlite
*.sqlite3
EOF
    echo "✅ .gitignore created"
else
    echo "✅ .gitignore already exists"
fi

# Stage all files
echo "📋 Staging files for commit..."
git add .

# Create initial commit if no commits exist
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "📋 Creating initial commit..."
    git commit -m "🧙‍♂️ Initial commit: DDL Wizard - Enterprise MariaDB Schema Management Tool

Features:
- Schema comparison and migration generation
- Foreign key constraint support
- Safety analysis and dependency management
- Interactive mode with colored output
- Migration history tracking
- Multi-format documentation export
- YAML configuration with profiles
- Enterprise-grade features for production use"
    echo "✅ Initial commit created"
else
    echo "✅ Repository already has commits"
fi

echo
echo "🎯 Next Steps to Create GitHub Repository:"
echo "=========================================="
echo
echo "1. Go to GitHub.com and create a new repository named 'ddlwizard'"
echo "   - Make it public or private as you prefer"
echo "   - Don't initialize with README, .gitignore, or license (we already have them)"
echo
echo "2. Copy the repository URL (it will look like: https://github.com/YOUR_USERNAME/ddlwizard.git)"
echo
echo "3. Run these commands to connect your local repo to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/ddlwizard.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo
echo "4. Your DDL Wizard will be live on GitHub! 🚀"
echo
echo "📚 Repository Features:"
echo "- Complete enterprise DDL Wizard codebase"
echo "- Comprehensive README with usage examples"
echo "- Requirements file for easy installation"
echo "- Sample configuration files"
echo "- Professional documentation"
echo
echo "🔧 To update the repository later:"
echo "   git add ."
echo "   git commit -m 'Your commit message'"
echo "   git push"
echo
