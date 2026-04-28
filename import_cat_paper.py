"""
Import a CAT P2 past paper into the TEACHER QUESTION BANK
(table `question_bank_items`, viewable at /teacher/bank).

Usage:
    python import_cat_paper.py <paper_pdf> <memo_pdf> <paper_label>

Each item is tagged with:
    - topic      = CAT topic (e.g. "Systems Technologies")
    - subtopic   = question number (e.g. "Q4.1.3")
    - tags       = "CAT P2, <paper_label>, Grade 12"
    - answer_text= marking-guideline answer
    - is_shared  = True
    - owner_id   = first admin user

Re-running the script for the same paper_label REPLACES the previous batch.
"""
import os, re, sys
import pdfplumber

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db, User, QuestionBankItem


TOPIC_FOR_QROOT = {
    "1":  "Multiple Choice",
    "2":  "Matching",
    "3":  "True/False",
    "4":  "Systems Technologies",
    "5":  "Internet & Network Technologies",
    "6":  "Information Management",
    "7":  "Social Implications",
    "8":  "Solution Development",
    "9":  "Integrated Scenario",
    "10": "Integrated Scenario",
}


def topic_for(num: str) -> str:
    return TOPIC_FOR_QROOT.get(num.split(".")[0], "Other")


# ---------------------------------------------------------------------------
def extract_text(pdf_path: str) -> str:
    out = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            out.append(p.extract_text() or "")
    return "\n".join(out)


def strip_headers(txt: str) -> str:
    keep = []
    for ln in txt.splitlines():
        if re.match(r"^\s*Computer Applications? Technology/P\d+\s+\d+", ln):
            continue
        if "SC/NSC" in ln or "Copyright reserved" in ln:
            continue
        # Bare "NSC" page header line
        if re.match(r"^\s*NSC\s*(–.*)?$", ln):
            continue
        keep.append(ln)
    return "\n".join(keep)


# ---------------------------- Section A ------------------------------------
def parse_q1_mc(paper_txt):
    m = re.search(r"QUESTION 1[^\n]*\n(.*?)(?=QUESTION 2:)", paper_txt, re.S)
    if not m:
        return []
    out = []
    for chunk in re.split(r"\n(?=1\.\d+\s)", m.group(1)):
        chunk = re.sub(r"\s*\[\d+\][\s\S]*$", "", chunk.strip()).strip()
        m2 = re.match(
            r"^(1\.\d+)\s+(.*?)\s+A\s+(.*?)\s+B\s+(.*?)\s+C\s+(.*?)\s+D\s+(.*?)\s*\((\d+)\)\s*$",
            chunk, re.S)
        if not m2:
            continue
        num, stem, a, b, c, d, marks = m2.groups()
        out.append({
            "num": num,
            "stem": re.sub(r"\s+", " ", stem).strip(),
            "options": [re.sub(r"\s+", " ", o).strip() for o in (a, b, c, d)],
            "marks": int(marks),
        })
    return out


def parse_q3_tf(paper_txt):
    m = re.search(r"QUESTION 3:[^\n]*TRUE/FALSE.*?\n(.*?)TOTAL SECTION A",
                  paper_txt, re.S)
    if not m:
        return []
    out = []
    for sub in re.split(r"\n(?=3\.\d+\s)", m.group(1)):
        sub = re.sub(r"\s*\[\d+\][\s\S]*$", "", sub.strip()).strip()
        m2 = re.match(r"^(3\.\d+)\s+(.+?)\s*\((\d+)\)\s*$", sub, re.S)
        if not m2:
            continue
        num, stem, marks = m2.groups()
        out.append({"num": num,
                    "stem": re.sub(r"\s+", " ", stem).strip(),
                    "marks": int(marks)})
    return out


def parse_memo_mc(memo_txt):
    return {m.group(1): m.group(2)
            for m in re.finditer(r"\b(1\.\d+)\s+([A-D])\b", memo_txt)}


def parse_memo_matching(memo_txt):
    return {m.group(1): m.group(2)
            for m in re.finditer(r"\b(2\.\d+)\s+([A-T])\b", memo_txt)}


def parse_memo_tf(memo_txt):
    out = {}
    for m in re.finditer(
            r"\b(3\.\d+)\s+(True|False)(?:,\s*([^\n]*?))?\s*\d?\s*$",
            memo_txt, re.M):
        out[m.group(1)] = (m.group(2), (m.group(3) or "").strip())
    return out


