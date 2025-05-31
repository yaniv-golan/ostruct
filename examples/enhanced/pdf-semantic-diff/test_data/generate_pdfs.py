#!/usr/bin/env python3
"""
Generate PDF files for the semantic diff example.
Creates v1.pdf and v2.pdf from the text content files.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import os


def create_pdf_from_text(text_file, pdf_file):
    """Create a PDF from a text file with proper formatting."""

    # Read the text content
    with open(text_file, "r") as f:
        content = f.read()

    # Create PDF document
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # Build the story (content)
    story = []

    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 12))
        elif line == "SAMPLE SERVICE AGREEMENT":
            story.append(Paragraph(line, title_style))
            story.append(Spacer(1, 12))
        elif line.startswith(("1.", "2.", "3.", "4.")):
            story.append(Paragraph(line, heading_style))
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(line, normal_style))
            story.append(Spacer(1, 6))

    # Build PDF
    doc.build(story)
    print(f"✅ Created {pdf_file}")


def main():
    """Generate both PDF files."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contracts_dir = os.path.join(script_dir, "contracts")

    # Generate v1.pdf
    v1_text = os.path.join(contracts_dir, "v1_content.txt")
    v1_pdf = os.path.join(contracts_dir, "v1.pdf")
    create_pdf_from_text(v1_text, v1_pdf)

    # Generate v2.pdf
    v2_text = os.path.join(contracts_dir, "v2_content.txt")
    v2_pdf = os.path.join(contracts_dir, "v2.pdf")
    create_pdf_from_text(v2_text, v2_pdf)

    print("🎉 PDF generation complete!")


if __name__ == "__main__":
    main()
