from dataclasses import dataclass
from typing import Dict, List, Tuple

from sbol_utilities.igem.qc_field import QCField, QCFieldQualityScore

@dataclass
class QCEntity:
    entity_id : str
    fields: Dict[str, QCField]

    def validate(self, data: Dict) -> Tuple[QCFieldQualityScore, List[str]]:
        entity_score = QCFieldQualityScore()
        entity_validation_messages = []
        for field_id, field in self.fields.items():
            validation_result = field.validate(data[field_id])
            entity_score = field.get_quality_score(failure = validation_result[0])
            entity_validation_messages.append(validation_result[1])

        return entity_score, entity_validation_messages

