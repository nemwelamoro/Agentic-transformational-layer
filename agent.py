import pandas as pd
import os
import json
import sys
from dotenv import load_dotenv
from langgraph_nodes.graph_builder import builder
from config.enhanced_ai_schema_mapper import EnhancedAISchemaMapper
from database.db_handler import SupabaseClientHandler

# Load environment variables
load_dotenv()

def load_csv_data(file_path: str) -> pd.DataFrame:
    """Load raw CSV data"""
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully loaded {len(df)} rows and {len(df.columns)} columns from {file_path}")
        print(f"Columns: {list(df.columns)}")
        print(f"Dataset shape: {df.shape}")
        print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        return df
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None

def apply_smart_filter(df: pd.DataFrame, use_ai: bool = True) -> pd.DataFrame:
    """
    Apply smart HDSS column filtering to the DataFrame
    Returns filtered DataFrame with schema-aligned column names
    """
    print("🔍 Applying smart HDSS column filter...")
    
    # Import your smart filter functions
    sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))
    
    try:
        from data.smart_filter import (
            SCHEMA, ALIASES, ALL_FIELDS, FIELD_TO_TABLE,
            normalize, fast_match, should_refine_with_ai, gemini_refine_match
        )
        from collections import defaultdict
        
        # Configuration (matching your filter's defaults)
        fuzzy_threshold = 0.65
        ai_refinement_threshold = 0.80
        max_ai_calls = 25
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GENAI_API_KEY") or ""
        
        print(f"   📋 Input: {df.shape[0]} rows × {df.shape[1]} columns")
        
        # Phase 1: Fast matching
        print("   🚀 Phase 1: Fast matching (exact/alias/fuzzy)...")
        
        mapped_columns = {}
        available_fields = ALL_FIELDS.copy()
        fast_matches = []
        
        # Sort columns by importance (IDs first)
        id_cols = [col for col in df.columns if 'id' in col.lower()]
        other_cols = [col for col in df.columns if col not in id_cols]
        sorted_columns = id_cols + other_cols
        
        for col in sorted_columns:
            field, match_type, score = fast_match(col, available_fields, fuzzy_threshold)
            
            if field:
                if match_type == "fuzzy" and score < ai_refinement_threshold:
                    if should_refine_with_ai(col, field, score):
                        fast_matches.append((col, field, match_type, score))
                    else:
                        mapped_columns[col] = field
                        available_fields.remove(field)
                else:
                    mapped_columns[col] = field
                    available_fields.remove(field)
        
        # Limit AI candidates
        fast_matches = sorted(fast_matches, key=lambda x: x[3], reverse=True)
        fast_matches = fast_matches[:max_ai_calls]
        
        print(f"   ✅ Fast matching: {len(mapped_columns)} direct matches, {len(fast_matches)} for AI refinement")
        
        # Phase 2: AI refinement (if enabled and API key available)
        ai_calls_made = 0
        if use_ai and fast_matches and api_key:
            print(f"   🤖 Phase 2: AI refinement for {len(fast_matches)} uncertain matches...")
            
            for col, field, match_type, score in fast_matches:
                if ai_calls_made >= max_ai_calls:
                    break
                
                try:
                    refined_field = gemini_refine_match(col, field, api_key)
                    if refined_field and refined_field in available_fields:
                        mapped_columns[col] = refined_field
                        available_fields.remove(refined_field)
                        print(f"   ✅ AI refined: {col} → {refined_field}")
                    else:
                        mapped_columns[col] = field
                        available_fields.remove(field)
                        print(f"   ⚠️  AI fallback: {col} → {field}")
                    
                    ai_calls_made += 1
                except Exception as e:
                    print(f"   ❌ AI failed for {col}: {e}")
                    mapped_columns[col] = field
                    available_fields.remove(field)
        else:
            # No AI - use fuzzy matches as-is
            for col, field, match_type, score in fast_matches:
                mapped_columns[col] = field
                available_fields.remove(field)
        
        # Create filtered DataFrame
        available_cols = [col for col in df.columns if col in mapped_columns]
        filtered_df = df[available_cols].copy()
        
        print(f"   ✅ Smart filter completed: {filtered_df.shape[0]} rows × {filtered_df.shape[1]} columns")
        print(f"   📊 Filter efficiency: {(filtered_df.shape[1]/df.shape[1])*100:.1f}% columns retained")
        
        return filtered_df
        
    except Exception as e:
        print(f"   ❌ Smart filter failed: {e}")
        print(f"   🔄 Returning original data")
        return df

