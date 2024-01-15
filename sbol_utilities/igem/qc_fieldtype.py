from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any
import re


class FieldTypeEnum(Enum):
    STRING = "String"
    NUMBER = "Number"
    BOOLEAN = "Boolean"
    DATETIME = "DateTime"
    ENUM = "Enum"



@dataclass
class QCFieldType:
    """A class to represent a QC field type"""

    type: FieldTypeEnum
    valid: Optional[Union[List[str], str]]

    @staticmethod
    def from_json(field_type_dict: Dict) -> QCFieldType:
        """ Create a QCFieldType object from a json string

        Args:
            field_type (str): The json string to create the object from

        Returns:
            QCFieldType: The created object
        """
        ret = QCFieldType(FieldTypeEnum(field_type_dict['type']), field_type_dict['valid'])
        return ret

    def validate(self, value: Any) -> bool:
        """ Validate a value against the field type

        Args:
            value (Any): The value to validate

        Raises:
            ValueError: If invalid data is passed to the function
            ValueError: An uknown field type is passed to the function

        Returns:
            bool: True if the value is valid, False otherwise
        """
        if self.type == FieldTypeEnum.STRING:
            # Check if valid field has a string
            if isinstance(self.valid, str):
                match_pattern = self.valid
                # Check if regex pattern stored in self.valid matches value
                if re.match(match_pattern, value):
                    return True
                else:
                    return False
            else:
                raise ValueError(f"Invalid field data fround for type: {self.type}")
        elif self.type == FieldTypeEnum.NUMBER:
            try:
                float(value)
                return True
            except ValueError:
                return False
        elif self.type == FieldTypeEnum.BOOLEAN:
            return value in ["True", "False"]
        elif self.type == FieldTypeEnum.DATETIME:
            try:
                datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
                return True
            except ValueError:
                return False
        elif self.type == FieldTypeEnum.ENUM:
            return value in self.valid
        else:
            raise ValueError("Unknown field type")
