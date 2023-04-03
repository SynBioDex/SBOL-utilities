from dataclasses import dataclass
from typing import Dict


@dataclass
class QCInputData:
    source_location: str
    data: Dict
