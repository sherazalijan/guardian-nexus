import sys
import os

# Add the backend folder to the path so it can resolve the 'app' module correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.main import app
