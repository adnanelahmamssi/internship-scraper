import os
import sys

# Debug information
print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Files in current directory:", os.listdir("."))

# Add the project root to the Python path
basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, basedir)

print("Base directory:", basedir)
if os.path.exists(os.path.join(basedir, "templates")):
    print("Templates directory found in base directory")
    print("Files in templates directory:", os.listdir(os.path.join(basedir, "templates")))
else:
    print("Templates directory NOT found in base directory")

from app import create_app

# Create the application instance
application = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)