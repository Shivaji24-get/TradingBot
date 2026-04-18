from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    def analyze(self, data: pd.DataFrame, market_data: Dict) -> str:
        pass
    
    @abstractmethod
    def should_enter(self, signal: str, current_position: bool) -> bool:
        pass    
    @abstractmethod
    def should_exit(self, position: Dict, current_price: float) -> bool:
        pass
    
    def get_parameters(self) -> Dict:
        return self.config