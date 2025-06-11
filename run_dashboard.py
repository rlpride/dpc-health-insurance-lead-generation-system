#!/usr/bin/env python3
"""
Dashboard launcher script for DPC Health Insurance Lead Generation System

Usage:
    python run_dashboard.py                    # Run in development mode
    python run_dashboard.py --production       # Run in production mode
    python run_dashboard.py --host 0.0.0.0 --port 8080  # Custom host/port
"""

import argparse
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """Set up environment variables and configuration."""
    # Load environment variables from .env file if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    # Set default environment variables if not set
    os.environ.setdefault('ENV', 'development')
    os.environ.setdefault('DEBUG', 'True')
    os.environ.setdefault('LOG_LEVEL', 'INFO')

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'flask',
        'plotly',
        'redis',
        'sqlalchemy',
        'pydantic'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("💡 Install them with: pip install -r requirements.txt")
        sys.exit(1)
    
    print("✅ All required dependencies are installed")

def check_database_connection():
    """Check if database connection is working."""
    try:
        from models import get_db_session
        with get_db_session() as db:
            # Simple query to test connection
            db.execute("SELECT 1")
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("💡 Make sure PostgreSQL is running and DATABASE_URL is configured")
        return False

def check_redis_connection():
    """Check if Redis connection is working."""
    try:
        import redis
        from config.settings import Settings
        settings = Settings()
        redis_client = redis.from_url(str(settings.redis_url))
        redis_client.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("💡 Make sure Redis is running and REDIS_URL is configured")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run the Lead Generation Dashboard')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--production', action='store_true', help='Run in production mode')
    parser.add_argument('--skip-checks', action='store_true', help='Skip dependency and connection checks')
    
    args = parser.parse_args()
    
    print("🚀 Starting DPC Health Insurance Lead Generation Dashboard")
    print("=" * 60)
    
    # Setup environment
    setup_environment()
    
    if not args.skip_checks:
        # Check dependencies
        print("🔍 Checking dependencies...")
        check_dependencies()
        
        # Check connections
        print("🔍 Checking connections...")
        db_ok = check_database_connection()
        redis_ok = check_redis_connection()
        
        if not db_ok:
            print("⚠️  Dashboard will run with limited functionality (database issues)")
        
        if not redis_ok:
            print("⚠️  Queue monitoring will be unavailable (Redis issues)")
    
    # Import and configure the app
    try:
        from dashboard import app
        
        # Configure app based on mode
        if args.production:
            app.config['DEBUG'] = False
            app.config['ENV'] = 'production'
            print("🏭 Running in PRODUCTION mode")
        else:
            app.config['DEBUG'] = True
            app.config['ENV'] = 'development'
            print("🛠️  Running in DEVELOPMENT mode")
        
        print(f"🌐 Dashboard will be available at: http://{args.host}:{args.port}")
        print("=" * 60)
        print("📊 Dashboard Features:")
        print("   • Real-time lead generation metrics")
        print("   • API usage and cost tracking")
        print("   • System health monitoring")
        print("   • Queue depth visualization")
        print("   • Interactive Plotly charts")
        print("=" * 60)
        
        # Start the Flask app
        app.run(
            host=args.host,
            port=args.port,
            debug=not args.production,
            threaded=True,
            use_reloader=not args.production
        )
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Failed to start dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()