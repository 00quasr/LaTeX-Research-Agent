"""
Draft Chapters Node - Sequential chapter drafting with rolling context.

This module implements resource-efficient paper generation by:
1. Processing chapters sequentially (not parallel)
2. Writing each chapter to disk immediately
3. Using rolling summaries for context (not full content)
4. Staying within LLM token limits (~3000 words per chapter)
"""

import tempfile
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from ..state import (
    ResearchState,
    ChapterDraft,
    Chapter,
    ChapterOutline,
    WORDS_PER_CHAPTER,
    MAX_SUMMARY_WORDS,
)

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "prompts"


class ChapterContent(BaseModel):
    """Structured output for chapter drafting."""
    content: str = Field(description="The full chapter content in markdown format")
    word_count: int = Field(description="Word count of the content")


class ChapterSummary(BaseModel):
    """Structured output for chapter summary."""
    summary: str = Field(
        description=f"A concise {MAX_SUMMARY_WORDS}-word summary of the chapter's main points",
        max_length=800
    )


def get_llm(provider: str, model: str, api_key: str, structured_output=None):
    """Get LLM instance with optional structured output."""
    if provider == "anthropic":
        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.7,
        )
    else:
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0.7,
        )

    if structured_output:
        return llm.with_structured_output(structured_output)
    return llm


async def draft_single_chapter(
    chapter: Chapter,
    previous_summaries: List[str],
    paper_title: str,
    thesis_statement: str,
    level: str,
    language: str,
    citation_style: str,
    additional_instructions: str,
    provider: str,
    model: str,
    api_key: str,
) -> str:
    """
    Draft a single chapter with context from previous chapters.

    Args:
        chapter: The chapter to draft
        previous_summaries: List of summaries from all previous chapters
        Other args: Context for drafting

    Returns:
        The chapter content as markdown string
    """
    # Load template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("draft_chapter.j2")

    # Build context from previous summaries (limited to avoid token overflow)
    context_text = "\n\n".join(previous_summaries) if previous_summaries else ""

    prompt = template.render(
        paper_title=paper_title,
        thesis_statement=thesis_statement,
        chapter=chapter,
        previous_context=context_text,
        level=level,
        language=language,
        citation_style=citation_style,
        additional_instructions=additional_instructions,
        target_words=chapter.target_words,
    )

    # Get LLM (use regular output, not structured, for longer content)
    llm = get_llm(provider, model, api_key)

    # Generate content
    response = await llm.ainvoke(prompt)
    return response.content


async def generate_chapter_summary(
    content: str,
    chapter_title: str,
    provider: str,
    model: str,
    api_key: str,
) -> str:
    """
    Generate a concise summary of a chapter for rolling context.

    Args:
        content: The full chapter content
        chapter_title: Title of the chapter

    Returns:
        A ~100-word summary of the chapter
    """
    # Load template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("chapter_summary.j2")

    prompt = template.render(
        chapter_title=chapter_title,
        content=content,
        max_words=MAX_SUMMARY_WORDS,
    )

    # Use structured output for summary
    llm = get_llm(provider, model, api_key, structured_output=ChapterSummary)

    response = await llm.ainvoke(prompt)
    return response.summary


async def draft_chapters_node(state: ResearchState) -> dict:
    """
    Draft all chapters sequentially with rolling context.

    This is the main node for resource-efficient paper generation.
    Each chapter is:
    1. Drafted with context from previous chapter summaries
    2. Written to disk immediately (not held in memory)
    3. Summarized for the next chapter's context

    Returns:
        Dict with chapter_dir, chapter_summaries, chapter_drafts
    """
    tracer = state.get("tracer")
    chapter_outline = state["chapter_outline"]
    research_plan = state["research_plan"]

    if tracer:
        await tracer.markdown("## ✍️ Drafting Chapters")
        await tracer.markdown(f"**Total Chapters**: {len(chapter_outline.chapters)}")
        await tracer.markdown(f"**Target Words per Chapter**: ~{WORDS_PER_CHAPTER}")
        await tracer.markdown("Using sequential drafting with rolling context...")

    # Create temp directory for chapter files
    temp_dir = Path(tempfile.mkdtemp(prefix="paper_chapters_"))

    # Prepare LLM settings
    provider = state.get("model_provider", "openai")
    if provider == "anthropic":
        strong_model = state.get("strong_model", "claude-sonnet-4-20250514")
        fast_model = state.get("fast_model", "claude-3-5-haiku-20241022")
        api_key = state.get("anthropic_api_key")
    else:
        strong_model = state.get("strong_model", "gpt-4o")
        fast_model = state.get("fast_model", "gpt-4o-mini")
        api_key = state.get("openai_api_key")

    chapter_summaries = []
    chapter_drafts = []
    total_words = 0

    # Process chapters sequentially
    for i, chapter in enumerate(chapter_outline.chapters):
        chapter_num = i + 1

        if tracer:
            await tracer.markdown(f"\n### Chapter {chapter_num}: {chapter.title}")
            await tracer.markdown(f"Drafting with context from {len(chapter_summaries)} previous chapters...")

        # Draft the chapter with rolling context
        content = await draft_single_chapter(
            chapter=chapter,
            previous_summaries=chapter_summaries,
            paper_title=chapter_outline.title,
            thesis_statement=research_plan.thesis_statement,
            level=state.get("level", "academic"),
            language=state.get("language", "en"),
            citation_style=state.get("citation_style", "apa"),
            additional_instructions=state.get("additional_instructions", ""),
            provider=provider,
            model=strong_model,  # Use strong model for main content
            api_key=api_key,
        )

        # Calculate word count
        word_count = len(content.split())
        total_words += word_count

        # Write to disk immediately (don't hold in memory)
        chapter_file = temp_dir / f"chapter_{chapter_num:02d}.md"
        chapter_file.write_text(f"## {chapter.title}\n\n{content}")

        if tracer:
            await tracer.markdown(f"✅ **{word_count} words** written to disk")

        # Generate summary for next chapter's context (use fast model)
        summary = await generate_chapter_summary(
            content=content,
            chapter_title=chapter.title,
            provider=provider,
            model=fast_model,
            api_key=api_key,
        )

        # Store summary with chapter title for context
        chapter_summaries.append(f"**Chapter {chapter_num}: {chapter.title}**\n{summary}")

        # Store draft metadata (content is on disk)
        chapter_drafts.append(ChapterDraft(
            chapter_id=chapter.id,
            title=chapter.title,
            content=content,  # Store content for now, but primary is disk
            summary=summary,
            word_count=word_count,
            file_path=str(chapter_file),
        ))

        if tracer:
            await tracer.markdown(f"📝 Summary generated for context")
            await tracer.markdown(f"Progress: **{chapter_num}/{len(chapter_outline.chapters)}** chapters")

    if tracer:
        await tracer.markdown("\n### Drafting Complete!")
        await tracer.markdown(f"**Total Words**: {total_words}")
        await tracer.markdown(f"**Chapter Files**: {temp_dir}")

    return {
        "chapter_dir": str(temp_dir),
        "chapter_summaries": chapter_summaries,
        "chapter_drafts": chapter_drafts,
    }