# ---------------------------- Sections B+C --------------------------------
def split_by_subnumber(region):
    blocks, num, buf = [], None, []
    for ln in region.splitlines():
        m = re.match(r"^\s*((?:[4-9]|10)(?:\.\d+){1,2})\s+(.*)$", ln)
        if m:
            if num is not None:
                blocks.append((num, "\n".join(buf).strip()))
            num = m.group(1)
            buf = [m.group(2)]
        elif num is not None:
            buf.append(ln)
    if num is not None:
        blocks.append((num, "\n".join(buf).strip()))
    return blocks


def parse_paper_bc(paper_txt):
    m = (re.search(r"\nSECTION B\b(.*?)GRAND TOTAL", paper_txt, re.S)
         or re.search(r"\nSECTION B\b(.*)$", paper_txt, re.S))
    region = m.group(1) if m else ""
    raw = split_by_subnumber(region)
    nums = [n for n, _ in raw]
    out = []
    for num, txt in raw:
        if any(o.startswith(num + ".") for o in nums):
            continue
        marks_m = re.search(r"\((\d+)\)\s*$", txt)
        marks = int(marks_m.group(1)) if marks_m else 1
        clean = re.sub(r"\s*\(\d+\)\s*$", "", txt).strip()
        clean = re.sub(r"\s+", " ", clean)
        if clean:
            out.append((num, clean, marks))
    return out


def parse_memo_bc(memo_txt):
    m = (re.search(r"\nSECTION B\b(.*?)GRAND TOTAL", memo_txt, re.S)
         or re.search(r"\nSECTION B\b(.*)$", memo_txt, re.S))
    region = m.group(1) if m else ""
    out = {}
    for num, body in split_by_subnumber(region):
        body = re.sub(r"\s+\d+\s*$", "", body).strip()
        out[num] = re.sub(r"[ \t]+", " ", body)
    return out


