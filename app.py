from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, abort, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import uuid
import json
import re
import csv
import io

from dotenv import load_dotenv
if os.path.exists('.env.development.local'):
    load_dotenv('.env.development.local')
elif os.path.exists('.env'):
    load_dotenv('.env')

from config import Config
from exam_guidelines import (
    CAPS_PAPER_TEMPLATES, CAPS_GUIDELINES, flatten_template
)

# =====================================================================
#  SHORT ANSWER GRADER  — expert-teacher-level scoring algorithm
# =====================================================================
_SA_STOP = {
    'a','an','the','is','are','was','were','be','been','being','have','has',
    'had','do','does','did','will','would','could','should','may','might',
    'must','shall','can','of','in','to','for','on','at','by','with','from',
    'as','that','this','these','those','it','its','they','them','and','or',
    'but','so','yet','i','you','he','she','we','my','your','his','her','our',
    'what','which','who','when','where','how','also','just','then','than',
}
_SA_NEGATIONS = {
    'not','never','no','neither','nor','nothing','nobody','nowhere','without',
    'lack','lacking','absent','absence','cannot','cant',
}

# Synonym map — each key maps to a set of equivalent words
# Covers common academic + CS/computer science vocabulary
_SA_SYNONYMS = {
    # CPU / Processor
    'cpu':{'processor','microprocessor'}, 'processor':{'cpu','microprocessor'},
    'microprocessor':{'cpu','processor'},
    # Memory / Storage
    'ram':{'memory'}, 'memory':{'ram'},
    'store':{'hold','contain','save','keep','retain','record'},
    'stores':{'holds','contains','saves','keeps','retains'},
    'storing':{'holding','containing','saving','keeping'},
    'stored':{'held','contained','saved','kept','recorded'},
    'hold':{'store','contain','keep','retain'}, 'holds':{'stores','contains','keeps'},
    'holding':{'storing','containing'},
    'storage':{'memory','retention','repository'},
    # Temporary / volatile
    'temporary':{'volatile','transient','short-term','momentary'},
    'temporarily':{'volatile','transiently','short-term'},
    'volatile':{'temporary','temporarily','transient'},
    # Active / current
    'active':{'current','running','present','ongoing'},
    'actively':{'currently','presently'},
    'currently':{'actively','presently','now'},
    'current':{'active','present','ongoing'},
    # Speed
    'fast':{'quick','rapid','speedy','swift'}, 'quick':{'fast','rapid','speedy'},
    'quickly':{'rapidly','swiftly','fast'}, 'rapidly':{'quickly','fast'},
    # Data / Information
    'data':{'information','info','content'}, 'information':{'data','info'},
    # Allow / enable
    'allow':{'enable','permit','let'}, 'allows':{'enables','permits'},
    'enables':{'allows','permits'}, 'enable':{'allow','permit'},
    # Use / utilize
    'use':{'utilize','employ','access'}, 'uses':{'utilizes','employs'},
    'using':{'utilizing','employing','accessing'},
    'used':{'utilized','employed','accessed'},
    # Permanent / persistent
    'permanent':{'persistent','non-volatile','long-term','fixed'},
    'permanently':{'persistently','non-volatile'},
    # Read / access
    'read':{'access','retrieve','fetch'}, 'reads':{'accesses','retrieves'},
    'access':{'read','retrieve','fetch'}, 'accesses':{'reads','retrieves'},
}

def _stem(word):
    """Lightweight suffix stripping — returns the root form."""
    for sfx in ('tion','sion','ness','ment','ity','ous','ive','ful','less',
                'able','ible','ance','ence','ing','er','ed','ly','al','es','s'):
        if word.endswith(sfx) and len(word) - len(sfx) >= 3:
            return word[:-len(sfx)]
    return word

def _expand(tokens):
    """Return an expanded set of tokens including stems and synonyms."""
    expanded = set(tokens)
    for t in tokens:
        # Add synonyms of the exact token
        for syn in _SA_SYNONYMS.get(t, set()):
            expanded.add(syn)
        # Add stem
        s = _stem(t)
        expanded.add(s)
        # Add synonyms of the stem
        for syn in _SA_SYNONYMS.get(s, set()):
            expanded.add(syn)
    return expanded

def _sa_normalize(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s'-]", ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def _sa_tokens(text):
    return [w for w in _sa_normalize(text).split()
            if w not in _SA_STOP and len(w) > 1]

def _lev_ratio(a, b):
    """Character-level Levenshtein similarity ratio."""
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    dp = list(range(lb + 1))
    for i, ca in enumerate(a):
        prev, dp[0] = dp[0], i + 1
        for j, cb in enumerate(b):
            prev, dp[j+1] = dp[j+1], min(prev + (0 if ca == cb else 1),
                                          dp[j] + 1, dp[j+1] + 1)
    return 1.0 - dp[lb] / max(la, lb)

def _kw_match(keyword, norm_user_text):
    """Check if a keyword appears in user text (exact or near-match)."""
    kw = _sa_normalize(keyword)
    if kw in norm_user_text:
        return True
    for w in norm_user_text.split():
        if len(w) >= 3 and _lev_ratio(kw, w) >= 0.88:
            return True
    # Also check expanded synonyms of keyword in user text
    for syn in _SA_SYNONYMS.get(kw, set()):
        if syn in norm_user_text:
            return True
    return False

def grade_short_answer(user_answer, model_answer, keywords=None, min_ratio=0.6):
    """
    Expert-teacher-level short answer grader.

    Scoring (weighted composite):
      40% — Jaccard similarity on expanded+stemmed content-word sets
      30% — Teacher keyword coverage  (if keywords provided)
      20% — Full-string Levenshtein similarity
      10% — Token sequence / LCS ordering bonus

    Expansions applied: synonym dictionary, lightweight suffix stemming,
    Levenshtein fuzzy matching for typos.
    Negation mismatch is penalised heavily (×0.35).

    Returns (is_correct: bool, score_ratio: float 0-1, feedback: str)
    """
    if not user_answer or not user_answer.strip():
        return False, 0.0, 'No answer provided.'

    norm_user  = _sa_normalize(user_answer)
    norm_model = _sa_normalize(model_answer)

    # ── Exact match after normalisation ─────────────────────────
    if norm_user == norm_model:
        return True, 1.0, 'Correct.'

    user_toks  = _sa_tokens(user_answer)
    model_toks = _sa_tokens(model_answer)

    # ── Negation mismatch detection ──────────────────────────────
    all_user_words  = set(_sa_normalize(user_answer).split())
    all_model_words = set(_sa_normalize(model_answer).split())
    user_negs  = bool(all_user_words  & _SA_NEGATIONS)
    model_negs = bool(all_model_words & _SA_NEGATIONS)
    negation_penalty = 0.35 if user_negs != model_negs else 1.0

    # ── Jaccard on expanded+stemmed token sets ───────────────────
    user_exp  = _expand(set(user_toks))
    model_exp = _expand(set(model_toks))
    if user_exp or model_exp:
        jac = len(user_exp & model_exp) / len(user_exp | model_exp)
    else:
        jac = 1.0

    # ── Keyword coverage ─────────────────────────────────────────
    if keywords:
        matched_kws = sum(1 for kw in keywords if _kw_match(kw, norm_user))
        kw_score = matched_kws / len(keywords)
        w_jac, w_kw, w_lev, w_ord = 0.40, 0.30, 0.20, 0.10
    else:
        kw_score = 0.0
        w_jac, w_kw, w_lev, w_ord = 0.55, 0.00, 0.30, 0.15

    # ── Levenshtein on full normalised strings ───────────────────
    lev = _lev_ratio(norm_user, norm_model)

    # ── Token ordering bonus (LCS ratio) ─────────────────────────
    def lcs_ratio(a, b):
        m, n = len(a), len(b)
        if not m or not n:
            return 0.0
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                dp[i][j] = dp[i-1][j-1] + 1 if a[i-1] == b[j-1] else max(dp[i-1][j], dp[i][j-1])
        return dp[m][n] / max(m, n)

    ord_score = lcs_ratio(user_toks, model_toks)

    composite = (jac * w_jac + kw_score * w_kw + lev * w_lev + ord_score * w_ord) * negation_penalty

    is_correct = composite >= min_ratio

    if composite >= 0.90:
        feedback = 'Excellent answer.'
    elif composite >= min_ratio:
        feedback = 'Correct.'
    elif composite >= min_ratio * 0.70:
        feedback = 'Partially correct — some key ideas are missing or misworded.'
    else:
        feedback = 'Incorrect.'

    return is_correct, round(composite, 3), feedback


# ── App setup ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

def gen_id():
    return str(uuid.uuid4())

# =====================================================================
#  MODELS
# =====================================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), default='')
    last_name = db.Column(db.String(50), default='')
    is_admin = db.Column(db.Boolean, default=False)
    is_teacher = db.Column(db.Boolean, default=False)
    grade = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy=True)
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    number = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, default='')
    courses = db.relationship('Course', backref='grade', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    grade_id = db.Column(db.String(36), db.ForeignKey('grades.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    icon = db.Column(db.String(50), default='fa-book')
    color = db.Column(db.String(20), default='#0078D4')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    lessons = db.relationship('Lesson', backref='course', lazy=True, order_by='Lesson.order')
    quizzes = db.relationship('Quiz', backref='course', lazy=True, order_by='Quiz.order')
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)

class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default='')
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    duration_minutes = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completions = db.relationship('LessonCompletion', backref='lesson', lazy=True)

class LessonCompletion(db.Model):
    __tablename__ = 'lesson_completions'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.String(36), db.ForeignKey('lessons.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Float, default=0.0)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    quiz_type = db.Column(db.String(20), default='quiz')
    time_limit_minutes = db.Column(db.Integer, nullable=True)
    pass_percentage = db.Column(db.Float, default=50.0)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='quiz', lazy=True, order_by='Question.order')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    quiz_id = db.Column(db.String(36), db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(30), nullable=False)
    options = db.Column(db.Text, default='[]')
    correct_answer = db.Column(db.Text, default='')
    points = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text, default='')
    def get_options(self):
        try: return json.loads(self.options)
        except: return []
    def get_correct_answer(self):
        try: return json.loads(self.correct_answer)
        except: return self.correct_answer

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.String(36), db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.Float, default=0.0)
    total_points = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    passed = db.Column(db.Boolean, default=False)
    answers = db.Column(db.Text, default='{}')
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    time_taken_seconds = db.Column(db.Integer, default=0)


# =====================================================================
#  TEACHER MODELS
# =====================================================================
class TeacherDocument(db.Model):
    """Past papers, data files and memos uploaded for teachers to download."""
    __tablename__ = 'teacher_documents'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    grade = db.Column(db.Integer, nullable=True)             # 10/11/12 or null = general
    subject = db.Column(db.String(100), default='CAT')       # CAT / IT / etc
    paper_year = db.Column(db.Integer, nullable=True)
    paper_type = db.Column(db.String(40), default='past_paper')  # past_paper | memo | data_files | other
    paper_number = db.Column(db.String(10), default='')      # '1' or '2' (optional)
    file_path = db.Column(db.String(400), nullable=False)    # relative to static/
    file_size = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)


class QuestionBankItem(db.Model):
    """Reusable bank of questions teachers can pull into generated papers."""
    __tablename__ = 'question_bank_items'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    grade = db.Column(db.Integer, default=12)
    topic = db.Column(db.String(120), default='')           # e.g. "Spreadsheets"
    subtopic = db.Column(db.String(120), default='')        # e.g. "VLOOKUP"
    difficulty = db.Column(db.String(20), default='medium') # easy | medium | hard
    question_type = db.Column(db.String(40), default='short_answer')  # short_answer | mcq | structured | practical
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text, default='')            # memo / model answer
    marks = db.Column(db.Integer, default=1)
    tags = db.Column(db.String(300), default='')            # comma list
    image_path = db.Column(db.String(400), default='')      # optional figure (relative to static/)
    is_shared = db.Column(db.Boolean, default=False)        # visible to other teachers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GeneratedPaper(db.Model):
    """A composed exam paper (with header info and selected questions)."""
    __tablename__ = 'generated_papers'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), default='Examination Paper')
    school_name = db.Column(db.String(200), default='')
    subject = db.Column(db.String(100), default='Computer Applications Technology')
    grade = db.Column(db.Integer, default=12)
    exam_date = db.Column(db.Date, nullable=True)
    duration_minutes = db.Column(db.Integer, default=180)
    total_marks = db.Column(db.Integer, default=150)
    examiner = db.Column(db.String(120), default='')
    moderator = db.Column(db.String(120), default='')
    instructions = db.Column(db.Text, default='')
    logo_path = db.Column(db.String(400), default='')       # relative to static/
    # Customisable cover / header / footer strings (DBE defaults applied in template if blank)
    paper_number = db.Column(db.String(10), default='')           # e.g. '1' or '2'  (auto from title if blank)
    cover_authority = db.Column(db.Text, default='')              # default: "SENIOR CERTIFICATE EXAMINATIONS/\nNATIONAL SENIOR CERTIFICATE EXAMINATIONS"
    cover_subtitle = db.Column(db.String(200), default='')        # default: "Confidential" (paper) or "MARKING GUIDELINES" (memo)
    header_left = db.Column(db.String(200), default='')           # default: "<Subject>/P<n>   <page>   DBE/<Month> <Year>"
    header_right = db.Column(db.String(200), default='')          # blank by default
    sub_header = db.Column(db.String(200), default='')            # default: "SC/NSC Confidential" / "SC/NSC – Marking Guidelines"
    footer_left = db.Column(db.String(200), default='Copyright reserved')
    footer_center = db.Column(db.String(200), default='')
    footer_right = db.Column(db.String(200), default='Please turn over')
    memo_title = db.Column(db.String(120), default='MARKING GUIDELINES')
    cover_extra_note = db.Column(db.Text, default='')             # extra free-text on cover (e.g. info-sheet note)
    sections = db.Column(db.Text, default='[]')             # JSON: [{title, instructions, question_ids:[...]}]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TeacherSchedule(db.Model):
    """Year planner / schedule entries for teachers."""
    __tablename__ = 'teacher_schedules'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    grade = db.Column(db.Integer, nullable=True)
    kind = db.Column(db.String(30), default='lesson')       # lesson | quiz | exam | event | task
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    term = db.Column(db.Integer, nullable=True)             # 1-4
    color = db.Column(db.String(20), default='#0078D4')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InstructionTemplate(db.Model):
    """Reusable instructions a teacher can save and pick when building a paper."""
    __tablename__ = 'instruction_templates'
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, uid)

