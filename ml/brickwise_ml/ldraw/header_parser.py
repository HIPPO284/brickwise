from pathlib import Path

def parse_header(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    name = author = license_raw = None
    dependencies, malformed = [], []
    for number, line in enumerate(lines, 1):
        if line.startswith("0 Name:"): name = line[7:].strip()
        elif line.startswith("0 Author:"): author = line[9:].strip()
        elif line.startswith("0 !LICENSE"): license_raw = line[10:].strip()
        elif line.startswith("0 FILE "): name = line[7:].strip()
        elif line.startswith("1 "):
            parts = line.split()
            if len(parts) < 15:
                malformed.append({"line": number, "text": line, "reason": "malformed type-1 reference"})
            else:
                dependencies.append(parts[-1].replace("\\", "/"))
        elif line and not line.startswith(("0 ", "1 ", "2 ", "3 ", "4 ", "5 ")):
            malformed.append({"line": number, "text": line, "reason": "unknown line type"})
    return {"file": str(path), "filename": path.name, "name": name, "author": author,
            "license_raw": license_raw, "raw_header": "\n".join(lines[:30]),
            "dependencies": sorted(set(dependencies)), "malformed_lines": malformed}
