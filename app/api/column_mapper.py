"""
Column mapping API endpoints for flexible CSV field recognition.
"""

import pandas as pd
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict, Optional

from app.models.column_mapping import (
    ColumnInfo, ColumnMapping, MappingRequest, 
    MappingResponse, FieldType
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def analyze_column(series: pd.Series, column_name: str) -> Dict:
    """Analyze a column to determine its likely type and characteristics"""
    
    # Check if column is empty
    non_null = series.dropna()
    is_empty = len(non_null) == 0 or all(str(v).strip() == '' for v in non_null)
    
    # Get sample values
    sample_values = []
    if not is_empty:
        sample_values = [str(v) for v in non_null.head(3).tolist()]
    
    # Suggest field type based on column name
    col_lower = column_name.lower()
    suggested_type = None
    
    # Check for company/dealer name
    if any(x in col_lower for x in ['company', 'dealer', 'business', 'name']):
        if 'owner' in col_lower or 'contact' in col_lower:
            if 'first' in col_lower:
                suggested_type = FieldType.OWNER_FIRST_NAME if is_empty else FieldType.CONTACT_NAME
            elif 'last' in col_lower:
                suggested_type = FieldType.OWNER_LAST_NAME if is_empty else FieldType.CONTACT_NAME
            else:
                suggested_type = FieldType.OWNER_FIRST_NAME if is_empty else FieldType.CONTACT_NAME
        else:
            suggested_type = FieldType.COMPANY_NAME
    
    # Check for address
    elif any(x in col_lower for x in ['address', 'location', 'street']):
        suggested_type = FieldType.ADDRESS
    
    # Check for phone
    elif 'phone' in col_lower or 'tel' in col_lower or 'mobile' in col_lower:
        if 'owner' in col_lower:
            suggested_type = FieldType.OWNER_PHONE if is_empty else FieldType.PHONE
        else:
            suggested_type = FieldType.PHONE
    
    # Check for email
    elif 'email' in col_lower or 'e-mail' in col_lower:
        if 'owner' in col_lower:
            suggested_type = FieldType.OWNER_EMAIL
        elif 'subject' in col_lower:
            suggested_type = FieldType.EMAIL_SUBJECT
        else:
            suggested_type = FieldType.EMAIL
    
    # Check for website
    elif any(x in col_lower for x in ['website', 'url', 'web', 'site']):
        suggested_type = FieldType.WEBSITE
    
    # Check for city/state/zip
    elif 'city' in col_lower:
        suggested_type = FieldType.CITY
    elif 'state' in col_lower:
        suggested_type = FieldType.STATE
    elif any(x in col_lower for x in ['zip', 'postal']):
        suggested_type = FieldType.ZIP_CODE
    
    # Check for email content fields
    elif any(x in col_lower for x in ['subject', 'subject line']):
        suggested_type = FieldType.EMAIL_SUBJECT
    elif any(x in col_lower for x in ['icebreaker', 'ice breaker', 'opener']):
        suggested_type = FieldType.EMAIL_ICEBREAKER
    elif any(x in col_lower for x in ['hot button', 'pain point', 'topic']):
        suggested_type = FieldType.HOT_BUTTON
    
    # Check for owner/contact name
    elif 'owner' in col_lower or 'contact' in col_lower:
        if 'first' in col_lower:
            suggested_type = FieldType.OWNER_FIRST_NAME
        elif 'last' in col_lower:
            suggested_type = FieldType.OWNER_LAST_NAME
        else:
            suggested_type = FieldType.CONTACT_NAME
    
    return {
        'name': column_name,
        'is_empty': is_empty,
        'sample_values': sample_values,
        'suggested_type': suggested_type
    }


@router.post("/analyze", response_model=MappingResponse)
async def analyze_csv_columns(file: UploadFile = File(...)):
    """
    Analyze CSV columns and suggest mappings.
    
    This endpoint:
    1. Reads the CSV file
    2. Analyzes each column for content and patterns
    3. Suggests field type mappings
    4. Identifies empty columns as enrichment targets
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(400, "Only CSV files are supported")
        
        # Read CSV content
        content = await file.read()
        
        # Parse CSV
        try:
            import io
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(400, f"Invalid CSV format: {str(e)}")
        
        logger.info(f"Analyzing CSV with {len(df.columns)} columns and {len(df)} rows")
        
        # Analyze each column
        columns_info = []
        suggested_mappings = []
        enrichment_targets = []
        
        for idx, col in enumerate(df.columns):
            analysis = analyze_column(df[col], col)
            
            col_info = ColumnInfo(
                name=col,
                index=idx,
                sample_values=analysis['sample_values'],
                is_empty=analysis['is_empty'],
                suggested_type=analysis['suggested_type']
            )
            columns_info.append(col_info)
            
            # Create suggested mapping
            if analysis['suggested_type']:
                mapping = ColumnMapping(
                    column_name=col,
                    field_type=analysis['suggested_type'],
                    is_target=analysis['is_empty']
                )
                suggested_mappings.append(mapping)
                
                # Track enrichment targets
                if analysis['is_empty']:
                    enrichment_targets.append(col)
        
        # Log findings
        logger.info(f"Found {len(enrichment_targets)} empty columns for enrichment")
        logger.info(f"Suggested {len(suggested_mappings)} mappings")
        
        # Generate temporary job ID for this analysis
        from uuid import uuid4
        temp_job_id = str(uuid4())
        
        # Save the analysis for later use
        analysis_path = settings.UPLOAD_DIR / f"{temp_job_id}_analysis.json"
        analysis_data = {
            'columns': [col.dict() for col in columns_info],
            'suggested_mappings': [m.dict() for m in suggested_mappings],
            'enrichment_targets': enrichment_targets
        }
        
        with open(analysis_path, 'w') as f:
            json.dump(analysis_data, f)
        
        return MappingResponse(
            job_id=temp_job_id,
            columns=columns_info,
            suggested_mappings=suggested_mappings,
            enrichment_targets=enrichment_targets,
            message=f"Analyzed {len(df.columns)} columns. Found {len(enrichment_targets)} fields for AI enrichment."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing CSV: {str(e)}")
        raise HTTPException(500, f"Failed to analyze CSV: {str(e)}")


@router.post("/save-mapping")
async def save_column_mapping(mapping_request: MappingRequest):
    """
    Save user-confirmed column mappings for a job.
    
    This allows users to override the suggested mappings
    and define custom field relationships.
    """
    try:
        # Save mappings to file
        mapping_path = settings.UPLOAD_DIR / f"{mapping_request.job_id}_mappings.json"
        
        mapping_data = {
            'job_id': mapping_request.job_id,
            'mappings': [m.dict() for m in mapping_request.mappings],
            'custom_fields': mapping_request.custom_fields or {}
        }
        
        with open(mapping_path, 'w') as f:
            json.dump(mapping_data, f)
        
        logger.info(f"Saved {len(mapping_request.mappings)} mappings for job {mapping_request.job_id}")
        
        # Count enrichment targets
        enrichment_count = sum(1 for m in mapping_request.mappings if m.is_target)
        
        return {
            'success': True,
            'message': f"Saved {len(mapping_request.mappings)} column mappings with {enrichment_count} enrichment targets",
            'job_id': mapping_request.job_id
        }
    
    except Exception as e:
        logger.error(f"Error saving mappings: {str(e)}")
        raise HTTPException(500, f"Failed to save mappings: {str(e)}")


@router.get("/mapping/{job_id}")
async def get_column_mapping(job_id: str):
    """Retrieve saved column mappings for a job"""
    try:
        mapping_path = settings.UPLOAD_DIR / f"{job_id}_mappings.json"
        
        if not mapping_path.exists():
            raise HTTPException(404, "Mappings not found for this job")
        
        with open(mapping_path, 'r') as f:
            mapping_data = json.load(f)
        
        return mapping_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving mappings: {str(e)}")
        raise HTTPException(500, f"Failed to retrieve mappings: {str(e)}")