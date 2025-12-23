"""
Render LaTeX Node - Converts the paper to LaTeX format.

Supports two modes:
1. Chapter-based (new): Reads chapter files from disk sequentially
2. Legacy: Uses coherent_paper from state (for backward compatibility)
"""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..state import ResearchState

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def read_chapters_from_disk(chapter_dir: str) -> str:
    """
    Read all chapter files from disk and combine them.

    This is the resource-efficient approach that doesn't hold
    the entire paper in memory at once.

    Args:
        chapter_dir: Path to directory containing chapter_XX.md files

    Returns:
        Combined markdown content from all chapters
    """
    chapter_path = Path(chapter_dir)
    chapter_files = sorted(chapter_path.glob("chapter_*.md"))

    combined_content = []
    for chapter_file in chapter_files:
        content = chapter_file.read_text()
        combined_content.append(content)

    return "\n\n".join(combined_content)


def markdown_to_latex(markdown_text: str) -> str:
    """
    Convert markdown to LaTeX with support for figures, tables, and charts.

    Handles:
    - Headers (## -> \section, ### -> \subsection)
    - Bold (**text** -> \textbf{text})
    - Italic (*text* -> \textit{text})
    - Lists
    - Citations [AuthorYear] -> \cite{AuthorYear}
    - Figure/Table/Chart placeholders
    """
    text = markdown_text

    # Process figure placeholders [FIGURE: id] or [FIGURE X: Title]
    def process_figure(match):
        full_match = match.group(0)
        # Try to extract caption from following lines
        lines_after = text[match.end():match.end()+500]
        caption_match = re.search(r'Caption:\s*(.+?)(?:\n|$)', lines_after)
        desc_match = re.search(r'Description:\s*(.+?)(?:\n\n|\n[A-Z]|$)', lines_after, re.DOTALL)

        caption = caption_match.group(1).strip() if caption_match else "Figure"
        description = desc_match.group(1).strip() if desc_match else "Placeholder figure"

        # Generate a label from caption
        label = re.sub(r'[^a-z0-9]', '', caption.lower())[:20]

        return f"""
\\begin{{figure}}[H]
    \\centering
    \\fbox{{\\parbox{{0.85\\textwidth}}{{\\centering\\vspace{{1.5cm}}\\textit{{{escape_latex_text(description)}}}\\vspace{{1.5cm}}}}}}
    \\caption{{{escape_latex_text(caption)}}}
    \\label{{fig:{label}}}
\\end{{figure}}
"""

    text = re.sub(r'\[FIGURE[^\]]*\]', process_figure, text)

    # Process table placeholders
    def process_table(match):
        # Look for markdown table after the placeholder
        lines_after = text[match.end():match.end()+1000]
        caption_match = re.search(r'Caption:\s*(.+?)(?:\n|$)', lines_after)
        caption = caption_match.group(1).strip() if caption_match else "Table"

        # Try to find markdown table
        table_match = re.search(r'(\|.+\|(?:\n\|.+\|)+)', lines_after)

        if table_match:
            md_table = table_match.group(1)
            latex_table = convert_markdown_table(md_table, caption)
            return latex_table
        else:
            label = re.sub(r'[^a-z0-9]', '', caption.lower())[:20]
            return f"""
\\begin{{table}}[H]
    \\centering
    \\caption{{{escape_latex_text(caption)}}}
    \\label{{tab:{label}}}
    \\begin{{tabular}}{{lll}}
        \\toprule
        Column 1 & Column 2 & Column 3 \\\\
        \\midrule
        Data & Data & Data \\\\
        \\bottomrule
    \\end{{tabular}}
\\end{{table}}
"""

    text = re.sub(r'\[TABLE[^\]]*\]', process_table, text)

    # Process chart placeholders
    def process_chart(match):
        lines_after = text[match.end():match.end()+500]
        caption_match = re.search(r'Caption:\s*(.+?)(?:\n|$)', lines_after)
        type_match = re.search(r'Type:\s*(.+?)(?:\n|$)', lines_after)

        caption = caption_match.group(1).strip() if caption_match else "Chart"
        chart_type = type_match.group(1).strip().lower() if type_match else "line"
        label = re.sub(r'[^a-z0-9]', '', caption.lower())[:20]

        return f"""
\\begin{{figure}}[H]
    \\centering
    \\begin{{tikzpicture}}
        \\begin{{axis}}[
            width=0.85\\textwidth,
            height=7cm,
            xlabel={{X-Axis}},
            ylabel={{Y-Axis}},
            grid=major,
            legend pos=north west,
        ]
        \\addplot[blue, thick, mark=*] coordinates {{(1,2) (2,4) (3,6) (4,5) (5,8) (6,7)}};
        \\addlegend{{Data Series}}
        \\end{{axis}}
    \\end{{tikzpicture}}
    \\caption{{{escape_latex_text(caption)}}}
    \\label{{chart:{label}}}
\\end{{figure}}
"""

    text = re.sub(r'\[CHART[^\]]*\]', process_chart, text)

    # Remove Caption:, Description:, Type:, Data: lines (already processed)
    text = re.sub(r'^Caption:\s*.+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Description:\s*.+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Type:\s*.+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Data:\s*.+$', '', text, flags=re.MULTILINE)

    # Headers
    text = re.sub(r'^#### (.+)$', r'\\subsubsection{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'\\subsection{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'\\section{\1}', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'\\section*{\1}', text, flags=re.MULTILINE)

    # Bold and italic (before escaping)
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    text = re.sub(r'\*(.+?)\*', r'\\textit{\1}', text)

    # Citations [AuthorYear] -> \cite{authoryear}
    def cite_replace(match):
        cite_key = match.group(1).lower().replace(" ", "")
        return f'\\cite{{{cite_key}}}'
    text = re.sub(r'\[([A-Za-z]+\d{4}[a-z]?)\]', cite_replace, text)

    # Multiple citations [Author2021; Author2022] -> \cite{author2021,author2022}
    def multi_cite_replace(match):
        citations = match.group(1).split(';')
        keys = [c.strip().lower().replace(" ", "") for c in citations]
        return f'\\cite{{{",".join(keys)}}}'
    text = re.sub(r'\[([A-Za-z]+\d{4}[a-z]?(?:\s*;\s*[A-Za-z]+\d{4}[a-z]?)+)\]', multi_cite_replace, text)

    # Convert markdown tables to LaTeX
    text = convert_inline_tables(text)

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
            item_text = escape_latex_text(stripped[2:])
            result_lines.append(f'  \\item {item_text}')
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
            item_text = escape_latex_text(re.sub(r'^\d+\. ', '', stripped))
            result_lines.append(f'  \\item {item_text}')
        else:
            if in_enum:
                result_lines.append('\\end{enumerate}')
                in_enum = False
            result_lines.append(line)

    if in_enum:
        result_lines.append('\\end{enumerate}')

    text = '\n'.join(result_lines)

    # Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def convert_markdown_table(md_table: str, caption: str = "Table") -> str:
    """Convert a markdown table to LaTeX tabular."""
    lines = [l.strip() for l in md_table.strip().split('\n') if l.strip()]

    if len(lines) < 2:
        return ""

    # Parse header
    header = [cell.strip() for cell in lines[0].split('|') if cell.strip()]
    num_cols = len(header)

    # Generate column spec
    col_spec = 'l' * num_cols

    # Build table
    label = re.sub(r'[^a-z0-9]', '', caption.lower())[:20]

    latex = f"""
\\begin{{table}}[H]
    \\centering
    \\caption{{{escape_latex_text(caption)}}}
    \\label{{tab:{label}}}
    \\begin{{tabular}}{{{col_spec}}}
        \\toprule
        {' & '.join([escape_latex_text(h) for h in header])} \\\\
        \\midrule
"""

    # Skip separator line and add data rows
    for line in lines[2:]:  # Skip header and separator
        if '|' in line:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                latex += f"        {' & '.join([escape_latex_text(c) for c in cells])} \\\\\n"

    latex += """        \\bottomrule
    \\end{tabular}
\\end{table}
"""
    return latex


def convert_inline_tables(text: str) -> str:
    """Find and convert inline markdown tables."""
    # Pattern for markdown tables
    table_pattern = r'(\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n?)+)'

    def replace_table(match):
        md_table = match.group(1)
        return convert_markdown_table(md_table, "Data Summary")

    return re.sub(table_pattern, replace_table, text)


def escape_latex_text(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    if not text:
        return ""
    # Don't escape if already contains LaTeX commands
    if '\\' in text and any(cmd in text for cmd in ['\\textbf', '\\textit', '\\cite', '\\ref']):
        return text
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


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters for title/abstract."""
    return escape_latex_text(text)


async def render_latex_node(state: ResearchState) -> dict:
    """
    Render the paper as a LaTeX document.

    Supports two modes:
    1. Chapter-based (new): Reads from chapter_dir, uses abstract from state
    2. Legacy: Uses coherent_paper from state

    Uses Jinja2 templates to generate the .tex file.
    """
    tracer = state.get("tracer")

    if tracer:
        await tracer.markdown("## 📄 Rendering LaTeX")
        await tracer.markdown("Converting to LaTeX format...")

    # Determine which mode we're in
    chapter_dir = state.get("chapter_dir")

    if chapter_dir:
        # Chapter-based mode (new, resource-efficient)
        if tracer:
            await tracer.markdown("Using chapter-based rendering...")

        # Read chapters from disk
        markdown_body = read_chapters_from_disk(chapter_dir)

        # Get title and abstract from state
        title = escape_latex(state.get("final_title", state["chapter_outline"].title))
        abstract = escape_latex(state.get("abstract", ""))
    else:
        # Legacy mode (coherent_paper from state)
        coherent_paper = state["coherent_paper"]
        markdown_body = coherent_paper.body
        title = escape_latex(coherent_paper.title)
        abstract = escape_latex(coherent_paper.abstract)

    # Convert markdown body to LaTeX
    latex_body = markdown_to_latex(markdown_body)

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

    # Generate bibliography from citations in text
    bibtex_content = generate_placeholder_bibtex(markdown_body)

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
    # Find all citation patterns [AuthorYear] including multi-citations
    single_citations = re.findall(r'\[([A-Za-z]+\d{4}[a-z]?)\]', body)
    multi_citations = re.findall(r'\[([A-Za-z]+\d{4}[a-z]?(?:\s*;\s*[A-Za-z]+\d{4}[a-z]?)+)\]', body)

    all_citations = set(single_citations)
    for multi in multi_citations:
        for cite in multi.split(';'):
            all_citations.add(cite.strip())

    unique_citations = sorted(all_citations)

    entries = []
    for cite in unique_citations:
        # Extract author and year
        match = re.match(r'([A-Za-z]+)(\d{4}[a-z]?)', cite)
        if match:
            author = match.group(1)
            year = match.group(2)[:4]
            key = cite.lower().replace(" ", "")

            entry = f"""@article{{{key},
  author = {{{author}, A. and {author}, B.}},
  title = {{Research on {author}'s Findings in the Field}},
  journal = {{Journal of Academic Research}},
  year = {{{year}}},
  volume = {{1}},
  pages = {{1--20}},
  note = {{Placeholder citation - replace with actual reference}}
}}"""
            entries.append(entry)

    return "\n\n".join(entries)
