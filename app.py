import streamlit as st
import pandas as pd
import logging

# Backend imports
from config import Config
from vertex_service import VertexAIService
from index_manager import IndexManager
from pipeline import RAGPipeline

# Import the new Excel Utility functions
from excel_utils import read_operation_sheet, to_excel_bytes

# Streamlit Setup
st.set_page_config(page_title="Brick Mapper AI", layout="wide")
logging.basicConfig(level=logging.INFO)

# Styling Helper
def style_results(df: pd.DataFrame):
    """
    Applies visual styling to the results DataFrame.
    """
    # Create the Styler object
    styler = df.style

    # 1. Highlight rows with "No Match" in light red
    def highlight_missing(row):
        # Check specific column "Brick ID"
        brick_id = str(row.get("Brick ID", ""))
        if "No Match" in brick_id or brick_id == "-":
            return ['background-color: #ffe6e6; color: #b30000'] * len(row)
        return [''] * len(row)

    styler = styler.apply(highlight_missing, axis=1)

    # 2. Text Formatting (Left align, wrap text)
    styler = styler.set_properties(**{
        'text-align': 'left',
        'white-space': 'pre-wrap', 
        'vertical-align': 'top'
    })
    
    return styler

# Initialization
@st.cache_resource
def initialize_rag_system():
    """Initializes the RAG system once."""
    GCP_PROJECT_ID = "prj-a63e-dp002-dev-d10d"
    GCP_LOCATION = "europe-west4"

    try:
        config = Config()
        vertex_service = VertexAIService(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        index_manager = IndexManager(vertex_service, config)

        # Use existing indices; don't rebuild from raw JSON
        retrievers = index_manager.build_retrievers([])

        return RAGPipeline(vertex_service, retrievers)

    except Exception as e:
        st.error(f"Critical Error Initializing RAG: {e}")
        return None

# UI Component: Sheet Selection
def select_target_sheet(file, excel_file: pd.ExcelFile) -> str | None:
    """
    Select a sheet that starts with 'TC'. Returns selected sheet name or None.
    """
    tc_sheets = [s for s in excel_file.sheet_names if s.upper().startswith("TC") and s != "TC Template"]
    if not tc_sheets:
        st.error(f"No valid 'TC*' sheets in file. Found: {excel_file.sheet_names}")
        return None

    if len(tc_sheets) == 1:
        st.info(f"Auto-selected sheet: **{tc_sheets[0]}**")
        return tc_sheets[0]

    return st.selectbox(f"Select sheet from: {file.name}", tc_sheets, key=f"sheet_{file.name}")

# Processing Logic
def process_operations(df: pd.DataFrame, pipeline: RAGPipeline):
    """Run RAG mapping for each row, with progress UI."""
    results = []
    
    progress = st.progress(0)
    status = st.empty()

    total = len(df)

    for idx, (row_index, row) in enumerate(df.iterrows()):
        desc = row["Operation description"]
        status.text(f"Processing {idx+1}/{total}: {str(desc)[:60]}...")
        progress.progress((idx + 1) / total)

        rag_output = pipeline.run_batch_row(desc)
        
        results.append({
            "Operation ID": row["Operation ID"],
            "Operation Description": desc,
            **rag_output,
        })

    # Cleanup UI
    progress.empty()
    status.success("Processing complete!")
    
    return pd.DataFrame(results)

# Main UI
st.title("🧱 Brick Mapper AI")
st.markdown("Upload Excel files that contain **Operation ID** and **Operation description** columns.")

pipeline = initialize_rag_system()
if not pipeline:
    st.stop()

st.success("AI System is Ready.")

uploaded_files = st.file_uploader(
    "Choose Excel file(s)", 
    type=["xlsx", "xlsm", "xls"], 
    accept_multiple_files=True,
)

if not uploaded_files:
    st.stop()

st.header("Processing Files")

for file in uploaded_files:
    with st.expander(f"File: {file.name}", expanded=True):
        try:
            excel_file = pd.ExcelFile(file)
            sheet = select_target_sheet(file, excel_file)
            if not sheet:
                continue

            # Call function from excel_utils.py
            data = read_operation_sheet(excel_file, sheet)
            
            if isinstance(data, str):
                st.error(data)
                continue

            st.success(f"Detected {len(data)} operations in '{sheet}'.")

            if st.button(f"Map Bricks for {sheet}", key=f"run_{file.name}"):
                
                # 1. Process
                df_results = process_operations(data, pipeline)

                # 2. Style
                styled_df = style_results(df_results)

                # 3. Display
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Operation ID": st.column_config.TextColumn("Operation ID", width="small"),
                        "Operation Description": st.column_config.TextColumn("Description", width="large"),
                        "Brick ID": st.column_config.TextColumn("Brick ID", width="medium", help="Mapped IDs"),
                        "Brick Name": st.column_config.TextColumn("Brick Name", width="medium"),
                        "Prerequisites": st.column_config.TextColumn("Prerequisites", width="medium"),
                    }
                )

                # 4. Download
                excel_output = to_excel_bytes(df_results)
                
                st.download_button(
                    "Download Mapped Results (Excel)",
                    data=excel_output,
                    file_name=f"mapped_results_{sheet}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        except Exception as e:
            st.error(f"Error reading file: {e}")