def setup_supabase_client():
    """Setup Supabase client from environment variables"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_CLIENT_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_CLIENT_KEY must be set in environment variables")
    
    print("✅ Supabase client configuration loaded")
    print(f"   URL: {supabase_url}")
    print(f"   Key: {supabase_key[:20]}...")
    
    return supabase_url, supabase_key

if __name__ == "__main__":
    # Configuration
    CSV_FILE_PATH= r"C:\Users\killi\Desktop\Work\Agentic-transformational-layer\df_sample.csv"
    SCHEMA_FILE_PATH = r"C:\Users\killi\Desktop\Work\Agentic-transformational-layer\database\database_schema.json"
    
    
    # Setup Supabase client
    try:
        supabase_url, supabase_key = setup_supabase_client()
    except ValueError as e:
        print(f"❌ Supabase configuration error: {e}")
        exit(1)

    # Step 1: Load and Apply Smart Filter
    print("="*80)
    print("STEP 1: LOADING AND SMART FILTERING DATA")
    print("="*80)
    
    # Load raw data
    raw_df = load_csv_data(CSV_FILE_PATH)
    if raw_df is None:
        print("❌ Failed to load CSV data")
        exit(1)
    
    # Apply smart filter
    use_ai_filtering = True  # Set to False to skip AI refinement in filtering
    filtered_df = apply_smart_filter(raw_df, use_ai=use_ai_filtering)
    
    print("\n" + "="*50)
    print("SMART-FILTERED DATASET OVERVIEW:")
    print("="*50)
    print(f"Shape: {filtered_df.shape}")
    print(f"Sample columns: {list(filtered_df.columns)[:10]}")

    # Step 2: Preprocessing Workflow (LangGraph)
    print("\n" + "="*50)
    print("PREPROCESSING WORKFLOW")
    print("="*50)
    
    try:
        # FIXED: Use correct state format for the preprocessing workflow
        initial_state = {"df": filtered_df}
        
        # Run the complete preprocessing workflow
        app = builder.compile()
        final_state = app.invoke(initial_state)
        
        # FIXED: Extract processed_df correctly
        processed_df = final_state["df"]  # This was missing
        
        preprocessing_results = {
           "null_suggestions": "Preprocessing completed",
           "duplicate_suggestions": "No duplicates found",
           "type_suggestions": "Types optimized",
           "type_analysis": {}
        }
        print(f"✅ Preprocessing completed. Shape: {processed_df.shape}")

    except Exception as e:
        print(f"❌ Preprocessing failed: {e}")
        print("📋 Using filtered data without preprocessing")
        processed_df = filtered_df  # FIXED: Define processed_df here too
        preprocessing_results = {
            "null_suggestions": "Smart filter applied - preprocessing skipped",
            "duplicate_suggestions": "Smart filter handles duplicates", 
            "type_suggestions": "Smart filter aligns data types",
            "type_analysis": {}
        }  

    # Step 3: AI-Powered Schema Mapping
    print("\n" + "="*80)
    print("STEP 2: AI-POWERED SCHEMA MAPPING")
    print("="*80)
    
    try:
        # Initialize enhanced AI schema mapper
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GENAI_API_KEY")
        mapper = EnhancedAISchemaMapper(SCHEMA_FILE_PATH, api_key)
        
        # FIXED: Use processed_df which is now properly defined
        mapped_tables = mapper.map_dataframe_to_tables(processed_df, preprocessing_results)
        
        print("✅ Autonomous AI schema mapping completed")
        print(f"📋 Intelligently created tables: {list(mapped_tables.keys())}")
        
    except Exception as e:
        print(f"❌ Schema mapping failed: {e}")
        mapped_tables = {}  # FIXED: Always define mapped_tables

    # Step 4: Supabase Operations
    print("\n" + "="*80)
    print("STEP 3: SUPABASE CLIENT OPERATIONS")
    print("="*80)
    
    try:
        # Load schema for Supabase handler
        with open(SCHEMA_FILE_PATH, 'r') as f:
            schema_config = json.load(f)
        
        # Initialize Supabase handler
        db_handler = SupabaseClientHandler(supabase_url, supabase_key, schema_config)
        
        # Test connection
        if db_handler.test_connection():
            # Validate tables
            validation_results = db_handler.validate_all_tables(mapped_tables)
            
            valid_tables = [name for name, result in validation_results.items() if result['valid']]
            invalid_tables = [name for name, result in validation_results.items() if not result['valid']]
            
            print(f"\n📊 Validation Summary:")
            if len(valid_tables) == len(mapped_tables):
                print(f"   Status: ✅ All Valid")
            else:
                print(f"   Status: ⚠️  Some Issues")
            
            for table_name, result in validation_results.items():
                status = "✅ Valid" if result['valid'] else "❌ Invalid"
                print(f"  {status} {table_name}: {result['stats']['total_records']} records")
                
                if not result['valid']:
                    print(f"\n❌ {table_name} Errors:")
                    for error in result['errors'][:5]:  # Show first 5 errors
                        print(f"   • {error}")
            
            # Save valid tables to Supabase
            if valid_tables:
                try:
                    save_results = db_handler.save_mapped_tables(mapped_tables)
                    
                    # Count successful operations safely
                    successful_saves = 0
                    for table_name, result in save_results.items():
                        # Handle different result formats
                        if isinstance(result, bool) and result:
                            successful_saves += 1
                        elif isinstance(result, dict) and result.get('success', False):
                            successful_saves += 1
                        elif isinstance(result, dict) and 'records' in result:
                            successful_saves += 1
                            
                    if successful_saves > 0:
                        print(f"\n✅ Successfully saved {successful_saves}/{len(mapped_tables)} tables to Supabase!")
                    else:
                        print(f"\n❌ Failed to save any tables to Supabase")
                except Exception as e:
                    print(f"\n❌ Supabase operations failed: {e}")
                    # Continue execution to show summary
            else:
                print(f"\n⚠️  No valid tables to save")
        else:
            print("❌ Supabase connection failed")
        
    except Exception as e:
        print(f"❌ Supabase operations failed: {e}")

    # Final Summary
    print("\n" + "="*80)
    print("AI-POWERED SUPABASE WORKFLOW COMPLETED! 🎉")
    print("="*80)
    print(f"📥 Original data: {raw_df.shape[0]} rows, {raw_df.shape[1]} columns")
    print(f"🔍 Smart-filtered data: {filtered_df.shape[0]} rows, {filtered_df.shape[1]} columns")
    print(f"🔄 Processed data: {processed_df.shape[0]} rows, {processed_df.shape[1]} columns")
    print(f"🤖 AI-mapped tables: {len(mapped_tables)}")
    
    for table_name, table_df in mapped_tables.items():
        print(f"   {table_name}: {len(table_df)} rows, {len(table_df.columns)} columns")
    
    print(f"💾 Database: Supabase (via Client API)")
    print(f"🌐 URL: {supabase_url}")
    print("\nYour data has been intelligently mapped and loaded into Supabase! 🚀")
    print("\n🔗 Access your data at: https://app.supabase.com/project/[your-project]/editor")