@app.template_filter('from_json')
def from_json_filter(s):
    try: return json.loads(s)
    except: return s

@app.template_filter('regex_replace')
def regex_replace_filter(s, pattern, repl=''):
    """Jinja filter: re.sub(pattern, repl, s)."""
    import re as _re
    if s is None:
        return ''
    try:
        return _re.sub(pattern, repl, str(s))
    except _re.error:
        return s

@app.template_filter('memo_ticks')
def memo_ticks_filter(s):
    """Escape user content, dedent each line, strip trailing (N) mark notation,
    then replace ✓ with an inline-SVG tick so it renders reliably in PDFs
    even when the system font lacks U+2713."""
    from markupsafe import escape, Markup
    import re as _re
    if not s:
        return Markup('')
    # Dedent every line (template indentation leaks into pre-line content)
    lines = [ln.strip() for ln in str(s).splitlines()]
    # Remove trailing parenthetical mark like "(2)" on its own line — marks col already shows it
    while lines and _re.fullmatch(r'\(\d+\)', lines[-1] or ''):
        lines.pop()
    # Drop empty trailing lines
    while lines and not lines[-1]:
        lines.pop()
    # Merge soft-wrapped continuations: a line that doesn't start with a list
    # marker, tick, bullet or sentence-end punctuation gets joined onto the
    # previous line. (DBE imports often hard-wrap mid-item at print width.)
    _re_marker = _re.compile(r'^\s*(?:\(\d+\)|\d+[.)]|[\u2022\u2013\u2014-])\s')
    _re_tickline = _re.compile(r'^\s*[\u2713\u2714\uf0fb\uf0fc]')
    merged = []
    for ln in lines:
        if (merged
                and ln
                and not _re_marker.match(ln)
                and not _re_tickline.match(ln)
                and not ln.lower().startswith(('any ', 'accept', 'max', 'note', 'example', 'reason', '(any', '(accept', '(max'))
                and _re_marker.match(merged[-1])):
            merged[-1] = merged[-1].rstrip() + ' ' + ln.lstrip()
        else:
            merged.append(ln)
    lines = merged
    cleaned = '\n'.join(lines)
    escaped = str(escape(cleaned))
    # Hanging indent: lines starting with "(N)" / "N)" / "N." get a left-padded
    # block so wrapped lines align under the first word, not under the marker.
    def _wrap_hang(line):
        m = _re.match(r'^(\(\d+\)|\d+[.)])\s+(.*)$', line)
        if not m:
            return line
        marker, rest = m.group(1), m.group(2)
        return ('<span class="li-num">' + marker + '</span>'
                '<span class="li-txt">' + rest + '</span>')
    escaped_lines = [_wrap_hang(ln) for ln in escaped.split('\n')]
    escaped = '\n'.join(escaped_lines)
    tick_svg = (
        '<svg class="tick" viewBox="0 0 16 16" width="13" height="13" '
        'aria-hidden="true" style="vertical-align:-2px; display:inline-block;">'
        '<path d="M1.8 8.4 L4.5 8.0 L6.8 11.6 L13.0 1.6 L14.6 2.6 L7.6 14.0 L5.6 13.2 Z" '
        'fill="currentColor" stroke="currentColor" stroke-width="0.4" '
        'stroke-linejoin="round"/></svg>'
    )
    # Common tick glyphs: U+2713 (✓), U+2714 (✔), and U+F0FC (Wingdings ü→tick
    # — frequently leaks in from Word / PDF imports as a private-use codepoint).
    for _ch in ('\u2713', '\u2714', '\uf0fc', '\uf0fb'):
        escaped = escaped.replace(_ch, tick_svg)
    # Right-align any line that consists of marking-tail notation
    # (leading ticks +/- "(Any N)" / "(Accept …)") so it sits in the
    # bottom-right of the answer cell, DBE-style.
    out_lines = []
    _re_tail = _re.compile(
        r'^\s*(?:%s\s*)+(?:\([^)]+\))?\s*$' % _re.escape(tick_svg)
    )
    _re_anyparen = _re.compile(
        r'^\s*(?:%s\s*)*\((?:any\s+\w+|accept[^)]*|max[^)]*)\)\s*$' % _re.escape(tick_svg),
        _re.IGNORECASE,
    )
    for ln in escaped.split('\n'):
        if _re_tail.match(ln) or _re_anyparen.match(ln):
            out_lines.append('<span class="memo-tail">' + ln.strip() + '</span>')
        else:
            out_lines.append(ln)
    # Detect runs of "left | right" lines and replace them with a 2-column
    # comparison table (DBE compare-and-contrast pattern).
    final_lines = []
    i = 0
    while i < len(out_lines):
        ln = out_lines[i]
        # A table line must contain " | " AND not be wrapped in memo-tail / li-num spans.
        if (' | ' in ln
                and '<span class="memo-tail">' not in ln
                and '<span class="li-num">' not in ln):
            # Find the run.
            j = i
            while (j < len(out_lines)
                   and ' | ' in out_lines[j]
                   and '<span class="memo-tail">' not in out_lines[j]
                   and '<span class="li-num">' not in out_lines[j]):
                j += 1
            run = out_lines[i:j]
            if len(run) >= 2:
                rows_html = []
                for k, rln in enumerate(run):
                    parts = [p.strip() for p in rln.split(' | ', 1)]
                    if len(parts) != 2:
                        parts = [rln, '']
                    tag = 'th' if k == 0 else 'td'
                    rows_html.append(
                        '<tr><{0}>{1}</{0}><{0}>{2}</{0}></tr>'.format(tag, parts[0], parts[1])
                    )
                final_lines.append(
                    '<table class="memo-cmp"><tbody>' + ''.join(rows_html) + '</tbody></table>'
                )
                i = j
                continue
        final_lines.append(ln)
        i += 1
    out_lines = final_lines
    # Join with explicit <br> so block-level memo-tail spans don't get a
    # phantom blank line from CSS white-space: pre-line.
    html = '<br>'.join(out_lines)
    # Collapse a trailing <br> just before a memo-tail block (the block
    # element already starts a new line).
    html = _re.sub(r'<br>\s*(<span class="memo-tail">)', r'\1', html)
    # Strip <br> immediately around inline tables.
    html = _re.sub(r'<br>\s*(<table class="memo-cmp">)', r'\1', html)
    html = _re.sub(r'(</table>)\s*<br>', r'\1', html)
    return Markup(html)

@app.context_processor
def inject_globals():
    course_svg_map = {
        'Word Processing':                 {'svg': 'word.svg',       'bg': '#2B579A'},
        'Advanced Word Processing':        {'svg': 'word.svg',       'bg': '#2B579A'},
        'Integrated Document Handling':    {'svg': 'word.svg',       'bg': '#2B579A'},
        'Spreadsheets':                    {'svg': 'excel.svg',      'bg': '#217346'},
        'Advanced Spreadsheets':           {'svg': 'excel.svg',      'bg': '#217346'},
        'Advanced Spreadsheet Functions':  {'svg': 'excel.svg',      'bg': '#217346'},
        'Database Concepts':               {'svg': 'access.svg',     'bg': '#A4373A'},
        'Advanced Databases':              {'svg': 'access.svg',     'bg': '#A4373A'},
        'Presentations':                   {'svg': 'powerpoint.svg', 'bg': '#D24726'},
        'Advanced Presentations':          {'svg': 'powerpoint.svg', 'bg': '#D24726'},
        'Internet & Social Implications':  {'svg': 'ictsociety.svg', 'bg': '#5C2D91'},
        'ICT & Society':                   {'svg': 'ictsociety.svg', 'bg': '#5C2D91'},
        'Information Management':          {'svg': 'InformationManagement.svg', 'bg': '#051d40'},
        'Computer Hardware':               {'svg': 'ComputerHardware.svg', 'bg': '#051d40'},
        'Networks & Internet':             {'svg': 'NetWorksInternet.svg', 'bg': '#003FAB'},
    }
    return {'now': datetime.utcnow(), 'app_name': 'CAT CAPS LMS', 'course_svg_map': course_svg_map}

# =====================================================================
#  AUTH ROUTES
# =====================================================================
@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        user = User.query.filter((User.username==username)|(User.email==username)).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back!','success')
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.','danger')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        grade = request.form.get('grade', type=int)
        first_name = request.form.get('first_name','').strip()
        last_name = request.form.get('last_name','').strip()
        if User.query.filter_by(username=username).first():
            flash('Username already taken.','danger'); return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.','danger'); return render_template('register.html')
        user = User(username=username, email=email, first_name=first_name, last_name=last_name, grade=grade)
        user.set_password(password)
        db.session.add(user); db.session.commit()
        grade_obj = Grade.query.filter_by(number=grade).first()
        if grade_obj:
            for course in grade_obj.courses:
                db.session.add(Enrollment(user_id=user.id, course_id=course.id))
            db.session.commit()
        login_user(user)
        flash('Account created! You are enrolled in your grade courses.','success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); flash('Logged out.','info'); return redirect(url_for('index'))

# =====================================================================
#  MAIN ROUTES
# =====================================================================
@app.route('/')
def index():
    grades = Grade.query.order_by(Grade.number).all()
    stats = {
        'courses': Course.query.count(),
        'lessons': Lesson.query.count(),
        'quizzes': Quiz.query.count(),
        'questions': QuestionBankItem.query.count(),
        'past_papers': TeacherDocument.query.filter_by(paper_type='past_paper').count(),
        'students': User.query.filter_by(is_admin=False, is_teacher=False).count(),
    }
    return render_template('index.html', grades=grades, stats=stats)

@app.route('/grade/<int:grade_number>')
def grade_courses(grade_number):
    grade = Grade.query.filter_by(number=grade_number).first_or_404()
    courses = Course.query.filter_by(grade_id=grade.id).order_by(Course.order).all()
    enrollment_map = {}
    if current_user.is_authenticated:
        course_ids = [c.id for c in courses]
        enrollments = Enrollment.query.filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id.in_(course_ids),
        ).all() if course_ids else []
        # Refresh stored progress so the bars match the latest content totals.
        for e in enrollments:
            _recompute_progress(current_user.id, e.course)
        if enrollments:
            db.session.commit()
        for e in enrollments:
            enrollment_map[e.course_id] = e
    return render_template('grade_courses.html', grade=grade, courses=courses, enrollment_map=enrollment_map)

@app.route('/course/<course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_authenticated:
        return redirect(url_for('login', next=url_for('course_detail', course_id=course_id)))
    # Auto-enroll on first visit so we can jump straight into content.
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not enrollment and not current_user.is_admin:
        db.session.add(Enrollment(user_id=current_user.id, course_id=course_id))
        db.session.commit()
    # Send the user to the first lesson; fall back to the first quiz.
    first_lesson = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.order).first()
    if first_lesson:
        return redirect(url_for('lesson_view', lesson_id=first_lesson.id))
    first_quiz = Quiz.query.filter_by(course_id=course_id).order_by(Quiz.order).first()
    if first_quiz:
        return redirect(url_for('quiz_start', quiz_id=first_quiz.id))
    flash('This course has no content yet.', 'info')
    return redirect(url_for('grade_courses', grade_number=course.grade.number) if course.grade else url_for('index'))

@app.route('/course/<course_id>/enroll', methods=['POST'])
@login_required
def enroll_course(course_id):
    course = Course.query.get_or_404(course_id)
    if not Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first():
        db.session.add(Enrollment(user_id=current_user.id, course_id=course_id)); db.session.commit()
        flash(f'Enrolled in {course.title}!','success')
    return redirect(url_for('course_detail', course_id=course_id))

def _recompute_progress(user_id, course):
    """Course progress = (completed lessons + passed quizzes) / (lessons + quizzes)."""
    enrollment = Enrollment.query.filter_by(user_id=user_id, course_id=course.id).first()
    if not enrollment:
        return
    lesson_ids = [l.id for l in course.lessons]
    quiz_ids = [q.id for q in course.quizzes]
    total = len(lesson_ids) + len(quiz_ids)
    if total == 0:
        enrollment.progress = 0
        return
    done_lessons = LessonCompletion.query.filter(
        LessonCompletion.user_id == user_id,
        LessonCompletion.lesson_id.in_(lesson_ids)).count() if lesson_ids else 0
    passed_quiz_ids = {a.quiz_id for a in QuizAttempt.query.filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.quiz_id.in_(quiz_ids),
        QuizAttempt.passed == True).all()} if quiz_ids else set()
    enrollment.progress = ((done_lessons + len(passed_quiz_ids)) / total) * 100


