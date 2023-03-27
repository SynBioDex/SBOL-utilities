from __future__ import annotations
from copy import copy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Dict, List, Optional, Tuple, Union
from sbol_utilities.igem.qc_field_quality_score import QCFieldQualityScore

from sbol_utilities.igem.qc_fieldtype import QCFieldType


ValidationResult = Tuple[bool, Optional[str]]

@dataclass
class QCField:
    type: QCFieldType
    required: bool
    sourcePointer: str
    qualityPoints: QCFieldQualityScore
    errors: Dict[str, str]
    warnings: Dict[str, str]

    def validate(self, value) -> ValidationResult:
        # Step 1 - Check if value is present
        # If value is required then we pull missing value error
        if self.required:
            if value is None:
                return (False, self.errors["missingValueError"])
        else:
            if value is None:
                return (True, self.warnings["missingValueWarning"])

        # Step 2 - Check if value is valid
        if self.type.validate(value):
            return (True, None)
        else:
            return (False, self.errors["validationError"])
        
    def get_quality_score(self, failure:bool = False) -> QCFieldQualityScore:        
        ret = copy(self.qualityPoints)
        if failure:
            for key in ret.keys():
                ret[key] = 0
        return ret
    
            
    
