"""策略集合：import 這個套件就會把所有策略登記進 REGISTRY。"""

from strategies import breakout, momentum, momentum_revenue  # noqa: F401
from strategies.base import REGISTRY, Strategy

__all__ = ["REGISTRY", "Strategy"]