@app.route('/lesson/<lesson_id>')
@login_required
def lesson_view(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not enrollment:
        # Auto-enrol on first lesson view so progress is tracked for everyone
        # (including admins / teachers who explore content).
        enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
        db.session.add(enrollment); db.session.commit()
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order).all()
    idx = next((i for i,l in enumerate(lessons) if l.id==lesson_id), 0)
    prev_lesson = lessons[idx-1] if idx>0 else None
    next_lesson = lessons[idx+1] if idx<len(lessons)-1 else None
    completion = LessonCompletion.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    completed_ids = {c.lesson_id for c in LessonCompletion.query.filter_by(user_id=current_user.id).filter(LessonCompletion.lesson_id.in_([l.id for l in lessons])).all()}
    quizzes = Quiz.query.filter_by(course_id=course.id).order_by(Quiz.order).all()
    passed_quiz_ids = {a.quiz_id for a in QuizAttempt.query.filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.quiz_id.in_([q.id for q in quizzes]),
        QuizAttempt.passed == True).all()} if quizzes else set()
    attempted_quiz_ids = {a.quiz_id for a in QuizAttempt.query.filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.quiz_id.in_([q.id for q in quizzes])).all()} if quizzes else set()
    return render_template('lesson.html', lesson=lesson, course=course, prev_lesson=prev_lesson, next_lesson=next_lesson, is_completed=completion is not None, lessons=lessons, current_idx=idx, completed_ids=completed_ids, quizzes=quizzes, enrollment=enrollment, passed_quiz_ids=passed_quiz_ids, attempted_quiz_ids=attempted_quiz_ids)

@app.route('/lesson/<lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    # Make sure an enrollment exists so progress is tracked even for admins.
    if not Enrollment.query.filter_by(user_id=current_user.id, course_id=lesson.course_id).first():
        db.session.add(Enrollment(user_id=current_user.id, course_id=lesson.course_id))
        db.session.flush()
    if not LessonCompletion.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first():
        db.session.add(LessonCompletion(user_id=current_user.id, lesson_id=lesson_id))
        db.session.flush()
        _recompute_progress(current_user.id, lesson.course)
        db.session.commit(); flash('Lesson completed!','success')
    nxt = Lesson.query.filter(Lesson.course_id==lesson.course_id, Lesson.order>lesson.order).order_by(Lesson.order).first()
    return redirect(url_for('lesson_view', lesson_id=nxt.id) if nxt else url_for('course_detail', course_id=lesson.course_id))

# =====================================================================
#  QUIZ / EXAM ROUTES
# =====================================================================
@app.route('/quiz/<quiz_id>')
@login_required
def quiz_start(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=quiz.course_id).first()
    if not enrollment and not current_user.is_admin:
        flash('Enroll in this course first.','warning'); return redirect(url_for('course_detail', course_id=quiz.course_id))
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).order_by(QuizAttempt.percentage.desc()).all()
    best_attempt = attempts[0] if attempts else None
    return render_template('quiz_start.html', quiz=quiz, best_attempt=best_attempt, attempts=attempts)

@app.route('/quiz/<quiz_id>/take')
@login_required
def quiz_take(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    raw_questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    import random
    questions = []
    for q in raw_questions:
        qobj = type('Q', (), {
            'id': q.id, 'question_text': q.question_text, 'question_type': q.question_type,
            'points': q.points, 'order': q.order,
        })()
        opts = q.get_options()
        if q.question_type == 'drag_drop':
            shuffled = list(opts)
            random.shuffle(shuffled)
            qobj.options = shuffled
        elif q.question_type == 'match_columns':
            qobj.options = opts
            if isinstance(opts, dict) and 'column_b' in opts:
                shuffled_b = list(opts['column_b'])
                random.shuffle(shuffled_b)
                qobj.options = {'column_a': opts['column_a'], 'column_b': shuffled_b}
        elif q.question_type == 'short_answer':
            qobj.options = {}  # no choices needed
        else:
            qobj.options = opts
        questions.append(qobj)
    return render_template('quiz_take.html', quiz=quiz, questions=questions)

@app.route('/api/quiz/<quiz_id>/submit', methods=['POST'])
@login_required
def api_quiz_submit(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()
    user_answers = data.get('answers', {})
    # Make sure an enrollment exists so quiz pass/fail counts toward progress.
    if not Enrollment.query.filter_by(user_id=current_user.id, course_id=quiz.course_id).first():
        db.session.add(Enrollment(user_id=current_user.id, course_id=quiz.course_id))
        db.session.flush()
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    score = 0; total_points = 0; correct_count = 0; review = []
    for q in questions:
        total_points += q.points
        user_ans = user_answers.get(q.id, None)
        correct = q.get_correct_answer()
        is_correct = False
        if q.question_type == 'multiple_choice':
            is_correct = (user_ans == correct)
        elif q.question_type == 'true_false':
            is_correct = (str(user_ans).strip().lower() == str(correct).strip().lower()) if user_ans is not None else False
        elif q.question_type == 'drag_drop':
            is_correct = (user_ans == correct) if isinstance(user_ans, list) else False
        elif q.question_type == 'match_columns':
            is_correct = (user_ans == correct) if isinstance(user_ans, dict) else False
        elif q.question_type == 'short_answer':
            opts = q.get_options()
            kws = opts.get('keywords', []) if isinstance(opts, dict) else []
            min_ratio = opts.get('min_ratio', 0.6) if isinstance(opts, dict) else 0.6
            is_correct, _ratio, _fb = grade_short_answer(user_ans or '', str(correct), kws, min_ratio)
        if is_correct:
            score += q.points
            correct_count += 1
    pct = (score/total_points*100) if total_points>0 else 0
    passed = pct >= quiz.pass_percentage
    attempt = QuizAttempt(user_id=current_user.id, quiz_id=quiz_id, score=round(pct, 1),
        total_points=total_points, percentage=round(pct,1), passed=passed,
        answers=json.dumps(user_answers), completed_at=datetime.utcnow(),
        time_taken_seconds=data.get('time_taken',0))
    db.session.add(attempt)
    db.session.flush()
    _recompute_progress(current_user.id, quiz.course)
    db.session.commit()
    return jsonify({'redirect': url_for('quiz_result', attempt_id=attempt.id)})

@app.route('/quiz/result/<attempt_id>')
@login_required
def quiz_result(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != current_user.id and not current_user.is_admin: abort(403)
    quiz = attempt.quiz
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order).all()
    user_answers = json.loads(attempt.answers) if attempt.answers else {}
    # Build review list and counts
    review = []
    correct_count = 0
    for q in questions:
        user_ans = user_answers.get(q.id, None)
        correct = q.get_correct_answer()
        is_correct = False
        if q.question_type == 'multiple_choice':
            is_correct = (user_ans == correct)
            ua_display = user_ans or 'No answer'
            ca_display = correct
            sa_feedback = None
        elif q.question_type == 'true_false':
            is_correct = (str(user_ans).strip().lower() == str(correct).strip().lower()) if user_ans is not None else False
            ua_display = user_ans if user_ans is not None else 'No answer'
            ca_display = correct
            sa_feedback = None
        elif q.question_type == 'drag_drop':
            is_correct = (user_ans == correct) if isinstance(user_ans, list) else False
            ua_display = ' → '.join(user_ans) if isinstance(user_ans, list) else 'No answer'
            ca_display = ' → '.join(correct) if isinstance(correct, list) else str(correct)
            sa_feedback = None
        elif q.question_type == 'match_columns':
            is_correct = (user_ans == correct) if isinstance(user_ans, dict) else False
            ua_display = ', '.join(f'{k}→{v}' for k,v in user_ans.items()) if isinstance(user_ans, dict) else 'No answer'
            ca_display = ', '.join(f'{k}→{v}' for k,v in correct.items()) if isinstance(correct, dict) else str(correct)
            sa_feedback = None
        elif q.question_type == 'short_answer':
            opts = q.get_options()
            kws = opts.get('keywords', []) if isinstance(opts, dict) else []
            min_ratio = opts.get('min_ratio', 0.6) if isinstance(opts, dict) else 0.6
            is_correct, score_ratio, sa_feedback = grade_short_answer(user_ans or '', str(correct), kws, min_ratio)
            ua_display = user_ans or 'No answer'
            ca_display = str(correct)
            sa_feedback = f'{sa_feedback} (match score: {int(score_ratio*100)}%)'
        else:
            ua_display = str(user_ans or 'No answer')
            ca_display = str(correct)
            sa_feedback = None
        if is_correct:
            correct_count += 1
        review.append({'question': q.question_text, 'type': q.question_type, 'correct': is_correct,
                       'user_answer': ua_display, 'correct_answer': ca_display, 'feedback': sa_feedback})
    # Patch attempt display values
    attempt.correct_answers = correct_count
    attempt.total_questions = len(questions)
    return render_template('quiz_result.html', attempt=attempt, quiz=quiz, review=review)

@app.route('/dashboard')
@login_required
def dashboard():
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    # Always refresh per-course progress so the bars reflect any newly-added
    # lessons or quizzes (denominator changes when content is seeded).
    if enrollments:
        for e in enrollments:
            _recompute_progress(current_user.id, e.course)
        db.session.commit()
    # Unique lessons completed (the LessonCompletion table is per-lesson per-user;
    # use distinct lesson_id so any duplicate rows don't double-count).
    completed_lessons = db.session.query(LessonCompletion.lesson_id).filter_by(
        user_id=current_user.id).distinct().count()
    quiz_attempts = QuizAttempt.query.filter_by(user_id=current_user.id).order_by(
        QuizAttempt.completed_at.desc()).all()
    # Build best-attempt-per-quiz so retakes don't skew stats.
    best_by_quiz = {}
    for a in quiz_attempts:
        cur = best_by_quiz.get(a.quiz_id)
        if cur is None or a.percentage > cur.percentage:
            best_by_quiz[a.quiz_id] = a
    quizzes_taken = len(best_by_quiz)                           # unique quizzes attempted
    passed_quizzes = sum(1 for a in best_by_quiz.values() if a.passed)
    avg_score = (sum(a.percentage for a in best_by_quiz.values()) / len(best_by_quiz)
                 ) if best_by_quiz else 0
    return render_template('dashboard.html',
        enrollments=enrollments,
        completed_lessons=completed_lessons,
        quiz_attempts=quiz_attempts,
        quizzes_taken=quizzes_taken,
        passed_quizzes=passed_quizzes,
        avg_score=avg_score,
    )

# =====================================================================
#  TEACHER ROUTES
# =====================================================================
from werkzeug.utils import secure_filename

TEACHER_DOC_EXTS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                    'zip', 'rar', '7z', 'mdb', 'accdb', 'csv', 'txt'}
TEACHER_LOGO_EXTS = {'png', 'jpg', 'jpeg', 'svg', 'webp', 'jfif', 'gif', 'bmp', 'avif'}


def teacher_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.path))
        if not (current_user.is_teacher or current_user.is_admin):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _ext(fname):
    return fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''


def _save_upload(file_storage, subdir, allowed):
    if not file_storage or not file_storage.filename:
        return None, 0
    ext = _ext(file_storage.filename)
    if ext not in allowed:
        return None, 0
    name = secure_filename(file_storage.filename)
    base, _ = os.path.splitext(name)
    unique = f"{base}_{uuid.uuid4().hex[:8]}.{ext}"
    folder = os.path.join('static', 'uploads', subdir)
    os.makedirs(folder, exist_ok=True)
    abs_path = os.path.join(folder, unique)
    file_storage.save(abs_path)
    rel = f"uploads/{subdir}/{unique}"
    return rel, os.path.getsize(abs_path)


@app.route('/teacher')
@teacher_required
def teacher_dashboard():
    docs = TeacherDocument.query.order_by(TeacherDocument.uploaded_at.desc()).limit(6).all()
    docs_count = TeacherDocument.query.count()
    bank_count = QuestionBankItem.query.filter_by(owner_id=current_user.id).count()
    paper_count = GeneratedPaper.query.filter_by(owner_id=current_user.id).count()
    upcoming = (TeacherSchedule.query
                .filter_by(owner_id=current_user.id)
                .filter(TeacherSchedule.start_date >= datetime.utcnow().date())
                .order_by(TeacherSchedule.start_date).limit(5).all())
    upcoming_count = (TeacherSchedule.query
                .filter_by(owner_id=current_user.id)
                .filter(TeacherSchedule.start_date >= datetime.utcnow().date())
                .count())
    return render_template('teacher/dashboard.html',
        docs=docs, docs_count=docs_count, bank_count=bank_count, paper_count=paper_count,
        upcoming=upcoming, upcoming_count=upcoming_count)


# ---------- Past papers / documents -------------------------------------
@app.route('/teacher/papers')
@teacher_required
def teacher_papers():
    grade = request.args.get('grade', type=int)
    ptype = request.args.get('type', '')
    year  = request.args.get('year', type=int)
    pnum  = request.args.get('paper', '').strip()
    q = TeacherDocument.query
    if grade:
        q = q.filter_by(grade=grade)
    if ptype:
        q = q.filter_by(paper_type=ptype)
    if year:
        q = q.filter_by(paper_year=year)
    if pnum:
        q = q.filter_by(paper_number=pnum)
    docs = q.order_by(TeacherDocument.paper_year.desc().nullslast(),
                      TeacherDocument.uploaded_at.desc()).all()
    # Distinct year list for the dropdown (newest first, exclude None)
    years = [y for (y,) in db.session.query(TeacherDocument.paper_year)
                              .filter(TeacherDocument.paper_year.isnot(None))
                              .distinct()
                              .order_by(TeacherDocument.paper_year.desc()).all()]
    return render_template('teacher/papers.html', docs=docs, grade=grade,
                           ptype=ptype, year=year, pnum=pnum, years=years)


@app.route('/teacher/papers/upload', methods=['GET', 'POST'])
@teacher_required
def teacher_paper_upload():
    if request.method == 'POST':
        f = request.files.get('file')
        rel, size = _save_upload(f, 'papers', TEACHER_DOC_EXTS)
        if not rel:
            flash('Please choose a valid file (PDF, Word, Excel, ZIP, etc.).', 'danger')
            return redirect(url_for('teacher_paper_upload'))
        doc = TeacherDocument(
            title=request.form.get('title', '').strip() or f.filename,
            description=request.form.get('description', '').strip(),
            grade=request.form.get('grade', type=int),
            subject=request.form.get('subject', 'CAT').strip() or 'CAT',
            paper_year=request.form.get('paper_year', type=int),
            paper_type=request.form.get('paper_type', 'past_paper'),
            paper_number=request.form.get('paper_number', '').strip(),
            file_path=rel, file_size=size, uploaded_by=current_user.id,
        )
        db.session.add(doc); db.session.commit()
        flash('Document uploaded.', 'success')
        return redirect(url_for('teacher_papers'))
    return render_template('teacher/paper_upload.html')


