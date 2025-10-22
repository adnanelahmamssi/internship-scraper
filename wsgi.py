import os
import sys

# Debug information
print("=" * 50)
print("WSGI DEBUG INFORMATION")
print("=" * 50)
print("Python version:", sys.version)
print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Files in current directory:", os.listdir("."))
print("Environment variables:")
for key, value in sorted(os.environ.items()):
    if 'RENDER' in key or 'PATH' in key:
        print(f"  {key}: {value}")

# Check for templates directory
template_dir = os.path.join(os.getcwd(), 'templates')
if os.path.exists(template_dir):
    print(f"Templates directory found: {template_dir}")
    print(f"Files in templates directory: {os.listdir(template_dir)}")
else:
    print(f"Templates directory NOT found at: {template_dir}")
    # Try alternative locations
    alt_locations = [
        '/opt/render/project/src/templates',
        os.path.join(os.path.dirname(__file__), 'templates')
    ]
    for location in alt_locations:
        if os.path.exists(location):
            print(f"Templates found at alternative location: {location}")
            print(f"Files: {os.listdir(location)}")
            break
    else:
        print("Templates directory not found in any expected location")

print("=" * 50)

from app import create_app

# Create the application instance
application = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)