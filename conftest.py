"""Pone src/ en sys.path para que `pytest` funcione desde la raiz del repo.

Sin esto, `from qreaper import ...` falla con ModuleNotFoundError salvo que
se instale el paquete o se exporte PYTHONPATH a mano.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
