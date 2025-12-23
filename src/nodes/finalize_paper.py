"""
Finalize Paper Node - Generate abstract and finalize paper metadata.

This is a lightweight replacement for the coherence pass.
Since chapters are drafted sequentially with rolling context,
coherence is built-in and we only need to:
1. Generate the abstract from chapter summaries
2. Finalize the paper title
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from ..state import ResearchState

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "prompts"


class PaperAbstract(BaseModel):
    """Structured output for abstract generation."""
    abstract: str = Field(
        description="The complete abstract text (200-300 words)",
        min_length=500,  # ~200 words minimum
        max_length=2500  # ~300 words maximum
    )


def get_llm(provider: str, model: str, api_key: str, structured_output=None):
    """Get LLM instance with optional structured output."""
    if provider == "anthropic":
        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.5,  # Lower temperature for abstract
        )
    else:
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0.5,
        )

    if structured_output:
        return llm.with_structured_output(structured_output)
    return llm


async def finalize_paper_node(state: ResearchState) -> dict:
    """
    Generate abstract and finalize paper metadata.

    This is a lightweight operation that:
    1. Generates abstract from chapter summaries (~500 words input)
    2. Returns final title and abstract

    No full paper reprocessing needed since sequential drafting
    handles coherence through rolling context.
    """
    tracer = state.get("tracer")
    chapter_outline = state["chapter_outline"]
    chapter_summaries = state["chapter_summaries"]
    research_plan = state["research_plan"]

    if tracer:
        await tracer.markdown("## 📄 Finalizing Paper")
        await tracer.markdown("Generating abstract from chapter summaries...")

    # Prepare LLM
    provider = state.get("model_provider", "openai")
    if provider == "anthropic":
        model = state.get("strong_model", "claude-sonnet-4-20250514")
        api_key = state.get("anthropic_api_key")
    else:
        model = state.get("strong_model", "gpt-4o")
        api_key = state.get("openai_api_key")

    # Load abstract template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("abstract_from_summaries.j2")

    prompt = template.render(
        title=chapter_outline.title,
        thesis_statement=research_plan.thesis_statement,
        chapter_summaries=chapter_summaries,
        level=state.get("level", "academic"),
        language=state.get("language", "en"),
    )

    # Generate abstract
    llm = get_llm(provider, model, api_key, structured_output=PaperAbstract)
    result = await llm.ainvoke(prompt)

    if tracer:
        await tracer.markdown("### Abstract Generated")
        await tracer.markdown(f"**Length**: {len(result.abstract.split())} words")

    return {
        "abstract": result.abstract,
        "final_title": chapter_outline.title,
    }
