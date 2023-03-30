from __future__ import annotations
from typing import Dict, Union


class QCFieldQualityScore( Dict[str, float]):
    """

    Data structure to store quality score for a field/entry/package.

    """    

    def __init__(self):
        super().__init__()

    def __add__(self, other:  Dict[str, float]) -> QCFieldQualityScore:
        """ Overload the + operator to add two QCFieldQualityScore objects

        Adds all the matching key values or otherwise adds the new keys

        Args:
            other (Dict[str, float]): The other QCFieldQualityScore object to add

        Returns:
            QCFieldQualityScore: QCFieldQualityScore
        """        
        for key, value in other.items():
            if key not in self.keys():
                self[key] = value
            else:
                self[key] += value
        return self
    
    def __copy__(self) -> QCFieldQualityScore:
        """ Overload the copy operator to copy a QCFieldQualityScore object

        Creates a new QCFieldQualityScore object and copies all the key values

        Returns:
            QCFieldQualityScore: _description_
        """        
        ret = QCFieldQualityScore()
        for key, value in self.items():
            ret[key] = value
        return ret
    
    def __truediv__(self, other: Union[float,int]) -> QCFieldQualityScore:
        for key, value in self.items():
            self[key] = value / other
        return self