# ---------------------------- Q2 matching tables ---------------------------
Q2_TABLES = {
    "CAT P2 May/June 2021": {
        "column_b": [
            ("A", "Blogs"), ("B", "ADSL"), ("C", "Defragmenter"),
            ("D", "NOW"), ("E", "Hacking"), ("F", "Graphics card"),
            ("G", "Wi-Fi functionality"), ("H", "MP"), ("I", "Click-jacking"),
            ("J", "Network card"), ("K", "NFC"), ("L", "Update"),
            ("M", "Phishing"), ("N", "DPI"), ("O", "Restart"),
            ("P", "Compatibility"), ("Q", "Identity theft"), ("R", "TODAY"),
            ("S", "Disk Cleanup"), ("T", "Wikis"),
        ],
        "column_a": {
            "2.1": "A feature that refers to whether a printer can be used with a particular operating system",
            "2.2": "One way of solving the problem of an application that has stopped responding",
            "2.3": "A specification that measures the quality of pictures taken by a camera",
            "2.4": "A technology that can be used to establish a wireless connection between two devices by bringing them close together",
            "2.5": "An attempt to access personal information by tricking a user into clicking on a link in an e-mail",
            "2.6": "Websites that read like a personal journal and are often updated with news and events",
            "2.7": "A spreadsheet function that returns both the date and time",
            "2.8": "A system utility that reorganises parts of files",
            "2.9": "The term given to the practice of accessing a network without permission",
            "2.10": "A hardware component that can be added to a computer to improve video editing performance",
        },
    },
    "CAT P2 Nov 2021": {
        "column_b": [
            ("A", "SUMIF"), ("B", "AI"), ("C", "RFID"),
            ("D", "Motherboard"), ("E", "Phishing"), ("F", "ROM"),
            ("G", "Firewall"), ("H", "Footnote"), ("I", "USB port"),
            ("J", "EULA"), ("K", "Disk Clean-Up"), ("L", "Antivirus"),
            ("M", "OCR"), ("N", "Identity theft"), ("O", "Endnote"),
            ("P", "AR"), ("Q", "IF"), ("R", "AUP"),
            ("S", "Defragmenter"), ("T", "RAM"),
        ],
        "column_a": {
            "2.1": "A legal agreement between a software company and a user for the use of their software",
            "2.2": "A utility program that can free up space on a storage medium",
            "2.3": "The act of opening a bank account using someone else's personal details",
            "2.4": "A spreadsheet function that totals the values in a range based on a certain condition",
            "2.5": "Software that can monitor all attempts made to access your computer",
            "2.6": "A technology that tries to solve problems in the way that humans do",
            "2.7": "Data needs to be loaded into this type of memory before it can be processed",
            "2.8": "A reference found at the bottom of a page in a word processing document",
            "2.9": "Technology using radio waves to communicate with a tag attached to an object",
            "2.10": "A circuit board that may be faulty if your computer will not start up",
        },
    },
    "CAT P2 May/June 2022": {
        "column_b": [
            ("A", "RAM"), ("B", "LTE"), ("C", "Word processing"),
            ("D", "Resolution"), ("E", "WAN"), ("F", "Shaping"),
            ("G", "Disk Cleanup"), ("H", "Spyware"), ("I", "SUM"),
            ("J", "Spam"), ("K", "MID"), ("L", "Keyboard"),
            ("M", "LAN"), ("N", "Phishing"), ("O", "VoIP"),
            ("P", "Explorer"), ("Q", "Adware"), ("R", "Spreadsheet"),
            ("S", "Brightness"), ("T", "Bluetooth"),
        ],
        "column_a": {
            "2.1": "A program that enables a user to organise his/her files and folders",
            "2.2": "An application most suited for data analysis",
            "2.3": "Software that attempts to collect information about a user without his/her permission",
            "2.4": "A spreadsheet function that extracts text data",
            "2.5": "A standard used in wireless communication that provides high-speed data transfers",
            "2.6": "Certain internet services are given bandwidth preference over other services",
            "2.7": "An important consideration when purchasing a monitor",
            "2.8": "A hardware component that will improve the performance of a computer",
            "2.9": "Type of network that connects offices of a company that are located in different cities",
            "2.10": "Unwanted e-mail sent to a large number of users",
        },
    },
    "CAT P2 May/June 2023": {
        "column_b": [
            ("A", "Asterisk (*)"), ("B", "Currency"), ("C", "VPN"),
            ("D", "Hashtag (#)"), ("E", "Data"), ("F", "Antivirus"),
            ("G", "PDF"), ("H", "Spyware"), ("I", "Authority"),
            ("J", "3D"), ("K", "Service pack"), ("L", "Information"),
            ("M", "Laser"), ("N", "Adware"), ("O", "Next (header/footer)"),
            ("P", "WAN"), ("Q", "Ad blocker"), ("R", "Patch"),
            ("S", "Section break"), ("T", "CSV"),
        ],
        "column_a": {
            "2.1": "Text, numbers and images in a format suitable for use by computers",
            "2.2": "Software used to remove malware from a computer system",
            "2.3": "A wild card used in database queries",
            "2.4": "A type of printer that uses plastic to print",
            "2.5": "A file format that can be used to share data between applications",
            "2.6": "A word processing option that allows you to apply different footers in the same document",
            "2.7": "A type of network with a very high level of security, that can be accessed over the internet",
            "2.8": "The evaluation of information that focuses on whether that information is still applicable",
            "2.9": "An update that corrects a single error found in software",
            "2.10": "A type of program that infects a computer and tracks the user's internet activities",
        },
    },
    "CAT P2 May/June 2024": {
        "column_b": [
            ("A", "Firewall"), ("B", "Evidence"), ("C", "<ul>…</ul>"),
            ("D", "Joystick"), ("E", "E-mail address"), ("F", "Hard copy"),
            ("G", "HDMI"), ("H", "Information"), ("I", "Page break"),
            ("J", "VGA"), ("K", "Section break"), ("L", "<ol>…</ol>"),
            ("M", "Soft copy"), ("N", "Text form field"), ("O", "Default value"),
            ("P", "Vibrating panel"), ("Q", "Switch"), ("R", "Drop-down form field"),
            ("S", "Required"), ("T", "CAPTCHA"),
        ],
        "column_a": {
            "2.1": "A printout is an example of a …",
            "2.2": "Data organised in a meaningful way",
            "2.3": "A device on a network that allows or prevents access to certain ports or communication channels",
            "2.4": "Distinguishes humans from bots on a website",
            "2.5": "The type of cable used to transmit high quality video and audio signals",
            "2.6": "Device used by hearing-impaired people",
            "2.7": "HTML code to create a bulleted list",
            "2.8": "A field property setting in Access that will ensure that a field cannot be left blank",
            "2.9": "A feature to ensure that a watermark only displays on the first two pages of a document",
            "2.10": "A control on the Developer Tab best suited for use with open-ended questions",
        },
    },
    "CAT P2 Nov 2022": {
        "column_b": [
            ("A", "VoIP"), ("B", "Information"), ("C", "BIOS"),
            ("D", "#NAME?"), ("E", "Data"), ("F", "ISP"),
            ("G", "Gamer"), ("H", "Password"), ("I", "Operating system"),
            ("J", "ROM"), ("K", "Telecommuting"), ("L", "<img src=\"bird.jpg\">"),
            ("M", "Biometrics"), ("N", "Data capturer"), ("O", "Server"),
            ("P", "<a href=\"bird.jpg\">"), ("Q", "SOHO"), ("R", "Hub"),
            ("S", "Software version"), ("T", "#VALUE!"),
        ],
        "column_a": {
            "2.1": "Raw numbers or facts that are unorganised",
            "2.2": "A device used on a network to manage and share resources",
            "2.3": "An internet technology that enables people from various countries to communicate in real time",
            "2.4": "This user generally requires a good quality graphics card",
            "2.5": "Firmware containing instructions for the start-up of a computer",
            "2.6": "An example of HTML code used to open a picture in a new browser window",
            "2.7": "A technology that uses a person's unique physical characteristics to control access",
            "2.8": "A reason why certain documents display unreadable content when you open it on your computer, even though you have an appropriate application",
            "2.9": "An arrangement for employees to work from home using ICTs",
            "2.10": "A spreadsheet error message that will appear if you enter the following function: =AVG(B1:B20)",
        },
    },
    "CAT P2 Nov 2023": {
        "column_b": [
            ("A", "Switch"), ("B", "Web page"), ("C", "Broadband"),
            ("D", "Fraud"), ("E", "AI"), ("F", "Firewall"),
            ("G", "VPN"), ("H", "Software"), ("I", "Bandwidth"),
            ("J", "Patch"), ("K", "Cell spacing"), ("L", "Blockchain"),
            ("M", "AR"), ("N", "Copyright"), ("O", "Digital footprint"),
            ("P", "Website"), ("Q", "Bluetooth"), ("R", "Service pack"),
            ("S", "Cell padding"), ("T", "Hub"),
        ],
        "column_a": {
            "2.1": "High-speed internet connection, which is referred to as 'always on'",
            "2.2": "A collection of instructions that enables a computer to perform specific tasks",
            "2.3": "Used to connect multiple devices within a LAN",
            "2.4": "A preventative action to protect your work from piracy",
            "2.5": "Used to encrypt and secure your internet traffic",
            "2.6": "Machines that can perform tasks (autonomously) that would normally require human action",
            "2.7": "Setting the space between the content of a cell and its border in an HTML table",
            "2.8": "Used to fix a specific programming problem in software",
            "2.9": "The electronic record of a person's online activity",
            "2.10": "A single HTML file on the internet",
        },
    },
    "CAT P2 May/June 2025": {
        "column_b": [
            ("A", "WiMAX"), ("B", "Information overload"), ("C", "Section break"),
            ("D", "Drone"), ("E", "Phishing"), ("F", "CAPTCHA"),
            ("G", "Patch"), ("H", "Router"), ("I", "Page break"),
            ("J", "Big data"), ("K", "Accuracy"), ("L", "VR helmet"),
            ("M", "OR"), ("N", "OTP"), ("O", "AND"),
            ("P", "ADSL"), ("Q", "Service pack"), ("R", "Keylogging"),
            ("S", "NIC"), ("T", "Currency"),
        ],
        "column_a": {
            "2.1": "A wired internet connection",
            "2.2": "A device that connects computers in a network to the internet",
            "2.3": "Splits the pages in a word processing document to be formatted differently",
            "2.4": "A device that has the ability to access areas that are too difficult or dangerous for humans to reach",
            "2.5": "An authentication used to distinguish between humans and bots",
            "2.6": "An operator that returns a TRUE result when either one of the two criteria is true",
            "2.7": "Software that updates and fixes multiple errors in applications",
            "2.8": "When large amounts of data are challenging for a person to process",
            "2.9": "A method that captures every character a user inputs without their consent",
            "2.10": "Verification of information with other sources",
        },
    },
}


