import sys
import os

# Ensure the backend directory is on the path so all modules import correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# Also ensure the tests directory is on the path so helpers can be imported
sys.path.insert(0, os.path.dirname(__file__))
