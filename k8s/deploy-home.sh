#!/bin/bash
set -e

# NFL Analysis Engine Deployment to Home Kubernetes Cluster
# Cluster: 192.168.0.18:6443 (K3s)
# Registry: 192.168.0.18:30500

echo "🏈 Deploying NFL Analysis Engine to Home Kubernetes Cluster..."

# Configuration
REGISTRY="192.168.0.18:30500"
IMAGE_NAME="nfl-analysis-engine"
IMAGE_TAG="latest"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

# Check if kubectl is available and configured
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Test connection to home cluster
echo "🔌 Testing connection to home cluster (192.168.0.18:6443)..."
if ! kubectl get nodes &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    echo "   Make sure you're using the kubernetes-home context:"
    echo "   kubectl config use-context default"
    exit 1
fi

echo "✅ Connected to home Kubernetes cluster"
kubectl get nodes

# Build Docker image
echo "🔨 Building Docker image..."
docker build -f Dockerfile.k8s -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Tag image for registry
echo "🏷️  Tagging image for registry..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE}

# Push to registry
echo "📦 Pushing image to registry (${REGISTRY})..."
docker push ${FULL_IMAGE}

# Verify image in registry
echo "🔍 Verifying image in registry..."
curl -s http://${REGISTRY}/v2/${IMAGE_NAME}/tags/list | grep -q ${IMAGE_TAG} && echo "✅ Image successfully pushed to registry"

# Update image references in manifests
echo "📝 Updating deployment manifests with registry image..."
sed -i.bak "s|image: nfl-analysis-engine:latest|image: ${FULL_IMAGE}|g" k8s/app-deployment.yaml

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
kubectl wait --for=condition=available --timeout=300s deployment/postgresql -n nfl-analysis-engine || true

# Check database pod status
echo "📊 Database pod status:"
kubectl get pods -n nfl-analysis-engine -l app.kubernetes.io/component=database

# Deploy application
echo "🏈 Deploying NFL Analysis Engine application..."
kubectl apply -f k8s/app-deployment.yaml

# Wait for application to be ready
echo "⏳ Waiting for application to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/nfl-analysis-app -n nfl-analysis-engine || true

# Get service information
echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n nfl-analysis-engine -o wide
echo ""
echo "🌐 Services:"
kubectl get services -n nfl-analysis-engine
echo ""

# Get NodePort
NODE_PORT=$(kubectl get service nfl-analysis-service -n nfl-analysis-engine -o jsonpath='{.spec.ports[0].nodePort}')

echo "🚀 Access Instructions:"
echo ""
echo "1. Direct NodePort Access:"
echo "   - Web Interface: http://192.168.0.18:${NODE_PORT}"
echo "   - API Documentation: http://192.168.0.18:${NODE_PORT}/api/docs"
echo ""
echo "2. Add to /etc/hosts for ingress (optional):"
echo "   192.168.0.18 nfl-analysis.local"
echo ""
echo "3. Monitor deployment:"
echo "   kubectl logs -f deployment/nfl-analysis-app -n nfl-analysis-engine"
echo ""
echo "4. Run database migrations:"
echo "   kubectl exec -it deployment/nfl-analysis-app -n nfl-analysis-engine -- alembic upgrade head"
echo ""
echo "5. Load initial data:"
echo "   kubectl exec -it deployment/nfl-analysis-app -n nfl-analysis-engine -- python load_teams.py"
echo ""
echo "📊 Monitoring available at:"
echo "   - Grafana: http://192.168.0.18:30030 (admin/admin)"
echo "   - Prometheus: http://192.168.0.18:30090"

# Restore original deployment file
mv k8s/app-deployment.yaml.bak k8s/app-deployment.yaml