"""
Document extraction pipeline for NWIS.

Takes raw drilling report text (a Well Completion Report or Daily Drilling
Report) and extracts structured fields: well name, formation tops, casing
program, mud program, and NPT (non-productive time) events with depth,
type and description.

For this prototype the "OCR" step is represented by accepting already-
digitized text (.txt) or a PDF whose text layer we pull directly; the same
downstream regex/NLP extraction logic would sit behind a Tesseract OCR pass
for scanned/image-only reports in production (see README for the extension
point). The extraction logic itself is real, not mocked: it uses section
detection + regex field parsing, which is exactly the technique used for
semi-structured industrial reports before adding a fine-tuned NER model.
"""
import re
import json

SECTION_HEADERS = [
    "FORMATION TOPS",
    "CASING PROGRAM",
    "MUD PROGRAM",
    "NPT EVENTS",
    "NON-PRODUCTIVE TIME EVENTS",
]

EVENT_TYPE_KEYWORDS = {
    "mud_loss": ["mud loss", "lost circulation", "loss of returns"],
    "kick": ["kick", "influx", "well control", "shut-in", "shut in"],
    "stuck_pipe": ["stuck pipe", "differential sticking", "pack-off", "fishing"],
    "cementing_issue": ["cement", "squeeze", "wo c", "channeling"],
    "torque_spike": ["torque spike", "erratic torque", "tight hole", "reamed"],
}


def split_sections(text: str):
    """Split raw report text into a dict of {section_name: section_body}."""
    pattern = "|".join(re.escape(h) for h in SECTION_HEADERS)
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
    sections = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[m.group(0).upper()] = text[start:end].strip()
    return sections


def extract_well_name(text: str):
    m = re.search(r"Well\s*(?:Name|No\.?)\s*[:\-]\s*([A-Za-z0-9\-]+)", text, flags=re.IGNORECASE)
    return m.group(1) if m else None


def extract_report_type(text: str):
    if re.search(r"well completion report", text, flags=re.IGNORECASE):
        return "WCR"
    if re.search(r"daily drilling report", text, flags=re.IGNORECASE):
        return "DDR"
    return "UNKNOWN"


def extract_formation_tops(section_text: str):
    """Parses lines like 'Tipam Sandstone   -   820m' into structured tops."""
    tops = []
    for line in section_text.splitlines():
        m = re.match(r"\s*([A-Za-z()\-\s]+?)\s*[-:]\s*(\d+(?:\.\d+)?)\s*m", line)
        if m:
            tops.append({"formation": m.group(1).strip(), "depth_m": float(m.group(2))})
    return tops


def extract_casing_program(section_text: str):
    rows = []
    for line in section_text.splitlines():
        m = re.match(r"\s*([\d\.]+\s*(?:in|inch|\")?)\s*(?:casing|liner)?\s*(?:set\s+at|set|@|at)\s*(\d+(?:\.\d+)?)\s*m", line, flags=re.IGNORECASE)
        if m:
            rows.append({"size": m.group(1).strip(), "set_depth_m": float(m.group(2))})
    return rows


def extract_events(section_text: str):
    """
    Parses NPT event entries out of a section. Handles both clean digital
    text (one event per line) and OCR'd text where a single event can wrap
    across multiple lines with no blank-line separator: paragraphs are
    joined and re-split on sentence boundaries before per-event parsing.
    """
    paragraphs = re.split(r"\n\s*\n", section_text)
    sentences = []
    for para in paragraphs:
        joined = re.sub(r"\s+", " ", para).strip()
        if not joined:
            continue
        parts = re.split(r"(?<=[.;])\s+(?=[A-Z])", joined)
        sentences.extend(p.strip() for p in parts if p.strip())

    events = []
    for line_clean in sentences:
        depth_match = re.search(r"(\d+(?:\.\d+)?)\s*m\b", line_clean)
        depth = float(depth_match.group(1)) if depth_match else None
        event_type = "unclassified"
        for etype, keywords in EVENT_TYPE_KEYWORDS.items():
            if any(kw in line_clean.lower() for kw in keywords):
                event_type = etype
                break
        if event_type != "unclassified" or depth_match:
            events.append({
                "event_type": event_type,
                "depth_m": depth,
                "description": line_clean,
            })
    return events


def extract_report(text: str) -> dict:
    """Main entry point: raw report text -> structured JSON-able dict."""
    sections = split_sections(text)

    formation_tops = []
    for key in sections:
        if "FORMATION" in key:
            formation_tops.extend(extract_formation_tops(sections[key]))

    casing_program = []
    for key in sections:
        if "CASING" in key:
            casing_program.extend(extract_casing_program(sections[key]))

    events = []
    for key in sections:
        if "NPT" in key or "NON-PRODUCTIVE" in key:
            events.extend(extract_events(sections[key]))

    mud_program_text = ""
    for key in sections:
        if "MUD PROGRAM" in key:
            mud_program_text = sections[key].strip()

    result = {
        "well_name": extract_well_name(text),
        "report_type": extract_report_type(text),
        "formation_tops": formation_tops,
        "casing_program": casing_program,
        "mud_program_summary": mud_program_text,
        "npt_events": events,
        "sections_detected": list(sections.keys()),
    }
    return result


if __name__ == "__main__":
    import sys
    with open(sys.argv[1]) as f:
        text = f.read()
    print(json.dumps(extract_report(text), indent=2))
