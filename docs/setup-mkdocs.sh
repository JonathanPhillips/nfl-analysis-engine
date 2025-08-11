#!/bin/bash
# Setup script for MkDocs TechDocs

echo "Setting up MkDocs for Backstage TechDocs..."

# Install MkDocs and required plugins
pip install mkdocs>=1.5.0
pip install mkdocs-material>=9.0.0
pip install mkdocs-techdocs-core>=1.3.0
pip install pymdown-extensions>=10.0.0

echo "MkDocs setup complete!"
echo "Test build with: mkdocs build"
echo "Test serve with: mkdocs serve"