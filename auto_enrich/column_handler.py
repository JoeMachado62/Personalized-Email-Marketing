"""
Column mapping handler for flexible CSV processing.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

logger = logging.getLogger(__name__)


class ColumnMapper:
    """Handles column mapping between user CSV and expected fields."""
    
    def __init__(self, mapping_file: Optional[Path] = None):
        """
        Initialize with optional mapping file.
        
        Args:
            mapping_file: Path to JSON file containing column mappings
        """
        self.mappings = {}
        self.reverse_mappings = {}
        self.enrichment_targets = []
        
        if mapping_file and mapping_file.exists():
            self.load_mappings(mapping_file)
    
    def load_mappings(self, mapping_file: Path):
        """Load column mappings from JSON file."""
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
            
            # Handle different mapping formats
            if isinstance(data, dict):
                # Format: {"column_name": {"field_type": "...", "is_target": bool}}
                for col_name, mapping_info in data.items():
                    if isinstance(mapping_info, dict):
                        field_type = mapping_info.get('field_type')
                        is_target = mapping_info.get('is_target', False)
                        
                        if field_type and field_type != 'ignore':
                            self.mappings[field_type] = col_name
                            self.reverse_mappings[col_name] = field_type
                            
                            if is_target:
                                self.enrichment_targets.append(col_name)
            
            logger.info(f"Loaded mappings for {len(self.mappings)} fields")
            logger.info(f"Enrichment targets: {self.enrichment_targets}")
            
        except Exception as e:
            logger.error(f"Failed to load mappings: {e}")
    
    def get_column_for_field(self, field_type: str, df: pd.DataFrame) -> Optional[str]:
        """
        Get the column name for a given field type.
        
        Args:
            field_type: The field type to look for
            df: The DataFrame to search in
            
        Returns:
            Column name if found, None otherwise
        """
        # First check explicit mappings
        if field_type in self.mappings:
            col_name = self.mappings[field_type]
            if col_name in df.columns:
                return col_name
        
        # If no mapping, try auto-detection
        return self._auto_detect_column(field_type, df)
    
    def _auto_detect_column(self, field_type: str, df: pd.DataFrame) -> Optional[str]:
        """Auto-detect column based on field type."""
        col_lower = [c.lower() for c in df.columns]
        
        # Define detection patterns for each field type
        patterns = {
            'company_name': ['company', 'dealer', 'business', 'name'],
            'address': ['address', 'location', 'street'],
            'phone': ['phone', 'tel', 'mobile'],
            'email': ['email', 'e-mail'],
            'city': ['city'],
            'state': ['state'],
            'zip_code': ['zip', 'postal'],
            'website': ['website', 'url', 'web'],
            'contact_name': ['contact', 'person'],
        }
        
        if field_type in patterns:
            for pattern in patterns[field_type]:
                for i, col in enumerate(col_lower):
                    if pattern in col:
                        return df.columns[i]
        
        return None
    
    def extract_data(self, df: pd.DataFrame, row_index: int) -> Dict[str, Any]:
        """
        Extract data from a DataFrame row using mappings.
        
        Args:
            df: The DataFrame
            row_index: Index of the row to extract
            
        Returns:
            Dictionary with extracted field values
        """
        data = {}
        row = df.iloc[row_index]
        
        # Extract mapped fields
        for field_type in ['company_name', 'address', 'phone', 'email', 
                          'city', 'state', 'zip_code', 'contact_name']:
            col_name = self.get_column_for_field(field_type, df)
            if col_name:
                value = row.get(col_name)
                if pd.notna(value) and str(value).strip():
                    data[field_type] = str(value).strip()
        
        # Extract any custom fields
        for col_name in df.columns:
            if col_name not in self.reverse_mappings and col_name not in self.enrichment_targets:
                # This is an unmapped column - include as custom field
                value = row.get(col_name)
                if pd.notna(value) and str(value).strip():
                    data[f'custom_{col_name}'] = str(value).strip()
        
        return data
    
    def get_enrichment_columns(self) -> List[str]:
        """Get list of columns that should be enriched."""
        return self.enrichment_targets
    
    def apply_enrichment(self, df: pd.DataFrame, row_index: int, enrichment_data: Dict[str, Any]) -> None:
        """
        Apply enrichment data back to the DataFrame.
        
        Args:
            df: The DataFrame to update
            row_index: Index of the row to update
            enrichment_data: Dictionary with enriched values
        """
        # Map enrichment fields back to columns
        field_to_column = {
            'website': self.get_target_column('website', df),
            'owner_first_name': self.get_target_column('owner_first_name', df),
            'owner_last_name': self.get_target_column('owner_last_name', df),
            'owner_email': self.get_target_column('owner_email', df),
            'owner_phone': self.get_target_column('owner_phone', df),
            'email_subject': self.get_target_column('email_subject', df),
            'email_icebreaker': self.get_target_column('email_icebreaker', df),
            'hot_button': self.get_target_column('hot_button', df),
        }
        
        for field, column in field_to_column.items():
            if column and field in enrichment_data:
                df.at[row_index, column] = enrichment_data[field]
    
    def get_target_column(self, field_type: str, df: pd.DataFrame) -> Optional[str]:
        """Get the target column for enrichment."""
        # Check if this field is in our enrichment targets
        for col in self.enrichment_targets:
            if col in df.columns:
                # Check if this column maps to the field type
                if self.reverse_mappings.get(col) == field_type:
                    return col
        
        # Fallback to mapped column
        return self.get_column_for_field(field_type, df)