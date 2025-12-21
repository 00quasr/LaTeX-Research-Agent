# LaTeX Research Agent

Generate comprehensive academic research papers with full LaTeX formatting and PDF output.

## Features

- **Structured Workflow**: LangGraph-based pipeline for predictable, inspectable execution
- **Parallel Drafting**: Ray-powered parallel section generation
- **Multi-Provider LLM**: Support for OpenAI (GPT-4o) and Anthropic (Claude)
- **Full LaTeX Output**: Professional academic formatting with BibTeX citations
- **Docker Compilation**: Reliable PDF generation via texlive container

## Pipeline

```
INPUT → RESEARCH_PLAN → BUILD_OUTLINE → DRAFT_SECTIONS (parallel)
      → COHERENCE_PASS → RENDER_LATEX → COMPILE_PDF → OUTPUT
```

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

### 3. Run Locally

```bash
# Development server
python -m latex_research_agent.app

# Or with uvicorn
uvicorn latex_research_agent.app:app --reload --port 8000
```

### 4. Deploy with Ray Serve

```bash
# Start Ray
ray start --head

# Deploy
serve run latex_research_agent.app:fast_app
```

### 5. Register with Kodosumi Panel

```bash
koco start --register http://localhost:8000/openapi.json
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required for OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required for Anthropic |
| `RAY_ADDRESS` | Ray cluster address | `auto` |

## Output Files

| File | Description |
|------|-------------|
| `paper.pdf` | Compiled PDF document |
| `paper.tex` | LaTeX source file |
| `references.bib` | BibTeX bibliography |
| `paper.zip` | Complete package |

## Architecture

```
latex_research_agent/
├── app.py              # ServeAPI endpoint + LangGraph workflow
├── forms.py            # Input form definition
├── state.py            # State types + Pydantic models
├── nodes/
│   ├── research_plan.py
│   ├── build_outline.py
│   ├── draft_sections.py
│   ├── coherence_pass.py
│   ├── render_latex.py
│   └── compile_pdf.py
├── templates/
│   ├── paper.tex.j2
│   └── prompts/
└── tools/
```

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
