"""
Simple test script to verify the workflow works.

Run with: uv run python test_workflow.py
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_research_plan_only():
    """Test just the research plan node (quick sanity check)."""
    from src.state import ResearchState, estimate_words_from_pages
    from src.nodes.research_plan import research_plan_node

    print("=" * 60)
    print("Testing Research Plan Node")
    print("=" * 60)

    # Determine provider based on available keys
    # Prefer OpenAI if both are set (change this if you prefer Anthropic)
    if os.getenv("OPENAI_API_KEY"):
        provider = "openai"
        strong_model = "gpt-4o"
        fast_model = "gpt-4o-mini"
    elif os.getenv("ANTHROPIC_API_KEY"):
        provider = "anthropic"
        strong_model = "claude-sonnet-4-20250514"
        fast_model = "claude-3-5-haiku-20241022"
    else:
        raise ValueError("No API key found")

    # Create minimal state
    state: ResearchState = {
        "topic": "The impact of Large Language Models on software development practices",
        "target_pages": 10,
        "language": "en",
        "level": "academic",
        "citation_style": "apa",
        "additional_instructions": "",
        "model_provider": provider,
        "strong_model": strong_model,
        "fast_model": fast_model,
        "tracer": None,  # No tracer for simple test
    }

    print(f"\nTopic: {state['topic']}")
    print(f"Target: {state['target_pages']} pages ({estimate_words_from_pages(state['target_pages'])} words)")
    print("\nGenerating research plan...")

    result = await research_plan_node(state)
    plan = result["research_plan"]

    print("\n" + "=" * 60)
    print("RESEARCH PLAN GENERATED")
    print("=" * 60)
    print(f"\nTitle: {plan.title}")
    print(f"\nThesis: {plan.thesis_statement}")
    print(f"\nResearch Questions:")
    for i, q in enumerate(plan.research_questions, 1):
        print(f"  {i}. {q}")
    print(f"\nKey Themes: {', '.join(plan.key_themes)}")
    print(f"\nMethodology: {plan.methodology_approach}")
    print(f"\nTarget Audience: {plan.target_audience}")

    return plan


async def test_outline_generation(research_plan):
    """Test outline generation based on research plan."""
    from src.state import ResearchState
    from src.nodes.build_outline import build_outline_node

    print("\n" + "=" * 60)
    print("Testing Outline Generation")
    print("=" * 60)

    state: ResearchState = {
        "topic": "The impact of Large Language Models on software development practices",
        "target_pages": 10,
        "language": "en",
        "level": "academic",
        "citation_style": "apa",
        "additional_instructions": "",
        "model_provider": "openai",
        "strong_model": "gpt-4o",
        "fast_model": "gpt-4o-mini",
        "research_plan": research_plan,
        "tracer": None,
    }

    print("\nGenerating outline...")
    result = await build_outline_node(state)
    outline = result["outline"]

    print("\n" + "=" * 60)
    print("OUTLINE GENERATED")
    print("=" * 60)
    print(f"\nTitle: {outline.title}")
    print(f"Abstract Summary: {outline.abstract_summary[:100]}...")
    print(f"Total Sections: {len(outline.sections)}")
    print(f"Estimated Words: {outline.total_estimated_words}")

    print("\nStructure:")
    for section in outline.sections:
        print(f"\n  {section.id}. {section.title} ({section.target_words} words)")
        for sub in section.subsections:
            print(f"      {sub.id} {sub.title} ({sub.target_words} words)")

    return outline


async def main():
    """Run tests."""
    print("\n🧪 LaTeX Research Agent - Test Suite\n")

    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not openai_key and not anthropic_key:
        print("❌ Error: No API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        print(f"   Checked: {env_path}")
        return

    provider = "openai" if openai_key else "anthropic"
    print(f"✅ Using LLM provider: {provider}")
    print(f"   Key: {(openai_key or anthropic_key)[:20]}...")

    try:
        # Test 1: Research Plan
        plan = await test_research_plan_only()

        # Test 2: Outline (optional - takes longer)
        print("\n")
        response = input("Generate outline too? (y/n): ").strip().lower()
        if response == "y":
            outline = await test_outline_generation(plan)

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
