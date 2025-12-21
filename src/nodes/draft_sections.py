"""
Draft Sections Node - Parallel drafting of all paper sections.

Uses Ray for parallel execution of section drafting.
"""

import os
from pathlib import Path
from typing import List

import ray
from jinja2 import Environment, FileSystemLoader
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..state import ResearchState, SectionDraft, Section, Subsection

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "prompts"


def get_llm_sync(provider: str, model: str, api_key: str):
    """Get LLM instance (sync version for Ray remote)."""
    if provider == "anthropic":
        return ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.7,
        )
    else:
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0.7,
        )


@ray.remote
def draft_single_section(
    section: dict,
    subsection: dict | None,
    paper_title: str,
    thesis_statement: str,
    level: str,
    language: str,
    citation_style: str,
    additional_instructions: str,
    previous_sections: List[dict],
    provider: str,
    model: str,
    api_key: str,
) -> dict:
    """
    Draft a single section or subsection.

    This is a Ray remote function for parallel execution.
    """
    # Load template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("draft_section.j2")

    # Convert dicts back to objects for template
    section_obj = Section(**section)
    subsection_obj = Subsection(**subsection) if subsection else None

    prompt = template.render(
        paper_title=paper_title,
        thesis_statement=thesis_statement,
        section=section_obj,
        subsection=subsection_obj,
        level=level,
        language=language,
        citation_style=citation_style,
        additional_instructions=additional_instructions,
        previous_sections=previous_sections,
    )

    # Get LLM
    llm = get_llm_sync(provider, model, api_key)

    # Generate content
    response = llm.invoke(prompt)
    content = response.content

    # Calculate word count
    word_count = len(content.split())

    # Determine section ID and title
    if subsection_obj:
        section_id = subsection_obj.id
        title = subsection_obj.title
    else:
        section_id = section_obj.id
        title = section_obj.title

    return {
        "section_id": section_id,
        "title": title,
        "content": content,
        "word_count": word_count,
        "citations_used": [],  # TODO: Extract citations from content
    }


async def draft_sections_node(state: ResearchState) -> dict:
    """
    Draft all sections in parallel using Ray.

    For each section with subsections, drafts subsections individually.
    For sections without subsections, drafts the entire section.
    """
    tracer = state.get("tracer")
    outline = state["outline"]
    research_plan = state["research_plan"]

    if tracer:
        await tracer.markdown("## ✍️ Drafting Sections")
        await tracer.markdown("Starting parallel section generation...")

    # Prepare drafting tasks
    provider = state.get("model_provider", "openai")
    # Use fast model for parallel drafting to save costs
    if provider == "anthropic":
        model = state.get("fast_model", "claude-3-5-haiku-20241022")
        api_key = state.get("anthropic_api_key")
    else:
        model = state.get("fast_model", "gpt-4o-mini")
        api_key = state.get("openai_api_key")

    # Collect all sections/subsections to draft
    draft_tasks = []
    for section in outline.sections:
        if section.subsections:
            # Draft each subsection
            for subsection in section.subsections:
                draft_tasks.append({
                    "section": section.model_dump(),
                    "subsection": subsection.model_dump(),
                })
        else:
            # Draft entire section
            draft_tasks.append({
                "section": section.model_dump(),
                "subsection": None,
            })

    if tracer:
        await tracer.markdown(f"**Total drafts to generate**: {len(draft_tasks)}")

    # Launch Ray tasks
    # Note: For simplicity, we're not passing previous_sections to enable full parallelism
    # In a more sophisticated version, we could batch by section groups
    futures = [
        draft_single_section.remote(
            section=task["section"],
            subsection=task["subsection"],
            paper_title=outline.title,
            thesis_statement=research_plan.thesis_statement,
            level=state.get("level", "academic"),
            language=state.get("language", "en"),
            citation_style=state.get("citation_style", "apa"),
            additional_instructions=state.get("additional_instructions", ""),
            previous_sections=[],  # Empty for parallel execution
            provider=provider,
            model=model,
            api_key=api_key,
        )
        for task in draft_tasks
    ]

    # Collect results with progress tracking
    section_drafts = []
    unready = futures.copy()
    completed = 0

    while unready:
        ready, unready = ray.wait(unready, num_returns=1, timeout=1)
        if ready:
            result = ray.get(ready[0])
            section_drafts.append(SectionDraft(**result))
            completed += 1

            if tracer:
                await tracer.markdown(
                    f"✅ Drafted **{result['section_id']}. {result['title']}** "
                    f"({result['word_count']} words) [{completed}/{len(futures)}]"
                )

    # Sort by section ID for proper ordering
    section_drafts.sort(key=lambda x: [int(n) if n.isdigit() else n for n in x.section_id.split(".")])

    total_words = sum(d.word_count for d in section_drafts)

    if tracer:
        await tracer.markdown("### Drafting Complete")
        await tracer.markdown(f"**Total Words**: {total_words}")

    return {
        "section_drafts": section_drafts,
    }