def build_q2_pairs(paper_label, memo_letters):
    table = Q2_TABLES.get(paper_label)
    if not table:
        return [], []
    options_text = [t for _, t in table["column_b"]]
    letter_to_text = {l: t for l, t in table["column_b"]}
    pairs = []
    for num, stem in table["column_a"].items():
        ltr = memo_letters.get(num)
        if ltr in letter_to_text:
            pairs.append((num, stem, ltr, letter_to_text[ltr]))
    return options_text, pairs


# ---------------------------- DB write ------------------------------------
def get_owner_id():
    u = User.query.filter_by(is_admin=True).first() or User.query.first()
    if not u:
        raise RuntimeError("No users in DB")
    return u.id


def clear_existing(paper_label):
    n = (QuestionBankItem.query
         .filter(QuestionBankItem.tags.like(f"%{paper_label}%"))
         .delete(synchronize_session=False))
    db.session.commit()
    return n


def add_item(owner_id, *, num, qtext, qtype, marks, answer, paper_label):
    db.session.add(QuestionBankItem(
        owner_id=owner_id,
        grade=12,
        topic=topic_for(num),
        subtopic=f"Q{num}",
        difficulty="medium",
        question_type=qtype,
        question_text=qtext,
        answer_text=answer,
        marks=marks,
        tags=f"CAT P2, {paper_label}, Grade 12",
        is_shared=True,
    ))


