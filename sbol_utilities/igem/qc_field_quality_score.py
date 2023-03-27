from __future__ import annotations
from typing import Dict


class QCFieldQualityScore( Dict[str, float]):
    def __add__(self, other:  Dict[str, float]):
        for key, value in other.items():
            self[key] += value
        return self
    
    def __copy__(self) -> QCFieldQualityScore:
        ret = QCFieldQualityScore()
        for key, value in self.items():
            ret[key] = value
        return ret
    
    def __truediv__(self, other: float):
        for key, value in self.items():
            self[key] = value / other
        return self


