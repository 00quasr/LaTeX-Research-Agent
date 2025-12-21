"""
Compile PDF Node - Compiles LaTeX to PDF using Docker.
"""

import os
import subprocess
import tempfile
import shutil
import zipfile
from pathlib import Path

from ..state import ResearchState


async def compile_pdf_node(state: ResearchState) -> dict:
    """
    Compile the LaTeX document to PDF using Docker.

    This node:
    - Writes .tex and .bib files to temp directory
    - Runs pdflatex via Docker
    - Packages all outputs into a ZIP file
    """
    tracer = state.get("tracer")

    if tracer:
        await tracer.markdown("## 🔨 Compiling PDF")
        await tracer.markdown("Running LaTeX compilation...")

    latex_content = state["latex_content"]
    bibtex_content = state["bibtex_content"]

    # Create temporary directory for compilation
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write files
        tex_file = tmpdir / "paper.tex"
        bib_file = tmpdir / "references.bib"

        tex_file.write_text(latex_content)
        bib_file.write_text(bibtex_content)

        if tracer:
            await tracer.markdown("Files written to temp directory")

        # Run pdflatex via Docker
        try:
            pdf_path = await run_latex_docker(tmpdir, "paper.tex", tracer)
            compilation_success = pdf_path is not None
        except Exception as e:
            if tracer:
                await tracer.markdown(f"⚠️ Docker compilation failed: {str(e)}")
                await tracer.markdown("Attempting local pdflatex...")

            # Fallback to local pdflatex
            try:
                pdf_path = await run_latex_local(tmpdir, "paper.tex", tracer)
                compilation_success = pdf_path is not None
            except Exception as e2:
                if tracer:
                    await tracer.markdown(f"❌ Local compilation also failed: {str(e2)}")
                compilation_success = False
                pdf_path = None

        # Get the tracer filesystem for output
        if tracer:
            fs = await tracer.fs()

        # Package outputs
        output_files = {}

        # Copy tex file
        if tracer:
            await fs.write("out/paper.tex", tex_file.read_bytes())
            output_files["tex_path"] = f"/files/{tracer.fid}/out/paper.tex"

        # Copy bib file
        if tracer:
            await fs.write("out/references.bib", bib_file.read_bytes())
            output_files["bib_path"] = f"/files/{tracer.fid}/out/references.bib"

        # Copy PDF if compilation succeeded
        if compilation_success and pdf_path and pdf_path.exists():
            if tracer:
                await fs.write("out/paper.pdf", pdf_path.read_bytes())
                output_files["pdf_path"] = f"/files/{tracer.fid}/out/paper.pdf"
                await tracer.markdown("✅ PDF compiled successfully!")
        else:
            output_files["pdf_path"] = None
            if tracer:
                await tracer.markdown("⚠️ PDF compilation failed - .tex file available for manual compilation")

        # Create ZIP package
        zip_buffer = create_zip_package(tmpdir, compilation_success)
        if tracer:
            await fs.write("out/paper.zip", zip_buffer)
            output_files["zip_path"] = f"/files/{tracer.fid}/out/paper.zip"
            await tracer.markdown("📦 ZIP package created")

    if tracer:
        await tracer.markdown("### Compilation Complete")
        if output_files.get("pdf_path"):
            await tracer.markdown(f"**PDF**: [Download]({output_files['pdf_path']})")
        await tracer.markdown(f"**LaTeX Source**: [Download]({output_files.get('tex_path', 'N/A')})")
        await tracer.markdown(f"**Full Package**: [Download]({output_files.get('zip_path', 'N/A')})")

    return output_files


async def run_latex_docker(workdir: Path, tex_filename: str, tracer) -> Path | None:
    """
    Run pdflatex inside Docker container.
    """
    # Use texlive Docker image
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{workdir}:/workdir",
        "-w", "/workdir",
        "texlive/texlive:latest",
        "sh", "-c",
        f"pdflatex -interaction=nonstopmode {tex_filename} && "
        f"bibtex paper && "
        f"pdflatex -interaction=nonstopmode {tex_filename} && "
        f"pdflatex -interaction=nonstopmode {tex_filename}"
    ]

    if tracer:
        await tracer.markdown("Running: `docker run texlive/texlive pdflatex...`")

    result = subprocess.run(
        docker_cmd,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout
    )

    if result.returncode != 0:
        if tracer:
            await tracer.debug(f"pdflatex stderr: {result.stderr[:1000]}")
        raise RuntimeError(f"pdflatex failed: {result.stderr[:500]}")

    pdf_path = workdir / "paper.pdf"
    if pdf_path.exists():
        return pdf_path
    return None


async def run_latex_local(workdir: Path, tex_filename: str, tracer) -> Path | None:
    """
    Run pdflatex locally (fallback if Docker not available).
    """
    if tracer:
        await tracer.markdown("Running local pdflatex...")

    # Run pdflatex multiple times for references
    for i in range(3):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_filename],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if i == 0 and (workdir / "paper.aux").exists():
            # Run bibtex
            subprocess.run(
                ["bibtex", "paper"],
                cwd=workdir,
                capture_output=True,
                timeout=60,
            )

    pdf_path = workdir / "paper.pdf"
    if pdf_path.exists():
        return pdf_path
    return None


def create_zip_package(workdir: Path, include_pdf: bool) -> bytes:
    """
    Create a ZIP package of all output files.
    """
    import io

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add tex file
        tex_file = workdir / "paper.tex"
        if tex_file.exists():
            zf.write(tex_file, "paper.tex")

        # Add bib file
        bib_file = workdir / "references.bib"
        if bib_file.exists():
            zf.write(bib_file, "references.bib")

        # Add PDF if available
        if include_pdf:
            pdf_file = workdir / "paper.pdf"
            if pdf_file.exists():
                zf.write(pdf_file, "paper.pdf")

        # Add log file for debugging
        log_file = workdir / "paper.log"
        if log_file.exists():
            zf.write(log_file, "paper.log")

    return zip_buffer.getvalue()
