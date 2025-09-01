"""
API routes for the Agentic Transformational Layer.
Contains all endpoint definitions for CSV processing pipeline.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import os
import shutil
import json
import uuid

# Import project modules
from agent import load_csv_data, apply_smart_filter, setup_supabase_client
from config.enhanced_ai_schema_mapper import EnhancedAISchemaMapper
from database.db_handler import SupabaseClientHandler
from langgraph_nodes.graph_builder import builder

# Create API router
router = APIRouter()

# In-memory session store (for demo; use Redis or DB for production)
session_store = {}

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file and start a processing session.
    
    Args:
        file: CSV file to upload
        
    Returns:
        dict: Session ID and data shape information
    """
    session_id = str(uuid.uuid4())
    temp_path = f"temp_{session_id}_{file.filename}"
    
    try:
        # Save uploaded file
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Load and validate CSV
        df = load_csv_data(temp_path)
        if df is None:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="Failed to load CSV data.")
        
        # Store in session
        session_store[session_id] = {
            "raw_df": df, 
            "temp_path": temp_path,
            "filename": file.filename
        }
        
        return {
            "session_id": session_id, 
            "shape": df.shape,
            "filename": file.filename,
            "columns": list(df.columns)
        }
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.post("/smart-filter")
async def smart_filter(session_id: str = Form(...), use_ai_filtering: bool = Form(True)):
    """
    Apply smart filtering to uploaded CSV data.
    
    Args:
        session_id: Session identifier from upload-csv
        use_ai_filtering: Whether to use AI for column matching refinement
        
    Returns:
        dict: Filtered data shape information
    """
    session = session_store.get(session_id)
    if not session or "raw_df" not in session:
        raise HTTPException(status_code=404, detail="Session not found or CSV not uploaded.")
    
    try:
        filtered_df = apply_smart_filter(session["raw_df"], use_ai=use_ai_filtering)
        session["filtered_df"] = filtered_df
        
        return {
            "filtered_shape": filtered_df.shape,
            "filtered_columns": list(filtered_df.columns),
            "original_shape": session["raw_df"].shape
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart filtering failed: {str(e)}")

@router.post("/preprocess")
async def preprocess(session_id: str = Form(...)):
    """
    Run preprocessing workflow on filtered data using LangGraph.
    
    Args:
        session_id: Session identifier
        
    Returns:
        dict: Processed data shape information
    """
    session = session_store.get(session_id)
    if not session or "filtered_df" not in session:
        raise HTTPException(status_code=404, detail="Session not found or smart filter not applied.")
    
    try:
        # Run LangGraph preprocessing workflow
        initial_state = {"df": session["filtered_df"]}
        app_graph = builder.compile()
        final_state = app_graph.invoke(initial_state)
        processed_df = final_state["df"]
        
        session["processed_df"] = processed_df
        
        return {
            "processed_shape": processed_df.shape,
            "processed_columns": list(processed_df.columns),
            "filtered_shape": session["filtered_df"].shape
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preprocessing failed: {str(e)}")

@router.post("/schema-map")
async def schema_map(session_id: str = Form(...)):
    """
    Map processed data to database tables using AI schema mapping.
    
    Args:
        session_id: Session identifier
        
    Returns:
        dict: Mapped tables information
    """
    session = session_store.get(session_id)
    if not session or "processed_df" not in session:
        raise HTTPException(status_code=404, detail="Session not found or preprocessing not done.")
    
    try:
        # Load schema configuration
        SCHEMA_FILE_PATH = os.path.join("database", "database_schema.json")
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GENAI_API_KEY")
        
        if not api_key:
            raise HTTPException(status_code=500, detail="AI API key not configured.")
        
        # Initialize AI schema mapper
        mapper = EnhancedAISchemaMapper(SCHEMA_FILE_PATH, api_key)
        
        # Prepare preprocessing results
        preprocessing_results = {
            "null_suggestions": "Preprocessing completed",
            "duplicate_suggestions": "No duplicates found",
            "type_suggestions": "Types optimized",
            "type_analysis": {}
        }
        
        # Map dataframe to tables
        mapped_tables = mapper.map_dataframe_to_tables(session["processed_df"], preprocessing_results)
        session["mapped_tables"] = mapped_tables
        
        # Prepare response
        tables_info = {}
        for table_name, table_df in mapped_tables.items():
            tables_info[table_name] = {
                "rows": len(table_df),
                "columns": len(table_df.columns),
                "column_names": list(table_df.columns)
            }
        
        return {
            "tables": tables_info,
            "total_tables": len(mapped_tables)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema mapping failed: {str(e)}")

@router.post("/save-db")
async def save_db(session_id: str = Form(...)):
    """
    Validate and save mapped tables to Supabase database.
    
    Args:
        session_id: Session identifier
        
    Returns:
        dict: Validation and save results
    """
    session = session_store.get(session_id)
    if not session or "mapped_tables" not in session:
        raise HTTPException(status_code=404, detail="Session not found or schema mapping not done.")
    
    try:
        # Load schema configuration
        SCHEMA_FILE_PATH = os.path.join("database", "database_schema.json")
        
        # Setup Supabase connection
        supabase_url, supabase_key = setup_supabase_client()
        
        with open(SCHEMA_FILE_PATH, 'r') as f:
            schema_config = json.load(f)
        
        # Initialize database handler
        db_handler = SupabaseClientHandler(supabase_url, supabase_key, schema_config)
        
        # Test connection
        if not db_handler.test_connection():
            raise HTTPException(status_code=500, detail="Supabase connection failed.")
        
        # Validate tables
        validation_results = db_handler.validate_all_tables(session["mapped_tables"])
        
        # Save tables
        save_results = db_handler.save_mapped_tables(session["mapped_tables"])
        
        # Count successful operations
        successful_saves = 0
        for table_name, result in save_results.items():
            if isinstance(result, bool) and result:
                successful_saves += 1
            elif isinstance(result, dict) and (result.get('success', False) or 'records' in result):
                successful_saves += 1
        
        return {
            "validation": validation_results,
            "save_results": save_results,
            "supabase_url": supabase_url,
            "successful_saves": successful_saves,
            "total_tables": len(session["mapped_tables"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database save failed: {str(e)}")

@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get information about a processing session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        dict: Session status and progress information
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    # Determine session progress
    progress = {
        "csv_uploaded": "raw_df" in session,
        "smart_filtered": "filtered_df" in session,
        "preprocessed": "processed_df" in session,
        "schema_mapped": "mapped_tables" in session
    }
    
    info = {
        "session_id": session_id,
        "filename": session.get("filename", "unknown"),
        "progress": progress
    }
    
    # Add shape information if available
    if "raw_df" in session:
        info["original_shape"] = session["raw_df"].shape
    if "filtered_df" in session:
        info["filtered_shape"] = session["filtered_df"].shape
    if "processed_df" in session:
        info["processed_shape"] = session["processed_df"].shape
    if "mapped_tables" in session:
        info["tables_count"] = len(session["mapped_tables"])
    
    return info

@router.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """
    Clean up a processing session and remove temporary files.
    
    Args:
        session_id: Session identifier
        
    Returns:
        dict: Cleanup status
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    try:
        # Remove temporary file if it exists
        temp_path = session.get("temp_path")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Remove session from store
        del session_store[session_id]
        
        return {
            "message": "Session cleaned up successfully",
            "session_id": session_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
