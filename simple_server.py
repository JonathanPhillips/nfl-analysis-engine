#!/usr/bin/env python3
"""Minimal server for testing."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
async def root():
    return HTMLResponse("""
    <html>
        <head><title>NFL Analysis Engine - Test</title></head>
        <body>
            <h1>NFL Analysis Engine</h1>
            <p>Server is running!</p>
            <ul>
                <li><a href="/web/">Go to Web Interface</a></li>
                <li><a href="/api/docs">API Documentation</a></li>
            </ul>
        </body>
    </html>
    """)

@app.get("/test")
async def test():
    return {"status": "Server is working!"}

if __name__ == "__main__":
    import uvicorn
    print("Starting simple test server on http://localhost:8003")
    uvicorn.run(app, host="127.0.0.1", port=8003)