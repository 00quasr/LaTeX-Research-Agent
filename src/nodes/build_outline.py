"""
Build Outline Node - Creates the detailed paper outline structure.

Supports two modes:
1. Chapter-based (for large papers 40+ pages): Uses ChapterOutline
2. Section-based (legacy): Uses PaperOutline
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..state import (
    ResearchState,
    PaperOutline,
    ChapterOutline,
    estimate_words_from_pages,
    estimate_chapters_from_pages,
    WORDS_PER_CHAPTER,
)
from .research_plan import get_llm

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "prompts"

# Threshold for using chapter-based mode (pages)
CHAPTER_MODE_THRESHOLD = 40


async def build_outline_node(state: ResearchState) -> dict:
    """
    Generate a detailed outline based on the research plan.

    For papers 40+ pages, uses chapter-based structure for resource efficiency.
    For smaller papers, uses section-based structure (legacy).
    """
    tracer = state.get("tracer")
    research_plan = state["research_plan"]

    # Calculate target words
    target_pages = int(state.get("target_pages", 20))
    target_words = estimate_words_from_pages(target_pages)

    # Determine which mode to use
    use_chapter_mode = target_pages >= CHAPTER_MODE_THRESHOLD

    if tracer:
        await tracer.markdown("## 📑 Building Paper Outline")
        await tracer.markdown(f"Creating structure for: **{research_plan.title}**")
        if use_chapter_mode:
            await tracer.markdown(f"📚 Using **chapter-based** mode for {target_pages}-page paper")
        else:
            await tracer.markdown(f"📝 Using **section-based** mode for {target_pages}-page paper")

    # Load and render template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    if use_chapter_mode:
        # Chapter-based outline for large papers
        return await _build_chapter_outline(
            env, state, research_plan, target_pages, target_words, tracer
        )
    else:
        # Legacy section-based outline
        return await _build_section_outline(
            env, state, research_plan, target_pages, target_words, tracer
        )


async def _build_chapter_outline(env, state, research_plan, target_pages, target_words, tracer):
    """Build chapter-based outline for large papers."""
    num_chapters = estimate_chapters_from_pages(target_pages)
    words_per_chapter = WORDS_PER_CHAPTER

    template = env.get_template("outline_chapters.j2")
    prompt = template.render(
        research_plan=research_plan,
        target_pages=target_pages,
        target_words=target_words,
        num_chapters=num_chapters,
        words_per_chapter=words_per_chapter,
        level=state.get("level", "academic"),
        language=state.get("language", "en"),
        additional_instructions=state.get("additional_instructions", ""),
    )

    # Get LLM with structured output
    llm = get_llm(state, use_strong=True)
    structured_llm = llm.with_structured_output(ChapterOutline)

    # Generate outline
    chapter_outline = await structured_llm.ainvoke(prompt)

    if tracer:
        await tracer.markdown("### Chapter Outline Generated")
        await tracer.markdown(f"**Chapters**: {len(chapter_outline.chapters)}")
        for chapter in chapter_outline.chapters:
            section_count = len(chapter.sections)
            await tracer.markdown(
                f"- **Chapter {chapter.id}: {chapter.title}** "
                f"({chapter.target_words} words, {section_count} sections)"
            )
        await tracer.markdown(f"**Total Estimated Words**: {chapter_outline.total_estimated_words}")

    return {
        "chapter_outline": chapter_outline,
    }


async def _build_section_outline(env, state, research_plan, target_pages, target_words, tracer):
    """Build section-based outline (legacy mode)."""
    template = env.get_template("outline.j2")
    prompt = template.render(
        research_plan=research_plan,
        target_pages=target_pages,
        target_words=target_words,
        level=state.get("level", "academic"),
        language=state.get("language", "en"),
        additional_instructions=state.get("additional_instructions", ""),
    )

    # Get LLM with structured output
    llm = get_llm(state, use_strong=True)
    structured_llm = llm.with_structured_output(PaperOutline)

    # Generate outline
    outline = await structured_llm.ainvoke(prompt)

    if tracer:
        await tracer.markdown("### Outline Generated")
        await tracer.markdown(f"**Sections**: {len(outline.sections)}")
        for section in outline.sections:
            subsection_count = len(section.subsections)
            await tracer.markdown(
                f"- {section.id}. {section.title} "
                f"({section.target_words} words, {subsection_count} subsections)"
            )
        await tracer.markdown(f"**Total Estimated Words**: {outline.total_estimated_words}")

    return {
        "outline": outline,
    }
