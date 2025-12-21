"""
Research Plan Node - Creates the initial research plan for the paper.
"""

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..state import ResearchState, ResearchPlan, estimate_words_from_pages

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "prompts"


def get_llm(state: ResearchState, use_strong: bool = True):
    """Get the appropriate LLM based on configuration."""
    provider = state.get("model_provider", "openai")

    if provider == "anthropic":
        model = state.get("strong_model", "claude-sonnet-4-20250514") if use_strong else state.get("fast_model", "claude-3-5-haiku-20241022")
        return ChatAnthropic(
            model=model,
            api_key=state.get("anthropic_api_key"),
            temperature=0.7,
        )
    else:
        model = state.get("strong_model", "gpt-4o") if use_strong else state.get("fast_model", "gpt-4o-mini")
        return ChatOpenAI(
            model=model,
            api_key=state.get("openai_api_key"),
            temperature=0.7,
        )


async def research_plan_node(state: ResearchState) -> dict:
    """
    Generate a research plan based on the user's topic and requirements.

    This is the first node in the pipeline - it analyzes the topic and
    creates a structured research plan to guide the paper.
    """
    tracer = state.get("tracer")

    if tracer:
        await tracer.markdown("## 📋 Creating Research Plan")
        await tracer.markdown(f"Analyzing topic: **{state['topic']}**")

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

    template = env.get_template("research_plan.j2")
    prompt = template.render(
        topic=state["topic"],
        target_pages=target_pages,
        target_words=target_words,
        level=state.get("level", "academic"),
        language=state.get("language", "en"),
        citation_style=state.get("citation_style", "apa"),
        additional_instructions=state.get("additional_instructions", ""),
    )

    # Get LLM with structured output
    llm = get_llm(state, use_strong=True)
    structured_llm = llm.with_structured_output(ResearchPlan)

    # Generate research plan
    research_plan = await structured_llm.ainvoke(prompt)

    if tracer:
        await tracer.markdown(f"### Research Plan Complete")
        await tracer.markdown(f"**Title**: {research_plan.title}")
        await tracer.markdown(f"**Thesis**: {research_plan.thesis_statement}")
        await tracer.markdown(f"**Research Questions**: {len(research_plan.research_questions)}")
        await tracer.markdown(f"**Key Themes**: {', '.join(research_plan.key_themes)}")

    return {
        "research_plan": research_plan,
    }
