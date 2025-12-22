"""
State definitions and Pydantic models for the LaTeX Research Agent.

This module defines:
- ResearchState: The TypedDict used by LangGraph for workflow state
- Pydantic models for structured LLM outputs (outline, sections, etc.)
"""

from typing import TypedDict, List, Optional, Literal, Any
from pydantic import BaseModel, Field


# =============================================================================
# Pydantic Models for Structured LLM Outputs
# =============================================================================

class ResearchPlan(BaseModel):
    """Output from the research planning node."""

    title: str = Field(description="Proposed title for the research paper")
    thesis_statement: str = Field(description="Central thesis or argument of the paper")
    research_questions: List[str] = Field(
        description="Key research questions to address",
        min_length=2,
        max_length=5
    )
    methodology_approach: str = Field(
        description="Brief description of the research methodology/approach"
    )
    key_themes: List[str] = Field(
        description="Main themes or topics to explore",
        min_length=3,
        max_length=8
    )
    target_audience: str = Field(
        description="Intended audience for the paper"
    )


class Subsection(BaseModel):
    """A subsection within a section."""

    id: str = Field(description="Unique identifier, e.g., '2.1'")
    title: str = Field(description="Subsection title")
    key_points: List[str] = Field(
        description="Key points to cover in this subsection",
        min_length=3,
        max_length=10
    )
    target_words: int = Field(
        description="Target word count for this subsection",
        ge=500,
        le=5000
    )
    suggested_figures: Optional[List[str]] = Field(
        description="Suggested figures, charts, or tables for this subsection",
        default=None
    )


class Section(BaseModel):
    """A major section of the paper."""

    id: str = Field(description="Unique identifier, e.g., '2'")
    title: str = Field(description="Section title")
    purpose: str = Field(description="Purpose/goal of this section")
    subsections: List[Subsection] = Field(
        description="Subsections within this section",
        default_factory=list
    )
    target_words: int = Field(
        description="Target word count for entire section",
        ge=1000,
        le=15000
    )


class PaperOutline(BaseModel):
    """Complete outline structure for the paper."""

    title: str = Field(description="Final paper title")
    abstract_summary: str = Field(
        description="Brief summary for the abstract (will be expanded later)",
        max_length=500
    )
    sections: List[Section] = Field(
        description="All major sections of the paper",
        min_length=4,
        max_length=12
    )
    total_estimated_words: int = Field(
        description="Total estimated word count"
    )

    def get_all_subsections(self) -> List[tuple[Section, Subsection]]:
        """Return all subsections with their parent sections."""
        result = []
        for section in self.sections:
            for subsection in section.subsections:
                result.append((section, subsection))
        return result


class SectionDraft(BaseModel):
    """A drafted section/subsection of the paper."""

    section_id: str = Field(description="Section/subsection ID (e.g., '2' or '2.1')")
    title: str = Field(description="Section/subsection title")
    content: str = Field(description="The drafted content in markdown format")
    word_count: int = Field(description="Actual word count")
    citations_used: List[str] = Field(
        description="List of citation keys used (if any)",
        default_factory=list
    )


class CoherentPaper(BaseModel):
    """The complete paper after coherence pass."""

    title: str
    abstract: str = Field(description="Full abstract text")
    body: str = Field(description="Complete paper body in markdown")
    word_count: int
    sections_count: int


class Citation(BaseModel):
    """A citation/reference entry."""

    key: str = Field(description="BibTeX key, e.g., 'smith2023'")
    type: Literal["article", "book", "inproceedings", "misc", "online"] = Field(
        default="misc"
    )
    title: str
    author: str
    year: str
    journal: Optional[str] = None
    booktitle: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None


class Bibliography(BaseModel):
    """Collection of citations."""

    citations: List[Citation] = Field(default_factory=list)

    def to_bibtex(self) -> str:
        """Convert to BibTeX format."""
        entries = []
        for cite in self.citations:
            entry = f"@{cite.type}{{{cite.key},\n"
            entry += f"  title = {{{cite.title}}},\n"
            entry += f"  author = {{{cite.author}}},\n"
            entry += f"  year = {{{cite.year}}},\n"
            if cite.journal:
                entry += f"  journal = {{{cite.journal}}},\n"
            if cite.booktitle:
                entry += f"  booktitle = {{{cite.booktitle}}},\n"
            if cite.url:
                entry += f"  url = {{{cite.url}}},\n"
            if cite.note:
                entry += f"  note = {{{cite.note}}},\n"
            entry = entry.rstrip(",\n") + "\n}"
            entries.append(entry)
        return "\n\n".join(entries)


# =============================================================================
# LangGraph State TypedDict
# =============================================================================

class ResearchState(TypedDict, total=False):
    """
    The state object passed through the LangGraph workflow.

    All fields are optional (total=False) to allow incremental population.
    """

    # === Input fields (from user form) ===
    topic: str
    target_pages: int
    language: str  # e.g., "en", "de"
    level: str  # "academic", "technical", "general"
    citation_style: str  # "apa", "ieee", "chicago", "mla"
    additional_instructions: str  # Optional user notes

    # === LLM Configuration ===
    model_provider: str  # "openai" or "anthropic"
    strong_model: str  # e.g., "gpt-4o" or "claude-sonnet-4-20250514"
    fast_model: str  # e.g., "gpt-4o-mini" or "claude-3-5-haiku-20241022"
    openai_api_key: str  # API key passed through state for Ray workers
    anthropic_api_key: str  # API key passed through state for Ray workers

    # === Generated content ===
    research_plan: ResearchPlan
    outline: PaperOutline
    section_drafts: List[SectionDraft]
    coherent_paper: CoherentPaper
    bibliography: Bibliography

    # === LaTeX outputs ===
    latex_content: str
    bibtex_content: str

    # === File outputs ===
    tex_path: str
    bib_path: str
    pdf_path: str
    zip_path: str

    # === Metadata ===
    total_tokens_used: int
    total_cost_usd: float
    errors: List[str]

    # === System (injected by Kodosumi) ===
    tracer: Any  # Tracer object for progress updates


# =============================================================================
# Default Configuration
# =============================================================================

DEFAULT_CONFIG = {
    "target_pages": 20,
    "language": "en",
    "level": "academic",
    "citation_style": "apa",
    "model_provider": "openai",
    "strong_model": "gpt-4o",
    "fast_model": "gpt-4o-mini",
}

# Words per page estimate (academic formatting with figures/tables)
# Standard academic paper: ~500 words per page with margins, spacing, figures
WORDS_PER_PAGE = 500

def estimate_words_from_pages(pages: int) -> int:
    """Estimate total words from target page count."""
    return pages * WORDS_PER_PAGE
