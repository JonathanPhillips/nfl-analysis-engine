#!/bin/bash
# NFL Analysis Engine Kubernetes Management Script

NAMESPACE="nfl-analysis-engine"

function show_help() {
    echo "🏈 NFL Analysis Engine Kubernetes Management"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status     - Show deployment status"
    echo "  logs       - Show application logs"
    echo "  shell      - Open shell in application pod"
    echo "  port       - Start port forwarding (8000:80)"
    echo "  migrate    - Run database migrations"
    echo "  restart    - Restart application deployment"
    echo "  scale      - Scale application (usage: $0 scale 3)"
    echo "  debug      - Show debug information"
    echo "  help       - Show this help"
}

function check_namespace() {
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        echo "❌ Namespace '$NAMESPACE' not found. Deploy first with ./k8s/deploy.sh"
        exit 1
    fi
}

function show_status() {
    echo "🏈 NFL Analysis Engine Status"
    echo ""
    echo "📊 Pods:"
    kubectl get pods -n $NAMESPACE -o wide
    echo ""
    echo "🌐 Services:"
    kubectl get services -n $NAMESPACE
    echo ""
    echo "🔗 Ingress:"
    kubectl get ingress -n $NAMESPACE
    echo ""
    echo "💾 PersistentVolumeClaims:"
    kubectl get pvc -n $NAMESPACE
}

function show_logs() {
    echo "📋 Application Logs (press Ctrl+C to exit):"
    kubectl logs -f deployment/nfl-analysis-app -n $NAMESPACE
}

function open_shell() {
    echo "🐚 Opening shell in application pod..."
    kubectl exec -it deployment/nfl-analysis-app -n $NAMESPACE -- /bin/bash
}

function start_port_forward() {
    echo "🔗 Starting port forward: localhost:8000 -> service:80"
    echo "   Access at: http://localhost:8000"
    echo "   API Docs at: http://localhost:8000/api/docs"
    echo "   Press Ctrl+C to stop"
    kubectl port-forward -n $NAMESPACE service/nfl-analysis-service 8000:80
}

function run_migrations() {
    echo "🗄️  Running database migrations..."
    kubectl exec deployment/nfl-analysis-app -n $NAMESPACE -- alembic upgrade head
    echo "✅ Migrations completed"
}

function restart_app() {
    echo "🔄 Restarting application deployment..."
    kubectl rollout restart deployment/nfl-analysis-app -n $NAMESPACE
    echo "⏳ Waiting for rollout to complete..."
    kubectl rollout status deployment/nfl-analysis-app -n $NAMESPACE
    echo "✅ Application restarted"
}

function scale_app() {
    if [ -z "$2" ]; then
        echo "❌ Please specify replica count: $0 scale <replicas>"
        exit 1
    fi
    echo "📈 Scaling application to $2 replicas..."
    kubectl scale deployment/nfl-analysis-app --replicas=$2 -n $NAMESPACE
    echo "⏳ Waiting for scaling to complete..."
    kubectl rollout status deployment/nfl-analysis-app -n $NAMESPACE
    echo "✅ Application scaled to $2 replicas"
}

function show_debug() {
    echo "🔍 Debug Information"
    echo ""
    echo "📊 Deployment Status:"
    kubectl describe deployment/nfl-analysis-app -n $NAMESPACE
    echo ""
    echo "🗄️  Database Status:"
    kubectl describe deployment/postgresql -n $NAMESPACE
    echo ""
    echo "🔧 Recent Events:"
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10
}

# Main command handling
case "$1" in
    "status")
        check_namespace
        show_status
        ;;
    "logs")
        check_namespace
        show_logs
        ;;
    "shell")
        check_namespace
        open_shell
        ;;
    "port")
        check_namespace
        start_port_forward
        ;;
    "migrate")
        check_namespace
        run_migrations
        ;;
    "restart")
        check_namespace
        restart_app
        ;;
    "scale")
        check_namespace
        scale_app "$@"
        ;;
    "debug")
        check_namespace
        show_debug
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac