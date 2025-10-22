import os
import sys

# Add the project root to the Python path
basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, basedir)

from app import create_app

# Create the application instance
application = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)