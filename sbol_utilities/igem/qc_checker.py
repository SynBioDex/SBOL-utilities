from __future__ import annotations
from typing import Dict, Optional, Tuple
from pathlib import Path

from sbol_utilities.igem.qc_entity import QCEntity
from sbol_utilities.igem.qc_field import QCFieldQualityScore

class QCChecker:
    """Class to perform the QC check on a package."""

    def __init__(self):
        """Initialize the QC checker.

        Args:
            qc_json_file: The QC JSON file to use.
        """
        self.entity: Dict[str, QCEntity]

    @staticmethod
    def from_json(schema_json_dict: Dict) -> QCChecker:
        """Read the QC JSON file and populate the QCChecker object."""
        # Read the 
        ret = QCChecker()
        for entity_id, entity_dict in schema_json_dict.items():
            entity = QCEntity.from_json(entity_dict)
            ret.entity[entity_id] = entity

    def perform_qc_check(self, package_data: Dict) -> Tuple[QCFieldQualityScore, str, Dict[str, Dict[str, Optional[str]]]]:
        """Perform the QC check on the package data.

        Package data shape Example:

        {
        
            "entity_id": [
                {
                    "source_location": "Whatever Excel Location is",
                    "data": { whatever data is }
                }
            ]
            "entity_id": [
                {
                    "source_location": "Whatever Excel Location is",
                    "data": { whatever data is }
                }
        }


        Args:
            package_data: The package data to check.

        Returns:
            The package data with the QC check results.
        """
        # Step through each QC section
        # Step through each QC field
        # Get the corresponding value from the package data
        # Validate the value
        # Compute the total score
        overall_score = QCFieldQualityScore()
        errors = {}
        for entity_id, entity in self.entity.items():
            # Pass the package data to the entity to validate
            data_to_validate = package_data[entity_id]
            normailization_factor = len(data_to_validate)
            # Since this can be a collection of matching entity types, we need to iterate through each
            for item in data_to_validate:
                entity_qc_score, entity_error_messages = entity.validate(item["data"])
                # Add the QC score to the item
                overall_score += entity_qc_score/normailization_factor
                # Add the error messages to the item
                errors[entity_id] = entity_error_messages

        return overall_score, errors


