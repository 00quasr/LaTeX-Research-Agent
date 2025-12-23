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


# =============================================================================
# Chapter-Based Models (for resource-efficient large paper generation)
# =============================================================================

class Chapter(BaseModel):
    """
    A chapter grouping 2-3 sections, ~3000 words max.

    This enables sequential drafting within LLM token limits while
    maintaining coherence through rolling context summaries.
    """

    id: str = Field(description="Chapter number, e.g., '1', '2'")
    title: str = Field(description="Chapter title")
    sections: List[Section] = Field(
        description="2-3 sections grouped in this chapter",
        min_length=1,
        max_length=4
    )
    target_words: int = Field(
        description="Target word count for entire chapter",
        ge=2000,
        le=4000
    )

    def get_section_titles(self) -> List[str]:
        """Return list of section titles in this chapter."""
        return [s.title for s in self.sections]


class ChapterDraft(BaseModel):
    """
    A drafted chapter with summary for rolling context.

    The summary is used to provide context to subsequent chapters
    without passing the full content (which would exceed token limits).
    """

    chapter_id: str = Field(description="Chapter ID matching the outline")
    title: str = Field(description="Chapter title")
    content: str = Field(description="Full chapter content in markdown")
    summary: str = Field(
        description="100-word summary for next chapter context",
        max_length=800  # ~100 words with buffer
    )
    word_count: int = Field(description="Actual word count of content")
    file_path: str = Field(description="Path to chapter markdown file on disk")


class ChapterOutline(BaseModel):
    """
    Chapter-based outline structure for large papers.

    Groups sections into chapters to enable sequential drafting
    within LLM token limits.
    """

    title: str = Field(description="Final paper title")
    abstract_summary: str = Field(
        description="Brief summary for the abstract (expanded from chapter summaries)",
        max_length=500
    )
    chapters: List[Chapter] = Field(
        description="All chapters of the paper",
        min_length=5,
        max_length=20
    )
    total_estimated_words: int = Field(
        description="Total estimated word count"
    )

    def get_all_sections(self) -> List[Section]:
        """Return all sections across all chapters."""
        result = []
        for chapter in self.chapters:
            result.extend(chapter.sections)
        return result

    def get_chapter_count(self) -> int:
        """Return number of chapters."""
        return len(self.chapters)


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

    # === Chapter-based content (for large papers) ===
    chapter_outline: ChapterOutline  # Chapter-based outline structure
    chapter_drafts: List[ChapterDraft]  # Drafted chapters with summaries
    chapter_dir: str  # Path to temp directory with chapter markdown files
    chapter_summaries: List[str]  # 100-word summaries for abstract generation
    abstract: str  # Final abstract generated from chapter summaries
    final_title: str  # Final paper title

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

# =============================================================================
# Chapter Sizing Configuration (for resource-efficient large papers)
# =============================================================================

# Maximum words per chapter to stay within LLM output limits
# GPT-4o output limit: ~16K tokens = ~4000 words
# We target 3000 words to leave headroom for formatting
WORDS_PER_CHAPTER = 3000

# Maximum summary words for rolling context
# Each chapter gets a ~100 word summary passed to the next chapter
MAX_SUMMARY_WORDS = 100

# Maximum total context words from previous chapters
# We include summaries of all previous chapters up to this limit
MAX_CONTEXT_WORDS = 500

# Minimum chapters for a large paper (60+ pages)
MIN_CHAPTERS_LARGE_PAPER = 10


def estimate_words_from_pages(pages: int) -> int:
    """Estimate total words from target page count."""
    return pages * WORDS_PER_PAGE


def estimate_chapters_from_pages(pages: int) -> int:
    """Estimate number of chapters needed for target page count."""
    total_words = estimate_words_from_pages(pages)
    chapters = max(5, total_words // WORDS_PER_CHAPTER)
    return chapters


def get_chapter_word_target(total_words: int, num_chapters: int) -> int:
    """Calculate target words per chapter."""
    base_target = total_words // num_chapters
    # Cap at WORDS_PER_CHAPTER to stay within LLM limits
    return min(base_target, WORDS_PER_CHAPTER)
