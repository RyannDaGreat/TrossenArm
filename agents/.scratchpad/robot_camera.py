"""Compatibility import for scratch experiments; implementation lives in web/source/backend."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from web.source.backend.robot_camera import *
