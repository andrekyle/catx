"""One-time fix: replace Wingdings PUA tick glyphs in question_bank_items.answer_text and question_text with the standard U+2713 check mark, so they render in normal fonts."""
import sqlite3, sys

DB = 'instance/brandcartel.db'
SUBS = [('\uf0fc', '\u2713'), ('\uf0fb', '\u2713'), ('\u2714', '\u2713')]

conn = sqlite3.connect(DB)
cur = conn.cursor()
total = 0
for col in ('answer_text', 'question_text'):
    rows = cur.execute(f"SELECT id, {col} FROM question_bank_items WHERE {col} IS NOT NULL").fetchall()
    for rid, val in rows:
        new = val
        for old, repl in SUBS:
            new = new.replace(old, repl)
        if new != val:
            cur.execute(f"UPDATE question_bank_items SET {col}=? WHERE id=?", (new, rid))
            total += 1
conn.commit()
print(f'Updated {total} cell(s).')
