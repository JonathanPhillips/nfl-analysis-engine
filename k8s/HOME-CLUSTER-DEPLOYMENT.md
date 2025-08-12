# Home Kubernetes Cluster Deployment

Deployment guide for the NFL Analysis Engine to the home Kubernetes cluster at `192.168.0.18`.

## 🏠 Cluster Information

- **Kubernetes API**: `192.168.0.18:6443`
- **Distribution**: K3s (lightweight Kubernetes)
- **Registry**: `192.168.0.18:30500` (insecure HTTP)
- **Storage Class**: `local-storage`
- **Assigned NodePort**: `30083` (from range 30083-30089)

## 🚀 Quick Deployment

### Prerequisites

1. **kubectl configured for home cluster**:
   ```bash
   kubectl config use-context default
   kubectl get nodes  # Should show 192.168.0.18
   ```

2. **Docker configured for insecure registry**:
   ```bash
   ./k8s/setup-docker-registry.sh
   # Follow instructions to restart Docker
   ```

### Deploy

```bash
# One-command deployment to home cluster
./k8s/deploy-home.sh
```

This script will:
1. Build the optimized Docker image
2. Push to the home registry (`192.168.0.18:30500`)
3. Deploy PostgreSQL with `local-storage`
4. Deploy the application with NodePort `30083`
5. Configure for Traefik ingress

## 🌐 Access Methods

### Primary Access (NodePort)
- **Web Interface**: http://192.168.0.18:30083
- **API Documentation**: http://192.168.0.18:30083/api/docs
- **Health Check**: http://192.168.0.18:30083/api/v1/health

### Ingress Access (Optional)
1. Add to `/etc/hosts`:
   ```
   192.168.0.18 nfl-analysis.local
   ```
2. Access at: http://nfl-analysis.local

## 📊 Architecture

```
Home Network (192.168.0.18)
├── K3s Cluster
│   ├── nfl-analysis-engine namespace
│   │   ├── PostgreSQL (local-storage PVC)
│   │   ├── NFL App (2 replicas)
│   │   └── NodePort Service (30083)
│   ├── Docker Registry (30500)
│   ├── Grafana (30030)
│   └── Prometheus (30090)
└── Storage: /mnt/kubernetes-storage/
    ├── databases/ (PostgreSQL data)
    └── persistent-volumes/ (ML models)
```

## 🗄️ Storage Configuration

### Database Storage
- **Location**: `/mnt/kubernetes-storage/databases/`
- **Size**: 10Gi PVC
- **Access**: ReadWriteOnce
- **Class**: `local-storage`

### ML Models Storage
- **Location**: `/mnt/kubernetes-storage/persistent-volumes/`
- **Size**: 5Gi PVC
- **Access**: ReadWriteOnce
- **Class**: `local-storage`

## 🔧 Configuration Details

### Resource Allocation
```yaml
PostgreSQL:
  requests: 256Mi memory, 250m CPU
  limits: 512Mi memory, 500m CPU

Application:
  requests: 512Mi memory, 250m CPU
  limits: 2Gi memory, 1000m CPU
  replicas: 2
```

### Environment Variables
```yaml
DATABASE_URL: postgresql://nfl_user:nfl_password@postgresql-service:5432/nfl_analysis
PYTHONPATH: /app
ENVIRONMENT: production
ML_MODEL_PATH: /app/models/
```

### Security Context
- Non-root user (UID 1000)
- Read-only root filesystem (where possible)
- Dropped capabilities
- Security context with fsGroup

## 📋 Post-Deployment Tasks

### 1. Run Database Migrations
```bash
kubectl exec -it deployment/nfl-analysis-app -n nfl-analysis-engine -- alembic upgrade head
```

### 2. Load Initial Data
```bash
# Load teams data
kubectl exec -it deployment/nfl-analysis-app -n nfl-analysis-engine -- python load_teams.py

# Load 2024 season data
kubectl exec -it deployment/nfl-analysis-app -n nfl-analysis-engine -- python load_2024_data.py
```

### 3. Verify Deployment
```bash
# Check all pods are running
kubectl get pods -n nfl-analysis-engine

# Check service and get NodePort
kubectl get services -n nfl-analysis-engine

# Test health endpoint
curl http://192.168.0.18:30083/api/v1/health
```

## 📊 Monitoring Integration

### Grafana Dashboards
- **URL**: http://192.168.0.18:30030
- **Login**: admin/admin
- **Metrics**: Available for NFL Analysis Engine pods

