"""
Bulk-import questions from CAT P2 past-paper PDFs (and their memos) into the
QuestionBankItem table.

Scope:
  * Section A — MCQ (Q1), Matching (Q2), True/False (Q3)  [layout-stable]
  * Section B/C — long-form structured questions, parsed heuristically using
    DBE's universal "N.M[.K]" sub-numbering scheme. Only LEAF sub-questions
    (those whose marks are stated as "(N)") are inserted; container/parent
    items that just introduce a scenario are skipped. Items are tagged
    `needs-review` so a teacher can clean any imperfect parse before assigning.

Idempotent: skips questions whose exact text already exists in the bank for
the same paper source, so the script can be re-run safely.
"""
import os, re, sys, io, glob
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pdfplumber
from app import app, db, User, QuestionBankItem

UPLOADS = Path('static/uploads')

# ---------- Filename helpers ----------------------------------------------

# Match: "Computer Application(s) Technology P2 <session> <year> Eng[.docx].pdf"
# session: "May-June" | "Nov" | "November" | "May-June " (note double-space variant)
PAPER_RE = re.compile(
    r"Computer Application[s]? Technology P(?P<pn>[12])\s+"
    r"(?P<session>[A-Za-z\-]+)\s+(?P<year>\d{4})\s*(?:MG\s+)?Eng",
    re.IGNORECASE,
)
MEMO_TOKEN_RE = re.compile(r"\bMG\b", re.IGNORECASE)


def classify(path: Path):
    """Return (paper_no, session, year, is_memo) or None."""
    name = path.name
    m = PAPER_RE.search(name)
    if not m:
        return None
    is_memo = bool(MEMO_TOKEN_RE.search(name))
    return int(m.group("pn")), m.group("session"), int(m.group("year")), is_memo


def find_pairs():
    """Yield (paper_path, memo_path, label) tuples for P2 papers only."""
    bucket = {}  # (pn, session, year) -> {"paper":..., "memo":...}
    for f in UPLOADS.glob("*.pdf"):
        c = classify(f)
        if not c:
            continue
        pn, session, year, is_memo = c
        if pn != 2:
            continue  # only P2 has parseable theory
        key = (pn, session.lower().rstrip("-"), year)
        bucket.setdefault(key, {})
        slot = "memo" if is_memo else "paper"
        # If duplicate (e.g. "(1)" copy), prefer the larger / non-duplicate
        existing = bucket[key].get(slot)
        if existing is None or f.stat().st_size > existing.stat().st_size:
            bucket[key][slot] = f

    for (pn, session, year), pair in sorted(bucket.items(), key=lambda x: (x[0][2], x[0][1])):
        if "paper" in pair:
            label = f"P{pn} {session.title()} {year}"
            yield pair["paper"], pair.get("memo"), label


# ---------- PDF text extraction --------------------------------------------

def extract_full_text(path: Path) -> str:
    """Concatenate text of all pages with form-feed separators."""
    out = []
    with pdfplumber.open(str(path)) as pdf:
        for p in pdf.pages:
            out.append(p.extract_text() or "")
    return "\n\f\n".join(out)


# ---------- Layout-aware helpers (for two-column pages) --------------------

def _words_grouped_by_line(words, y_tol=3):
    """Group word dicts into rows by similar 'top' coordinate. Sort rows top-down,
    words left-right within each row."""
    rows = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(w["top"] - rows[-1][0]["top"]) <= y_tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    for r in rows:
        r.sort(key=lambda w: w["x0"])
    return rows


