import streamlit as st
import pandas as pd
import logging
from io import BytesIO

# Backend imports
from config import Config
from vertex_service import VertexAIService
from index_manager import IndexManager
from pipeline import RAGPipeline


# -----------------------------------------------------------------------------
# Streamlit Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Brick Mapper AI", layout="wide")
logging.basicConfig(level=logging.INFO)


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Excel Utilities
# -----------------------------------------------------------------------------
def detect_header_row(df_preview) -> int | None:
    """Find header row containing required column names."""
    REQUIRED = {"Operation ID", "Operation description"}

    for idx, row in df_preview.iterrows():
        values = {str(v).strip() for v in row.values}
        if REQUIRED.issubset(values):
            return idx
    return None


def read_operation_sheet(file_obj, sheet_name):
    """
    Reads sheet and detects header row dynamically.
    Returns DataFrame or error message.
    """
    try:
        preview = pd.read_excel(file_obj, sheet_name=sheet_name, header=None, nrows=50)
        header_idx = detect_header_row(preview)

        if header_idx is None:
            return f"Error: Could not find required header row in sheet '{sheet_name}'."

        df = pd.read_excel(file_obj, sheet_name=sheet_name, header=header_idx)
        df.columns = df.columns.str.strip()

        if "Operation description" not in df:
            return f"Error: Missing 'Operation description' column in sheet '{sheet_name}'."

        df_clean = df[["Operation ID", "Operation description"]].dropna(subset=["Operation description"])
        if df_clean.empty:
            return "Error: No valid operation descriptions found."

        return df_clean

    except Exception as e:
        return f"Error reading sheet '{sheet_name}': {e}"


def to_excel_bytes(df):
    """Convert DataFrame into Excel bytes with wrapped text formatting."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Mapped_Bricks")

        workbook = writer.book
        worksheet = writer.sheets["Mapped_Bricks"]

        wrap_fmt = workbook.add_format({"text_wrap": True, "valign": "top"})
        worksheet.set_column("A:F", 25, wrap_fmt)
        worksheet.set_column("B:B", 40, wrap_fmt)
        worksheet.set_column("F:F", 40, wrap_fmt)

    return output.getvalue()


# -----------------------------------------------------------------------------
# Sheet Selection UI
# -----------------------------------------------------------------------------
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

    return st.selectbox(f"Select sheet for {file.name}", tc_sheets, key=f"sheet_{file.name}")


# -----------------------------------------------------------------------------
# Processing Logic
# -----------------------------------------------------------------------------
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

    progress.progress(1.0)
    status.text("Processing complete!")
    return pd.DataFrame(results)


# -----------------------------------------------------------------------------
# Main UI
# -----------------------------------------------------------------------------
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

            data = read_operation_sheet(excel_file, sheet)
            if isinstance(data, str):
                st.error(data)
                continue

            st.success(f"Detected {len(data)} operations in '{sheet}'.")

            if st.button(f"Map Bricks for {file.name}", key=f"run_{file.name}"):
                df_results = process_operations(data, pipeline)

                st.dataframe(
                    df_results,
                    use_container_width=True,
                    hide_index=True
                )

                excel_output = to_excel_bytes(df_results)
                st.download_button(
                    "📥 Download Mapped Results (Excel)",
                    data=excel_output,
                    file_name=f"mapped_{file.name}_{sheet}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        except Exception as e:
            st.error(f"Error reading file: {e}")
