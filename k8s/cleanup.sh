#!/bin/bash
set -e

# NFL Analysis Engine Kubernetes Cleanup Script

echo "🧹 Cleaning up NFL Analysis Engine from Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Confirm deletion
read -p "⚠️  This will delete the entire nfl-analysis-engine namespace and all its resources. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled."
    exit 1
fi

echo "🗑️  Deleting resources..."

# Delete all resources in the namespace
kubectl delete -f k8s/app-deployment.yaml --ignore-not-found=true
kubectl delete -f k8s/postgresql.yaml --ignore-not-found=true
kubectl delete -f k8s/configmap.yaml --ignore-not-found=true
kubectl delete -f k8s/secrets.yaml --ignore-not-found=true

# Delete the namespace (this will delete any remaining resources)
kubectl delete -f k8s/namespace.yaml --ignore-not-found=true

# Wait for namespace deletion
echo "⏳ Waiting for namespace deletion..."
kubectl wait --for=delete namespace/nfl-analysis-engine --timeout=60s

echo "✅ Cleanup completed!"
echo ""
echo "🧼 Additional cleanup (optional):"
echo "1. Remove Docker image:"
echo "   docker rmi nfl-analysis-engine:latest"
echo ""
echo "2. Clean up local Docker cache:"
echo "   docker system prune -f"