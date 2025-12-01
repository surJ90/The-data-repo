import json
import logging
import re
from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from vertex_service import VertexAIService


class RAGPipeline:
    """
    Unified RAG pipeline:
    - Routes query to correct retriever
    - Formats retrieval context with metadata awareness
    - Builds strict JSON enforcement prompt with Few-Shot examples
    - Post-processes output to ensure strict ID-only format
    """

    # Regex to detect Brick IDs (e.g., KW-1, S-10.5)
    BRICK_ID_PATTERN = re.compile(r'(KW|S|G)-\d+(\.\d+)?', re.IGNORECASE)

    def __init__(self, vertex_service: VertexAIService, retrievers: Dict[str, BaseRetriever]):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.vertex_service = vertex_service
        self.specific_retriever = retrievers["specific"]
        self.general_retriever = retrievers["general"]
        self.chain = self._build_chain()
        self.logger.info("RAGPipeline initialized (Enhanced Mode).")

    # ------------ Routing --------------

    def _select_retriever(self, query: str) -> BaseRetriever:
        """Choose specific retriever if query contains explicit brick-like ID."""
        return (
            self.specific_retriever
            if self.BRICK_ID_PATTERN.search(query)
            else self.general_retriever
        )

    # ----------- Formatting -----------------

    @staticmethod
    def _format_context(docs: List[Document]) -> str:
        """
        Formats documents preserving the 'chunk_type' context.
        This helps the LLM distinguish between 'Purpose' and 'Dependencies'.
        """
        if not docs:
            return "No relevant context found."

        formatted = []
        for i, doc in enumerate(docs):
            # Clean content
            content = doc.page_content.replace("\n", " ").strip()
            meta = doc.metadata or {}
            
            # Use the chunk_type we saved in data_processor.py
            # e.g., "dependencies", "parameters", "purpose"
            section_type = meta.get('chunk_type', 'General Info').upper()
            brick_id = meta.get('id', 'Unknown ID')
            
            formatted.append(
                f"--- SOURCE {i+1}: Brick {brick_id} [{section_type}] ---\n{content}"
            )
        return "\n\n".join(formatted)

    # ------------- Logic Cleaning ------------------

    def _clean_prerequisites(self, raw_prereq_string: str) -> str:
        """
        Python-side guardrail.
        Even if the LLM outputs 'KW-1 (Launch Catia)', this strips the text.
        Returns comma-separated IDs like: 'KW-1, S-5'
        """
        if not raw_prereq_string or raw_prereq_string == "-":
            return "-"
            
        # Find all matches of IDs
        matches = self.BRICK_ID_PATTERN.findall(raw_prereq_string)
        
        # findall returns tuples if groups are used, flatten them
        cleaned_ids = []
        if matches:
            # Re-scan the string to extract the full match (e.g. KW-1.2)
            # findall with groups returns ('KW', '.2') which is annoying to reconstruct
            # So we use finditer for full objects
            for match in self.BRICK_ID_PATTERN.finditer(raw_prereq_string):
                cleaned_ids.append(match.group(0).upper())
        
        if not cleaned_ids:
            return "-"
            
        return ", ".join(cleaned_ids)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse LLM output into valid JSON, removing code fences."""
        cleaned = re.sub(r"```json|```", "", text).strip()
        try:
            data = json.loads(cleaned)
            # Ensure 'bricks' key exists
            if "bricks" not in data:
                return {"bricks": []}
            return data
        except json.JSONDecodeError:
            self.logger.error(f"JSON decode failed. Raw output:\n{text}")
            return {"bricks": []}

    # ------------- Prompt Builder ---------------

    def _build_prompt(self, data: Dict[str, Any]) -> List:
        context = self._format_context(data["context"])
        question = data["question"]

        system_msg = SystemMessage(
            content=(
                "You are a strict Data Extraction Engine for CATIA automation.\n"
                "Your job is to identify the 'Brick ID', 'Brick Name', and 'Prerequisite IDs' "
                "required for the user's operation.\n\n"
                
                "**RULES:**\n"
                "1. **Multiple Bricks:** If the operation implies a sequence, list ALL required bricks.\n"
                "2. **Strict JSON:** Return ONLY a JSON object.\n"
                "3. **Prerequisites:** Extract ONLY the ID codes (e.g., KW-1, S-5). DO NOT include descriptions.\n"
                "4. **No Hallucinations:** If information is missing, use '-'.\n\n"

                "**FEW-SHOT EXAMPLE:**\n"
                "User: 'Launch Catia and then check if window is responsive'\n"
                "Context: '...Brick KW-1 (Launch Catia) requires nothing... Brick S-5 (Check Responsive) requires KW-1...'\n"
                "Output:\n"
                "{\n"
                '  "bricks": [\n'
                '    {"id": "KW-1", "name": "Launch Catia", "prerequisites": "-"},\n'
                '    {"id": "S-5", "name": "Check Responsive", "prerequisites": "KW-1"}\n'
                "  ]\n"
                "}\n"
            )
        )

        human_msg = HumanMessage(
            content=f"**Retrieval Context:**\n{context}\n\n**Target Operation:**\n{question}"
        )

        return [system_msg, human_msg]
    
    # --------------- Chain Builder -----------------

    def _build_chain(self):
        """Build LCEL chain: route → retrieve → prompt → LLM → parse JSON."""

        def route_and_retrieve(inputs: Dict[str, str]) -> Dict[str, Any]:
            query = inputs["query"]
            retriever = self._select_retriever(query)
            context = retriever.invoke(query)
            return {"context": context, "question": query}

        return (
            RunnablePassthrough()
            | RunnableLambda(lambda q: {"query": q})
            | RunnableLambda(route_and_retrieve)
            | RunnableLambda(self._build_prompt)
            | self.vertex_service.llm_rag
            | StrOutputParser()
            | RunnableLambda(self._parse_json)
        )

    # ----------------- API -----------------------

    def run_batch_row(self, operation_description: str) -> Dict[str, str]:
        """
        Main entry for UI.
        Runs RAG + LLM + JSON + Post-Processing + Formatting.
        """
        try:
            result = self.chain.invoke(operation_description)
            bricks = result.get("bricks", [])

            if not bricks:
                return {
                    "Brick ID": "No Match", 
                    "Brick Name": "-", 
                    "Prerequisites": "-",
                    "Description": "No relevant brick found."
                }

            # Pre-calculate lists to join later
            ids = []
            names = []
            prereqs = []
            reasons = []

            for b in bricks:
                b_id = b.get("id", "-")
                b_name = b.get("name", "-")
                
                # --- APPLY THE FIX HERE ---
                # We clean the raw string from the LLM to ensure only IDs remain
                raw_prereq = str(b.get("prerequisites", "-"))
                clean_prereq = self._clean_prerequisites(raw_prereq)
                
                ids.append(b_id)
                names.append(b_name)
                prereqs.append(clean_prereq)
                
                # Use reasoning if available, or just default text
                reasons.append(f"[{b_id}]: Mapped based on operation description.")

            return {
                "Brick ID": "\n".join(ids),
                "Brick Name": "\n".join(names),
                "Prerequisites": "\n".join(prereqs),
                "Description": "\n".join(reasons)
            }

        except Exception as exc:
            self.logger.error(
                f"Error processing row '{operation_description}': {exc}",
                exc_info=True
            )
            return {
                "Brick ID": "ERROR",
                "Brick Name": "System Error",
                "Prerequisites": "-",
                "Description": str(exc),
            }
