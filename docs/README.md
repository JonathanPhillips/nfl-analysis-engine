# Documentation Setup for Backstage TechDocs

## MkDocs Installation Required

The current Backstage error `spawn mkdocs ENOENT` indicates that MkDocs is not installed in the Backstage environment.

## Quick Fix Options

### Option 1: Install MkDocs in Backstage Environment
```bash
# In your Backstage environment
pip install -r docs/requirements.txt
```

### Option 2: Run Setup Script
```bash
# From project root
./docs/setup-mkdocs.sh
```

### Option 3: Disable TechDocs Temporarily
The `backstage.io/techdocs-ref` annotation has been commented out in `catalog-info.yaml` until MkDocs is available.

## Test Locally
```bash
# Test MkDocs build
mkdocs build

# Test MkDocs serve
mkdocs serve
```

## Documentation Structure

The documentation includes:
- **Getting Started**: Installation, quickstart, configuration
- **Architecture**: Overview, service layer, database, ML models  
- **API Reference**: Teams, players, games, predictions
- **Features**: Team analytics, player stats, ML predictions
- **Development**: Setup, testing, contributing

## Backstage Integration

Once MkDocs is installed in your Backstage environment:
1. Uncomment the `backstage.io/techdocs-ref: dir:.` line in `catalog-info.yaml`
2. Commit and push the change
3. TechDocs should build successfully