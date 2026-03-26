"""
Utility for sorting parking slots by position (left to right, row by row)
"""

from typing import List, Dict, Any
import math


def sort_slots_by_position(predictions: List[Dict[str, Any]], row_threshold: int = 50) -> List[Dict[str, Any]]:
    """
    Sort parking slot predictions by position (left to right, row by row)
    
    Args:
        predictions: List of prediction dictionaries from Roboflow workflow
        row_threshold: Vertical distance threshold to consider slots in the same row (pixels)
        
    Returns:
        Sorted list of predictions with consistent ordering
    """
    if not predictions:
        return []
    
    # Create a list of (prediction, y_center, x_center) tuples for sorting
    slots_with_positions = []
    for pred in predictions:
        x_center = pred.get("x", 0)
        y_center = pred.get("y", 0)
        slots_with_positions.append((pred, y_center, x_center))
    
    # Group slots into rows based on y-coordinate proximity
    # First, sort by y-coordinate to identify rows
    slots_with_positions.sort(key=lambda item: item[1])  # Sort by y_center
    
    rows = []
    current_row = []
    current_row_y = None
    
    for slot_data in slots_with_positions:
        pred, y_center, x_center = slot_data
        
        if current_row_y is None:
            # First slot - start first row
            current_row_y = y_center
            current_row.append(slot_data)
        elif abs(y_center - current_row_y) <= row_threshold:
            # Slot is in the same row
            current_row.append(slot_data)
        else:
            # New row detected
            rows.append(current_row)
            current_row = [slot_data]
            current_row_y = y_center
    
    # Add the last row
    if current_row:
        rows.append(current_row)
    
    # Sort each row by x-coordinate (left to right)
    sorted_predictions = []
    for row in rows:
        # Sort row by x_center (left to right)
        row.sort(key=lambda item: item[2])
        # Extract just the predictions
        sorted_predictions.extend([item[0] for item in row])
    
    return sorted_predictions


def assign_sorted_slot_ids(predictions: List[Dict[str, Any]], row_threshold: int = 50) -> List[Dict[str, Any]]:
    """
    Sort parking slots by position and assign sequential slot IDs
    
    Args:
        predictions: List of prediction dictionaries from Roboflow workflow
        row_threshold: Vertical distance threshold to consider slots in the same row (pixels)
        
    Returns:
        List of predictions with sorted slot IDs (1, 2, 3, ...)
    """
    # Sort predictions by position
    sorted_predictions = sort_slots_by_position(predictions, row_threshold)
    
    # Assign sequential slot IDs
    for idx, pred in enumerate(sorted_predictions, start=1):
        pred['sorted_slot_id'] = idx
    
    return sorted_predictions
