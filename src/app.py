"""
LaTeX Research Agent - Main Application

Kodosumi ServeAPI endpoint with LangGraph workflow.
"""

import os
from pathlib import Path
from typing import Any

# Load environment variables - try multiple locations
import dotenv

# Try loading from the actual project directory (not Ray temp)
PROJECT_ROOT = Path("/Users/keanuklestil/Documents/GitHub/LaTeX-Research-Agent")
dotenv.load_dotenv(PROJECT_ROOT / ".env")

# Also try relative path as fallback
dotenv.load_dotenv(Path(__file__).parent.parent / ".env")

# Store API keys for passing to Ray workers
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Debug: print if keys are loaded
print(f"[DEBUG] OPENAI_API_KEY loaded: {OPENAI_API_KEY[:20] if OPENAI_API_KEY else 'None'}...")

import ray
import fastapi
from ray import serve
from langgraph.graph import StateGraph, END

from kodosumi.core import ServeAPI, Launch, InputsError, Tracer
from kodosumi.response import HTML

from .forms import research_form_model
from .state import ResearchState, DEFAULT_CONFIG, estimate_words_from_pages
from .nodes import (
    research_plan_node,
    build_outline_node,
    draft_sections_node,
    coherence_pass_node,
    render_latex_node,
    compile_pdf_node,
)

# =============================================================================
# LangGraph Workflow Definition
# =============================================================================


def create_workflow() -> StateGraph:
    """Create the LangGraph workflow for research paper generation."""

    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("research_plan", research_plan_node)
    workflow.add_node("build_outline", build_outline_node)
    workflow.add_node("draft_sections", draft_sections_node)
    workflow.add_node("coherence_pass", coherence_pass_node)
    workflow.add_node("render_latex", render_latex_node)
    workflow.add_node("compile_pdf", compile_pdf_node)

    # Define edges (linear flow for MVP)
    workflow.set_entry_point("research_plan")
    workflow.add_edge("research_plan", "build_outline")
    workflow.add_edge("build_outline", "draft_sections")
    workflow.add_edge("draft_sections", "coherence_pass")
    workflow.add_edge("coherence_pass", "render_latex")
    workflow.add_edge("render_latex", "compile_pdf")
    workflow.add_edge("compile_pdf", END)

    return workflow.compile()


# Compile workflow once
graph = create_workflow()


# =============================================================================
# Runner Function (Entry Point)
# =============================================================================


async def runner(inputs: dict, tracer: Tracer) -> Any:
    """
    Main entry point for the LaTeX Research Agent.

    This function is called by Kodosumi when the workflow is triggered.
    """
    # Initialize Ray if not already
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    await tracer.markdown("# LaTeX Research Paper Generator")
    await tracer.markdown(f"**Topic**: {inputs.get('topic', 'N/A')}")
    await tracer.markdown(f"**Target Pages**: {inputs.get('target_pages', DEFAULT_CONFIG['target_pages'])}")
    await tracer.markdown("---")

    # Prepare initial state
    target_pages = int(inputs.get("target_pages") or DEFAULT_CONFIG["target_pages"])

    # Determine model configuration based on provider
    provider = inputs.get("model_provider", "openai")
    if provider == "anthropic":
        strong_model = "claude-sonnet-4-20250514"
        fast_model = "claude-3-5-haiku-20241022"
    else:
        strong_model = "gpt-4o"
        fast_model = "gpt-4o-mini"

    initial_state: ResearchState = {
        # User inputs
        "topic": inputs.get("topic", ""),
        "target_pages": target_pages,
        "language": inputs.get("language", DEFAULT_CONFIG["language"]),
        "level": inputs.get("level", DEFAULT_CONFIG["level"]),
        "citation_style": inputs.get("citation_style", DEFAULT_CONFIG["citation_style"]),
        "additional_instructions": inputs.get("additional_instructions", ""),

        # LLM configuration
        "model_provider": provider,
        "strong_model": strong_model,
        "fast_model": fast_model,
        "openai_api_key": OPENAI_API_KEY,
        "anthropic_api_key": ANTHROPIC_API_KEY,

        # System
        "tracer": tracer,
        "errors": [],
    }

    # Run the workflow
    try:
        result = await graph.ainvoke(initial_state)

        # Build final HTML output
        html = build_result_html(result)
        await tracer.html(html)

        return {
            "success": True,
            "title": result.get("coherent_paper", {}).title if result.get("coherent_paper") else "Untitled",
            "pdf_path": result.get("pdf_path"),
            "tex_path": result.get("tex_path"),
            "zip_path": result.get("zip_path"),
        }

    except Exception as e:
        await tracer.markdown(f"## ❌ Error")
        await tracer.markdown(f"An error occurred: {str(e)}")
        raise