def extract_matching_layout(paper_path: Path):
    """Use word-level layout extraction to read the two-column MATCHING page.

    Returns (descriptions_dict, column_b_dict):
        descriptions_dict: {2.N -> text}
        column_b_dict:     {LETTER -> term}
    """
    descriptions = {}
    column_b = {}
    with pdfplumber.open(str(paper_path)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if "MATCHING ITEMS" not in txt.upper():
                continue
            words = page.extract_words(use_text_flow=False)
            if not words:
                continue
            page_w = page.width
            # Auto-detect the x-position of Column B by clustering the x0 of
            # all single-capital-letter (A-T) words. The dominant cluster is
            # the column-B label column (≥10 labels typically). We round to the
            # nearest 5pt and pick the bin with the most members that lies in
            # the right ~40% of the page.
            cand = [w for w in words if re.fullmatch(r"[A-T]", w["text"])]
            from collections import Counter
            bins = Counter(round(w["x0"] / 5) * 5 for w in cand
                           if w["x0"] >= page_w * 0.40)
            if not bins:
                continue
            # Some papers split Column B into two physical sub-columns
            # (e.g. A-J on the left half of Column B, K-T on the right). Take
            # the union of all x-bins that have >= 3 single-letter occurrences
            # — these are the candidate label columns.
            label_bins = sorted(b for b, c in bins.items() if c >= 3)
            if not label_bins:
                col_b_x = page_w * 0.55
                label_columns = []
            else:
                # Use the ACTUAL minimum x0 of words that fall into any label
                # bin — using the rounded bin value as a cutoff can misclassify
                # words whose x0 sits just below the bin boundary.
                bin_set = set(label_bins)
                label_word_xs = [w["x0"] for w in cand
                                 if round(w["x0"] / 5) * 5 in bin_set]
                col_b_x = min(label_word_xs) - 1
                label_columns = label_bins
            rows = _words_grouped_by_line(words)

            cur_desc_num = None
            cur_desc_parts = []
            cur_label = None
            cur_term_parts = []

            def flush_desc():
                nonlocal cur_desc_num, cur_desc_parts
                if cur_desc_num is not None and cur_desc_parts:
                    descriptions.setdefault(cur_desc_num, [])
                    descriptions[cur_desc_num].extend(cur_desc_parts)
                cur_desc_parts = []

            def flush_label():
                nonlocal cur_label, cur_term_parts
                if cur_label and cur_term_parts:
                    column_b[cur_label] = " ".join(cur_term_parts).strip()
                cur_term_parts = []

            for row in rows:
                row_text = " ".join(w["text"] for w in row)
                # Skip COLUMN A / COLUMN B header row, footer marks.
                if re.search(r"COLUMN\s*A\s*COLUMN\s*B", row_text, re.IGNORECASE):
                    continue
                if re.search(r"\(\s*10\s*x\s*1\s*\)|\[\s*10\s*\]", row_text):
                    continue
                if "Copyright reserved" in row_text or row_text.strip().startswith("NSC"):
                    continue

                left = [w for w in row if w["x0"] < col_b_x]
                right = [w for w in row if w["x0"] >= col_b_x]

                # ---- Left side: Column A descriptions ----
                if left:
                    left_text = " ".join(w["text"] for w in left).strip()
                    dm = re.match(r"^(2)\.(\d{1,2})\s+(.*)$", left_text)
                    if dm:
                        flush_desc()
                        cur_desc_num = int(dm.group(2))
                        if dm.group(3):
                            cur_desc_parts.append(dm.group(3))
                    elif cur_desc_num is not None:
                        cur_desc_parts.append(left_text)

                # ---- Right side: Column B label(s) + term(s) ----
                # A row may contain ONE or TWO label entries when Column B is
                # split into sub-columns. Walk the right-side words and start a
                # new label whenever we see a single-capital A-T word whose x0
                # is near one of the detected label columns (or as the first
                # right-side word).
                if right:
                    label_xs_set = set(label_columns)

                    def is_label_anchor(w):
                        if not re.fullmatch(r"[A-T]", w["text"]):
                            return False
                        # Snap to nearest 5pt and check if it's a known label column.
                        snap = round(w["x0"] / 5) * 5
                        return snap in label_xs_set or not label_columns

                    for j, w in enumerate(right):
                        if is_label_anchor(w) and (j == 0 or is_label_anchor(w)):
                            # Start a fresh label.
                            flush_label()
                            cur_label = w["text"]
                        elif cur_label:
                            cur_term_parts.append(w["text"])

            flush_desc()
            flush_label()

    # Flatten descriptions list-of-parts into single strings.
    descriptions = {n: re.sub(r"\s+", " ", " ".join(parts)).strip()
                    for n, parts in descriptions.items()}
    return descriptions, column_b


def extract_memo_section_a_layout(memo_path: Path):
    """Use word-level layout extraction on the memo Section-A page (two-column
    Q1 | Q2 layout) to get answers.

    Returns dict {(qno, sub) -> answer_str}.
    """
    answers = {}
    with pdfplumber.open(str(memo_path)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            up = txt.upper()
            wants = (
                "QUESTION 1: MULTIPLE" in up
                or "MULTIPLE-CHOICE" in up
                or "QUESTION 2: MATCHING" in up
                or "MATCHING ITEMS" in up
                or "QUESTION 3: TRUE" in up
                or "TRUE/FALSE" in up
            )
            if not wants:
                continue
            words = page.extract_words(use_text_flow=False)
            if not words:
                continue
            page_w = page.width
            rows = _words_grouped_by_line(words)
            for row in rows:
                row_text = " ".join(w["text"] for w in row)
                if "Copyright reserved" in row_text or row_text.strip().startswith("NSC"):
                    continue
                # Split the row into chunks anchored on "X.Y" tokens (where X in
                # {1,2,3}). For each anchor take subsequent words up to the next
                # anchor or end-of-row, then strip the trailing tick + mark digit.
                anchors = []
                for i, w in enumerate(row):
                    if re.fullmatch(r"[123]\.\d{1,2}", w["text"]):
                        anchors.append(i)
                for k, idx in enumerate(anchors):
                    q_str = row[idx]["text"]
                    q, n = q_str.split(".")
                    q, n = int(q), int(n)
                    end = anchors[k+1] if k+1 < len(anchors) else len(row)
                    chunk = row[idx+1:end]
                    # Drop trailing standalone digit (mark column).
                    while chunk and re.fullmatch(r"\d", chunk[-1]["text"]):
                        chunk.pop()
                    # Drop trailing tick / replacement glyphs.
                    while chunk and re.search(r"[^\x20-\x7E]", chunk[-1]["text"]) and len(chunk[-1]["text"]) <= 3:
                        chunk.pop()
                    ans = " ".join(w["text"] for w in chunk).strip()
                    # Strip tick chars inside.
                    ans = re.sub(r"[\u2713\u2714]", "", ans)
                    ans = re.sub(r"[^\x20-\x7E/,\-\.\(\)' ]", "", ans)
                    ans = re.sub(r"\s+", " ", ans).strip(" ,;-")
                    # Trim trailing standalone digit again post-cleanup.
                    ans = re.sub(r"\s+\d+$", "", ans)
                    if ans:
                        answers[(q, n)] = ans
    return answers


# ---------- Section A parsing (paper) --------------------------------------

# Strip running headers / footers like:
#   Computer Applications Technology/P2 7 DBE/November 2023
#   NSC
#   Copyright reserved Please turn over   /   Please-turn-over
HEADER_LINES = re.compile(
    r"^(?:"
    r"Computer Application[s]? Technology/P\d.*$"
    r"|NSC.*$"
    r"|Copyright reserved.*$"
    r"|SC/NSC.*$"
    r"|DBE Stamp.*$"
    r"|EXAMINATION\s*$"
    r"|NUMBER\s*$"
    r")",
    re.MULTILINE | re.IGNORECASE,
)

def clean_text(t: str) -> str:
    t = HEADER_LINES.sub("", t)
    # Collapse multiple blank lines.
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def slice_section_a(paper_text: str) -> str:
    """Return only the SECTION A region of the paper text.

    The instructions page mentions 'SECTION A (25)' / 'SECTION B (75)' so we
    cannot anchor on those. Instead, anchor on the actual content headings:
    'QUESTION 1: MULTIPLE' (start) and 'QUESTION 4' / 'SECTION B' line that
    introduces Section B's first question (end).
    """
    txt = clean_text(paper_text)
    m_start = re.search(r"QUESTION\s+1\s*:?\s*MULTIPLE", txt, re.IGNORECASE)
    if not m_start:
        return ""
    # Find end: 'QUESTION 4' (start of Section B's first question) OR
    # 'TOTAL SECTION A' marker, whichever comes first after the start.
    m_end_q4 = re.search(r"QUESTION\s+4\b", txt[m_start.end():], re.IGNORECASE)
    m_end_total = re.search(r"TOTAL\s+SECTION\s+A", txt[m_start.end():], re.IGNORECASE)
    candidates = [m for m in (m_end_q4, m_end_total) if m]
    if candidates:
        # Use TOTAL SECTION A end if present (it sits right after Q3); else Q4.
        if m_end_total:
            end_offset = m_start.end() + m_end_total.end()
        else:
            end_offset = m_start.end() + m_end_q4.start()
    else:
        end_offset = len(txt)
    return txt[m_start.start():end_offset]


def parse_mcq(section_a: str):
    """Parse Q1 MCQ. Returns list of {num, text, options:[A,B,C,D], marks}."""
    # Slice between QUESTION 1 and QUESTION 2 headings.
    m1 = re.search(r"QUESTION\s+1\s*:?\s*MULTIPLE", section_a, re.IGNORECASE)
    m2 = re.search(r"QUESTION\s+2\s*:?\s*MATCHING", section_a, re.IGNORECASE)
    if not m1:
        return []
    blob = section_a[m1.end(): (m2.start() if m2 else len(section_a))]
    # Each item starts with "1.N " on its own (after a newline). Capture up to next "1.N " or end.
    items = []
    # Find all 1.N anchor positions
    starts = [m for m in re.finditer(r"(?m)^\s*1\.(\d{1,2})(?=[ \t])", blob)]
    for i, sm in enumerate(starts):
        num = int(sm.group(1))
        body = blob[sm.end(): (starts[i+1].start() if i+1 < len(starts) else len(blob))].strip()
        # body looks like:
        #   Which ONE of the following ...?
        #   A option1
        #   B option2
        #   C option3
        #   D option4 (1)
        # Marks: trailing "(N)" — we only want 1-mark MCQs typically.
        marks_m = re.search(r"\((\d)\)\s*$", body)
        marks = int(marks_m.group(1)) if marks_m else 1
        if marks_m:
            body = body[:marks_m.start()].rstrip()
        # Split options A-D
        # Use a regex that finds option lines starting with capital A-E followed by space.
        opt_starts = [m for m in re.finditer(r"(?m)^\s*([A-E])\s+", body)]
        if len(opt_starts) >= 4:
            stem = body[:opt_starts[0].start()].strip()
            opts = []
            for j, om in enumerate(opt_starts):
                end = opt_starts[j+1].start() if j+1 < len(opt_starts) else len(body)
                letter = om.group(1)
                txt = body[om.end():end].strip().replace("\n", " ")
                txt = re.sub(r"\s+", " ", txt)
                opts.append((letter, txt))
            items.append({
                "num": num,
                "text": re.sub(r"\s+", " ", stem),
                "options": opts,
                "marks": marks,
            })
    return items


def parse_matching(section_a: str):
    """Parse Q2 MATCHING. Returns (descriptions, columnB_options).

    descriptions: list of {num, text, marks}
    columnB_options: dict letter -> term  (the candidate pool; same for every q)
    """
    m2 = re.search(r"QUESTION\s+2\s*:?\s*MATCHING", section_a, re.IGNORECASE)
    m3 = re.search(r"QUESTION\s+3\s*:?\s*TRUE", section_a, re.IGNORECASE)
    if not m2:
        return [], {}
    blob = section_a[m2.end(): (m3.start() if m3 else len(section_a))]
    # Drop the leading "Choose a term..." instruction line(s) and "COLUMN A COLUMN B" header.
    blob = re.sub(r".*COLUMN\s*A\s*COLUMN\s*B", "", blob, count=1, flags=re.DOTALL | re.IGNORECASE)

    # Each Column-A description starts with "2.N ", description text may span
    # multiple lines, and Column-B options (single capital letter on its own
    # at start of a "word") are interleaved in the same physical text. We
    # separate them by classifying each line.
    lines = [ln.rstrip() for ln in blob.splitlines()]
    desc_lines_by_num = {}
    current_num = None
    column_b = {}
    last_letter = None

    desc_start_re = re.compile(r"^\s*2\.(\d{1,2})\s+(.*)$")
    column_b_re = re.compile(r"^\s*([A-T])\s+(.+)$")  # single capital then space then term

    for raw in lines:
        ln = raw.strip()
        if not ln:
            current_num = None
            last_letter = None
            continue
        # Footer marks like "(10 x 1) [10]" — stop processing.
        if re.search(r"\(\s*10\s*x\s*1\s*\)|\[\s*10\s*\]", ln):
            current_num = None
            last_letter = None
            continue
        dm = desc_start_re.match(ln)
        if dm:
            current_num = int(dm.group(1))
            desc_lines_by_num.setdefault(current_num, []).append(dm.group(2))
            last_letter = None
            continue
        cb = column_b_re.match(ln)
        # A line is a Column-B option if it's a single capital letter (A-T) followed
        # by 1+ words AND it's not currently inside a description line continuation
        # that starts with text. We trust the regex match here.
        if cb and len(cb.group(2).split()) <= 6 and not re.match(r"^\s*\d", ln):
            letter = cb.group(1)
            term = cb.group(2).strip()
            column_b[letter] = term
            last_letter = letter
            continue
        # Otherwise it's a continuation line of either the current description
        # OR the last Column-B term (term wrap-around).
        if current_num is not None:
            desc_lines_by_num[current_num].append(ln)
        elif last_letter is not None:
            column_b[last_letter] = (column_b[last_letter] + " " + ln).strip()

    descriptions = []
    for num in sorted(desc_lines_by_num):
        text = " ".join(desc_lines_by_num[num])
        text = re.sub(r"\s+", " ", text).strip()
        descriptions.append({"num": num, "text": text, "marks": 1})
    return descriptions, column_b


def parse_true_false(section_a: str):
    """Parse Q3 TRUE/FALSE. Returns list of {num, text, marks}."""
    m3 = re.search(r"QUESTION\s+3\s*:?\s*TRUE", section_a, re.IGNORECASE)
    if not m3:
        return []
    blob = section_a[m3.end():]
    # Stop at TOTAL SECTION A or end.
    end_m = re.search(r"TOTAL\s+SECTION\s+A", blob, re.IGNORECASE)
    if end_m:
        blob = blob[:end_m.start()]

    # Find all 3.N starts
    starts = [m for m in re.finditer(r"(?m)^\s*3\.(\d)\s+", blob)]
    items = []
    for i, sm in enumerate(starts):
        num = int(sm.group(1))
        body = blob[sm.end(): (starts[i+1].start() if i+1 < len(starts) else len(blob))].strip()
        marks_m = re.search(r"\((\d)\)\s*$", body)
        marks = int(marks_m.group(1)) if marks_m else 1
        if marks_m:
            body = body[:marks_m.start()].rstrip()
        text = re.sub(r"\s+", " ", body)
        items.append({"num": num, "text": text, "marks": marks})
    return items


# ---------- Section B / C parsing (paper) ---------------------------------

# Question heading like:
#   QUESTION 4: SYSTEMS TECHNOLOGIES
#   QUESTION 5: INTERNET AND NETWORK TECHNOLOGIES
#   QUESTION 6: INFORMATION MANAGEMENT
#   QUESTION 7: SOCIAL IMPLICATIONS
#   QUESTION 8: SOLUTION DEVELOPMENT
#   QUESTION 9: WORD PROCESSING AND DTP / SPREADSHEETS / DATABASE / HTML / GENERAL
QUESTION_HEAD_RE = re.compile(
    r"(?m)^\s*QUESTION\s+(\d{1,2})\s*:\s*(.+?)\s*$",
)

# Sub-question anchor: 4.1, 4.1.1, 12.3.4 etc. (1-2 digit major to be safe)
SUB_ANCHOR_RE = re.compile(r"(?m)^\s*(\d{1,2}(?:\.\d{1,2}){1,2})\s+")

# Marks at the end of an item line, e.g. "(2)" or "(15)"
TRAILING_MARKS_RE = re.compile(r"\((\d{1,2})\)\s*$")

# Section/total markers that end a section.
END_SECTION_RE = re.compile(
    r"(?:TOTAL\s+SECTION\s+[BC]\b|GRAND\s+TOTAL|TOTAL:\s*150)",
    re.IGNORECASE,
)


def slice_section_bc(paper_text: str):
    """Return the SECTION B + C text combined (everything from QUESTION 4 to
    end-of-paper / 'GRAND TOTAL: 150')."""
    txt = clean_text(paper_text)
    m_start = re.search(r"(?m)^\s*QUESTION\s+4\b", txt)
    if not m_start:
        return ""
    end_m = END_SECTION_RE.search(txt, m_start.end())
    end = end_m.start() if end_m else len(txt)
    return txt[m_start.start():end]


def parse_section_bc(paper_text: str):
    """Parse Section B/C of a paper into a list of leaf sub-question dicts.

    Each item: {
        'major': int,           # the parent QUESTION number (4, 5, ...)
        'topic': str,           # e.g. "SYSTEMS TECHNOLOGIES"
        'num':   str,           # full sub-number, e.g. "4.3.2"
        'text':  str,           # question text (single line, whitespace-collapsed)
        'marks': int,           # marks from trailing "(N)"
    }

    Only LEAF items (those with explicit "(N)" marks AND no descendants in the
    paper) are returned. Parents that merely introduce sub-questions are
    excluded.
    """
    bc = slice_section_bc(paper_text)
    if not bc:
        return []

    # 1) Build a map of major-question topic by scanning headings.
    topic_by_major = {}
    for m in QUESTION_HEAD_RE.finditer(bc):
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if n >= 4:
            topic_by_major[n] = m.group(2).strip()

    # 2) Find every sub-question anchor in document order.
    anchors = list(SUB_ANCHOR_RE.finditer(bc))
    if not anchors:
        return []

    raw_items = []  # list of {num, body}
    for i, am in enumerate(anchors):
        num = am.group(1)
        end_pos = anchors[i + 1].start() if i + 1 < len(anchors) else len(bc)
        body = bc[am.end():end_pos]
        # Cut out any QUESTION X: heading that fell into the body (start of
        # the NEXT major question).
        qh = QUESTION_HEAD_RE.search(body)
        if qh:
            body = body[:qh.start()]
        raw_items.append({"num": num, "body": body})

    # 3) Determine which numbers have descendants → they're parents/containers.
    all_nums = {it["num"] for it in raw_items}
    has_child = set()
    for n in all_nums:
        # n has a child if n + ".X" exists for some X.
        for other in all_nums:
            if other != n and other.startswith(n + "."):
                has_child.add(n)
                break

    leaves = []
    for it in raw_items:
        if it["num"] in has_child:
            continue  # container / scenario intro, skip
        major = int(it["num"].split(".")[0])
        if major < 4 or major > 12:
            continue  # not in Section B/C range
        body = it["body"].strip()
        # Find marks: scan all "(N)" tokens in the body and take the LAST one
        # (the trailing one). Some bodies have parenthetical numbers in the
        # text itself (e.g. "(IPv4)") — restrict to digits-only pure marks.
        marks = None
        for mm in re.finditer(r"\((\d{1,2})\)", body):
            marks = int(mm.group(1))
            marks_end = mm.end()
        if marks is None:
            continue  # no marks → not a real question, skip
        # Strip everything from the LAST marks marker onward.
        body = body[:marks_end - len(f"({marks})")].rstrip()
        # Collapse newlines + whitespace into single spaces but keep paragraph
        # breaks where there were blank lines.
        # First normalise CRLF, then split on blank lines.
        paragraphs = [re.sub(r"\s+", " ", p).strip()
                      for p in re.split(r"\n\s*\n", body)
                      if p.strip()]
        text = "\n".join(paragraphs)
        # Drop items whose text is empty or absurdly short.
        if len(text) < 4:
            continue
        leaves.append({
            "major": major,
            "topic": topic_by_major.get(major, f"Question {major}"),
            "num": it["num"],
            "text": text,
            "marks": marks,
        })
    return leaves


# ---------- Section B / C parsing (memo) ----------------------------------

def parse_memo_section_bc(memo_text: str):
    """Return dict {sub_num_str -> answer_text} for Section B/C items in the memo.

    Memo bodies for an item run from its anchor to the next anchor or to the
    next "Total for QUESTION X" / "QUESTION X" header. We keep the raw text
    (multi-line bullets), only stripping headers / page footers / tick glyphs.
    """
    if not memo_text:
        return {}
    txt = clean_text(memo_text)
    # Memo Section B starts at "QUESTION 4" too (after Section A which ends
    # around "Total for QUESTION 3").
    m_start = re.search(r"(?m)^\s*QUESTION\s+4\b", txt)
    if not m_start:
        return {}
    blob = txt[m_start.start():]

    anchors = list(SUB_ANCHOR_RE.finditer(blob))
    if not anchors:
        return {}

    answers = {}
    for i, am in enumerate(anchors):
        num = am.group(1)
        end_pos = anchors[i + 1].start() if i + 1 < len(anchors) else len(blob)
        body = blob[am.end():end_pos]
        # Strip "Total for QUESTION X" footers and any subsequent "QUESTION X"
        # heading that fell in.
        body = re.sub(r"Total\s+for\s+QUESTION\s+\d+.*", "", body,
                      flags=re.IGNORECASE | re.DOTALL)
        qh = QUESTION_HEAD_RE.search(body)
        if qh:
            body = body[:qh.start()]
        # Strip ✓ ✔ tick glyphs (and PUA glyphs from Wingdings/Symbol fonts
        # that get used for ticks: U+F0FC = Wingdings tick, U+F0B7 = bullet,
        # U+F0E0 = arrow). Also strip the multi-byte CP437 surrogate sequences
        # that appear when the PDF embeds those glyphs (∩â╝, ∩é╖).
        body = re.sub(r"[\u2713\u2714\u25A0-\u25FF\uF000-\uF8FF]", "", body)
        body = body.replace("∩â╝", "").replace("∩é╖", "").replace("∩Çá", "")
        # Strip the recurring header artefacts.
        body = re.sub(r"(?m)^\s*EXAMINATION\s*$", "", body)
        body = re.sub(r"(?m)^\s*NUMBER\s*$", "", body)
        body = re.sub(r"(?m)^\s*Maximum\s+Candidate\s*$", "", body)
        body = re.sub(r"(?m)^\s*Mark\s+Mark\s*$", "", body)
        body = re.sub(r"(?m)^\s*No\.?\s+Criteria\s*$", "", body)
        # Strip trailing "X" or "X Y" digit-only lines (mark column residue)
        # and trailing standalone digit at end of last non-empty line.
        body = re.sub(r"(?m)^\s*\d{1,2}(?:\s+\d{1,2})?\s*$", "", body)
        # Collapse runs of blank lines.
        body = re.sub(r"[ \t]+\n", "\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        # Strip trailing standalone digit (mark) at end of body.
        body = re.sub(r"\s+\d{1,2}\s*$", "", body)
        # Strip "(Any one) 1" / "(Any two) 2" trailing mark digits.
        body = re.sub(r"(\(Any\s+\w+\))\s+\d{1,2}\b", r"\1", body, flags=re.IGNORECASE)
        if body:
            answers[num] = body
    return answers


# ---------- Memo parsing ----------------------------------------------------

def parse_memo_section_a(memo_text: str):
    """Return dict {(qno, sub) -> answer_str} for keys (1, 1..10), (2, 1..10), (3, 1..5)."""
    if not memo_text:
        return {}
    txt = clean_text(memo_text)
    # Limit to before "SECTION B".
    m_b = re.search(r"\bSECTION\s+B\b", txt, re.IGNORECASE)
    if m_b:
        txt = txt[:m_b.start()]
    answers = {}

    # Pattern: "1.10 D" or "1.1 C" or "2.3 A / D" or "3.1 False, HTTP" — answer
    # text runs until we hit a tick/checkmark, the digit "1" trailing mark, or
    # the next "X.Y" anchor.
    # Simplest: line-based scan.
    cur_q = None
    for ln in txt.splitlines():
        ln = ln.rstrip()
        s = ln.strip()
        if not s:
            continue
        # Match "Q.N answer..." possibly with junk after.
        m = re.match(r"^(\d)\.(\d{1,2})\s+(.+)$", s)
        if not m:
            continue
        q, n = int(m.group(1)), int(m.group(2))
        if q not in (1, 2, 3):
            continue
        rest = m.group(3)
        # Strip trailing tick markers and standalone marks digit.
        # Tick chars come through as ✓ or weird CID chars (e.g. "∩â╝"). Strip
        # everything from the first occurrence of a non-printable / box char.
        # Also strip trailing " 1" mark.
        rest = re.sub(r"[\u2713\u2714].*$", "", rest)  # ✓ ✔
        # Strip MuPDF-style replacement chars from CID glyphs.
        rest = re.sub(r"[^\x20-\x7E/,\-\.\(\)' ].*$", "", rest)
        rest = rest.rstrip()
        # Strip trailing standalone " 1" or " 2" (the marks column)
        rest = re.sub(r"\s+\d+$", "", rest)
        rest = rest.strip(" ,;-")
        if rest:
            answers[(q, n)] = rest
    return answers


# ---------- Build & insert -------------------------------------------------

# Topic guess based on memo / paper terminology — section B/C themes for context.
# For Section A items we use a generic topic.
SECTION_A_TOPIC = "Section A — Theory"


def build_question_text_mcq(item):
    parts = [item["text"]]
    parts.append("")  # blank line before options
    for letter, txt in item["options"]:
        parts.append(f"{letter}) {txt}")
    return "\n".join(parts)


def build_question_text_match(item, column_b):
    base = "Match the following description with the correct term from the list: " + item["text"]
    if column_b:
        opts = " | ".join(f"{k}) {v}" for k, v in sorted(column_b.items()))
        base += "\n\nOptions: " + opts
    return base


def main():
    pairs = list(find_pairs())
    print(f"Found {len(pairs)} P2 paper PDFs to ingest:")
    for paper, memo, label in pairs:
        print(f"  - {label}  paper={paper.name!r}  memo={memo.name if memo else 'NONE'!r}")

    with app.app_context():
        # Ingest under the first admin user (or first teacher if no admin).
        owner = (User.query.filter_by(is_admin=True).first()
                 or User.query.filter_by(is_teacher=True).first()
                 or User.query.first())
        if not owner:
            print("ERROR: No users in database — cannot assign owner.")
            return
        print(f"\nIngesting under owner: {owner.username} ({owner.id})\n")

        total_added, total_skipped = 0, 0

        for paper_path, memo_path, label in pairs:
            print(f"\n=== {label} ===")
            try:
                paper_text = extract_full_text(paper_path)
            except Exception as e:
                print(f"  ! Could not read paper: {e}")
                continue

            section_a = slice_section_a(paper_text)
            if not section_a:
                print("  ! No SECTION A found, skipping.")
                continue

            mcq = parse_mcq(section_a)
            matching, column_b = parse_matching(section_a)
            tf = parse_true_false(section_a)

            # Override matching descriptions + Column B with layout-aware
            # extraction (the text-based parse merges the two columns).
            try:
                desc_lay, col_b_lay = extract_matching_layout(paper_path)
                if desc_lay:
                    new_matching = []
                    for it in matching:
                        clean = desc_lay.get(it["num"])
                        if clean:
                            new_matching.append({**it, "text": clean})
                        else:
                            new_matching.append(it)
                    matching = new_matching
                if col_b_lay and len(col_b_lay) >= len(column_b):
                    column_b = col_b_lay
            except Exception as e:
                print(f"  ! Layout parse of matching failed: {e}")

            answers = {}
            if memo_path:
                try:
                    memo_text = extract_full_text(memo_path)
                    # Verify memo is for P2 (some MG files were mislabelled).
                    if "P2" in memo_text or "/P2 " in memo_text:
                        # Prefer layout-aware extraction (handles two-column memo).
                        try:
                            answers = extract_memo_section_a_layout(memo_path)
                        except Exception as e:
                            print(f"  ! Layout memo parse failed, falling back: {e}")
                            answers = parse_memo_section_a(memo_text)
                        if not answers:
                            answers = parse_memo_section_a(memo_text)
                    else:
                        print("  ! Memo file does not appear to be for P2 — skipping memo answers.")
                except Exception as e:
                    print(f"  ! Could not read memo: {e}")

            print(f"  parsed: MCQ={len(mcq)}  Matching={len(matching)} (pool={len(column_b)})  T/F={len(tf)}  memo_keys={len(answers)}")

            # ---- Section B/C ----
            bc_items = parse_section_bc(paper_text)
            bc_answers = {}
            if memo_path:
                try:
                    memo_text_bc = extract_full_text(memo_path)
                    bc_answers = parse_memo_section_bc(memo_text_bc)
                except Exception as e:
                    print(f"  ! Memo B/C parse failed: {e}")
            bc_with_ans = sum(1 for it in bc_items if it["num"] in bc_answers)
            print(f"  Section B/C: {len(bc_items)} leaf items  ({bc_with_ans} with memo answers)")

            tag_label = label.replace(" ", "-")  # e.g. "P2-May-June-2023"

            def add_q(qtype, text, ans, marks, subnum,
                      topic=SECTION_A_TOPIC, subtopic=None, section="Section-A",
                      difficulty="easy", extra_tags=""):
                nonlocal total_added, total_skipped
                # Idempotency: skip if a question with this exact text + tag already exists.
                existing = QuestionBankItem.query.filter(
                    QuestionBankItem.question_text == text,
                    QuestionBankItem.tags.like(f"%{tag_label}%"),
                ).first()
                if existing:
                    total_skipped += 1
                    return
                tag_parts = ["CAT", tag_label, section, qtype]
                if extra_tags:
                    tag_parts.append(extra_tags)
                q = QuestionBankItem(
                    owner_id=owner.id,
                    grade=12,
                    topic=topic,
                    subtopic=subtopic or qtype.replace("_", " ").title(),
                    difficulty=difficulty,
                    question_type=qtype,
                    question_text=text,
                    answer_text=ans or "",
                    marks=marks,
                    tags=",".join(tag_parts),
                    is_shared=True,
                )
                db.session.add(q)
                total_added += 1

            for it in mcq:
                add_q("mcq", build_question_text_mcq(it),
                      answers.get((1, it["num"]), ""),
                      it["marks"], it["num"])

            for it in matching:
                add_q("match_columns", build_question_text_match(it, column_b),
                      answers.get((2, it["num"]), ""),
                      it["marks"], it["num"])

            for it in tf:
                add_q("true_false", it["text"],
                      answers.get((3, it["num"]), ""),
                      it["marks"], it["num"])

            # ---- Section B/C insertion ----
            for it in bc_items:
                marks = it["marks"]
                if marks <= 2:
                    diff = "easy"
                elif marks <= 4:
                    diff = "medium"
                else:
                    diff = "hard"
                # Section B = Q4..Q7, Section C = Q8..Q12 (varies — Q8/Q9 in
                # most papers map to applications; we tag based on major no.)
                section_tag = "Section-B" if it["major"] <= 7 else "Section-C"
                # Prepend the sub-question number to the text so teachers can
                # cross-reference back to the source paper.
                qtext = f"{it['num']}  {it['text']}"
                ans = bc_answers.get(it["num"], "")
                add_q(
                    "short_answer",
                    qtext,
                    ans,
                    marks,
                    it["num"],
                    topic=it["topic"].title(),
                    subtopic=f"{label}  Q{it['major']}",
                    section=section_tag,
                    difficulty=diff,
                    extra_tags="needs-review",
                )

            db.session.commit()

        print(f"\nDONE.  Added: {total_added}  Skipped (already present): {total_skipped}")


if __name__ == "__main__":
    main()
