#!/usr/bin/env python3
"""
Jaskr GymGrid - Web Server Entry Point
Usage: python run.py
Starts development server on http://127.0.0.1:5000
"""
import os
import socket
from app import create_app

app = create_app()

def find_available_port(preferred_port=5000, fallback_port=5050):
    env_port = os.environ.get("PORT")
    if env_port:
        return int(env_port)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", preferred_port))
            return preferred_port
    except OSError:
        return fallback_port

if __name__ == "__main__":
    port = find_available_port()
    print(f"\n==================================================")
    print(f"  Jaskr GymGrid Web Server Starting")
    print(f"  Access URL: http://127.0.0.1:{port}")
    print(f"  Demo Clock: 2026-10-30 10:00:00 (DEMO_MODE=true)")
    print(f"==================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
