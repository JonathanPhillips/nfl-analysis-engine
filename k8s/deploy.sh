#!/bin/bash
set -e

# NFL Analysis Engine Kubernetes Deployment Script

echo "🏈 Deploying NFL Analysis Engine to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if we can connect to Kubernetes cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

echo "✅ Connected to Kubernetes cluster"

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t nfl-analysis-engine:latest .

# Load image into local cluster (for kind/minikube)
echo "📦 Loading image into cluster..."
if command -v kind &> /dev/null && kind get clusters | grep -q "kind"; then
    echo "Loading image into kind cluster..."
    kind load docker-image nfl-analysis-engine:latest
elif command -v minikube &> /dev/null && minikube status | grep -q "Running"; then
    echo "Loading image into minikube..."
    minikube image load nfl-analysis-engine:latest
else
    echo "ℹ️  Using local Docker registry (make sure your cluster can access it)"
fi

# Apply Kubernetes manifests
echo "🚀 Applying Kubernetes manifests..."

# Create namespace first
kubectl apply -f k8s/namespace.yaml

# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# Deploy database
echo "🗄️  Deploying PostgreSQL database..."
kubectl apply -f k8s/postgresql.yaml

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/postgresql -n nfl-analysis-engine

# Deploy application
echo "🏈 Deploying NFL Analysis Engine application..."
kubectl apply -f k8s/app-deployment.yaml

# Wait for application to be ready
echo "⏳ Waiting for application to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/nfl-analysis-app -n nfl-analysis-engine

# Get service information
echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n nfl-analysis-engine
echo ""
echo "🌐 Services:"
kubectl get services -n nfl-analysis-engine
echo ""
echo "🔗 Ingress:"
kubectl get ingress -n nfl-analysis-engine

# Instructions for accessing the application
echo ""
echo "🚀 Access Instructions:"
echo ""
echo "1. Add to /etc/hosts (if using ingress):"
echo "   127.0.0.1 nfl-analysis.local"
echo ""
echo "2. Port forward (alternative access method):"
echo "   kubectl port-forward -n nfl-analysis-engine service/nfl-analysis-service 8000:80"
echo ""
echo "3. Access the application:"
echo "   - Web Interface: http://nfl-analysis.local (or http://localhost:8000 with port-forward)"
echo "   - API Documentation: http://nfl-analysis.local/api/docs"
echo ""
echo "4. Monitor deployment:"
echo "   kubectl logs -f deployment/nfl-analysis-app -n nfl-analysis-engine"
echo ""
echo "5. Run database migrations (if needed):"
echo "   kubectl exec -it deployment/nfl-analysis-app -n nfl-analysis-engine -- alembic upgrade head"