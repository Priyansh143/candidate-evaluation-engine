import pdfplumber
from pathlib import Path
import re


SECTION_HEADERS = {
    "EXPERIENCE", "PROJECTS", "EDUCATION",
    "SKILLS", "RESEARCH", "TRAINING", "CERTIFICATIONS"
}


def extract_lines_with_style(pdf_path: str, logger = None) -> list[dict]:

    logger.info(f"\tInside extract_lines_with_style")
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    lines = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:

            words = page.extract_words(extra_attrs=["fontname"])

            current_line = []
            current_top = None

            for w in words:

                if current_top is None:
                    current_top = w["top"]

                # new line detection
                if abs(w["top"] - current_top) > 3:
                    if current_line:
                        lines.append(current_line)
                    current_line = []
                    current_top = w["top"]

                current_line.append(w)

            if current_line:
                lines.append(current_line)
    logger.info(f"\tTotal lines extracted: {len(lines)}")
    formatted_lines = []

    for line in lines:

        text = " ".join(w["text"] for w in line)
        bold = any("Bold" in w["fontname"] for w in line)

        formatted_lines.append({
            "text": text.strip(),
            "bold": bold
        })

    logger.info(f"\tExiting extract_lines_with_style\n")
    return formatted_lines

def clean_resume_text(text: str) -> str:
    
    # normalize unicode artifacts from PDFs
    text = text.replace("\xa0", " ")   # non-breaking space
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    # normalize excessive newlines but preserve structure
    text = re.sub(r'\n{3,}', '\n\n', text)

    # remove stray bullet characters
    text = re.sub(r'[•▪◦]', '', text)

    # remove separators
    text = re.sub(r'[-_=]{3,}', '', text)

    # remove emails
    text = re.sub(r'\S+@\S+', '', text)

    # remove phone numbers
    text = re.sub(r'\+?\d[\d\s\-]{8,}\d', '', text)

    # trim whitespace
    text = "\n".join(line.strip() for line in text.splitlines())
    # remove date ranges like "Jan 2022 - Mar 2023"
    text = re.sub(
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s?\d{4}\s?[-–]\s?(?:Present|\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s?\d{4})',
        '',
        text,
        flags=re.IGNORECASE
    )
    
    # remove date ranges like "10/2024 - 01/2025"
    text = re.sub(r'\b\d{1,2}/\d{4}\s*-\s*\d{1,2}/\d{4}\b', '', text)

    # remove year ranges like "2021 - 2025"
    text = re.sub(r'\b(19|20)\d{2}\s*-\s*(19|20)\d{2}\b', '', text)

    # remove standalone years
    text = re.sub(r'\b(19|20)\d{2}\b', '', text)

    # remove standalone years
    text = re.sub(r'\b(19|20)\d{2}\b', '', text)    
    # remove patterns like "10/ - 01/" , "06/-07/" etc
    text = re.sub(r'\b\d{1,2}\s*/\s*-\s*\d{1,2}\s*/\b', '', text)

    # remove leftover fragments like "10/" or "06/"
    text = re.sub(r'\b\d{1,2}\s*/\b', '', text)
    return text.strip()


def split_by_sections(text: str) -> dict:
    sections = {}
    current_section = "OTHER"
    sections[current_section] = []

    for line in text.splitlines():
        clean = line.strip()

        if clean.upper() in SECTION_HEADERS:
            current_section = clean.upper()
            sections[current_section] = []
            continue

        if clean:
            sections[current_section].append(clean)

    return sections


def extract_sentences(lines: list[str]) -> list[str]:
    """
    Convert section lines into sentences.
    Works even if PDF breaks sentences across lines.
    """

    text = " ".join(lines)

    # normalize spacing
    text = re.sub(r'\s+', ' ', text)

    # split sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    return [s.strip() for s in sentences if len(s.strip()) > 20]


def preprocess_resume(pdf_path: str, logger=None) -> list[dict]:
    """Preprocess resume PDF into list of text chunks with section metadata.
"""
    logger.info("Inside preprocess_resume\n")

    lines = extract_lines_with_style(pdf_path, logger)

    current_section = "OTHER"
    current_context = None

    SKIP_SECTIONS = {"OTHER", "EDUCATION", "SKILLS"}

    final_chunks = []

    for line in lines:

        text = line["text"]
        bold = line["bold"]

        clean = text.strip()

        # section detection
        if clean.upper() in SECTION_HEADERS:
            current_section = clean.upper()
            current_context = None
            continue

        if current_section in SKIP_SECTIONS:
            continue

        # detect context titles (company / project)
        if bold and clean.upper() not in SECTION_HEADERS:
            current_context = clean
            continue

        # sentence splitting
        sentences = extract_sentences([clean])

        for sentence in sentences:

            final_chunks.append({
                "text": sentence,
                "section": current_section,
                "context": current_context
            })
    logger.info("exiting preprocess_resume\n")

    return final_chunks

def init_test_resume_pipeline(pdf_path: str):
    """
    Simple runner to test resume preprocessing pipeline.
    Prints extracted chunks with section metadata.
    """

    chunks = preprocess_resume(pdf_path)

    print("\nTotal chunks extracted:", len(chunks))
    print("-" * 60)
    # print(f"Chunks: \n{chunks}")
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}\n")
        print(f"{chunk}")
        print("-" * 60)


if __name__ == "__main__":
    resume_path = "resume_a2.pdf"   # testing
    init_test_resume_pipeline(resume_path)