@app.route('/teacher/papers/<doc_id>/download')
@teacher_required
def teacher_paper_download(doc_id):
    from flask import send_from_directory
    doc = TeacherDocument.query.get_or_404(doc_id)
    doc.download_count = (doc.download_count or 0) + 1
    db.session.commit()
    folder = os.path.join('static', os.path.dirname(doc.file_path))
    return send_from_directory(folder, os.path.basename(doc.file_path),
                               as_attachment=True,
                               download_name=os.path.basename(doc.file_path))


@app.route('/teacher/papers/<doc_id>/delete', methods=['POST'])
@teacher_required
def teacher_paper_delete(doc_id):
    doc = TeacherDocument.query.get_or_404(doc_id)
    if doc.uploaded_by != current_user.id and not current_user.is_admin:
        abort(403)
    try:
        os.remove(os.path.join('static', doc.file_path))
    except OSError:
        pass
    db.session.delete(doc); db.session.commit()
    flash('Document deleted.', 'info')
    return redirect(url_for('teacher_papers'))


# ---------- Question bank -----------------------------------------------
@app.route('/teacher/bank')
@teacher_required
def teacher_bank():
    grade = request.args.get('grade', type=int)
    topic_list = [t.strip() for t in request.args.getlist('topic') if t.strip()]
    diff = request.args.get('difficulty', '').strip()
    paper = request.args.get('paper', '').strip()
    server_filter = request.args.get('server_filter') == '1'

    base_q = QuestionBankItem.query.filter(
        (QuestionBankItem.owner_id == current_user.id) |
        (QuestionBankItem.is_shared == True))

    q = base_q
    if server_filter:
        if grade:
            q = q.filter_by(grade=grade)
        if topic_list:
            q = q.filter(QuestionBankItem.topic.in_(topic_list))
        if diff:
            q = q.filter_by(difficulty=diff)
        if paper:
            # Match the paper label as a whole tag entry within the comma-separated tags string
            like_a = f"%, {paper},%"      # middle position
            like_b = f"{paper},%"          # first position
            like_c = f"%, {paper}"        # last position
            like_d = paper                  # only tag
            q = q.filter(db.or_(
                QuestionBankItem.tags.like(like_a),
                QuestionBankItem.tags.like(like_b),
                QuestionBankItem.tags.like(like_c),
                QuestionBankItem.tags == like_d,
            ))
    items = q.order_by(QuestionBankItem.created_at.desc()).all()

    # Build dropdown lists from full bank
    all_items = base_q.order_by(QuestionBankItem.created_at.desc()).all()
    topics = sorted({i.topic for i in all_items if i.topic})

    # Paper labels are stored as tags like "CAT P2 May/June 2025" or "CAT P2 Nov 2022"
    paper_re = re.compile(r"^[A-Z]{2,5}\s+P\d+\s+(May/June|Nov|November|March|Sept|September|Feb|February)\s+\d{4}$")
    paper_set = set()
    for i in all_items:
        if not i.tags:
            continue
        for tag in (t.strip() for t in i.tags.split(',')):
            if paper_re.match(tag):
                paper_set.add(tag)

    def _paper_sort_key(label):
        # Sort newest first: extract year then season weight
        m = re.search(r"(\d{4})$", label)
        year = int(m.group(1)) if m else 0
        season = 1 if 'Nov' in label else 0  # Nov after May/June within same year
        return (-year, -season, label)
    papers = sorted(paper_set, key=_paper_sort_key)

    return render_template('teacher/bank.html', items=items, topics=topics,
                           papers=papers, grade=grade,
                           selected_topics=topic_list, diff=diff, paper=paper)


@app.route('/teacher/bank/new', methods=['GET', 'POST'])
@app.route('/teacher/bank/<item_id>/edit', methods=['GET', 'POST'])
@teacher_required
def teacher_bank_edit(item_id=None):
    item = QuestionBankItem.query.get_or_404(item_id) if item_id else None
    if item and item.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    if request.method == 'POST':
        if not item:
            item = QuestionBankItem(owner_id=current_user.id)
            db.session.add(item)
        item.grade = request.form.get('grade', type=int) or 12
        item.topic = request.form.get('topic', '').strip()
        item.subtopic = request.form.get('subtopic', '').strip()
        item.difficulty = request.form.get('difficulty', 'medium')
        item.question_type = request.form.get('question_type', 'short_answer')
        item.question_text = request.form.get('question_text', '').strip()
        # Normalize Wingdings PUA tick chars (\uF0FC / \uF0FB) and U+2714 to U+2713
        # so they render as a real check mark in any font (no missing-glyph boxes).
        _ans_raw = request.form.get('answer_text', '').strip()
        item.answer_text = (_ans_raw
                            .replace('\uf0fc', '\u2713')
                            .replace('\uf0fb', '\u2713')
                            .replace('\u2714', '\u2713'))
        # Allow 0 marks for scenario stems (intro text with no marks badge).
        marks_raw = request.form.get('marks', '').strip()
        try:
            item.marks = max(0, int(marks_raw)) if marks_raw != '' else 1
        except (TypeError, ValueError):
            item.marks = 1
        item.tags = request.form.get('tags', '').strip()
        item.is_shared = bool(request.form.get('is_shared'))
        # Optional figure / diagram for the question
        if request.form.get('image_clear') == '1':
            item.image_path = ''
        img = request.files.get('image')
        if img and img.filename:
            rel, _ = _save_upload(img, 'questions', TEACHER_LOGO_EXTS)
            if rel:
                item.image_path = rel
        if not item.question_text:
            flash('Question text is required.', 'danger')
        else:
            db.session.commit()
            flash('Question saved.', 'success')
            nxt = request.form.get('next') or request.args.get('next') or ''
            # Only allow same-origin relative redirects.
            if nxt and nxt.startswith('/') and not nxt.startswith('//'):
                return redirect(nxt)
            return redirect(url_for('teacher_bank'))
    return render_template('teacher/bank_edit.html', item=item)


@app.route('/teacher/bank/<item_id>/delete', methods=['POST'])
@teacher_required
def teacher_bank_delete(item_id):
    item = QuestionBankItem.query.get_or_404(item_id)
    if item.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(item); db.session.commit()
    flash('Question deleted.', 'info')
    return redirect(url_for('teacher_bank'))


# ---------- Paper generator ---------------------------------------------
@app.route('/teacher/generator')
@teacher_required
def teacher_papers_generated():
    papers = (GeneratedPaper.query.filter_by(owner_id=current_user.id)
              .order_by(GeneratedPaper.created_at.desc()).all())
    return render_template('teacher/generator_list.html', papers=papers)


@app.route('/teacher/generator/new', methods=['GET', 'POST'])
@app.route('/teacher/generator/<paper_id>/edit', methods=['GET', 'POST'])
@teacher_required
def teacher_paper_edit(paper_id=None):
    # For a brand-new paper on GET, create a blank record immediately so the
    # split-screen editor (which requires a paper_id for the preview pane) is
    # always shown in full. Keep rendering in the same request to avoid an
    # extra browser hop before the editor opens.
    if request.method == 'GET' and paper_id is None:
        paper = GeneratedPaper(
            owner_id=current_user.id,
            title='',
            subject='Computer Applications Technology',
            grade=12,
            duration_minutes=180,
            total_marks=150,
            sections='[]',
        )
        db.session.add(paper)
        db.session.commit()
        paper_id = paper.id

    paper = GeneratedPaper.query.get_or_404(paper_id) if paper_id else None
    if paper and paper.owner_id != current_user.id and not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        if not paper:
            paper = GeneratedPaper(owner_id=current_user.id)
            db.session.add(paper)
        logo_upload_error = None
        paper.title = request.form.get('title', 'Examination Paper').strip()
        paper.school_name = request.form.get('school_name', '').strip()
        paper.subject = request.form.get('subject', 'Computer Applications Technology').strip()
        paper.grade = request.form.get('grade', type=int) or 12
        date_str = request.form.get('exam_date', '').strip()
        paper.exam_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        paper.duration_minutes = request.form.get('duration_minutes', type=int) or 180
        paper.total_marks = request.form.get('total_marks', type=int) or 150
        paper.examiner = request.form.get('examiner', '').strip()
        paper.moderator = request.form.get('moderator', '').strip()
        paper.instructions = request.form.get('instructions', '').strip()
        # Cover / header / footer customisation
        paper.paper_number     = request.form.get('paper_number', '').strip()
        paper.cover_authority  = request.form.get('cover_authority', '').strip()
        paper.cover_subtitle   = request.form.get('cover_subtitle', '').strip()
        paper.header_left      = request.form.get('header_left', '').strip()
        paper.header_right     = request.form.get('header_right', '').strip()
        paper.sub_header       = request.form.get('sub_header', '').strip()
        paper.footer_left      = request.form.get('footer_left', 'Copyright reserved').strip()
        paper.footer_right     = request.form.get('footer_right', 'Please turn over').strip()
        paper.footer_center    = request.form.get('footer_center', '').strip()
        paper.memo_title       = request.form.get('memo_title', 'MARKING GUIDELINES').strip()
        paper.cover_extra_note = request.form.get('cover_extra_note', '').strip()
        # logo upload / clear
        if request.form.get('logo_clear') == '1':
            paper.logo_path = ''
        logo = request.files.get('logo')
        if logo and logo.filename:
            rel, _ = _save_upload(logo, 'logos', TEACHER_LOGO_EXTS)
            if rel:
                paper.logo_path = rel
            else:
                logo_upload_error = 'Unsupported logo format. Use PNG, JPG, JPEG, SVG, WEBP, JFIF, GIF, BMP, or AVIF.'
        # sections JSON
        try:
            paper.sections = request.form.get('sections_json', '[]')
            json.loads(paper.sections)  # validate
        except Exception:
            paper.sections = '[]'
        db.session.commit()
        if request.form.get('__autosave') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if logo_upload_error:
                return (logo_upload_error, 415)
            return ('', 204)
        if logo_upload_error:
            flash(logo_upload_error, 'warning')
        else:
            flash('Paper saved.', 'success')
        return redirect(url_for('teacher_paper_edit', paper_id=paper.id))

    bank = (QuestionBankItem.query
            .filter((QuestionBankItem.owner_id == current_user.id) |
                    (QuestionBankItem.is_shared == True))
            .order_by(QuestionBankItem.topic, QuestionBankItem.created_at.desc()).all())
    # CAPS-aligned scaffolds: rendered as preset buttons in the editor.
    caps_templates = {
        key: {
            'label': tpl['label'],
            'subject': tpl.get('subject', ''),
            'paper_number': tpl.get('paper_number', ''),
            'grade': tpl.get('grade'),
            'duration_minutes': tpl.get('duration_minutes'),
            'total_marks': tpl.get('total_marks'),
            'instructions': tpl.get('instructions', ''),
            'sections': flatten_template(key),
        }
        for key, tpl in CAPS_PAPER_TEMPLATES.items()
    }
    return render_template('teacher/generator_edit.html',
                           paper=paper, bank=bank,
                           caps_templates=caps_templates,
                           caps_guidelines=CAPS_GUIDELINES,
                           instruction_library=INSTRUCTION_LIBRARY)


