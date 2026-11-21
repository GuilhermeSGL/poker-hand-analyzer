"""pokerhud — estatísticas de HUD e alertas de leaks a partir de hand histories."""

from .parser import Hand, load_hands, parse_hand
from .stats import PlayerStats, compute, leaks, player_type

__all__ = ["Hand", "PlayerStats", "compute", "leaks", "load_hands", "parse_hand", "player_type"]
__version__ = "1.0.0"
