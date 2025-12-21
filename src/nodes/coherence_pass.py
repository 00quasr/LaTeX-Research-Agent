"""
Coherence Pass Node - Final editing pass for consistency and quality.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..state import ResearchState, CoherentPaper, estimate_words_from_pages
from .research_plan import get_llm

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "prompts"


async def coherence_pass_node(state: ResearchState) -> dict:
    """
    Perform a global coherence pass on the drafted sections.

    This node:
    - Ensures smooth transitions between sections
    - Eliminates redundancy
    - Standardizes terminology
    - Writes the abstract
    - Polishes the final text
    """
    tracer = state.get("tracer")
    section_drafts = state["section_drafts"]
    research_plan = state["research_plan"]

    if tracer:
        await tracer.markdown("## 🔄 Coherence Pass")
        await tracer.markdown("Performing final editing and integration...")

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

    template = env.get_template("coherence_pass.j2")
    prompt = template.render(
        paper_title=state["outline"].title,
        thesis_statement=research_plan.thesis_statement,
        target_words=target_words,
        level=state.get("level", "academic"),
        language=state.get("language", "en"),
        section_drafts=[d.model_dump() for d in section_drafts],
    )

    # Use strong model for coherence pass
    llm = get_llm(state, use_strong=True)
    structured_llm = llm.with_structured_output(CoherentPaper)

    # Generate coherent paper
    coherent_paper = await structured_llm.ainvoke(prompt)

    if tracer:
        await tracer.markdown("### Coherence Pass Complete")
        await tracer.markdown(f"**Final Title**: {coherent_paper.title}")
        await tracer.markdown(f"**Abstract**: {len(coherent_paper.abstract)} characters")
        await tracer.markdown(f"**Body Word Count**: {coherent_paper.word_count}")
        await tracer.markdown(f"**Sections**: {coherent_paper.sections_count}")

    return {
        "coherent_paper": coherent_paper,
    }
