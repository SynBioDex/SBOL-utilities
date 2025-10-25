from typing import List, Tuple
import re

CELL_SELECTOR_REGEX = r'((\w+)!)(\$[A-Z]+\$[\d]+):(\$[A-Z]+\$[\d]+)'
CELL_LOCATION_REGEX = r'\$?(\w+)\$?(\d+)'

def col_num_to_index(col_num):
    """Converts a base-26 column number to a zero-based column index."""
    col_idx = 0
    for i, c in enumerate(reversed(col_num)):
        col_idx += (ord(c) - ord('A') + 1) * (26 ** i)
    return col_idx - 1

def col_index_to_num(col_idx):
    """Converts a zero-based column index to a base-26 column number."""
    col_num = ''
    while col_idx >= 0:
        col_num = chr((col_idx % 26) + ord('A')) + col_num
        col_idx = col_idx // 26 - 1
    return col_num

def get_area_enumeration(start_cell: str, end_cell: str) -> List[str]:
    """Generates a list of cells from the start cell to the end cell.

    Note this assumes a contiguous area of cells and the width and height of the area is not greater than 26.

    Args:
        start_cell (str): Start cell in the format of A1, $A1, A$1, or $A$1
        end_cell (str): End cell in the format of A1, $A1, A$1, or $A$1

    Raises:
        ValueError: If the start or end cell is invalid.

    Returns:
        List[str]: A list of cells from the start cell to the end cell.
    """    
    ret = []

    # Parse the start and end cells
    start_cell_match = re.match(CELL_LOCATION_REGEX, start_cell)
    end_cell_match = re.match(CELL_LOCATION_REGEX, end_cell)

    if start_cell_match is None or end_cell_match is None:
        raise ValueError(f'Invalid start/end cell: {start_cell}, {end_cell}')

    start_col = col_num_to_index(start_cell_match[1])
    start_row = int(start_cell_match[2])
    end_col = col_num_to_index(end_cell_match[1])
    end_row = int(end_cell_match[2])

    # Enumerate the cells
    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            ret.append(f'{col_index_to_num(col)}{row}')

    return ret

def get_selection(cell_selector_query: str) -> List[Tuple[str, str]]:
    """Returns a selector that can be used to return the cells from the Excel sheet.

    Args:
        cell_selector_query (str): The query to use to select the cells.

    Returns:
        List[str]: Selector strings for the cells to return.
    """
    ret = []

    # Perform the regex query
    matches = re.findall(CELL_SELECTOR_REGEX, cell_selector_query)

    if matches is None:
        raise ValueError(f'Invalid cell selector query: {cell_selector_query}')

    for match in matches:
        sheet_name = match[1]
        start_cell = match[2]
        end_cell = match[3]
        area_locations = get_area_enumeration(start_cell, end_cell)
        for area_location in area_locations:
            ret.append((sheet_name, area_location))

    return ret
