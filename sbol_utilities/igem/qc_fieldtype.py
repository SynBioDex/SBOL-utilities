from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
import re


class FieldTypeEnum(Enum):
    STRING = "String"
    NUMBER = "Number"
    BOOLEAN = "Boolean"
    DATETIME = "DateTime"
    ENUM = "Enum"



@dataclass
class QCFieldType:
    type: FieldTypeEnum
    valid: Optional[Union[List[str], str]]

    def validate(self, value) -> bool:
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
