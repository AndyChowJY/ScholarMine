"""Remove reference/bibliography sections from paper text."""
import re

class ReferenceStripper:
    REFERENCE_HEADERS = [
        r'(?i)^\s*references?\s*$',
        r'(?i)^\s*bibliography\s*$',
        r'(?i)^\s*literature\s+cited\s*$',
        r'(?i)^\s*works\s+cited\s*$',
        r'(?i)^\s*references?\s+and\s+notes?\s*$',
        r'(?i)^\s*acknowledg?ments?\s*$',
    ]

    @classmethod
    def strip(cls, text: str) -> str:
        lines = text.split('\n')
        best_cut = len(lines)

        for i, line in enumerate(lines):
            stripped = line.strip()
            for pattern in cls.REFERENCE_HEADERS:
                if re.match(pattern, stripped):
                    # Verify it looks like a section header (short, no trailing punctuation)
                    if len(stripped) < 40 and not stripped.endswith(('.', ',', ';', ':')):
                        # Check that following lines look like references
                        if cls._looks_like_references(lines, i):
                            best_cut = min(best_cut, i)
                            break

        if best_cut < len(lines):
            return '\n'.join(lines[:best_cut]).strip()
        return text

    @classmethod
    def _looks_like_references(cls, lines: list, header_idx: int) -> bool:
        """Heuristic: check if lines after header look like references."""
        ref_count = 0
        check_lines = lines[header_idx+1:header_idx+11]
        if len(check_lines) < 2:
            return True
        for line in check_lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Reference lines often start with [number], (Author, Year), or DOI
            if re.match(r'^\[\d+\]', stripped):
                ref_count += 1
            elif re.match(r'^\d+\.\s', stripped):
                ref_count += 1
            elif re.match(r'^[A-Z][a-z]+,\s[A-Z]\.', stripped):
                ref_count += 1
            elif 'doi.org' in stripped.lower() or 'doi:' in stripped.lower():
                ref_count += 1
        return ref_count >= 1