def build_result_html(result: ResearchState) -> str:
    """Build the final HTML output for display."""

    coherent_paper = result.get("coherent_paper")
    pdf_path = result.get("pdf_path")
    tex_path = result.get("tex_path")
    zip_path = result.get("zip_path")

    html_parts = [
        "<div style='font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;'>",
        "<h1>📄 Research Paper Complete</h1>",
    ]

    if coherent_paper:
        html_parts.append(f"<h2>{coherent_paper.title}</h2>")
        html_parts.append(f"<p><strong>Word Count:</strong> {coherent_paper.word_count}</p>")
        html_parts.append(f"<p><strong>Sections:</strong> {coherent_paper.sections_count}</p>")

        # Abstract preview
        html_parts.append("<h3>Abstract</h3>")
        html_parts.append(f"<p style='font-style: italic; background: #f5f5f5; padding: 15px; border-radius: 5px;'>{coherent_paper.abstract}</p>")

    # Download links
    html_parts.append("<h3>📥 Downloads</h3>")
    html_parts.append("<div style='display: flex; gap: 10px; flex-wrap: wrap;'>")

    if pdf_path:
        html_parts.append(
            f"<a href='{pdf_path}' download style='display: inline-block; padding: 10px 20px; "
            f"background: #2196F3; color: white; text-decoration: none; border-radius: 5px;'>"
            f"📄 Download PDF</a>"
        )

    if tex_path:
        html_parts.append(
            f"<a href='{tex_path}' download style='display: inline-block; padding: 10px 20px; "
            f"background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;'>"
            f"📝 Download LaTeX</a>"
        )

    if zip_path:
        html_parts.append(
            f"<a href='{zip_path}' download style='display: inline-block; padding: 10px 20px; "
            f"background: #FF9800; color: white; text-decoration: none; border-radius: 5px;'>"
            f"📦 Download All (ZIP)</a>"
        )

    html_parts.append("</div>")

    # Outline summary
    outline = result.get("outline")
    if outline:
        html_parts.append("<h3>📋 Paper Structure</h3>")
        html_parts.append("<ul>")
        for section in outline.sections:
            html_parts.append(f"<li><strong>{section.id}. {section.title}</strong>")
            if section.subsections:
                html_parts.append("<ul>")
                for sub in section.subsections:
                    html_parts.append(f"<li>{sub.id} {sub.title}</li>")
                html_parts.append("</ul>")
            html_parts.append("</li>")
        html_parts.append("</ul>")

    html_parts.append("</div>")

    return "\n".join(html_parts)


# =============================================================================
# Kodosumi API Endpoint
# =============================================================================

app = ServeAPI()


@app.enter(
    path="/",
    model=research_form_model,
    summary="LaTeX Research Paper Generator",
    description="Generate comprehensive academic research papers with full LaTeX formatting and PDF output. "
                "Supports multiple languages, citation styles, and academic levels.",
    tags=["Research", "Academic", "LaTeX", "PDF"],
    version="0.1.0",
    author="research-agent@example.com",
    organization="LaTeX Research Agent",
)
async def enter(request: fastapi.Request, inputs: dict):
    """
    Entry point for the LaTeX Research Agent.

    Validates inputs and launches the workflow.
    """
    error = InputsError()

    # Validate required fields
    if not inputs.get("topic"):
        error.add(topic="Research topic is required")

    topic = inputs.get("topic", "")
    if len(topic) < 10:
        error.add(topic="Topic must be at least 10 characters")

    # Validate target pages
    target_pages = inputs.get("target_pages", "")
    if target_pages:
        try:
            pages = int(target_pages)
            if pages < 5 or pages > 100:
                error.add(target_pages="Page count must be between 5 and 100")
        except ValueError:
            error.add(target_pages="Page count must be a number")

    # Check for API keys
    provider = inputs.get("model_provider", "openai")
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        error.add(model_provider="OPENAI_API_KEY environment variable not set")
    elif provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        error.add(model_provider="ANTHROPIC_API_KEY environment variable not set")

    if error.has_errors():
        raise error

    return Launch(
        request,
        "src.app:runner",
        inputs=inputs,
    )


# =============================================================================
# Ray Serve Deployment
# =============================================================================

@serve.deployment
@serve.ingress(app)
class LaTeXResearchAgent:
    """Ray Serve deployment for the LaTeX Research Agent."""
    pass


# For Ray Serve deployment
fast_app = LaTeXResearchAgent.bind()


# =============================================================================
# Local Development
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
