
"""S3: TenderScope AI MCP server — read-only RAG tool."""

from pathlib import Path
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from core.agent_tool_schemas import (
    RAGOutput,
    rag_search_documents as search_existing_dossier,
)

PROJECT_ROOT = Path(__file__).resolve().parent
DEMO_DIR = PROJECT_ROOT / "data" / "demo"

mcp = MCPServer(
    "TenderScope AI — RAG",
    instructions=(
        "Read-only procurement evidence retrieval. "
        "All results need human verification; "
        "demo documents are fictional."
    ),
)


def _load_fictional_dossier() -> list[dict]:
    paths = sorted(DEMO_DIR.glob("*_FICTIF.txt"))

    if len(paths) != 3:
        raise FileNotFoundError(
            "Expected three fictional demo files in data/demo/."
        )

    return [
        {
            "document": path.name,
            "page": 1,
            "text": path.read_text(encoding="utf-8"),
        }
        for path in paths
    ]


@mcp.tool(
    title="Search procurement documents (RAG)",
    annotations=ToolAnnotations(
        read_only_hint=True,
        open_world_hint=False,
    ),
)
def rag_search_documents(
    question: Annotated[
        str,
        Field(
            min_length=3,
            max_length=500,
            description="Tender question to investigate.",
        ),
    ],
    method: Literal["bm25", "hybrid"] = "bm25",
    top_k: Annotated[int, Field(ge=1, le=10)] = 6,
) -> RAGOutput:
    """READ: retrieve source-indexed procurement passages.

    Uses BM25 or optional local BGE-M3 hybrid retrieval.
    The bundled fictional dossier is used for demonstration.
    """
    return search_existing_dossier(
        arguments={
            "question": question,
            "method": method,
            "top_k": top_k,
        },
        pages=_load_fictional_dossier(),
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")