def import_paper(paper_pdf, memo_pdf, paper_label):
    paper_txt = strip_headers(extract_text(paper_pdf))
    memo_txt = strip_headers(extract_text(memo_pdf))

    q1 = parse_q1_mc(paper_txt)
    mc_ans = parse_memo_mc(memo_txt)
    for q in q1:
        q["answer_letter"] = mc_ans.get(q["num"], "")

    q2_options, q2_pairs = build_q2_pairs(paper_label, parse_memo_matching(memo_txt))

    q3 = parse_q3_tf(paper_txt)
    tf_ans = parse_memo_tf(memo_txt)
    for q in q3:
        a, c = tf_ans.get(q["num"], ("True", ""))
        q["answer"], q["correction"] = a, c

    bc_paper = parse_paper_bc(paper_txt)
    bc_memo = parse_memo_bc(memo_txt)
    bc_pairs = [(num, stem, marks, bc_memo.get(num, ""))
                for num, stem, marks in bc_paper]

    print(f"Parsed: Q1={len(q1)}  Q2={len(q2_pairs)}  Q3={len(q3)}  B/C={len(bc_pairs)}")

    with app.app_context():
        owner = get_owner_id()
        removed = clear_existing(paper_label)
        if removed:
            print(f"Removed {removed} existing item(s) for '{paper_label}'.")

        # Q1 multiple-choice
        for q in q1:
            opts = q["options"]
            letter = q["answer_letter"]
            correct_text = opts[ord(letter) - ord("A")] if letter else ""
            qtext = (q["stem"] + "\n\n" +
                     "\n".join(f"{chr(ord('A')+i)}) {o}" for i, o in enumerate(opts)))
            add_item(owner, num=q["num"], qtext=qtext, qtype="mcq",
                     marks=q["marks"],
                     answer=f"{letter}) {correct_text}",
                     paper_label=paper_label)

        # Q2 matching
        for num, stem, ltr, text in q2_pairs:
            opts_str = "\n".join(
                f"{chr(ord('A')+i)}) {t}" for i, t in enumerate(q2_options))
            qtext = (f"Match the following description with the correct "
                     f"term from the list:\n\n{stem}\n\nOptions:\n{opts_str}")
            add_item(owner, num=num, qtext=qtext, qtype="mcq",
                     marks=1, answer=f"{ltr}) {text}", paper_label=paper_label)

        # Q3 true/false
        for q in q3:
            ans = q["answer"]
            if q["correction"]:
                ans = f"{q['answer']}, {q['correction']}"
            qtext = (q["stem"] +
                     "\n\n(Indicate True or False. If False, give the correction.)")
            add_item(owner, num=q["num"], qtext=qtext, qtype="short_answer",
                     marks=q["marks"], answer=ans, paper_label=paper_label)

        # Sections B + C
        for num, stem, marks, memo in bc_pairs:
            add_item(owner, num=num, qtext=stem, qtype="short_answer",
                     marks=marks,
                     answer=memo or "(See marking guideline)",
                     paper_label=paper_label)

        db.session.commit()
        n = QuestionBankItem.query.filter(
            QuestionBankItem.tags.like(f"%{paper_label}%")).count()
        total = db.session.query(db.func.sum(QuestionBankItem.marks)).filter(
            QuestionBankItem.tags.like(f"%{paper_label}%")).scalar() or 0
        print(f"Imported {n} items into question bank ({total} marks total).")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    import_paper(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
