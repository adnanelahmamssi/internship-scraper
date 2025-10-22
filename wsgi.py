import os
import sys
import logging

# Add the project root to the Python path
basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, basedir)

# Add logging to help debug template issues
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log the base directory and check if templates exist
logger.info(f"Base directory: {basedir}")
template_dir = os.path.join(basedir, 'templates')
logger.info(f"Template directory: {template_dir}")
logger.info(f"Template directory exists: {os.path.exists(template_dir)}")

if os.path.exists(template_dir):
    logger.info(f"Files in template directory: {os.listdir(template_dir)}")

from app import create_app

# Create the application instance
application = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)