"""PDF Forge Desktop — entry point."""
import sys
import os

# Ensure the package root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from pdf_forge.app import run

if __name__ == "__main__":
    sys.exit(run())
