"""
Build Outline Node - Creates the detailed paper outline structure.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..state import ResearchState, PaperOutline, estimate_words_from_pages
from .research_plan import get_llm

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "prompts"


async def build_outline_node(state: ResearchState) -> dict:
    """
    Generate a detailed outline based on the research plan.

    Creates the complete structure including all sections and subsections
    with target word counts.
    """
    tracer = state.get("tracer")
    research_plan = state["research_plan"]

    if tracer:
        await tracer.markdown("## 📑 Building Paper Outline")
        await tracer.markdown(f"Creating structure for: **{research_plan.title}**")

    # Calculate target words
    target_pages = int(state.get("target_pages", 20))
    target_words = estimate_words_from_pages(target_pages)

    # Load and render template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

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
            await tracer.markdown(f"- {section.id}. {section.title} ({section.target_words} words, {subsection_count} subsections)")
        await tracer.markdown(f"**Total Estimated Words**: {outline.total_estimated_words}")

    return {
        "outline": outline,
    }
