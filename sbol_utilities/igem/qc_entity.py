from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

from sbol_utilities.igem.qc_field import QCField, QCFieldQualityScore

@dataclass
class QCEntity:
    fields: Dict[str, QCField]

    def __init__(self) -> None:
        self.fields = {}

    @staticmethod
    def from_json(entity_dict: Dict) -> QCEntity:
        """Convert the JSON entity to a QCEntity object.

        Args:
            entity_dict (Dict): JSON dictionary of the entity.

        Returns:
            QCEntity: The QCEntity object.
        """
        ret = QCEntity()
        for field_id, field_dict in entity_dict['fields'].items():
            field = QCField.from_json(field_dict)
            ret.fields[field_id] = field
        return ret

    def validate(self, data: Dict) -> Tuple[QCFieldQualityScore, Dict[str, Optional[str]]]:
        """Validate the data against the entity.

        Args:
            data (Dict): JSON dictionary of the data to validate.

        Returns:
            Tuple[QCFieldQualityScore, Dict[str, Optional[str]]]: The QC score and the validation messages.
        """        
        entity_score = QCFieldQualityScore()
        entity_validation_messages: Dict[str, Optional[str]] = {}
        for field_id, field in self.fields.items():
            validation_result = field.validate(data[field_id])
            entity_score = field.get_quality_score(failure = validation_result[0])
            entity_validation_messages[field_id] = validation_result[1]

        return entity_score, entity_validation_messages

