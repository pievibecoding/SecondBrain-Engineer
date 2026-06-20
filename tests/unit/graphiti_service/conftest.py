"""Add graphiti-service root to sys.path so tests can import directly."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "graphiti-service"))
