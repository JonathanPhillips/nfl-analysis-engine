"""NFL Analysis Engine data models."""

from .base import Base, BaseModel, BasePydanticModel
from .team import TeamModel
from .player import PlayerModel
from .game import GameModel
from .play import PlayModel

# Ensure all models are imported for relationship resolution
__all__ = ['Base', 'BaseModel', 'BasePydanticModel', 'TeamModel', 'PlayerModel', 'GameModel', 'PlayModel']