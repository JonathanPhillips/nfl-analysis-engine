#!/usr/bin/env python3
"""Quick test to verify the server works."""

if __name__ == "__main__":
    from src.api.main import app
    import uvicorn
    
    print("Starting NFL Analysis Engine on http://localhost:8002")
    print("Routes available:")
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"  - {route.path}")
    
    print("\nStarting server...")
    uvicorn.run(app, host="0.0.0.0", port=8002)