@app.route('/teacher/generator/<paper_id>/delete', methods=['POST'])
@teacher_required
def teacher_paper_remove(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if paper.owner_id != current_user.id and not current_user.is_admin: abort(403)
    db.session.delete(paper); db.session.commit()
    flash('Paper deleted.', 'info')
    return redirect(url_for('teacher_papers_generated'))


@app.route('/teacher/generator/<paper_id>/add_stem', methods=['POST'])
@teacher_required
def teacher_paper_add_stem(paper_id):
    """Create a 0-mark scenario-stem QuestionBankItem (text + optional image)
    and return its id/text/image_path as JSON for the editor to inject into
    the current section. The stem is owned by the current user but stays
    private (is_shared=False) so it doesn't pollute the shared bank.
    """
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if paper.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    text = (request.form.get('text') or '').strip()
    if not text:
        return ({'error': 'Stem text is required.'}, 400)
    img = request.files.get('image')
    image_rel = ''
    if img and img.filename:
        image_rel, _ = _save_upload(img, 'questions', TEACHER_LOGO_EXTS)
        if not image_rel:
            return ({'error': 'Unsupported image format. Use PNG, JPG, JPEG, SVG, WEBP, GIF, BMP, or AVIF.'}, 415)
    item = QuestionBankItem(
        owner_id=current_user.id,
        grade=paper.grade or 12,
        topic='Stem',
        subtopic='',
        difficulty='medium',
        question_type='stem',
        question_text=text,
        answer_text='',
        marks=0,
        tags='stem',
        is_shared=False,
        image_path=image_rel or '',
    )
    db.session.add(item)
    db.session.commit()
    return ({
        'id': item.id,
        'text': item.question_text,
        'marks': 0,
        'image_path': item.image_path,
        'type': 'stem',
        'topic': 'Stem',
    }, 200)


def _is_matching_question(q):
    """Return True if q is a match_columns type question."""
    return (getattr(q, 'question_type', '') or '').lower() == 'match_columns' or \
           bool(_MATCH_INTRO_RE.match((getattr(q, 'question_text', '') or '').lstrip()))


def _split_mcq_matching(qs, sec_title, sec_instructions):
    """If a section contains both MCQ and matching questions, split into
    separate sub-sections: MCQ first, then matching.  Any non-MCQ/non-matching
    questions go into a 'rest' group after matching.
    Returns a list of section dicts (may be length 1 if no split needed)."""
    mcq_qs, match_qs, rest_qs = [], [], []
    for q in qs:
        if _is_matching_question(q):
            match_qs.append(q)
        elif (getattr(q, 'question_type', '') or '').lower() in ('mcq', 'multiple_choice'):
            mcq_qs.append(q)
        else:
            rest_qs.append(q)

    # Only split when both groups are non-empty.
    if not (mcq_qs and match_qs):
        return None  # caller will use the original single section

    result = []
    if mcq_qs:
        result.append({'title': sec_title, 'sub_title': 'MULTIPLE-CHOICE',
                       'instructions': sec_instructions,
                       'questions': mcq_qs,
                       'marks': sum(q.marks or 0 for q in mcq_qs),
                       'is_tf': False, 'is_split_child': True})
    if match_qs:
        result.append({'title': sec_title, 'sub_title': 'MATCHING ITEMS',
                       'instructions': '',
                       'questions': match_qs,
                       'marks': sum(q.marks or 0 for q in match_qs),
                       'is_tf': False, 'is_split_child': True})
    if rest_qs:
        result.append({'title': sec_title, 'sub_title': '',
                       'instructions': '',
                       'questions': rest_qs,
                       'marks': sum(q.marks or 0 for q in rest_qs),
                       'is_tf': False, 'is_split_child': True})
    return result


def _build_paper_context(paper, with_memo=False):
    """Resolve question_ids in sections to full question objects."""
    # Pre-compiled patterns used to scrub stale tail noise from imported
    # answer_text (per-mark notation, section totals, leaked next-question
    # heading). Same shape as the cleaner that already runs on question_text.
    _RE_NEXT_Q_HEAD = re.compile(
        r'\s*(?:\(\d+\)\s*)?\[\d+\]\s*QUESTION\s+\d+\s*:\s*[A-Z][A-Z0-9 ()/\-&]+\s*$',
        re.IGNORECASE,
    )
    _RE_TRAIL_BRACKET = re.compile(r'\s*\[\d+\]\s*$')
    _RE_TRAIL_MARK_DIGITS = re.compile(r'\s+\d+(?:\s+\d+)?\s*$')

    def _clean_memo_answer(q):
        """Strip imported tail noise from `q.answer_text` and split into
        (heading, body): the FIRST non-blank line becomes the italic memo
        heading (DBE-style topical phrase, e.g. "TWO limitations for
        customers using QR codes"), the rest is the body. Falls back to
        question_text if answer_text has no separate heading line."""
        txt = (getattr(q, 'answer_text', '') or '').strip()
        if not txt:
            qt = (getattr(q, 'question_text', '') or '').strip()
            return (qt, '')
        # Iteratively peel off trailing junk.
        for _ in range(4):
            new = _RE_NEXT_Q_HEAD.sub('', txt)
            new = _RE_TRAIL_BRACKET.sub('', new)
            new = _RE_TRAIL_MARK_DIGITS.sub('', new)
            new = new.rstrip()
            if new == txt:
                break
            txt = new
        lines = [ln for ln in txt.split('\n')]
        # Drop leading blank lines, then split off the first non-blank as heading.
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            return ((getattr(q, 'question_text', '') or '').strip(), '')
        heading = lines[0].strip()
        body_lines = lines[1:]
        # Trim leading blanks of body too.
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        body = '\n'.join(body_lines).rstrip()
        # If the heading contains a bullet/answer marker (starts with "(1)",
        # a digit, or a tick), the import had no separate heading line — fall
        # back to question_text and treat the whole answer as body.
        if re.match(r'^\s*(?:\(\d+\)|\d+[.)]|[\u2713\u2714\uF0FB\uF0FC])', heading):
            qt = (getattr(q, 'question_text', '') or '').strip()
            body = '\n'.join(lines).rstrip()
            heading = qt
        return (heading, body)

    sections = json.loads(paper.sections or '[]')
    resolved = []
    grand_marks = 0
    # Track a global question number that increments per group across all sections.
    global_qn = 0
    for sec in sections:
        qs = []
        for qid in sec.get('question_ids', []):
            q = QuestionBankItem.query.get(qid)
            if q:
                qs.append(q); grand_marks += q.marks or 0
        # Consolidate consecutive matching items so the shared Column B options
        # block is only rendered once.
        _annotate_matching_runs(qs)
        # Build per-section question groups based on the editor's `splits` array.
        # Each split index marks the start of a new numbered Question (5, 6, ...)
        # within the same section letter. Default = single group starting at 0.
        raw_splits = sec.get('splits') or [0]
        try:
            splits = sorted({int(s) for s in raw_splits if isinstance(s, (int, float)) and 0 <= int(s) <= len(qs)})
        except Exception:
            splits = [0]
        if not splits or splits[0] != 0:
            splits = [0] + [s for s in splits if s != 0]
        # Per-Question titles (parallel to splits) and 3-level sub-item indices.
        raw_qtitles = sec.get('qtitles') or []
        try:
            qtitles = [str(t or '') for t in raw_qtitles]
        except Exception:
            qtitles = []
        raw_qinstr = sec.get('qinstructions') or []
        try:
            qinstr = [str(t or '') for t in raw_qinstr]
        except Exception:
            qinstr = []
        raw_subitems = sec.get('subitems') or []
        try:
            split_set = set(splits)
            subitems_set = {int(s) for s in raw_subitems
                            if isinstance(s, (int, float)) and 0 <= int(s) < len(qs)
                            and int(s) not in split_set}
        except Exception:
            subitems_set = set()
        qgroups = []
        for gi, start in enumerate(splits):
            end = splits[gi + 1] if gi + 1 < len(splits) else len(qs)
            global_qn += 1
            group_qs = qs[start:end]
            # Compute per-item printed labels (2 or 3 levels) using subitems.
            labels = []
            top_k = 0
            child_j = 0
            for offset in range(end - start):
                qi = start + offset
                is_child = (qi != start) and (qi in subitems_set)
                if is_child:
                    child_j += 1
                    labels.append('{}.{}.{}'.format(global_qn, top_k, child_j))
                else:
                    top_k += 1
                    child_j = 0
                    labels.append('{}.{}'.format(global_qn, top_k))
            grp_title = qtitles[gi] if gi < len(qtitles) else ''
            grp_instr = qinstr[gi] if gi < len(qinstr) else ''
            # Detect TF for THIS group (so the TF intro + examples render only
            # on the TF Question, not on the section's first Question).
            grp_is_tf = _is_true_false_section(grp_title, group_qs)
            # Pre-compute memo row metadata so the template doesn't have to
            # juggle rowspans for stem→sub-item groupings. Stem rows are
            # SKIPPED in the memo (they belong only in the printed paper).
            # Each surviving row has:
            #   sub, depth, q, group_first, group_rowspan, group_total, in_group
            memo_rows = []
            # Build a parallel list of (label, q) excluding stems but keeping
            # the depth structure (a stem becomes the parent of the run that
            # immediately follows it in the editor's data model).
            i = 0
            n = len(group_qs)
            while i < n:
                lbl = labels[i]
                depth = lbl.count('.') + 1
                q = group_qs[i]
                qt_lower = (getattr(q, 'question_type', '') or '').lower()
                topic_lower = (getattr(q, 'topic', '') or '').lower()
                is_stem = (qt_lower == 'stem') or (topic_lower == 'stem')
                if is_stem:
                    # Skip the stem row entirely. The sub-items that follow
                    # are still in the labels list with depth-3 numbering and
                    # will be picked up by the chain handler below.
                    i += 1
                    continue
                if depth == 3:
                    # Open a chain of consecutive depth-3 rows.
                    chain_start = i
                    chain_end = i
                    while chain_end + 1 < n and (labels[chain_end + 1].count('.') + 1) == 3:
                        # Skip stems hidden inside the chain (defensive).
                        nxt_q = group_qs[chain_end + 1]
                        nxt_is_stem = ((getattr(nxt_q, 'question_type', '') or '').lower() == 'stem'
                                       or (getattr(nxt_q, 'topic', '') or '').lower() == 'stem')
                        if nxt_is_stem:
                            break
                        chain_end += 1
                    chain_total = sum((group_qs[t].marks or 0) for t in range(chain_start, chain_end + 1))
                    chain_len = chain_end - chain_start + 1
                    for t in range(chain_start, chain_end + 1):
                        _h, _b = _clean_memo_answer(group_qs[t])
                        memo_rows.append({
                            'sub': labels[t], 'depth': 3, 'q': group_qs[t],
                            'clean_heading': _h, 'clean_body': _b,
                            'group_first': (t == chain_start),
                            'group_rowspan': chain_len if t == chain_start else 0,
                            'group_total': chain_total if t == chain_start else 0,
                            'in_group': True,
                        })
                    i = chain_end + 1
                    continue
                # Plain depth-2 row.
                _h, _b = _clean_memo_answer(q)
                memo_rows.append({
                    'sub': lbl, 'depth': depth, 'q': q,
                    'clean_heading': _h, 'clean_body': _b,
                    'group_first': False, 'group_rowspan': 0, 'group_total': 0,
                    'in_group': False,
                })
                i += 1
            grp_has_groups = any(r['in_group'] for r in memo_rows)
            qgroups.append({
                'qn': global_qn,
                'questions': group_qs,
                'marks': sum(q.marks or 0 for q in group_qs),
                'labels': labels,
                'title': grp_title,
                'instructions': grp_instr,
                'is_tf': grp_is_tf,
                'memo_rows': memo_rows,
                'has_groups': grp_has_groups,
            })
        is_tf = _is_true_false_section(sec.get('title', ''), qs)
        # Auto-splitting MCQ/Matching into separate Questions is disabled — the
        # editor's `splits` array is now the single source of truth for
        # question numbering, so the editor and the printed paper agree.
        resolved.append({'title': sec.get('title', 'Section'),
                         'sub_title': '',
                         'instructions': sec.get('instructions', ''),
                         'questions': qs,
                         'qgroups': qgroups,
                         'marks': sum(q.marks or 0 for q in qs),
                         'is_tf': is_tf,
                         'is_split_child': False})
    return {'paper': paper, 'sections': resolved, 'with_memo': with_memo,
            'grand_marks': grand_marks}


_TF_DETECT_RE = re.compile(r'\(indicate\s+true\s+or\s+false', re.IGNORECASE)

def _is_true_false_section(sec_title, questions):
    """Return True if this section is a True/False section."""
    title_lower = (sec_title or '').lower()
    if 'true' in title_lower and 'false' in title_lower:
        return True
    for q in questions:
        if (getattr(q, 'question_type', '') or '') == 'true_false':
            return True
        if _TF_DETECT_RE.search(getattr(q, 'question_text', '') or ''):
            return True
    return False





_MATCH_INTRO_RE = re.compile(
    r"^\s*Match the following description with the correct term from the list:\s*",
    re.IGNORECASE,
)


def _is_matching_item(q):
    if (q.question_type or '').lower() == 'match_columns':
        return True
    text = (q.question_text or '').lstrip()
    return bool(_MATCH_INTRO_RE.match(text))
def _annotate_matching_runs(qs):
    """Attach a structured matching-table payload to each run of matching items.

    For each maximal run of consecutive matching items, the FIRST item in the
    run gets ``match_table = {'rows': [(label, description, marks), ...],
    'options': [(letter, term), ...], 'total_marks': N, 'count': N}`` and is
    flagged ``match_run_first = True``. All subsequent items in that run get
    ``match_skip = True`` so the template renders the table only once.
    Non-matching items just get ``display_text = question_text``.
    """
    # Numbering of matching runs follows the surrounding question numbering,
    # which the template controls. Here we only record per-row labels relative
    # to the run (1, 2, ... N); the template will compose the final "Q.subN".
    i = 0
    while i < len(qs):
        q = qs[i]
        if not _is_matching_item(q):
            try:
                q.display_text = q.question_text
                q.match_skip = False
                q.match_run_first = False
            except Exception:
                pass
            i += 1
            continue
        # Collect the run
        run_start = i
        rows = []           # list of (description, marks)
        options = []        # list of (letter, term)
        while i < len(qs) and _is_matching_item(qs[i]):
            text = qs[i].question_text or ''
            body = text
            opts_tail = ''
            if 'Options:' in text:
                body, _, opts_tail = text.partition('Options:')
            description = _MATCH_INTRO_RE.sub('', body).strip()
            rows.append((description, qs[i].marks or 0))
            if i == run_start and opts_tail:
                # Parse "A) WiMAX\nB) Information overload\n..."
                for line in opts_tail.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    m = re.match(r'^([A-Z])[\)\.\:\-]\s*(.+)$', line)
                    if m:
                        options.append((m.group(1), m.group(2).strip()))
            try:
                qs[i].display_text = description
                qs[i].match_skip = (i != run_start)
                qs[i].match_run_first = (i == run_start)
            except Exception:
                pass
            i += 1
        # Attach the table to the first item in the run
        try:
            qs[run_start].match_table = {
                'rows': rows,
                'options': options,
                'count': len(rows),
                'total_marks': sum(m for _, m in rows),
            }
        except Exception:
            pass
    return qs


@app.route('/teacher/generator/<paper_id>/preview')
@teacher_required
def teacher_paper_preview(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if paper.owner_id != current_user.id and not current_user.is_admin: abort(403)
    return render_template('teacher/paper_print.html',
                           **_build_paper_context(paper, with_memo=False))


@app.route('/teacher/generator/<paper_id>/memo')
@teacher_required
def teacher_paper_memo(paper_id):
    paper = GeneratedPaper.query.get_or_404(paper_id)
    if paper.owner_id != current_user.id and not current_user.is_admin: abort(403)
    return render_template('teacher/paper_print.html',
                           **_build_paper_context(paper, with_memo=True))


# ---------- Instruction templates (per-teacher saved instructions) -------
# Instructions taken verbatim from DBE NSC question papers (Computer
# Applications Technology, Grade 12). Grouped by usage so teachers can pick
# the right block for the paper / section they are building.
INSTRUCTION_LIBRARY = {
    "Paper 2 – Theory (cover instructions)": [
        "This question paper consists of SECTION A (25), SECTION B (75) and SECTION C (50).",
        "Answer ALL the questions.",
        "Number the answers correctly according to the numbering system used in this question paper.",
        "Start EACH question on a NEW page.",
        "Do NOT write in the right-hand margin of the ANSWER BOOK.",
        "Leave a line after EACH subquestion.",
        "Generally, one mark is allocated per fact; therefore, a 2-mark question would require TWO facts, etc.",
        "Read the questions carefully. Do NOT give more answers than the question requires, as it will NOT be marked.",
        "All answers MUST be related to Computer Applications Technology.",
        "Unless otherwise specified, answers such as 'cheaper', 'slower'/'faster', etc. will NOT be accepted.",
        "Do NOT use brand names in your answers, unless specifically required.",
        "Write neatly and legibly.",
    ],
    "Paper 1 – Practical (cover instructions)": [
        "Owing to the nature of this practical examination, you will NOT be permitted to leave the examination room until all administrative functions associated with the examination have been finalised.",
        "Enter your examination number and centre number in the header of EVERY document that you create or save.",
        "The invigilator will give you a CD/DVD/flash disk containing all the files needed for the examination, OR you will be told where on the hard drive the files can be found.",
        "A copy of the master files will be available from the invigilator. Should there be any problems with a file, you may request another copy from the invigilator.",
        "This question paper consists of SEVEN questions. Answer ALL the questions.",
        "Save your work regularly.",
        "Read through each question before answering or solving the problem. Do NOT do more than is required by the question.",
        "At the end of the examination, hand in the storage media given to you by the invigilator with ALL your answer files saved on it. Ensure that ALL the files can be read.",
        "Note that no printing is required.",
        "During the examination you may make use of the help functions of the programs you are using. You may NOT use any other resource material.",
        "Unless instructed otherwise, formulae and/or functions must be used for ALL calculations in the spreadsheet questions. Use absolute cell references only where necessary to ensure that formulae are correct when copied to other cells.",
        "All formulae and/or functions should be inserted in such a manner that the correct results will still be obtained even if the data changes.",
        "Save all answer files in the examination folder using your examination number as the file name.",
        "Use only the data files provided to answer the questions.",
        "Make a backup copy of your work on the storage media provided.",
    ],
    "Section A – Multiple-choice": [
        "Various options are given as possible answers to the following questions. Choose the answer and write only the letter (A–D) next to the question numbers (1.1 to 1.10) in the ANSWER BOOK, e.g. 1.11 D.",
    ],
    "Section A – Matching items": [
        "Choose a term/concept from COLUMN B that matches the description in COLUMN A. Write only the letter (A–T) next to the question numbers (2.1 to 2.10) in the ANSWER BOOK, e.g. 2.11 U.",
        "Only ONE answer per question is allowed.",
    ],
    "Section A – True/False items": [
        "Indicate whether the following statements are TRUE or FALSE. Write 'true' or 'false' next to the question numbers (3.1 to 3.5) in the ANSWER BOOK.",
        "Correct the statement if it is FALSE by changing the underlined word(s) to make the statement TRUE. (Do NOT simply use the word 'NOT' to change the statement.)",
        "NO mark will be awarded if only FALSE is written.",
    ],
    "Section C – Integrated Scenario": [
        "The questions in this section are based on the scenario given below. Read the scenario carefully before attempting to answer the questions.",
        "Answer ALL the questions in this section.",
    ],
    "Web development (HTML)": [
        "An information sheet with HTML tags is provided as Annexure A.",
        "A text editor (e.g. Notepad++) MUST be used to answer the web development question.",
        "ANY HTML QUESTION ANSWERED USING A WORD PROCESSOR OR OTHER WEB DESIGN SOFTWARE (e.g. Dreamweaver, Wix, WordPress) WILL NOT BE MARKED.",
        "All changes made to web pages must be saved before the file is closed.",
    ],
    "Databases": [
        "An input mask character sheet is provided as Annexure B.",
        "Save the database after each subquestion to ensure that no work is lost.",
        "Do NOT add or remove records from the table unless asked to do so.",
    ],
    "General conduct & equipment": [
        "Write your name/examination number on every page of the ANSWER BOOK.",
        "The use of cell phones, smart watches or any other electronic devices is NOT permitted in the examination room.",
        "You may NOT borrow stationery or equipment from other candidates.",
        "Approved non-programmable, non-graphical scientific calculators may be used unless stated otherwise.",
        "Show ALL calculations and round answers to TWO decimal places where applicable.",
        "Diagrams are NOT necessarily drawn to scale.",
        "No marks will be awarded for answers that are NOT motivated, where required.",
        "Use a black or blue pen only. Pencil may only be used for diagrams.",
    ],
}

# Flattened list kept for backward compatibility with older clients of the
# /teacher/instruction-templates endpoint.
DEFAULT_INSTRUCTIONS = [text for group in INSTRUCTION_LIBRARY.values() for text in group]


@app.route('/teacher/instruction-templates', methods=['GET'])
@teacher_required
def teacher_instruction_templates_list():
    rows = (InstructionTemplate.query
            .filter_by(owner_id=current_user.id)
            .order_by(InstructionTemplate.created_at.desc()).all())
    return jsonify({
        'defaults': DEFAULT_INSTRUCTIONS,
        'categories': [
            {'name': name, 'items': items}
            for name, items in INSTRUCTION_LIBRARY.items()
        ],
        'mine': [{'id': r.id, 'text': r.text} for r in rows],
    })


@app.route('/teacher/instruction-templates', methods=['POST'])
@teacher_required
def teacher_instruction_templates_create():
    text = (request.json or request.form).get('text', '').strip()
    if not text:
        return jsonify({'ok': False, 'error': 'Text is required'}), 400
    if len(text) > 1000:
        return jsonify({'ok': False, 'error': 'Too long (max 1000 chars)'}), 400
    # de-dup against this teacher's existing list
    existing = InstructionTemplate.query.filter_by(owner_id=current_user.id, text=text).first()
    if existing:
        return jsonify({'ok': True, 'id': existing.id, 'text': existing.text, 'duplicate': True})
    row = InstructionTemplate(owner_id=current_user.id, text=text)
    db.session.add(row)
    db.session.commit()
    return jsonify({'ok': True, 'id': row.id, 'text': row.text})


@app.route('/teacher/instruction-templates/<tid>', methods=['DELETE'])
@teacher_required
def teacher_instruction_templates_delete(tid):
    row = InstructionTemplate.query.get_or_404(tid)
    if row.owner_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(row)
    db.session.commit()
    return jsonify({'ok': True})


# ---------- Schedule / year planner -------------------------------------
@app.route('/teacher/planner')
@teacher_required
def teacher_planner():
    year = request.args.get('year', type=int) or 2026
    grade = request.args.get('grade', type=int) or 12
    if grade not in (10, 11, 12):
        grade = 12
    items = (TeacherSchedule.query.filter_by(owner_id=current_user.id)
             .filter(db.extract('year', TeacherSchedule.start_date) == year)
             .order_by(TeacherSchedule.start_date).all())
    by_term = {1: [], 2: [], 3: [], 4: [], 0: []}
    for it in items:
        by_term.setdefault(it.term or 0, []).append(it)
    return render_template('teacher/planner.html', items=items,
                           by_term=by_term, year=year, grade=grade)


@app.route('/teacher/planner/new', methods=['GET', 'POST'])
@app.route('/teacher/planner/<item_id>/edit', methods=['GET', 'POST'])
@teacher_required
def teacher_planner_edit(item_id=None):
    item = TeacherSchedule.query.get_or_404(item_id) if item_id else None
    if item and item.owner_id != current_user.id and not current_user.is_admin: abort(403)
    if request.method == 'POST':
        if not item:
            item = TeacherSchedule(owner_id=current_user.id,
                                   start_date=datetime.utcnow().date())
            db.session.add(item)
        item.title = request.form.get('title', '').strip()
        item.description = request.form.get('description', '').strip()
        item.grade = request.form.get('grade', type=int)
        item.kind = request.form.get('kind', 'lesson')
        item.term = request.form.get('term', type=int)
        item.color = request.form.get('color', '#0078D4')
        sd = request.form.get('start_date', '').strip()
        ed = request.form.get('end_date', '').strip()
        if sd: item.start_date = datetime.strptime(sd, '%Y-%m-%d').date()
        item.end_date = datetime.strptime(ed, '%Y-%m-%d').date() if ed else None
        if not item.title:
            flash('Title required.', 'danger')
        else:
            db.session.commit(); flash('Saved.', 'success')
            return redirect(url_for('teacher_planner'))
    return render_template('teacher/planner_edit.html', item=item)


@app.route('/teacher/planner/<item_id>/delete', methods=['POST'])
@teacher_required
def teacher_planner_delete(item_id):
    item = TeacherSchedule.query.get_or_404(item_id)
    if item.owner_id != current_user.id and not current_user.is_admin: abort(403)
    db.session.delete(item); db.session.commit()
    flash('Removed.', 'info')
    return redirect(url_for('teacher_planner'))


# =====================================================================
#  ADMIN ROUTES
# =====================================================================
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin: abort(403)
        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    stats = {'courses': Course.query.count(), 'lessons': Lesson.query.count(), 'quizzes': Quiz.query.count(), 'users': User.query.count()}
    recent_enrollments = Enrollment.query.order_by(Enrollment.enrolled_at.desc()).limit(10).all()
    recent_attempts = QuizAttempt.query.order_by(QuizAttempt.completed_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', stats=stats, recent_enrollments=recent_enrollments, recent_attempts=recent_attempts)

@app.route('/admin/courses')
@login_required
@admin_required
def admin_courses():
    courses = Course.query.order_by(Course.order).all()
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/course/create', methods=['GET','POST'])
@login_required
@admin_required
def admin_course_create():
    grades = Grade.query.order_by(Grade.number).all()
    if request.method == 'POST':
        c = Course(title=request.form['title'], description=request.form.get('description',''),
            grade_id=request.form['grade_id'], icon=request.form.get('icon','fa-book'),
            color=request.form.get('color','#0078D4'), order=int(request.form.get('order_index',0)))
        db.session.add(c); db.session.commit(); flash('Course created!','success')
        return redirect(url_for('admin_courses'))
    return render_template('admin/course_form.html', grades=grades, course=None)

@app.route('/admin/course/<course_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def admin_course_edit(course_id):
    course = Course.query.get_or_404(course_id)
    grades = Grade.query.order_by(Grade.number).all()
    if request.method == 'POST':
        course.title=request.form['title']; course.description=request.form.get('description','')
        course.grade_id=request.form['grade_id']; course.icon=request.form.get('icon','fa-book')
        course.color=request.form.get('color','#0078D4'); course.order=int(request.form.get('order_index',0))
        db.session.commit(); flash('Course updated!','success'); return redirect(url_for('admin_courses'))
    return render_template('admin/course_form.html', grades=grades, course=course)

@app.route('/admin/course/<course_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_course_delete(course_id):
    course = Course.query.get_or_404(course_id)
    for q in Quiz.query.filter_by(course_id=course_id).all():
        Question.query.filter_by(quiz_id=q.id).delete()
        QuizAttempt.query.filter_by(quiz_id=q.id).delete()
    Quiz.query.filter_by(course_id=course_id).delete()
    for l in Lesson.query.filter_by(course_id=course_id).all():
        LessonCompletion.query.filter_by(lesson_id=l.id).delete()
    Lesson.query.filter_by(course_id=course_id).delete()
    Enrollment.query.filter_by(course_id=course_id).delete()
    db.session.delete(course); db.session.commit(); flash('Course deleted.','success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/lessons')
@login_required
@admin_required
def admin_lessons():
    lessons = Lesson.query.order_by(Lesson.order).all()
    return render_template('admin/lessons.html', lessons=lessons)

@app.route('/admin/lesson/create', methods=['GET','POST'])
@login_required
@admin_required
def admin_lesson_create():
    courses = Course.query.order_by(Course.order).all()
    if request.method == 'POST':
        l = Lesson(title=request.form['title'], content=request.form.get('content',''),
            course_id=request.form['course_id'], order=int(request.form.get('order_index',1)),
            duration_minutes=int(request.form.get('duration_minutes',15)))
        db.session.add(l); db.session.commit(); flash('Lesson created!','success')
        return redirect(url_for('admin_lessons'))
    return render_template('admin/lesson_form.html', courses=courses, lesson=None)

@app.route('/admin/lesson/<lesson_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def admin_lesson_edit(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    courses = Course.query.order_by(Course.order).all()
    if request.method == 'POST':
        lesson.title=request.form['title']; lesson.content=request.form.get('content','')
        lesson.course_id=request.form['course_id']; lesson.order=int(request.form.get('order_index',1))
        lesson.duration_minutes=int(request.form.get('duration_minutes',15))
        db.session.commit(); flash('Lesson updated!','success')
        return redirect(url_for('admin_lessons'))
    return render_template('admin/lesson_form.html', courses=courses, lesson=lesson)

@app.route('/admin/lesson/<lesson_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_lesson_delete(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    LessonCompletion.query.filter_by(lesson_id=lesson_id).delete()
    db.session.delete(lesson); db.session.commit(); flash('Lesson deleted.','success')
    return redirect(url_for('admin_lessons'))

@app.route('/admin/quizzes')
@login_required
@admin_required
def admin_quizzes():
    quizzes = Quiz.query.order_by(Quiz.order).all()
    return render_template('admin/quizzes.html', quizzes=quizzes)

@app.route('/admin/quiz/create', methods=['GET','POST'])
@login_required
@admin_required
def admin_quiz_create():
    courses = (Course.query.join(Grade)
               .order_by(Grade.number, Course.order, Course.title).all())
    if request.method == 'POST':
        tl = request.form.get('time_limit_minutes')
        tl_val = int(tl) if tl and tl != '0' else None
        q = Quiz(title=request.form['title'], description=request.form.get('description',''),
            course_id=request.form['course_id'], quiz_type=request.form.get('quiz_type','quiz'),
            time_limit_minutes=tl_val, pass_percentage=float(request.form.get('pass_percentage',50)),
            order=int(request.form.get('order',0)))
        db.session.add(q); db.session.commit(); flash('Quiz created!','success')
        return redirect(url_for('admin_questions', quiz_id=q.id))
    return render_template('admin/quiz_form.html', courses=courses, quiz=None)

@app.route('/admin/quiz/<quiz_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def admin_quiz_edit(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    courses = (Course.query.join(Grade)
               .order_by(Grade.number, Course.order, Course.title).all())
    if request.method == 'POST':
        tl = request.form.get('time_limit_minutes')
        quiz.title=request.form['title']; quiz.description=request.form.get('description','')
        quiz.course_id=request.form['course_id']; quiz.quiz_type=request.form.get('quiz_type','quiz')
        quiz.time_limit_minutes=int(tl) if tl and tl != '0' else None
        quiz.pass_percentage=float(request.form.get('pass_percentage',50))
        db.session.commit(); flash('Quiz updated!','success')
        return redirect(url_for('admin_quizzes'))
    return render_template('admin/quiz_form.html', courses=courses, quiz=quiz)

@app.route('/admin/quiz/<quiz_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_quiz_delete(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    Question.query.filter_by(quiz_id=quiz_id).delete(); QuizAttempt.query.filter_by(quiz_id=quiz_id).delete()
    db.session.delete(quiz); db.session.commit(); flash('Quiz deleted.','success')
    return redirect(url_for('admin_quizzes'))

@app.route('/admin/quiz/<quiz_id>/questions')
@login_required
@admin_required
def admin_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    raw_questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    questions = []
    for q in raw_questions:
        q.parsed_options = q.get_options()
        q.parsed_correct = q.get_correct_answer()
        questions.append(q)
    return render_template('admin/questions.html', quiz=quiz, questions=questions)

@app.route('/admin/quiz/<quiz_id>/question/create', methods=['GET','POST'])
@login_required
@admin_required
def admin_question_create(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        qtype = request.form['question_type']
        if qtype == 'multiple_choice':
            opts = [o.strip() for o in request.form.get('mc_options','').split('\n') if o.strip()]
            options_json = json.dumps(opts)
            correct_json = json.dumps(request.form.get('mc_correct','').strip())
        elif qtype == 'true_false':
            tf_correct = request.form.get('tf_correct','True').strip()
            if tf_correct not in ('True','False'): tf_correct = 'True'
            options_json = json.dumps(['True','False'])
            correct_json = json.dumps(tf_correct)
        elif qtype == 'drag_drop':
            items = [o.strip() for o in request.form.get('dd_correct_order','').split('\n') if o.strip()]
            options_json = json.dumps(items)
            correct_json = json.dumps(items)
        elif qtype == 'match_columns':
            col_a = [o.strip() for o in request.form.get('match_col_a','').split('\n') if o.strip()]
            col_b = [o.strip() for o in request.form.get('match_col_b','').split('\n') if o.strip()]
            options_json = json.dumps({'column_a': col_a, 'column_b': col_b})
            correct_json = json.dumps(dict(zip(col_a, col_b)))
        elif qtype == 'short_answer':
            kws = [k.strip() for k in request.form.get('sa_keywords','').split('\n') if k.strip()]
            min_ratio = float(request.form.get('sa_min_ratio', 0.6))
            options_json = json.dumps({'keywords': kws, 'min_ratio': min_ratio})
            correct_json = json.dumps(request.form.get('sa_model_answer','').strip())
        else:
            options_json = '[]'; correct_json = '""'
        q = Question(quiz_id=quiz_id, question_text=request.form['question_text'], question_type=qtype,
            options=options_json, correct_answer=correct_json,
            points=int(request.form.get('points',1)), order=int(request.form.get('order_index',1)))
        db.session.add(q); db.session.commit(); flash('Question added!','success')
        return redirect(url_for('admin_questions', quiz_id=quiz_id))
    return render_template('admin/question_form.html', quiz=quiz, question=None)

@app.route('/admin/question/<question_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def admin_question_edit(question_id):
    question = Question.query.get_or_404(question_id); quiz = question.quiz
    if request.method == 'POST':
        qtype = request.form['question_type']
        if qtype == 'multiple_choice':
            opts = [o.strip() for o in request.form.get('mc_options','').split('\n') if o.strip()]
            question.options = json.dumps(opts)
            question.correct_answer = json.dumps(request.form.get('mc_correct','').strip())
        elif qtype == 'true_false':
            tf_correct = request.form.get('tf_correct','True').strip()
            if tf_correct not in ('True','False'): tf_correct = 'True'
            question.options = json.dumps(['True','False'])
            question.correct_answer = json.dumps(tf_correct)
        elif qtype == 'drag_drop':
            items = [o.strip() for o in request.form.get('dd_correct_order','').split('\n') if o.strip()]
            question.options = json.dumps(items)
            question.correct_answer = json.dumps(items)
        elif qtype == 'match_columns':
            col_a = [o.strip() for o in request.form.get('match_col_a','').split('\n') if o.strip()]
            col_b = [o.strip() for o in request.form.get('match_col_b','').split('\n') if o.strip()]
            question.options = json.dumps({'column_a': col_a, 'column_b': col_b})
            question.correct_answer = json.dumps(dict(zip(col_a, col_b)))
        elif qtype == 'short_answer':
            kws = [k.strip() for k in request.form.get('sa_keywords','').split('\n') if k.strip()]
            min_ratio = float(request.form.get('sa_min_ratio', 0.6))
            question.options = json.dumps({'keywords': kws, 'min_ratio': min_ratio})
            question.correct_answer = json.dumps(request.form.get('sa_model_answer','').strip())
        question.question_text=request.form['question_text']; question.question_type=qtype
        question.points=int(request.form.get('points',1)); question.order=int(request.form.get('order_index',1))
        db.session.commit(); flash('Question updated!','success')
        return redirect(url_for('admin_questions', quiz_id=quiz.id))
    question.parsed_options = question.get_options()
    question.parsed_correct = question.get_correct_answer()
    return render_template('admin/question_form.html', quiz=quiz, question=question)

@app.route('/admin/question/<question_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_question_delete(question_id):
    question = Question.query.get_or_404(question_id); quiz_id=question.quiz_id
    db.session.delete(question); db.session.commit(); flash('Question deleted.','success')
    return redirect(url_for('admin_questions', quiz_id=quiz_id))

@app.route('/admin/quiz/<quiz_id>/bulk-upload', methods=['POST'])
@login_required
@admin_required
def admin_bulk_upload(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    f = request.files.get('csv_file')
    if not f or not f.filename.endswith('.csv'):
        flash('Please upload a .csv file.', 'danger')
        return redirect(url_for('admin_questions', quiz_id=quiz_id))
    stream = io.TextIOWrapper(f.stream, encoding='utf-8-sig')  # handle BOM
    reader = csv.DictReader(stream)
    added = 0; errors = []
    for i, row in enumerate(reader, start=2):  # row 1 = header
        try:
            qtype = row.get('question_type','').strip().lower()
            qtext = row.get('question_text','').strip()
            if not qtext or qtype not in ('multiple_choice','true_false','drag_drop','match_columns','short_answer'):
                errors.append(f'Row {i}: skipped (missing text or unknown type "{qtype}")')
                continue
            points = int(row.get('points','1').strip() or 1)
            if qtype == 'multiple_choice':
                opts = [row.get(f'option_{c}','').strip() for c in ('a','b','c','d','e') if row.get(f'option_{c}','').strip()]
                correct = row.get('correct_answer','').strip()
                opt_json = json.dumps(opts)
                cor_json = json.dumps(correct)
            elif qtype == 'true_false':
                correct = row.get('correct_answer','True').strip().capitalize()
                if correct not in ('True','False'): correct = 'True'
                opt_json = json.dumps(['True','False'])
                cor_json = json.dumps(correct)
            elif qtype == 'drag_drop':
                items = [row.get(f'option_{c}','').strip() for c in ('a','b','c','d','e') if row.get(f'option_{c}','').strip()]
                opt_json = json.dumps(items)
                cor_json = json.dumps(items)
            elif qtype == 'match_columns':
                col_a = [x.strip() for x in row.get('option_a','').split('|') if x.strip()]
                col_b = [x.strip() for x in row.get('option_b','').split('|') if x.strip()]
                opt_json = json.dumps({'column_a': col_a, 'column_b': col_b})
                cor_json = json.dumps(dict(zip(col_a, col_b)))
            elif qtype == 'short_answer':
                kw_raw = row.get('keywords','').strip()
                kws = [k.strip() for k in kw_raw.split('|') if k.strip()]
                min_ratio = float(row.get('min_ratio','0.6').strip() or 0.6)
                opt_json = json.dumps({'keywords': kws, 'min_ratio': min_ratio})
                cor_json = json.dumps(row.get('correct_answer','').strip())
            next_order = (Question.query.filter_by(quiz_id=quiz_id).count() + 1)
            q = Question(quiz_id=quiz_id, question_text=qtext, question_type=qtype,
                options=opt_json, correct_answer=cor_json, points=points, order=next_order)
            db.session.add(q); added += 1
        except Exception as e:
            errors.append(f'Row {i}: {e}')
    db.session.commit()
    if added:
        flash(f'{added} question(s) imported successfully.', 'success')
    for err in errors:
        flash(err, 'warning')
    return redirect(url_for('admin_questions', quiz_id=quiz_id))

@app.route('/admin/quiz/<quiz_id>/bulk-template')
@login_required
@admin_required
def admin_bulk_template(quiz_id):
    header = 'question_type,question_text,option_a,option_b,option_c,option_d,option_e,correct_answer,keywords,min_ratio,points\n'
    rows = [
        'multiple_choice,"What does CPU stand for?","Central Processing Unit","Computer Personal Unit","Central Program Utility","Computer Processing Unit",,"Central Processing Unit",,, 1',
        'drag_drop,"Arrange storage units smallest to largest:","Kilobyte (KB)","Megabyte (MB)","Gigabyte (GB)","Terabyte (TB)",,,,, 1',
        'match_columns,"Match each device to its category:","CPU|RAM|Monitor|Keyboard","Processing|Memory|Output|Input",,,,,,, 1',
        'short_answer,"Explain what RAM does in a computer.",,,,,,"RAM temporarily stores data that the CPU is actively using","temporary|storage|CPU|active",0.6, 2',
    ]
    content = header + '\n'.join(rows) + '\n'
    return Response(content, mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=bulk_questions_template.csv'})

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def admin_toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'{"Admin granted" if user.is_admin else "Admin revoked"} for {user.username}.','success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<user_id>/toggle-teacher', methods=['POST'])
@login_required
@admin_required
def admin_toggle_teacher(user_id):
    user = User.query.get_or_404(user_id)
    user.is_teacher = not bool(user.is_teacher)
    db.session.commit()
    flash(f'{"Teacher access granted" if user.is_teacher else "Teacher access revoked"} for {user.username}.','success')
    return redirect(url_for('admin_users'))

# =====================================================================
#  ERROR HANDLERS
# =====================================================================
@app.errorhandler(404)
def not_found(e): return render_template('error.html', error_code=404, error_message='Page not found'), 404
@app.errorhandler(403)
def forbidden(e): return render_template('error.html', error_code=403, error_message='Access denied'), 403
@app.errorhandler(500)
def server_error(e): return render_template('error.html', error_code=500, error_message='Server error'), 500

# =====================================================================
#  SEED DATA
# =====================================================================
def seed_data():
    grades_data = [
        {'number':10,'name':'Grade 10','description':'Computer Applications Technology — CAPS Grade 10'},
        {'number':11,'name':'Grade 11','description':'Computer Applications Technology — CAPS Grade 11'},
        {'number':12,'name':'Grade 12','description':'Computer Applications Technology — CAPS Grade 12'},
    ]
    grade_objects = {}
    for gd in grades_data:
        g = Grade.query.filter_by(number=gd['number']).first()
        if not g: g = Grade(**gd); db.session.add(g); db.session.flush()
        grade_objects[gd['number']] = g

    g10c = [
        {'title':'Word Processing','description':'Creating, editing and formatting documents. Mail merge, styles, tables.','icon':'fa-file-word','color':'#2B579A','order':1},
        {'title':'Spreadsheets','description':'Formulas, functions, charts, and data organisation.','icon':'fa-file-excel','color':'#217346','order':2},
        {'title':'Presentations','description':'Slide layouts, animations, transitions, and multimedia.','icon':'fa-file-powerpoint','color':'#D24726','order':3},
        {'title':'Computer Hardware','description':'Components, peripherals, storage devices, troubleshooting.','icon':'fa-microchip','color':'#5C2D91','order':4},
        {'title':'Networks & Internet','description':'Networking concepts, internet, browsers, email.','icon':'fa-globe','color':'#0078D4','order':5},
        {'title':'Information Management','description':'Finding, evaluating digital information. File management.','icon':'fa-folder-open','color':'#008272','order':6},
    ]
    g11c = [
        {'title':'Advanced Word Processing','description':'Long documents, TOC, citations, advanced formatting.','icon':'fa-file-word','color':'#2B579A','order':1},
        {'title':'Advanced Spreadsheets','description':'VLOOKUP, IF functions, pivot tables, data analysis.','icon':'fa-file-excel','color':'#217346','order':2},
        {'title':'Database Concepts','description':'Tables, queries, forms, reports, relational design.','icon':'fa-database','color':'#E81123','order':3},
        {'title':'Advanced Presentations','description':'Master slides, interactive presentations, multimedia.','icon':'fa-file-powerpoint','color':'#D24726','order':4},
        {'title':'System Software','description':'OS, utility software, maintenance, installation.','icon':'fa-cogs','color':'#5C2D91','order':5},
        {'title':'Internet & Social Implications','description':'E-commerce, cyber safety, digital citizenship.','icon':'fa-shield-alt','color':'#0078D4','order':6},
    ]
    g12c = [
        {'title':'Integrated Document Handling','description':'Integrating word processing, spreadsheets, and databases.','icon':'fa-file-alt','color':'#2B579A','order':1},
        {'title':'Advanced Spreadsheet Functions','description':'Complex formulas, macros, advanced charting.','icon':'fa-file-excel','color':'#217346','order':2},
        {'title':'Advanced Databases','description':'Complex queries, SQL basics, relationships, reports.','icon':'fa-database','color':'#E81123','order':3},
        {'title':'Web & HTML Basics','description':'HTML, CSS, web page creation concepts.','icon':'fa-code','color':'#F7B500','order':4},
        {'title':'Solution Development','description':'Problem-solving with ICT, integrated solutions.','icon':'fa-lightbulb','color':'#5C2D91','order':5},
        {'title':'ICT & Society','description':'Impact of ICT, emerging tech, green computing.','icon':'fa-users','color':'#008272','order':6},
    ]

    course_objects = {}
    for gn, clist in [(10,g10c),(11,g11c),(12,g12c)]:
        for cd in clist:
            ex = Course.query.filter_by(title=cd['title'], grade_id=grade_objects[gn].id).first()
            if not ex: ex = Course(grade_id=grade_objects[gn].id, **cd); db.session.add(ex); db.session.flush()
            course_objects[(gn, cd['title'])] = ex

    # Sample Lessons — Grade 10 Computer Hardware
    hw = course_objects.get((10,'Computer Hardware'))
    if hw and Lesson.query.filter_by(course_id=hw.id).count()==0:
        for ld in [
            {'title':'Introduction to Computer Systems','order':1,'duration_minutes':35,'content':'<h2>Introduction to Computer Systems</h2><p>A computer system consists of hardware and software working together.</p><h3>Components</h3><ul><li><strong>CPU</strong> — The brain of the computer</li><li><strong>RAM</strong> — Temporary memory for active programs</li><li><strong>Storage</strong> — HDD and SSD for permanent storage</li><li><strong>Motherboard</strong> — Main circuit board</li><li><strong>PSU</strong> — Power supply unit</li></ul><h3>IPO Cycle</h3><p><strong>Input</strong> → <strong>Process</strong> → <strong>Output</strong></p>'},
            {'title':'Input and Output Devices','order':2,'duration_minutes':30,'content':'<h2>Input and Output Devices</h2><h3>Input Devices</h3><ul><li>Keyboard, Mouse, Scanner, Microphone, Webcam, Touchscreen</li></ul><h3>Output Devices</h3><ul><li>Monitor, Printer, Speakers, Projector</li></ul>'},
            {'title':'Storage Devices and Media','order':3,'duration_minutes':35,'content':'<h2>Storage Devices</h2><h3>Primary Storage</h3><ul><li><strong>RAM</strong> — Volatile, fast</li><li><strong>ROM</strong> — Non-volatile, firmware</li></ul><h3>Secondary Storage</h3><ul><li>HDD, SSD, USB Flash Drive, External drives</li></ul><h3>Cloud Storage</h3><p>Google Drive, OneDrive, Dropbox</p><p>1 KB → 1 MB → 1 GB → 1 TB (each ×1024)</p>'},
        ]:
            db.session.add(Lesson(course_id=hw.id, **ld))

    # Sample Lessons — Grade 12 Spreadsheets
    ss = course_objects.get((12,'Advanced Spreadsheet Functions'))
    if ss and Lesson.query.filter_by(course_id=ss.id).count()==0:
        for ld in [
            {'title':'VLOOKUP and HLOOKUP','order':1,'duration_minutes':45,'content':'<h2>VLOOKUP and HLOOKUP</h2><p>VLOOKUP searches the first column of a range and returns a value from a specified column.</p><h3>Syntax</h3><pre>=VLOOKUP(lookup_value, table_array, col_index_num, [range_lookup])</pre><ul><li><strong>lookup_value</strong> — Value to find</li><li><strong>table_array</strong> — Data range</li><li><strong>col_index_num</strong> — Column to return from</li><li><strong>range_lookup</strong> — FALSE=exact match</li></ul>'},
            {'title':'IF and Nested IF Functions','order':2,'duration_minutes':40,'content':'<h2>IF Functions</h2><pre>=IF(condition, true_value, false_value)</pre><p>Example: =IF(A1>=50, "Pass", "Fail")</p><h3>Nested IF</h3><pre>=IF(A1>=80,"A",IF(A1>=60,"B",IF(A1>=50,"C","F")))</pre>'},
            {'title':'COUNTIF, SUMIF, AVERAGEIF','order':3,'duration_minutes':35,'content':'<h2>Conditional Functions</h2><h3>COUNTIF</h3><pre>=COUNTIF(range, criteria)</pre><h3>SUMIF</h3><pre>=SUMIF(range, criteria, sum_range)</pre><h3>AVERAGEIF</h3><pre>=AVERAGEIF(range, criteria, average_range)</pre>'},
            {'title':'Data Validation','order':4,'duration_minutes':30,'content':'<h2>Data Validation</h2><ul><li>List validation — dropdown lists</li><li>Number validation — ranges</li><li>Date validation</li><li>Text length limits</li></ul><h3>Protection</h3><p>Protect sheets and workbooks from unauthorized changes.</p>'},
            {'title':'Charts and Visualisation','order':5,'duration_minutes':40,'content':'<h2>Charts</h2><ul><li><strong>Column/Bar</strong> — Compare categories</li><li><strong>Line</strong> — Trends over time</li><li><strong>Pie</strong> — Parts of a whole</li><li><strong>Scatter</strong> — Relationships</li></ul><p>Always include title, axis labels, and legend.</p>'},
        ]:
            db.session.add(Lesson(course_id=ss.id, **ld))

    # Quizzes
    if hw and Quiz.query.filter_by(course_id=hw.id).count()==0:
        quiz = Quiz(title='Computer Hardware Quiz', description='Test your knowledge of hardware components.', course_id=hw.id, quiz_type='quiz', pass_percentage=50, order=1)
        db.session.add(quiz); db.session.flush()
        for qd in [
            Question(quiz_id=quiz.id, question_text='What does CPU stand for?', question_type='multiple_choice', options=json.dumps(['Central Processing Unit','Computer Personal Unit','Central Program Utility','Computer Processing Unit']), correct_answer=json.dumps('Central Processing Unit'), points=2, order=1, explanation='CPU = Central Processing Unit.'),
            Question(quiz_id=quiz.id, question_text='Which is an OUTPUT device?', question_type='multiple_choice', options=json.dumps(['Keyboard','Mouse','Printer','Scanner']), correct_answer=json.dumps('Printer'), points=2, order=2, explanation='A printer produces hard copies.'),
            Question(quiz_id=quiz.id, question_text='RAM is volatile. What does this mean?', question_type='multiple_choice', options=json.dumps(['It can explode','Data is lost when power is off','It is fast','It stores data permanently']), correct_answer=json.dumps('Data is lost when power is off'), points=2, order=3, explanation='Volatile = data lost without power.'),
            Question(quiz_id=quiz.id, question_text='Arrange storage units SMALLEST to LARGEST:', question_type='drag_drop', options=json.dumps(['Terabyte (TB)','Kilobyte (KB)','Gigabyte (GB)','Megabyte (MB)']), correct_answer=json.dumps(['Kilobyte (KB)','Megabyte (MB)','Gigabyte (GB)','Terabyte (TB)']), points=4, order=4, explanation='KB → MB → GB → TB'),
            Question(quiz_id=quiz.id, question_text='Match each device to its category:', question_type='match_columns', options=json.dumps({'column_a':['Keyboard','Monitor','SSD','Webcam'],'column_b':['Input Device','Output Device','Storage Device','Input Device']}), correct_answer=json.dumps({'Keyboard':'Input Device','Monitor':'Output Device','SSD':'Storage Device','Webcam':'Input Device'}), points=4, order=5, explanation='Keyboard/Webcam=Input, Monitor=Output, SSD=Storage.'),
        ]:
            db.session.add(qd)

    if ss and Quiz.query.filter_by(course_id=ss.id).count()==0:
        exam = Quiz(title='Spreadsheet Functions Exam', description='Formal assessment on advanced spreadsheet functions.', course_id=ss.id, quiz_type='exam', time_limit_minutes=30, pass_percentage=50, order=1)
        db.session.add(exam); db.session.flush()
        for qd in [
            Question(quiz_id=exam.id, question_text='What does the 3rd argument in VLOOKUP specify?', question_type='multiple_choice', options=json.dumps(['Lookup value','Table range','Column index number','Match type']), correct_answer=json.dumps('Column index number'), points=2, order=1, explanation='3rd argument = column index number.'),
            Question(quiz_id=exam.id, question_text='Result of =IF(80>=50,"Pass","Fail")?', question_type='multiple_choice', options=json.dumps(['Pass','Fail','TRUE','80']), correct_answer=json.dumps('Pass'), points=2, order=2, explanation='80>=50 is TRUE → "Pass".'),
            Question(quiz_id=exam.id, question_text='Which function counts cells meeting a condition?', question_type='multiple_choice', options=json.dumps(['SUM','COUNT','COUNTIF','AVERAGE']), correct_answer=json.dumps('COUNTIF'), points=2, order=3, explanation='COUNTIF counts cells matching a criteria.'),
            Question(quiz_id=exam.id, question_text='Order the steps to create a chart:', question_type='drag_drop', options=json.dumps(['Add title and labels','Select data range','Choose chart type','Insert chart']), correct_answer=json.dumps(['Select data range','Choose chart type','Insert chart','Add title and labels']), points=4, order=4, explanation='Select data → chart type → insert → add labels.'),
            Question(quiz_id=exam.id, question_text='Match each function to its purpose:', question_type='match_columns', options=json.dumps({'column_a':['VLOOKUP','COUNTIF','SUMIF','AVERAGEIF'],'column_b':['Looks up a value in a table','Counts cells meeting a condition','Sums values meeting a condition','Averages values meeting a condition']}), correct_answer=json.dumps({'VLOOKUP':'Looks up a value in a table','COUNTIF':'Counts cells meeting a condition','SUMIF':'Sums values meeting a condition','AVERAGEIF':'Averages values meeting a condition'}), points=4, order=5, explanation='Each function has a specific conditional purpose.'),
        ]:
            db.session.add(qd)

    dbc = course_objects.get((11,'Database Concepts'))
    if dbc and Quiz.query.filter_by(course_id=dbc.id).count()==0:
        dbq = Quiz(title='Database Concepts Quiz', description='Test database terminology and concepts.', course_id=dbc.id, quiz_type='quiz', pass_percentage=50, order=1)
        db.session.add(dbq); db.session.flush()
        for qd in [
            Question(quiz_id=dbq.id, question_text='What is a PRIMARY KEY?', question_type='multiple_choice', options=json.dumps(['A number field','A unique identifier for each record','The first field','A password']), correct_answer=json.dumps('A unique identifier for each record'), points=2, order=1, explanation='Primary key uniquely identifies each record.'),
            Question(quiz_id=dbq.id, question_text='Match database terms:', question_type='match_columns', options=json.dumps({'column_a':['Table','Field','Record','Query'],'column_b':['Collection of records','A single column','A single row','A request for data']}), correct_answer=json.dumps({'Table':'Collection of records','Field':'A single column','Record':'A single row','Query':'A request for data'}), points=4, order=2, explanation='Table=records, Field=column, Record=row, Query=request.'),
            Question(quiz_id=dbq.id, question_text='Order steps to create a database:', question_type='drag_drop', options=json.dumps(['Enter data','Identify purpose','Create relationships','Design tables']), correct_answer=json.dumps(['Identify purpose','Design tables','Create relationships','Enter data']), points=4, order=3, explanation='Purpose → Design → Relationships → Data.'),
        ]:
            db.session.add(qd)

    db.session.commit()

def init_db():
    with app.app_context():
        db.create_all()
        # Lightweight in-place migration: add columns introduced after the
        # initial schema was deployed. Safe to run on every startup.
        try:
            from sqlalchemy import inspect, text
            insp = inspect(db.engine)
            cols = {c['name'] for c in insp.get_columns('question_bank_items')}
            if 'image_path' not in cols:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE question_bank_items ADD COLUMN image_path VARCHAR(400) DEFAULT ''"
                    ))
                print("Migrated: question_bank_items.image_path added")
        except Exception as _mig_err:
            print(f"Schema migration skipped: {_mig_err}")
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@catcaps.edu.za', first_name='Admin', last_name='User', is_admin=True)
            admin.set_password('admin123'); db.session.add(admin); db.session.commit()
            print('Admin created (admin / admin123)')
        student = User.query.filter_by(username='student').first()
        if not student:
            student = User(username='student', email='student@catcaps.edu.za', first_name='Test', last_name='Student', grade=12)
            student.set_password('student123'); db.session.add(student); db.session.commit()
            print('Student created (student / student123)')
        seed_data()
        g12 = Grade.query.filter_by(number=12).first()
        if g12 and student:
            for c in g12.courses:
                if not Enrollment.query.filter_by(user_id=student.id, course_id=c.id).first():
                    db.session.add(Enrollment(user_id=student.id, course_id=c.id))
            db.session.commit()
        print('Database initialized successfully')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5004))
    app.run(debug=True, host='0.0.0.0', port=port)

