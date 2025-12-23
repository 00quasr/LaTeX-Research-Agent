"""
Compile PDF Node - Compiles LaTeX to PDF using Docker or local pdflatex.
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
    Compile the LaTeX document to PDF using Docker or local pdflatex.

    This node:
    - Writes .tex and .bib files to temp directory
    - Runs pdflatex via Docker (or local fallback)
    - Packages all outputs into a ZIP file
    """
    tracer = state.get("tracer")

    if tracer:
        await tracer.markdown("## 🔨 Compiling PDF")
        await tracer.markdown("Running LaTeX compilation...")

    latex_content = state["latex_content"]
    bibtex_content = state["bibtex_content"]

    # Create temporary directory for compilation (don't auto-delete)
    tmpdir = Path(tempfile.mkdtemp(prefix="latex_research_"))

    # Write files
    tex_file = tmpdir / "paper.tex"
    bib_file = tmpdir / "references.bib"

    tex_file.write_text(latex_content)
    bib_file.write_text(bibtex_content)

    if tracer:
        await tracer.markdown(f"Files written to: `{tmpdir}`")

    # Run pdflatex via Docker
    compilation_success = False
    pdf_path = None

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
                await tracer.markdown(f"⚠️ Local pdflatex not available: {str(e2)}")
            compilation_success = False
            pdf_path = None

    # Package outputs
    output_files = {}

    if tracer:
        fs = await tracer.fs()
        fid = tracer.fid

        # Upload tex file
        await fs.upload(str(tex_file))
        output_files["tex_path"] = f"/files/{fid}/out/paper.tex"

        # Upload bib file
        await fs.upload(str(bib_file))
        output_files["bib_path"] = f"/files/{fid}/out/references.bib"

        # Upload PDF if compilation succeeded
        if compilation_success and pdf_path and pdf_path.exists():
            await fs.upload(str(pdf_path))
            output_files["pdf_path"] = f"/files/{fid}/out/paper.pdf"
            await tracer.markdown("✅ PDF compiled successfully!")
        else:
            output_files["pdf_path"] = None
            await tracer.markdown("⚠️ PDF compilation failed - .tex file available for manual compilation")

        # Create and upload ZIP package
        zip_file_path = create_zip_package(tmpdir, compilation_success)
        await fs.upload(str(zip_file_path))
        output_files["zip_path"] = f"/files/{fid}/out/paper.zip"
        await tracer.markdown("📦 ZIP package created")

        # Close the filesystem to ensure files are written
        await fs.close()

        # Show download links
        await tracer.markdown("### Download Files")
        await tracer.html(f"""
        <div style='display: flex; gap: 10px; flex-wrap: wrap; margin: 15px 0;'>
            {f"<a href='{output_files['pdf_path']}' style='display: inline-block; padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px;'>📄 Download PDF</a>" if output_files.get('pdf_path') else ""}
            <a href='{output_files['tex_path']}' style='display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;'>📝 Download LaTeX</a>
            <a href='{output_files['zip_path']}' style='display: inline-block; padding: 10px 20px; background: #FF9800; color: white; text-decoration: none; border-radius: 5px;'>📦 Download All (ZIP)</a>
        </div>
        """)

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
        timeout=300,  # 5 minute timeout
    )

    # Decode output with error handling for non-UTF-8 bytes
    stderr = result.stderr.decode('utf-8', errors='replace')

    if result.returncode != 0:
        if tracer:
            await tracer.debug(f"pdflatex stderr: {stderr[:1000]}")
        raise RuntimeError(f"pdflatex failed: {stderr[:500]}")

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

    # Check if pdflatex exists
    try:
        subprocess.run(["which", "pdflatex"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("pdflatex not found on system")

    # Run pdflatex multiple times for references
    for i in range(3):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_filename],
            cwd=workdir,
            capture_output=True,
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


def create_zip_package(workdir: Path, include_pdf: bool) -> Path:
    """
    Create a ZIP package of all output files.
    Returns the path to the ZIP file.
    """
    zip_path = workdir / "paper.zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
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

    return zip_path
