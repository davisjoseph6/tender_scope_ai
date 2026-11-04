
"""S2: Agent tool schemas and validated execution adapters.

All tool inputs and outputs are checked using Pydantic.
WRITE tools modify only local in-session application data.
"""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


# ============================================================
# TOOL 1: READ — Lookup an official public BOAMP notice
# ============================================================

class BOAMPInput(StrictModel):
    idweb: str = Field(
        ...,
        pattern=r"^\d{2}-\d{4,7}$",
        description="Official BOAMP notice identifier, e.g. 26-99630."
    )


class BOAMPOutput(StrictModel):
    idweb: str
    objet: str | None
    nomacheteur: str | None
    datelimitereponse: str | None
    dateparution: str | None
    etat: str | None
    source_url: str
    requires_verification: bool


def lookup_boamp_notice(arguments: dict) -> BOAMPOutput:
    from core.boamp import get_notice

    args = BOAMPInput.model_validate(arguments)
    record = get_notice(args.idweb)

    fields = {
        key: record.get(key)
        for key in BOAMPOutput.model_fields
    }

    return BOAMPOutput.model_validate(fields)


# ============================================================
# TOOL 2: READ — RAG retrieval from the current dossier
# ============================================================

class RAGInput(StrictModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Question to answer using document evidence."
    )
    method: Literal["bm25", "hybrid"] = Field(
        default="bm25",
        description="BM25 only, or BM25 plus BGE-M3 and RRF."
    )
    top_k: int = Field(
        default=6,
        ge=1,
        le=10,
        description="Maximum number of passages to retrieve."
    )


class Evidence(StrictModel):
    source_id: str
    document: str
    page: int
    text: str


class RAGOutput(StrictModel):
    question: str
    method: Literal["bm25", "hybrid"]
    passages: list[Evidence]
    human_review_required: bool


def rag_search_documents(
    arguments: dict,
    pages: list[dict]
) -> RAGOutput:
    from core.rag import chunk_pages, retrieve
    from core.hybrid import retrieve_hybrid

    args = RAGInput.model_validate(arguments)
    chunks = chunk_pages(pages)

    if args.method == "hybrid":
        results = retrieve_hybrid(
            chunks, args.question, limit=args.top_k
        )
    else:
        results = retrieve(
            chunks, args.question, limit=args.top_k
        )

    output = {
        "question": args.question,
        "method": args.method,
        "passages": [
            {
                "source_id": chunk["id"],
                "document": chunk["document"],
                "page": chunk["page"],
                "text": chunk["text"],
            }
            for chunk in results
        ],
        "human_review_required": True,
    }

    return RAGOutput.model_validate(output)


# ============================================================
# TOOL 3: WRITE — Add an item to the review checklist
# ============================================================

class ChecklistInput(StrictModel):
    label: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Requirement to add to the checklist."
    )
    source_document: str = Field(
        ...,
        min_length=1,
        description="Filename of the supporting document."
    )
    source_page: int = Field(
        ...,
        ge=1,
        description="Page containing the supporting quotation."
    )
    quote: str = Field(
        ...,
        min_length=3,
        description="Exact supporting quotation from the source."
    )
    mandatory: bool = Field(
        ...,
        description="Whether the requirement is mandatory."
    )


class ChecklistOutput(StrictModel):
    created: bool
    item_index: int
    label: str
    status: Literal["À vérifier"]


def add_requirement_to_checklist(
    arguments: dict,
    pages: list[dict],
    requirements: list[dict],
) -> ChecklistOutput:

    args = ChecklistInput.model_validate(arguments)

    # Check the supporting quotation before allowing the write.
    matching_page = next(
        (
            page for page in pages
            if page["document"] == args.source_document
            and page["page"] == args.source_page
        ),
        None,
    )

    if matching_page is None or args.quote not in matching_page["text"]:
        raise ValueError(
            "WRITE rejected: the quotation was not found "
            "on the specified source page."
        )

    item = {
        "label": args.label,
        "source": (
            f"{args.source_document}, page {args.source_page}: "
            f"{args.quote}"
        ),
        "mandatory": args.mandatory,
        "status": "À vérifier",
    }

    requirements.append(item)

    return ChecklistOutput.model_validate({
        "created": True,
        "item_index": len(requirements) - 1,
        "label": args.label,
        "status": "À vérifier",
    })


# ============================================================
# JSON SCHEMA EXPORT — The actual Session 2 deliverable
# ============================================================

TOOLS = [
    {
        "name": "lookup_boamp_notice",
        "description": (
            "Retrieve publicly available BOAMP notice metadata "
            "by official notice ID without accessing protected "
            "buyer portals."
        ),
        "access": "read",
        "input_model": BOAMPInput,
        "output_model": BOAMPOutput,
    },
    {
        "name": "rag_search_documents",
        "description": (
            "Retrieve source-indexed passages from the active "
            "procurement dossier using BM25 or hybrid BM25 "
            "and BGE-M3 semantic retrieval."
        ),
        "access": "read",
        "input_model": RAGInput,
        "output_model": RAGOutput,
    },
    {
        "name": "add_requirement_to_checklist",
        "description": (
            "Add a source-supported requirement to the current "
            "in-session bid/no-bid checklist, initially marked "
            "as requiring human verification."
        ),
        "access": "write",
        "input_model": ChecklistInput,
        "output_model": ChecklistOutput,
    },
]


def export_tool_schemas() -> dict:
    return {
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"],
                "access": tool["access"],
                "parameters": tool["input_model"].model_json_schema(),
                "returns": tool["output_model"].model_json_schema(),
            }
            for tool in TOOLS
        ]
    }


if __name__ == "__main__":
    print(json.dumps(
        export_tool_schemas(),
        indent=2,
        ensure_ascii=False,
    ))

