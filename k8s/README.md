# Kubernetes Deployment Guide

This directory contains Kubernetes manifests and scripts for deploying the NFL Analysis Engine to a local Kubernetes cluster.

## 🏗️ Architecture

The deployment consists of:

- **Namespace**: `nfl-analysis-engine` - Isolated environment
- **PostgreSQL Database**: Single replica with persistent storage
- **Application**: 2 replicas with load balancing
- **Services**: ClusterIP for internal communication
- **Ingress**: External access via nginx-ingress
- **Persistent Storage**: For database data and ML models

## 📋 Prerequisites

### Required Tools
- `kubectl` - Kubernetes CLI
- `docker` - Container runtime
- Local Kubernetes cluster (kind, minikube, Docker Desktop, etc.)

### Optional Tools
- `nginx-ingress-controller` - For ingress support
- `helm` - For advanced deployments

### Verify Prerequisites
```bash
# Check kubectl
kubectl version --client

# Check cluster connection
kubectl cluster-info

# Check Docker
docker --version
```

## 🚀 Quick Deployment

Deploy everything with one command:

```bash
./k8s/deploy.sh
```

This script will:
1. Build the Docker image
2. Load it into your local cluster
3. Create the namespace
4. Deploy PostgreSQL with persistent storage
5. Deploy the application with 2 replicas
6. Set up services and ingress

## 📁 Manifest Files

### Core Resources
- `namespace.yaml` - Creates the nfl-analysis-engine namespace
- `configmap.yaml` - Application configuration
- `secrets.yaml` - Database credentials and API keys
- `postgresql.yaml` - Database deployment, service, and PVC
- `app-deployment.yaml` - Application deployment, service, and ingress

### Management Scripts
- `deploy.sh` - Complete deployment automation
- `cleanup.sh` - Remove all resources
- `manage.sh` - Management commands (logs, scaling, etc.)

## 🔧 Configuration

### Environment Variables (ConfigMap)
```yaml
PYTHONPATH: "/app"
ENVIRONMENT: "production"
DB_HOST: "postgresql-service"
DB_PORT: "5432"
ML_MODEL_PATH: "/app/models/"
```

### Secrets
Update `secrets.yaml` with your actual credentials:
```bash
# Generate base64 encoded secrets
echo -n "your-password" | base64
echo -n "your-api-key" | base64
```

### Resource Limits
```yaml
Application:
  requests: 512Mi memory, 250m CPU
  limits: 2Gi memory, 1000m CPU

Database:
  requests: 256Mi memory, 250m CPU
  limits: 512Mi memory, 500m CPU
```

## 🌐 Access Methods

### Method 1: Ingress (Recommended)
1. Add to `/etc/hosts`:
   ```
   127.0.0.1 nfl-analysis.local
   ```

2. Access application:
   - Web Interface: http://nfl-analysis.local
   - API Documentation: http://nfl-analysis.local/api/docs

### Method 2: Port Forward
```bash
# Start port forwarding
./k8s/manage.sh port

# Or manually:
kubectl port-forward -n nfl-analysis-engine service/nfl-analysis-service 8000:80
```

Access at: http://localhost:8000

### Method 3: NodePort (if needed)
Modify service type in `app-deployment.yaml`:
```yaml
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 8000
    nodePort: 30000  # Add this line
```

## 📊 Management Commands

Use the management script for common operations:

```bash
# Show deployment status
./k8s/manage.sh status

# View application logs
./k8s/manage.sh logs

# Open shell in application pod
./k8s/manage.sh shell

# Start port forwarding
./k8s/manage.sh port

# Run database migrations
./k8s/manage.sh migrate

# Restart application
./k8s/manage.sh restart

# Scale application
./k8s/manage.sh scale 3

# Debug deployment issues
./k8s/manage.sh debug
```

## 🗄️ Database Operations

### Initial Setup
After deployment, run migrations:
```bash
./k8s/manage.sh migrate
```

### Load Data
Connect to the application pod and run data loading scripts:
```bash
./k8s/manage.sh shell

# Inside the pod:
python load_teams.py
python load_2024_data.py
```

### Database Access
Direct database access:
```bash
kubectl exec -it deployment/postgresql -n nfl-analysis-engine -- psql -U nfl_user -d nfl_analysis
```

## 🔍 Monitoring & Debugging

### Check Pod Status
```bash
kubectl get pods -n nfl-analysis-engine -o wide
```

### View Logs
```bash
# Application logs
kubectl logs -f deployment/nfl-analysis-app -n nfl-analysis-engine

# Database logs
kubectl logs -f deployment/postgresql -n nfl-analysis-engine
```

### Debug Pod Issues
```bash
# Describe pod for events
kubectl describe pod <pod-name> -n nfl-analysis-engine

# Check resource usage
kubectl top pods -n nfl-analysis-engine
```

### Health Checks
The application includes health check endpoints:
- Liveness: `/api/v1/health`
- Readiness: `/api/v1/health`

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale application replicas
./k8s/manage.sh scale 5

# Or manually:
kubectl scale deployment/nfl-analysis-app --replicas=5 -n nfl-analysis-engine
```

### Vertical Scaling
Update resource limits in `app-deployment.yaml`:
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## 🔒 Security Features

### Pod Security
- Non-root user (UID 1000)
- Read-only root filesystem (where possible)
- Dropped capabilities
- Security context with fsGroup

### Network Security
- Services use ClusterIP (internal only)
- Ingress controls external access
- Network policies can be added for additional isolation

### Secret Management
- Database credentials stored in Kubernetes secrets
- API keys managed through secret resources
- Environment variables sourced from configs/secrets

## 🧹 Cleanup

Remove all resources:
```bash
./k8s/cleanup.sh
```

This will delete:
- All application pods and services
- Database and persistent volumes
- Configurations and secrets
- The entire namespace

## 🛠️ Troubleshooting

### Common Issues

**Image Pull Errors**
```bash
# For local clusters, ensure image is loaded
kind load docker-image nfl-analysis-engine:latest
# or
minikube image load nfl-analysis-engine:latest
```

**Database Connection Issues**
```bash
# Check database pod status
kubectl get pods -n nfl-analysis-engine -l app.kubernetes.io/component=database

# Check database logs
kubectl logs deployment/postgresql -n nfl-analysis-engine
```

**Application Startup Issues**
```bash
# Check application logs
kubectl logs deployment/nfl-analysis-app -n nfl-analysis-engine

# Check if database is ready
kubectl exec deployment/postgresql -n nfl-analysis-engine -- pg_isready -U nfl_user
```

**Ingress Not Working**
```bash
# Check if nginx-ingress is installed
kubectl get pods -n ingress-nginx

# Install nginx-ingress (if needed)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
```

### Performance Tuning

**Database Performance**
- Adjust PostgreSQL configuration in deployment
- Monitor resource usage and adjust limits
- Consider using a dedicated storage class

**Application Performance**
- Increase replica count for load distribution
- Adjust resource requests/limits based on usage
- Enable horizontal pod autoscaling

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Troubleshooting Guide](https://kubernetes.io/docs/tasks/debug-application-cluster/)
- [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)