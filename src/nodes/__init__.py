"""Workflow nodes for the LaTeX Research Agent pipeline."""

from .research_plan import research_plan_node
from .build_outline import build_outline_node
from .draft_sections import draft_sections_node
from .coherence_pass import coherence_pass_node
from .render_latex import render_latex_node
from .compile_pdf import compile_pdf_node

# Chapter-based workflow nodes (for large papers 40+ pages)
from .draft_chapters import draft_chapters_node
from .finalize_paper import finalize_paper_node

__all__ = [
    # Core nodes
    "research_plan_node",
    "build_outline_node",
    "render_latex_node",
    "compile_pdf_node",
    # Section-based workflow (legacy, < 40 pages)
    "draft_sections_node",
    "coherence_pass_node",
    # Chapter-based workflow (40+ pages)
    "draft_chapters_node",
    "finalize_paper_node",
]
