# LaTeX Research Agent

Generate comprehensive academic research papers with full LaTeX formatting and PDF output.


https://github.com/user-attachments/assets/f2302b4a-8712-45c1-9510-f62246f72b59


## Features

- **Structured Workflow**: LangGraph-based pipeline for predictable, inspectable execution
- **Dual Workflow Modes**:
  - **Chapter-based** (40+ pages): Sequential drafting with rolling context summaries
  - **Section-based** (< 40 pages): Parallel section generation with coherence pass
- **Multi-Provider LLM**: Support for OpenAI (GPT-4o) and Anthropic (Claude)
- **Full LaTeX Output**: Professional academic formatting with BibTeX citations
- **Visual Elements**: Automatic figure/table/chart placeholders with TikZ/PGFPlots
- **Docker/Local Compilation**: PDF generation via texlive container or local pdflatex

## Pipeline

### Chapter-Based Mode (40+ pages)
```
INPUT → RESEARCH_PLAN → BUILD_OUTLINE → DRAFT_CHAPTERS (sequential)
      → FINALIZE_PAPER → RENDER_LATEX → COMPILE_PDF → OUTPUT
```

Each chapter is drafted sequentially with rolling ~100-word summaries passed as context to maintain coherence across the paper.

### Section-Based Mode (< 40 pages)
```
INPUT → RESEARCH_PLAN → BUILD_OUTLINE → DRAFT_SECTIONS (parallel)
      → COHERENCE_PASS → RENDER_LATEX → COMPILE_PDF → OUTPUT
```

Sections are drafted in parallel using Ray, then unified in a coherence pass.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required:
- `OPENAI_API_KEY` - For OpenAI models (GPT-4o, GPT-4o-mini)
- `ANTHROPIC_API_KEY` - For Anthropic models (Claude Sonnet, Claude Haiku)

### 3. Run with Kodosumi

```bash
# Start the spooler and server
koco start --register http://localhost:8000/openapi.json

# Access the UI at http://localhost:3370
```

### 4. Alternative: Run Locally

```bash
# Development server
python -m src.app

# Or with uvicorn
uvicorn src.app:app --reload --port 8000
```

### 5. Deploy with Ray Serve

```bash
# Start Ray
ray start --head

# Deploy
serve run src.app:fast_app
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required for OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required for Anthropic |
| `RAY_ADDRESS` | Ray cluster address | `auto` |

### Form Options

| Option | Values | Default |
|--------|--------|---------|
| Target Pages | 5-100 | 20 |
| Language | English, German, Spanish, French | English |
| Level | Academic, Graduate, Professional | Academic |
| Citation Style | APA, MLA, Chicago, IEEE, Harvard | APA |
| Model Provider | OpenAI, Anthropic | OpenAI |

## Output Files

| File | Description |
|------|-------------|
| `paper.pdf` | Compiled PDF document |
| `paper.tex` | LaTeX source file |
| `references.bib` | BibTeX bibliography |
| `paper.zip` | Complete package (all files) |

## Architecture

```
src/
├── app.py                    # ServeAPI endpoint + LangGraph workflow
├── forms.py                  # Input form definition
├── state.py                  # State types + Pydantic models
├── nodes/
│   ├── __init__.py
│   ├── research_plan.py      # Generate research plan from topic
│   ├── build_outline.py      # Create paper outline (chapter or section)
│   ├── draft_sections.py     # Parallel section drafting (< 40 pages)
│   ├── draft_chapters.py     # Sequential chapter drafting (40+ pages)
│   ├── coherence_pass.py     # Unify sections (section mode only)
│   ├── finalize_paper.py     # Generate abstract (chapter mode only)
│   ├── render_latex.py       # Convert markdown to LaTeX
│   └── compile_pdf.py        # Compile LaTeX to PDF
├── templates/
│   ├── paper.tex.j2          # LaTeX document template
│   └── prompts/
│       ├── research_plan.j2
│       ├── outline.j2
│       ├── outline_chapters.j2
│       ├── draft_section.j2
│       ├── draft_chapter.j2
│       ├── chapter_summary.j2
│       ├── coherence.j2
│       └── abstract.j2
└── tools/                    # Utility functions
```

## Current Status

### Working
- Full pipeline execution for both chapter and section modes
- PDF compilation (Docker with fallback to local pdflatex)
- Multi-language support
- Visual element placeholders (figures, tables, charts)
- BibTeX citation generation

### Known Issues
- **Word Count Shortfall**: Chapters currently generate ~46% of target word count (e.g., 10,972 words instead of 24,000 for a 40-page paper). LLMs struggle with self-counting.
- **SyntaxWarning**: Minor warning in `render_latex.py` about escape sequences (non-breaking)

### Planned Improvements
- Word count validation with retry logic
- Better enforcement of chapter length targets

## Development

### Run Tests

```bash
pytest tests/
```

### Docker Build

```bash
docker build -t latex-research-agent .
docker run -p 8000:8000 --env-file .env latex-research-agent
```

## License

MIT