### Prometheus Metrics
- **URL**: http://192.168.0.18:30090
- **Targets**: NFL Analysis Engine application metrics

### Useful Monitoring Queries
```prometheus
# CPU usage
rate(container_cpu_usage_seconds_total{pod=~"nfl-analysis-app-.*"}[5m])

# Memory usage
container_memory_usage_bytes{pod=~"nfl-analysis-app-.*"}

# Request rate
rate(http_requests_total{job="nfl-analysis-engine"}[5m])
```

## 🛠️ Management Commands

### View Status
```bash
kubectl get pods -n nfl-analysis-engine -o wide
kubectl get services -n nfl-analysis-engine
kubectl get pvc -n nfl-analysis-engine
```

### View Logs
```bash
# Application logs
kubectl logs -f deployment/nfl-analysis-app -n nfl-analysis-engine

# Database logs
kubectl logs -f deployment/postgresql -n nfl-analysis-engine
```

### Scale Application
```bash
# Scale to 3 replicas
kubectl scale deployment/nfl-analysis-app --replicas=3 -n nfl-analysis-engine

# Check scaling status
kubectl get pods -n nfl-analysis-engine -l app.kubernetes.io/component=application
```

### Debug Issues
```bash
# Describe pods for events
kubectl describe pod -n nfl-analysis-engine

# Check recent events
kubectl get events -n nfl-analysis-engine --sort-by=.metadata.creationTimestamp

# Shell into application pod
kubectl exec -it deployment/nfl-analysis-app -n nfl-analysis-engine -- /bin/bash
```

## 🔄 Updates and Maintenance

### Update Application
```bash
# Build and push new image
docker build -f Dockerfile.k8s -t nfl-analysis-engine:v2 .
docker tag nfl-analysis-engine:v2 192.168.0.18:30500/nfl-analysis-engine:v2
docker push 192.168.0.18:30500/nfl-analysis-engine:v2

# Update deployment
kubectl set image deployment/nfl-analysis-app nfl-analysis-app=192.168.0.18:30500/nfl-analysis-engine:v2 -n nfl-analysis-engine

# Check rollout status
kubectl rollout status deployment/nfl-analysis-app -n nfl-analysis-engine
```

### Backup Database
```bash
# Create database backup
kubectl exec deployment/postgresql -n nfl-analysis-engine -- pg_dump -U nfl_user nfl_analysis > nfl_backup_$(date +%Y%m%d).sql

# Copy backup from pod
kubectl cp nfl-analysis-engine/postgresql-pod:/tmp/backup.sql ./nfl_backup.sql
```

### Rollback if Needed
```bash
# Rollback to previous version
kubectl rollout undo deployment/nfl-analysis-app -n nfl-analysis-engine

# Check rollback status
kubectl rollout status deployment/nfl-analysis-app -n nfl-analysis-engine
```

## 🧹 Cleanup

### Remove Application Only
```bash
kubectl delete -f k8s/app-deployment.yaml
```

### Complete Cleanup
```bash
kubectl delete namespace nfl-analysis-engine
```

### Remove from Registry
```bash
# Check what's in registry
curl http://192.168.0.18:30500/v2/_catalog

# Remove specific image (requires registry API calls or manual cleanup)
```

## 🔍 Troubleshooting

### Registry Issues
```bash
# Test registry connectivity
curl http://192.168.0.18:30500/v2/_catalog

# Check Docker daemon configuration
cat ~/.docker/daemon.json  # macOS
cat /etc/docker/daemon.json  # Linux
```

### Storage Issues
```bash
# Check storage class
kubectl get storageclass local-storage

# Check PV availability
kubectl get pv

# Check node storage
kubectl describe node
```

### Networking Issues
```bash
# Check node IP and ports
kubectl get nodes -o wide

# Test NodePort accessibility
curl http://192.168.0.18:30083/api/v1/health

# Check service endpoints
kubectl get endpoints -n nfl-analysis-engine
```

### Performance Issues
```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n nfl-analysis-engine

# Monitor in real-time
watch kubectl get pods -n nfl-analysis-engine
```

## 📞 Support

For cluster-specific issues:
- **Cluster Admin**: Jon
- **Monitoring**: http://192.168.0.18:30030 (Grafana)
- **Registry**: http://192.168.0.18:30500/v2/_catalog
- **Cluster Info**: `kubectl cluster-info`

---

**Ready to deploy?** Run `./k8s/deploy-home.sh` and your NFL Analysis Engine will be live at http://192.168.0.18:30083! 🏈