#!/bin/bash
# Configure Docker to use the home cluster's insecure registry

REGISTRY_HOST="192.168.0.18:30500"

echo "🔧 Configuring Docker for home cluster registry ($REGISTRY_HOST)..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS Docker Desktop
    DOCKER_CONFIG_DIR="$HOME/.docker"
    DOCKER_CONFIG_FILE="$DOCKER_CONFIG_DIR/daemon.json"
    
    echo "📝 Configuring Docker Desktop on macOS..."
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    DOCKER_CONFIG_DIR="/etc/docker"
    DOCKER_CONFIG_FILE="$DOCKER_CONFIG_DIR/daemon.json"
    
    echo "📝 Configuring Docker on Linux..."
    echo "⚠️  This requires sudo privileges to modify /etc/docker/daemon.json"
    
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

# Create Docker config directory if it doesn't exist
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo mkdir -p "$DOCKER_CONFIG_DIR"
else
    mkdir -p "$DOCKER_CONFIG_DIR"
fi

# Check if daemon.json exists
if [ -f "$DOCKER_CONFIG_FILE" ]; then
    echo "📋 Existing Docker configuration found"
    
    # Check if insecure-registries already exists
    if grep -q "insecure-registries" "$DOCKER_CONFIG_FILE"; then
        echo "🔍 Checking if registry is already configured..."
        
        if grep -q "$REGISTRY_HOST" "$DOCKER_CONFIG_FILE"; then
            echo "✅ Registry $REGISTRY_HOST is already configured"
            exit 0
        else
            echo "⚠️  insecure-registries exists but our registry is not listed"
            echo "📝 Please manually add \"$REGISTRY_HOST\" to the insecure-registries array in:"
            echo "   $DOCKER_CONFIG_FILE"
            exit 1
        fi
    else
        echo "⚠️  daemon.json exists but doesn't have insecure-registries"
        echo "📝 Please manually add the following to $DOCKER_CONFIG_FILE:"
        echo '   "insecure-registries": ["'$REGISTRY_HOST'"]'
        exit 1
    fi
else
    echo "📝 Creating new Docker daemon configuration..."
    
    # Create new daemon.json
    cat > /tmp/daemon.json << EOF
{
  "insecure-registries": ["$REGISTRY_HOST"]
}
EOF
    
    # Copy to the correct location
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo cp /tmp/daemon.json "$DOCKER_CONFIG_FILE"
        sudo chown root:root "$DOCKER_CONFIG_FILE"
        sudo chmod 644 "$DOCKER_CONFIG_FILE"
    else
        cp /tmp/daemon.json "$DOCKER_CONFIG_FILE"
    fi
    
    rm /tmp/daemon.json
    echo "✅ Docker configuration created at $DOCKER_CONFIG_FILE"
fi

echo ""
echo "🔄 Please restart Docker for the changes to take effect:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "   - Docker Desktop: Right-click Docker icon → Restart"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "   sudo systemctl restart docker"
fi

echo ""
echo "🧪 Test the configuration after restart:"
echo "   docker pull hello-world"
echo "   docker tag hello-world $REGISTRY_HOST/hello-world:test"
echo "   docker push $REGISTRY_HOST/hello-world:test"
echo "   curl http://$REGISTRY_HOST/v2/_catalog"