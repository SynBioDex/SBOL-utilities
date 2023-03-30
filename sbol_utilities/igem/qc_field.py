from __future__ import annotations
from copy import copy
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from sbol_utilities.igem.qc_default_evaluators import MISSING_VALUE_ERROR, MISSING_VALUE_WARNING, VALIDATION_ERROR
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

    @staticmethod
    def from_json(field_dict: Dict) -> QCField:
        ret = QCField(
            type = QCFieldType.from_json(field_dict['type']),
            required = field_dict['required'],
            sourcePointer = field_dict['sourcePointer'],
            qualityPoints = QCFieldQualityScore.from_json(field_dict['qualityPoints']),
            errors = field_dict['errors'],
            warnings = field_dict['warnings']
        )
        return ret

    def validate(self, value) -> ValidationResult:
        # Step 1 - Check if value is present
        # If value is required then we pull missing value error
        if self.required:
            if value is None:
                return (False, self.errors[MISSING_VALUE_ERROR])
        else:
            if value is None:
                return (True, self.warnings[MISSING_VALUE_WARNING])

        # Step 2 - Check if value is valid
        if self.type.validate(value):
            return (True, None)
        else:
            return (False, self.errors[VALIDATION_ERROR])

    def get_quality_score(self, failure:bool = False) -> QCFieldQualityScore:        
        ret = copy(self.qualityPoints)
        if failure:
            for key in ret.keys():
                ret[key] = 0
        return ret
