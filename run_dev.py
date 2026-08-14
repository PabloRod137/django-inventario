import os
import subprocess
import sys

port = os.environ.get('PORT', '8000')
subprocess.run([sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}'], check=True)
