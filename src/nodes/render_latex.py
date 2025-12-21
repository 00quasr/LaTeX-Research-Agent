"""
Render LaTeX Node - Converts the coherent paper to LaTeX format.
"""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..state import ResearchState

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def markdown_to_latex(markdown_text: str) -> str:
    """
    Convert markdown to LaTeX.

    Handles:
    - Headers (## -> \section, ### -> \subsection)
    - Bold (**text** -> \textbf{text})
    - Italic (*text* -> \textit{text})
    - Lists
    - Citations [AuthorYear] -> \cite{AuthorYear}
    """
    text = markdown_text

    # Headers
    text = re.sub(r'^#### (.+)$', r'\\subsubsection{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'\\subsection{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'\\section{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'\\section*{\1}', text, flags=re.MULTILINE)

    # Bold and italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    text = re.sub(r'\*(.+?)\*', r'\\textit{\1}', text)

    # Citations [AuthorYear] -> \cite{authoryear}
    def cite_replace(match):
        cite_key = match.group(1).lower().replace(" ", "")
        return f'\\cite{{{cite_key}}}'
    text = re.sub(r'\[([A-Za-z]+\d{4}[a-z]?)\]', cite_replace, text)

    # Bullet lists
    lines = text.split('\n')
    in_list = False
    result_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- '):
            if not in_list:
                result_lines.append('\\begin{itemize}')
                in_list = True
            result_lines.append('  \\item ' + stripped[2:])
        else:
            if in_list:
                result_lines.append('\\end{itemize}')
                in_list = False
            result_lines.append(line)

    if in_list:
        result_lines.append('\\end{itemize}')

    text = '\n'.join(result_lines)

    # Numbered lists
    lines = text.split('\n')
    in_enum = False
    result_lines = []

    for line in lines:
        stripped = line.strip()
        if re.match(r'^\d+\. ', stripped):
            if not in_enum:
                result_lines.append('\\begin{enumerate}')
                in_enum = True
            result_lines.append('  \\item ' + re.sub(r'^\d+\. ', '', stripped))
        else:
            if in_enum:
                result_lines.append('\\end{enumerate}')
                in_enum = False
            result_lines.append(line)

    if in_enum:
        result_lines.append('\\end{enumerate}')

    text = '\n'.join(result_lines)

    # Escape special characters (but not already converted LaTeX commands)
    # This is tricky - we need to be careful not to escape our LaTeX
    text = text.replace('%', '\\%')
    text = text.replace('&', '\\&')
    text = text.replace('#', '\\#')
    text = text.replace('_', '\\_')

    # Fix over-escaped LaTeX commands
    text = text.replace('\\\\', '\\')

    return text


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    chars = {
        '&': '\\&',
        '%': '\\%',
        '$': '\\$',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\textasciicircum{}',
    }
    for char, escaped in chars.items():
        text = text.replace(char, escaped)
    return text


async def render_latex_node(state: ResearchState) -> dict:
    """
    Render the coherent paper as a LaTeX document.

    Uses Jinja2 templates to generate the .tex file.
    """
    tracer = state.get("tracer")
    coherent_paper = state["coherent_paper"]

    if tracer:
        await tracer.markdown("## 📄 Rendering LaTeX")
        await tracer.markdown("Converting to LaTeX format...")

    # Convert markdown body to LaTeX
    latex_body = markdown_to_latex(coherent_paper.body)

    # Escape title and abstract
    title = escape_latex(coherent_paper.title)
    abstract = escape_latex(coherent_paper.abstract)

    # Load LaTeX template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        # Use different delimiters to avoid conflicts with LaTeX
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
    )

    template = env.get_template("paper.tex.j2")

    # Determine document class options
    language = state.get("language", "en")
    language_map = {
        "en": "english",
        "de": "ngerman",
        "es": "spanish",
        "fr": "french",
    }
    babel_language = language_map.get(language, "english")

    # Render LaTeX
    latex_content = template.render(
        title=title,
        abstract=abstract,
        body=latex_body,
        language=babel_language,
        citation_style=state.get("citation_style", "apa"),
        author="Research Agent",  # Could be parameterized
        date="\\today",
    )

    # Generate placeholder bibliography
    bibtex_content = generate_placeholder_bibtex(coherent_paper.body)

    if tracer:
        await tracer.markdown("### LaTeX Rendered")
        await tracer.markdown(f"**Document Length**: {len(latex_content)} characters")
        await tracer.markdown(f"**Bibliography Entries**: {bibtex_content.count('@')}")

    return {
        "latex_content": latex_content,
        "bibtex_content": bibtex_content,
    }


def generate_placeholder_bibtex(body: str) -> str:
    """
    Generate placeholder BibTeX entries for citations found in the text.
    """
    # Find all citation patterns [AuthorYear]
    citations = re.findall(r'\[([A-Za-z]+\d{4}[a-z]?)\]', body)
    unique_citations = sorted(set(citations))

    entries = []
    for cite in unique_citations:
        # Extract author and year
        match = re.match(r'([A-Za-z]+)(\d{4}[a-z]?)', cite)
        if match:
            author = match.group(1)
            year = match.group(2)[:4]
            key = cite.lower()

            entry = f"""@misc{{{key},
  author = {{{author}}},
  title = {{Placeholder Title for {cite}}},
  year = {{{year}}},
  note = {{Placeholder citation - replace with actual reference}}
}}"""
            entries.append(entry)

    return "\n\n".join(entries)
