"""
Input form definitions for the LaTeX Research Agent.

Uses Kodosumi's form builder (F.Model) to create the user-facing input form.
"""

from kodosumi.core import forms as F

# =============================================================================
# Form Model
# =============================================================================

research_form_model = F.Model(
    # Header
    F.Markdown("""
# LaTeX Research Paper Generator

Generate comprehensive academic research papers with full LaTeX formatting and PDF output.

---
"""),

    # Core Input: Topic
    F.InputArea(
        name="topic",
        label="Research Topic",
        placeholder="e.g., 'The impact of Large Language Models on scientific research methodologies' or 'Blockchain technology in supply chain management'",
        required=True,
    ),

    F.Break(),

    # Paper Configuration
    F.Markdown("### Paper Configuration"),

    F.InputText(
        name="target_pages",
        label="Target Page Count",
        placeholder="20",
        required=False,
    ),

    F.Select(
        name="language",
        label="Language",
        option=[
            F.InputOption("English", "en"),
            F.InputOption("German", "de"),
            F.InputOption("Spanish", "es"),
            F.InputOption("French", "fr"),
        ],
    ),

    F.Select(
        name="level",
        label="Academic Level",
        option=[
            F.InputOption("Academic / Research Paper", "academic"),
            F.InputOption("Technical Report", "technical"),
            F.InputOption("General / Educational", "general"),
        ],
    ),

    F.Select(
        name="citation_style",
        label="Citation Style",
        option=[
            F.InputOption("APA (7th Edition)", "apa"),
            F.InputOption("IEEE", "ieee"),
            F.InputOption("Chicago", "chicago"),
            F.InputOption("MLA", "mla"),
        ],
    ),

    F.Break(),

    # LLM Configuration
    F.Markdown("### Model Configuration"),

    F.Select(
        name="model_provider",
        label="LLM Provider",
        option=[
            F.InputOption("OpenAI (GPT-4o)", "openai"),
            F.InputOption("Anthropic (Claude)", "anthropic"),
        ],
    ),

    F.Break(),

    # Additional Instructions
    F.Markdown("### Additional Instructions (Optional)"),

    F.InputArea(
        name="additional_instructions",
        label="Additional Instructions",
        placeholder="Any specific requirements, focus areas, or constraints for the paper...",
        required=False,
    ),

    F.Break(),

    # Submit
    F.Submit("Generate Research Paper"),
    F.Cancel("Cancel"),
)
