"""
Column mapping models for flexible CSV field recognition.
"""

from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from enum import Enum


class FieldType(str, Enum):
    """Types of fields we can map"""
    # Required source fields (must have data)
    COMPANY_NAME = "company_name"
    ADDRESS = "address"
    PHONE = "phone"
    
    # Optional source fields
    EMAIL = "email"
    CONTACT_NAME = "contact_name"
    CITY = "city"
    STATE = "state"
    ZIP_CODE = "zip_code"
    
    # Target enrichment fields (empty columns to populate)
    WEBSITE = "website"
    OWNER_FIRST_NAME = "owner_first_name"
    OWNER_LAST_NAME = "owner_last_name"
    OWNER_EMAIL = "owner_email"
    OWNER_PHONE = "owner_phone"
    EMAIL_SUBJECT = "email_subject"
    EMAIL_ICEBREAKER = "email_icebreaker"
    HOT_BUTTON = "hot_button"
    
    # Custom fields
    CUSTOM = "custom"
    IGNORE = "ignore"


class ColumnInfo(BaseModel):
    """Information about a CSV column"""
    name: str
    index: int
    sample_values: List[str]
    is_empty: bool
    suggested_type: Optional[FieldType] = None


class ColumnMapping(BaseModel):
    """Maps a CSV column to a field type"""
    column_name: str
    field_type: FieldType
    is_target: bool = False  # True if this is an empty column for enrichment


class MappingRequest(BaseModel):
    """Request to save column mappings"""
    job_id: str
    mappings: List[ColumnMapping]
    custom_fields: Optional[Dict[str, Any]] = None


class MappingResponse(BaseModel):
    """Response with column analysis and suggestions"""
    job_id: str
    columns: List[ColumnInfo]
    suggested_mappings: List[ColumnMapping]
    enrichment_targets: List[str]  # Empty columns for AI to populate
    message: str