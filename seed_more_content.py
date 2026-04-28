"""
Seed an additional layer of CAPS-aligned content for every course.

For each of the 18 courses this script adds (idempotent — safe to re-run):
  * Lesson at order 8  -> "Common Mistakes & Troubleshooting"
  * Lesson at order 9  -> "Exam Preparation Toolkit"
  * Quiz at order 3    -> "<Course> — Mastery Quiz"  (10 questions, mixed types)

Existing rows are never overwritten:
  * Lessons skipped when (course_id, order) already exists.
  * Quizzes skipped when (course_id, title) already exists.

Run:
    python seed_more_content.py
"""
import json

from app import app, db, Course, Lesson, Quiz, Question


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def kbd(*keys):
    parts = []
    for i, k in enumerate(keys):
        if i:
            parts.append('<span class="plus">+</span>')
        parts.append(f'<span class="kbd">{k}</span>')
    return '<span class="kbd-combo">' + ''.join(parts) + '</span>'


def intro(label, text):
    return (f'<div class="lesson-intro"><div class="label">{label}</div>'
            f'<p>{text}</p></div>')


def callout(kind, icon, title, body):
    return (f'<div class="callout {kind}"><div class="ico">'
            f'<i class="fas {icon}"></i></div><div class="body">'
            f'<strong>{title}</strong>{body}</div></div>')


def grid(items):
    cards = ''.join(
        f'<div class="card-mini"><h4><i class="fas {it["icon"]}"></i> '
        f'{it["title"]}</h4><p>{it["body"]}</p></div>'
        for it in items
    )
    return f'<div class="lesson-grid">{cards}</div>'


def steps(items):
    return '<ol class="steps">' + ''.join(f'<li>{x}</li>' for x in items) + '</ol>'


def table(headers, rows):
    th = ''.join(f'<th>{h}</th>' for h in headers)
    body = ''.join(
        '<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>'
        for r in rows
    )
    return f'<table><tr>{th}</tr>{body}</table>'


# ---------------------------------------------------------------------------
# Per-course content data
# Each entry has:
#   mistakes: [(symptom, cause, fix), ...]   (4–5 items)
#   exam_tips: [str, ...]                    (5–6 short tips)
#   glossary: [(term, definition), ...]      (5 items, used in mastery quiz)
#   short_answer: (question, answer)         (single short-answer for mastery)
# ---------------------------------------------------------------------------
PACKS = {

    # ============================ GRADE 10 ============================
    'Word Processing': {
        'mistakes': [
            ('Text suddenly jumps to a new page when you delete a space.',
             'A page break or section break is hiding in the document.',
             'Turn on <strong>Show/Hide</strong> (<code>&para;</code>) and delete the break manually.'),
            ('Bullet points line up unevenly.',
             'Spaces or tabs were typed by hand instead of using a list style.',
             'Select the lines &rarr; Home tab &rarr; <strong>Bullets</strong>; adjust list indent on the ruler.'),
            ('Image refuses to move where you want.',
             'Wrap-text is set to <em>In Line with Text</em>.',
             'Right-click the image &rarr; Wrap Text &rarr; <strong>Square</strong> or <strong>Tight</strong>.'),
            ('Header changes break previous pages.',
             'Sections are linked.',
             'On the Header &amp; Footer tab, click <strong>Link to Previous</strong> to break the link.'),
        ],
        'exam_tips': [
            'Read the entire question paper first &mdash; mark the marks-per-question.',
            'Do the easy formatting tasks (font, alignment, page setup) first to bank marks.',
            'Save your file as instructed (often <code>.docx</code>) every 5 minutes.',
            'Use Show/Hide (<code>&para;</code>) to reveal hidden formatting issues.',
            'Re-read the brief at the end &mdash; check every sub-task is done.',
        ],
        'glossary': [
            ('Style', 'A saved set of formatting (font, size, colour) applied with one click.'),
            ('Section break', 'A divider that lets different parts of a document use different settings.'),
            ('Header', 'Text that repeats at the top of every page.'),
            ('Mail merge', 'A feature that combines a template with a data source to produce many letters.'),
            ('Watermark', 'Faded text or image behind the main content of every page.'),
        ],
        'short_answer': ('Which file extension does Word 2016+ use by default?', '.docx'),
    },

    'Spreadsheets': {
        'mistakes': [
            ('Cell shows <code>#####</code>.',
             'Column is too narrow to display the number.',
             'Double-click the column border to <strong>auto-fit</strong> the width.'),
            ('Formula returns <code>#DIV/0!</code>.',
             'Dividing by zero or by an empty cell.',
             'Wrap with <code>=IFERROR(formula, 0)</code> or check the divisor first.'),
            ('Copying a formula gives wrong results.',
             'Cell references shift &mdash; you needed an absolute reference.',
             'Press <kbd>F4</kbd> to add <code>$</code> signs (e.g. <code>$B$1</code>).'),
            ('SUM gives 0 even though numbers are visible.',
             'Numbers are stored as text.',
             'Select column &rarr; Data &rarr; <strong>Text to Columns</strong> &rarr; Finish.'),
        ],
        'exam_tips': [
            'Always read the column headings &mdash; they hint at the formula needed.',
            'Use cell references, never type raw values into formulas.',
            'Format numbers (currency / percentage) before doing calculations to spot errors.',
            'Build charts after data is final &mdash; selection rectangle includes labels.',
            'Sort and filter ONLY after backing up the sheet (Ctrl + Z is your friend).',
        ],
        'glossary': [
            ('Function', 'A built-in formula like <code>SUM</code> or <code>AVERAGE</code>.'),
            ('Absolute reference', 'A locked cell address like <code>$A$1</code>.'),
            ('Range', 'A group of cells, e.g. <code>A1:A10</code>.'),
            ('Cell', 'The intersection of a row and column.'),
            ('Chart', 'A graphical representation of spreadsheet data.'),
        ],
        'short_answer': ('Which key adds dollar signs to a cell reference?', 'F4'),
    },

    'Presentations': {
        'mistakes': [
            ('Text disappears off the side of a slide.',
             'Text box was resized by dragging instead of using slide layouts.',
             'Reset the layout: Home &rarr; <strong>Reset</strong>.'),
            ('Animation triggers on click instead of automatically.',
             '<em>Start</em> is set to <code>On Click</code>.',
             'Animation pane &rarr; change Start to <strong>With Previous</strong> or <strong>After Previous</strong>.'),
            ('Audio stops when the slide changes.',
             'Audio is set to <em>Across slides</em> off.',
             'Audio Tools &rarr; Playback &rarr; tick <strong>Play Across Slides</strong>.'),
            ('Slide transitions look jerky.',
             'Hardware acceleration is off or transition speed is too slow.',
             'Transitions tab &rarr; reduce <strong>Duration</strong>; close other apps.'),
        ],
        'exam_tips': [
            'Apply a Theme first &mdash; it sets colours and fonts site-wide.',
            'Use <strong>View &rarr; Slide Master</strong> to change every slide at once.',
            'Save as <code>.pptx</code>; only export to PDF if instructed.',
            'Test every animation &amp; hyperlink with <kbd>F5</kbd>.',
            'Keep one idea per slide &mdash; markers reward clarity.',
        ],
        'glossary': [
            ('Slide master', 'A template that controls every slide in a presentation.'),
            ('Transition', 'The visual effect when moving between slides.'),
            ('Animation', 'A visual effect applied to an object on a slide.'),
            ('Layout', 'A pre-built slide structure (title, content, etc.).'),
            ('Action button', 'A clickable shape that links to another slide or file.'),
        ],
        'short_answer': ('Which key starts a slideshow from slide 1?', 'F5'),
    },

    'Computer Hardware': {
        'mistakes': [
            ('PC will not turn on.',
             'Loose power cable or PSU switch is off.',
             'Check the wall outlet, the cable and the PSU rocker switch.'),
            ('Constant beeping at startup.',
             'A POST error &mdash; usually RAM not seated.',
             'Power off, re-seat RAM modules, try again.'),
            ('Mouse cursor stutters.',
             'Dirty optical sensor or low USB power.',
             'Clean sensor with a dry cloth; try a different USB port.'),
            ('External drive is not detected.',
             'Drive is unformatted or driver missing.',
             'Open <strong>Disk Management</strong> and assign a drive letter / format if blank.'),
        ],
        'exam_tips': [
            'Memorise the input/output/storage classification of every device.',
            'Know the difference between <strong>RAM</strong> (volatile) and <strong>ROM</strong> (non-volatile).',
            'Be able to convert KB &rarr; MB &rarr; GB &rarr; TB.',
            'Practise drawing the data-flow diagram (input &rarr; CPU &rarr; output).',
            'Learn cable connector shapes &mdash; HDMI, VGA, USB-A, USB-C, Ethernet.',
        ],
        'glossary': [
            ('CPU', 'The processor &mdash; the brain that executes instructions.'),
            ('RAM', 'Volatile memory used while programs are running.'),
            ('ROM', 'Read-only memory storing firmware that boots the computer.'),
            ('SSD', 'Solid-state drive &mdash; fast storage with no moving parts.'),
            ('Peripheral', 'A device connected to the computer (printer, mouse, scanner).'),
        ],
        'short_answer': ('How many bytes are in 1 kilobyte (decimal definition)?', '1000'),
    },

    'Networks & Internet': {
        'mistakes': [
            ('Wi-Fi connects but no internet.',
             'DNS server unreachable.',
             'Switch DNS to <code>8.8.8.8</code> or restart the router.'),
            ('Email bounces back.',
             'Wrong address or full mailbox.',
             'Check the bounce message for the SMTP error code.'),
            ('Webpage shows "Not secure".',
             'Site uses HTTP instead of HTTPS.',
             'Avoid entering passwords; look for the padlock icon.'),
            ('Slow downloads on a fast line.',
             'Many devices sharing the connection.',
             'Pause background updates; use a wired connection where possible.'),
        ],
        'exam_tips': [
            'Know the OSI model layers in order (mnemonic: <em>Please Do Not Throw Sausage Pizza Away</em>).',
            'Memorise common port numbers: 80 HTTP, 443 HTTPS, 25 SMTP, 21 FTP.',
            'Be able to draw a LAN topology (star, bus, ring).',
            'Know the difference between <strong>HTTP</strong> and <strong>HTTPS</strong>.',
            'Practise explaining IP vs MAC addresses.',
        ],
        'glossary': [
            ('LAN', 'Local Area Network &mdash; covers one building or campus.'),
            ('WAN', 'Wide Area Network &mdash; spans cities or countries.'),
            ('Router', 'A device that forwards packets between networks.'),
            ('Bandwidth', 'The maximum data transfer rate of a connection.'),
            ('Protocol', 'A set of rules for how computers communicate.'),
        ],
        'short_answer': ('What does HTTPS stand for?',
                         'Hypertext Transfer Protocol Secure'),
    },

    'Information Management': {
        'mistakes': [
            ('Search returns millions of useless results.',
             'Keywords are too broad.',
             'Add quotes for phrases and use <code>site:</code> filters.'),
            ('Source cannot be trusted.',
             'No author, no date, no references.',
             'Apply the <strong>CRAAP test</strong>: Currency, Relevance, Authority, Accuracy, Purpose.'),
            ('Lost a file on the PC.',
             'Saved to default Downloads folder.',
             'Use Explorer search with <code>*.docx</code> and sort by date.'),
            ('Information overload while researching.',
             'No filtering plan.',
             'Write 3 focused questions before opening the browser.'),
        ],
        'exam_tips': [
            'Always cite sources &mdash; even if the question does not say so.',
            'Compare at least two sources before quoting a fact.',
            'Use folders named <code>YYYY-MM-DD_topic</code> for easy sorting.',
            'Distinguish data, information and knowledge in your answer.',
            'Practise summarising a 500-word article in 100 words.',
        ],
        'glossary': [
            ('Data', 'Raw, unprocessed facts.'),
            ('Information', 'Data that has been organised and given meaning.'),
            ('Knowledge', 'Information that can be acted upon.'),
            ('Bias', 'A one-sided view that distorts information.'),
            ('Plagiarism', 'Using someone else&rsquo;s work without credit.'),
        ],
        'short_answer': ('Which acronym helps you evaluate online sources?', 'CRAAP'),
    },

    # ============================ GRADE 11 ============================
    'Advanced Word Processing': {
        'mistakes': [
            ('Cross-reference shows "Error! Bookmark not defined."',
             'The target heading or bookmark was deleted.',
             'Re-insert the cross-reference or update fields with <kbd>F9</kbd>.'),
            ('Footnotes restart on every page.',
             'Numbering is set to <em>Restart each page</em>.',
             'References &rarr; Footnote dialog &rarr; Numbering: <strong>Continuous</strong>.'),
            ('Two columns display unevenly on the last page.',
             'Column break missing.',
             'Insert &rarr; Break &rarr; <strong>Column</strong>.'),
            ('Track changes show old author name.',
             'User name was not updated.',
             'File &rarr; Options &rarr; General &rarr; change <strong>User name</strong>.'),
        ],
        'exam_tips': [
            'Plan section breaks before adding headers/footers.',
            'Use heading styles consistently &mdash; the TOC depends on them.',
            'Insert citations using References &rarr; Insert Citation, not by typing.',
            'Update all fields (<kbd>Ctrl</kbd>+<kbd>A</kbd>, <kbd>F9</kbd>) before printing.',
            'Save with a meaningful name following the brief&rsquo;s convention.',
        ],
        'glossary': [
            ('Section break', 'Divider letting parts of a document use different settings.'),
            ('Cross-reference', 'A field that points to another item (heading, figure).'),
            ('Track changes', 'Word feature that records every edit by author.'),
            ('Footnote', 'A note printed at the bottom of the same page.'),
            ('Citation', 'A reference to a source listed in the bibliography.'),
        ],
        'short_answer': ('Which keyboard shortcut updates all fields in a document?', 'F9'),
    },

    'Advanced Spreadsheets': {
        'mistakes': [
            ('VLOOKUP returns <code>#N/A</code>.',
             'Lookup value missing from first column of table.',
             'Verify spelling, or use <code>IFERROR</code> for a friendly message.'),
            ('Pivot table shows old data.',
             'Source range changed but pivot was not refreshed.',
             'Right-click pivot &rarr; <strong>Refresh</strong>.'),
            ('Conditional formatting did not apply to new rows.',
             'Range was static.',
             'Convert range to a Table (<kbd>Ctrl</kbd>+<kbd>T</kbd>); rules expand automatically.'),
            ('Charts showing wrong category labels.',
             'Source data not contiguous.',
             'Reselect Data Source and edit horizontal axis labels.'),
        ],
        'exam_tips': [
            'Always test VLOOKUP with a value you know exists.',
            'Use <strong>Tables</strong> instead of plain ranges for dynamic charts and pivots.',
            'Read the question for the exact function required &mdash; SUMIF vs SUMIFS matters.',
            'Format calculated cells in a different colour to track logic.',
            'Save as <code>.xlsx</code>; <code>.xls</code> loses some features.',
        ],
        'glossary': [
            ('VLOOKUP', 'Function that searches a value in the first column of a table.'),
            ('Pivot table', 'A summary tool that aggregates data dynamically.'),
            ('Conditional formatting', 'Format applied automatically based on a rule.'),
            ('Named range', 'A friendly name given to a cell or range.'),
            ('Sparkline', 'A tiny in-cell chart.'),
        ],
        'short_answer': ('Which function counts cells that match a criterion?', 'COUNTIF'),
    },

    'Database Concepts': {
        'mistakes': [
            ('Cannot enter data &mdash; "duplicate value" error.',
             'Field is set as the <strong>Primary Key</strong> or unique-indexed.',
             'Use a different value or change the field&rsquo;s indexed property.'),
            ('Query returns nothing.',
             'Criteria too strict or wrong field name.',
             'Run query with empty criteria first; check spelling.'),
            ('Form does not save changes.',
             'Form is bound to a query that is not updateable.',
             'Bind to the table directly or use a single-table query.'),
            ('Report shows duplicates.',
             'Joined tables created a Cartesian product.',
             'Add the missing join or use <code>SELECT DISTINCT</code>.'),
        ],
        'exam_tips': [
            'Always identify the Primary Key before designing tables.',
            'Use Design View, not Wizard, when accuracy matters.',
            'Practise drawing 1:1, 1:M and M:N relationships.',
            'Save queries with descriptive names (<code>qry_OverdueBooks</code>).',
            'Backup the <code>.accdb</code> before structural changes.',
        ],
        'glossary': [
            ('Primary Key', 'A field that uniquely identifies each record.'),
            ('Foreign Key', 'A field linking a record to another table.'),
            ('Query', 'A request for data that meets criteria.'),
            ('Form', 'A user-friendly interface for entering or viewing data.'),
            ('Report', 'Formatted output of data, usually for printing.'),
        ],
        'short_answer': ('What property makes a field uniquely identify a record?',
                         'Primary Key'),
    },

    'Advanced Presentations': {
        'mistakes': [
            ('Embedded video plays a black screen.',
             'Codec not installed, or file linked from a missing path.',
             'Re-insert as <strong>Embed</strong>, or convert to MP4 (H.264).'),
            ('Fonts look different on another PC.',
             'Custom fonts not embedded.',
             'File &rarr; Options &rarr; Save &rarr; tick <strong>Embed fonts in the file</strong>.'),
            ('Action button jumps to wrong slide.',
             'Hyperlink target was deleted; numbering shifted.',
             'Re-insert the action; choose slide by title not number.'),
            ('PDF export is huge.',
             'High-resolution images embedded uncompressed.',
             'File &rarr; Compress Pictures before exporting.'),
        ],
        'exam_tips': [
            'Apply the Slide Master before any per-slide formatting.',
            'Use the <strong>Selection Pane</strong> to manage layered objects.',
            'Test slideshow on the actual delivery PC if possible.',
            'Practise rehearse-timings to know your speech length.',
            'Always include a closing slide with a clear "Thank you / Questions" prompt.',
        ],
        'glossary': [
            ('Trigger', 'An animation that starts when an object is clicked.'),
            ('Hyperlink', 'A clickable link to another slide, file or URL.'),
            ('Action button', 'A pre-built shape with a hyperlink action.'),
            ('Selection Pane', 'A panel listing every object on a slide.'),
            ('Rehearse Timings', 'A feature that records how long each slide is shown.'),
        ],
        'short_answer': ('Which file extension is best for embedded video in PowerPoint?',
                         '.mp4'),
    },

    'System Software': {
        'mistakes': [
            ('PC suddenly very slow.',
             'Background updates or full disk.',
             'Check Task Manager; clear temp files with Disk Cleanup.'),
            ('Driver install fails.',
             'Wrong architecture (32 vs 64-bit) or unsigned driver.',
             'Download the matching version; use <strong>Run as administrator</strong>.'),
            ('Files refuse to delete.',
             'File is in use by another process.',
             'Close the application or restart in Safe Mode.'),
            ('System restore point missing.',
             'System Protection is off.',
             'Control Panel &rarr; System &rarr; <strong>Configure</strong> &rarr; turn on protection.'),
        ],
        'exam_tips': [
            'Know the difference between <strong>system</strong> and <strong>application</strong> software.',
            'Memorise common utility programs: antivirus, defragmenter, backup, compression.',
            'Practise listing installation steps in order.',
            'Recognise common file extensions and their owners.',
            'Be able to describe a typical update cycle.',
        ],
        'glossary': [
            ('OS', 'Operating system &mdash; manages hardware and software.'),
            ('Driver', 'Software that lets the OS talk to a hardware device.'),
            ('Utility', 'Helper program for maintenance (backup, antivirus).'),
            ('Patch', 'A small update that fixes bugs or security holes.'),
            ('Safe Mode', 'A diagnostic startup mode with minimal drivers.'),
        ],
        'short_answer': ('Name a Windows utility used to free up disk space.', 'Disk Cleanup'),
    },

    'Internet & Social Implications': {
        'mistakes': [
            ('Account hacked.',
             'Weak or reused password.',
             'Enable <strong>2FA</strong> and use a password manager.'),
            ('Phishing email opened.',
             'Looked like a legitimate brand.',
             'Disconnect from the network; report to IT; change passwords.'),
            ('Stolen identity used online.',
             'Personal info shared on social media.',
             'Lock down privacy settings; remove address &amp; ID number.'),
            ('Bank app shows unknown transactions.',
             'Card or password compromised.',
             'Block card immediately; report to the bank.'),
        ],
        'exam_tips': [
            'Distinguish <strong>e-commerce</strong> from <strong>e-banking</strong> &mdash; both are exam favourites.',
            'Know examples of cybercrime: phishing, hacking, identity theft.',
            'Be ready to discuss netiquette and digital citizenship.',
            'Mention legislation: ECT Act, POPIA.',
            'Use real-world South African examples in your answers.',
        ],
        'glossary': [
            ('Phishing', 'Trying to trick someone into revealing private info.'),
            ('2FA', 'Two-factor authentication &mdash; password + a second proof.'),
            ('Cookie', 'A small file storing site preferences in your browser.'),
            ('VPN', 'Virtual Private Network &mdash; encrypts traffic over the internet.'),
            ('POPIA', 'South African law protecting personal information.'),
        ],
        'short_answer': ('Which abbreviation describes adding a second login factor?', '2FA'),
    },

    # ============================ GRADE 12 ============================
    'Integrated Document Handling': {
        'mistakes': [
            ('Mail-merge data shows raw codes (e.g. <code>{ MERGEFIELD }</code>).',
             'Field codes are toggled on.',
             'Press <kbd>Alt</kbd>+<kbd>F9</kbd> to toggle results.'),
            ('Embedded Excel sheet does not update.',
             'It was pasted as a static picture.',
             'Re-paste using <strong>Paste Special &rarr; Link</strong>.'),
            ('Imported Access data has wrong types.',
             'Excel guessed wrong on import.',
             'Pre-format columns in Excel; re-import or use Get &amp; Transform.'),
            ('PDF lost hyperlinks.',
             'Exported via "Print to PDF" instead of Save As.',
             'Use File &rarr; Save As &rarr; <strong>PDF</strong> to keep links live.'),
        ],
        'exam_tips': [
            'Plan the data flow first &mdash; source &rarr; merge &rarr; output.',
            'Always verify the data source after merging.',
            'Use <strong>Paste Special &rarr; Link</strong> for live data.',
            'Open the PDF after export to verify hyperlinks.',
            'Check the brief for the exact deliverable file types.',
        ],
        'glossary': [
            ('OLE', 'Object Linking and Embedding &mdash; share objects between apps.'),
            ('Embed', 'Stores a copy of the object in the document.'),
            ('Link', 'Stores a reference to the original file.'),
            ('Mail merge', 'Combines a template with a data source.'),
            ('PDF', 'Portable Document Format &mdash; preserves layout across devices.'),
        ],
        'short_answer': ('Which key combo toggles field codes on or off?', 'Alt+F9'),
    },

    'Advanced Spreadsheet Functions': {
        'mistakes': [
            ('Macro disabled when opening file.',
             'File saved as <code>.xlsx</code> instead of <code>.xlsm</code>.',
             'Save As &rarr; choose <strong>Excel Macro-Enabled Workbook</strong>.'),
            ('Nested IF returns #VALUE!',
             'Mismatched parentheses.',
             'Use <strong>Formula Bar</strong> colour matching to find the problem.'),
            ('Data Validation rule ignored.',
             'Pasted values bypass validation.',
             'Use <strong>Data &rarr; Data Validation &rarr; Circle Invalid Data</strong>.'),
            ('Solver gives no solution.',
             'Constraints contradict each other.',
             'Loosen one constraint; verify with manual estimate.'),
        ],
        'exam_tips': [
            'Plan a nested IF on paper first to avoid bracket errors.',
            'Use named ranges to make formulas readable.',
            'Test every macro with a copy of the workbook open.',
            'Annotate complex formulas with comments (Insert &rarr; Comment).',
            'Save in <code>.xlsm</code> when macros are present.',
        ],
        'glossary': [
            ('Macro', 'A recorded sequence of actions, written in VBA.'),
            ('Nested function', 'A function placed inside another function.'),
            ('Solver', 'An add-in that finds an optimal value for a target cell.'),
            ('Data Validation', 'Rule limiting what can be entered in a cell.'),
            ('VBA', 'Visual Basic for Applications &mdash; the macro language.'),
        ],
        'short_answer': ('Which file extension stores Excel macros?', '.xlsm'),
    },

    'Advanced Databases': {
        'mistakes': [
            ('Cannot delete a record.',
             'Referential integrity links it to another table.',
             'Delete the related child records first or enable Cascade Delete.'),
            ('Calculated field not allowed in query.',
             'Wrong syntax in the field row.',
             'Use <code>FieldName: [Field1]*[Field2]</code> format.'),
            ('Subform shows no records.',
             'Link Master/Child fields not set.',
             'Open subform property sheet &rarr; set the linking fields.'),
            ('Macro action fails silently.',
             '"Single Step" disabled, hiding the error.',
             'Macro Tools &rarr; <strong>Single Step</strong> to debug.'),
        ],
        'exam_tips': [
            'Practise writing simple <code>SELECT</code> SQL by hand.',
            'Know the difference between an Inner Join and a Left Join.',
            'Use the Relationships window in every design question.',
            'Document each query with a one-line comment in the description.',
            'Save backups before running update or delete queries.',
        ],
        'glossary': [
            ('SQL', 'Structured Query Language &mdash; standard database query language.'),
            ('Join', 'Combining rows from two tables based on a common field.'),
            ('Cascade Update', 'Updates child records when a parent key changes.'),
            ('Subform', 'A form embedded inside another form.'),
            ('Index', 'A structure that speeds up searches on a field.'),
        ],
        'short_answer': ('Which SQL keyword retrieves data from a table?', 'SELECT'),
    },

    'Web & HTML Basics': {
        'mistakes': [
            ('Image broken on the page.',
             'Wrong path or filename case.',
             'Use a relative path; remember Linux servers are case-sensitive.'),
            ('CSS rule has no effect.',
             'A more specific rule overrides it.',
             'Use browser DevTools (<kbd>F12</kbd>) to inspect cascade.'),
            ('Page looks fine on PC, broken on phone.',
             'No viewport meta tag.',
             'Add <code>&lt;meta name="viewport" content="width=device-width"&gt;</code> in <code>&lt;head&gt;</code>.'),
            ('Form data not sent.',
             'Missing <code>name</code> attribute on inputs.',
             'Add <code>name=""</code> to every input you want submitted.'),
        ],
        'exam_tips': [
            'Indent your HTML &mdash; markers can read it.',
            'Always close every tag; HTML5 still rewards clean nesting.',
            'Memorise common tags: <code>p</code>, <code>a</code>, <code>img</code>, <code>ul</code>, <code>table</code>, <code>form</code>.',
            'Test your page in at least two browsers.',
            'Validate your code at <em>validator.w3.org</em> before submitting.',
        ],
        'glossary': [
            ('HTML', 'HyperText Markup Language &mdash; describes structure of a web page.'),
            ('CSS', 'Cascading Style Sheets &mdash; describes appearance.'),
            ('Tag', 'Element keyword wrapped in angle brackets, e.g. <code>&lt;p&gt;</code>.'),
            ('Attribute', 'A property of a tag, e.g. <code>href="..."</code>.'),
            ('Hyperlink', 'A clickable connection between resources, made with <code>&lt;a&gt;</code>.'),
        ],
        'short_answer': ('Which tag creates a hyperlink?', 'a'),
    },

    'Solution Development': {
        'mistakes': [
            ('Solution does not match the brief.',
             'Skipped the analysis phase.',
             'Re-read the brief and write requirements before coding.'),
            ('Used the wrong tool.',
             'Picked Excel for what should have been a database task.',
             'Match the tool to the data shape (records vs calculations).'),
            ('No backup before testing.',
             'Single working file got corrupted.',
             'Keep dated copies in a <code>backups/</code> folder.'),
            ('Documentation written last and forgotten.',
             'Time pressure at deadline.',
             'Document each phase as you finish it.'),
        ],
        'exam_tips': [
            'Follow the SDLC: Analyse, Design, Build, Test, Deploy, Document.',
            'Always justify your tool choice in writing.',
            'Show evidence of testing &mdash; screenshots count.',
            'Keep the user manual short and screenshot-driven.',
            'Submit one folder containing source + docs + executable / file.',
        ],
        'glossary': [
            ('SDLC', 'Software Development Life Cycle.'),
            ('Prototype', 'A first version used for feedback.'),
            ('Use case', 'A description of how a user interacts with the system.'),
            ('User manual', 'A how-to document for the end user.'),
            ('Backup', 'A second copy of a file kept in case the first is lost.'),
        ],
        'short_answer': ('What does SDLC stand for?', 'Software Development Life Cycle'),
    },

    'ICT & Society': {
        'mistakes': [
            ('Cited a Wikipedia article in an exam.',
             'Wikipedia is a starting point, not a primary source.',
             'Follow Wikipedia&rsquo;s reference list to the original source.'),
            ('Shared a copyrighted photo without credit.',
             'Misunderstood "free to use".',
             'Use Creative Commons sources and credit the author.'),
            ('Discussed AI without examples.',
             'Vague answers earn few marks.',
             'Mention real systems (ChatGPT, recommendation engines).'),
            ('Confused green computing with green energy.',
             'Different focus.',
             'Green computing = efficient ICT; green energy = renewable power source.'),
        ],
        'exam_tips': [
            'Always link impact to a stakeholder (citizen, business, government).',
            'Mention positives <em>and</em> negatives for balance.',
            'Use current South African examples wherever possible.',
            'Distinguish digital divide from digital literacy.',
            'Mention POPIA when discussing personal data.',
        ],
        'glossary': [
            ('Digital divide', 'The gap between those with and without ICT access.'),
            ('Green computing', 'Designing and using computers efficiently.'),
            ('AI', 'Artificial intelligence &mdash; machines performing tasks usually needing humans.'),
            ('IoT', 'Internet of Things &mdash; everyday objects connected to the internet.'),
            ('POPIA', 'South African personal-information protection law.'),
        ],
        'short_answer': ('What does IoT stand for?', 'Internet of Things'),
    },
}


# ---------------------------------------------------------------------------
# Lesson and quiz builders
# ---------------------------------------------------------------------------
def mistakes_lesson(course_title, mistakes):
    body = intro(
        'Lesson 8 &middot; Common Mistakes &amp; Troubleshooting',
        f'Smart students learn from their own mistakes. Brilliant students learn from everyone else&rsquo;s. '
        f'Here are the most common <strong>{course_title.lower()}</strong> traps and how to escape them.',
    )
    body += '<h2>Top problems and proven fixes</h2>'
    body += table(['Symptom', 'Cause', 'Fix'], mistakes)
    body += '<h3>Troubleshooting routine</h3>'
    body += steps([
        '<strong>Reproduce</strong> the problem &mdash; can you make it happen again?',
        '<strong>Isolate</strong> &mdash; remove things until the problem disappears.',
        '<strong>Research</strong> &mdash; copy the exact error message into a search engine.',
        '<strong>Try one fix at a time</strong> &mdash; never two.',
        '<strong>Document</strong> what worked so future-you (or a friend) can copy it.',
    ])
    body += callout(
        'try', 'fa-bug',
        'Practise like a pro',
        f'Pick any two problems above, recreate them on purpose, and apply the fix. '
        f'Write a one-paragraph summary in your own words.',
    )
    body += callout(
        'info', 'fa-life-ring',
        'When all else fails',
        'Restart the program, then the computer. If it still breaks &mdash; ask a classmate, '
        'then your teacher. Never silently delete work.',
    )
    return body


def exam_lesson(course_title, exam_tips, glossary):
    body = intro(
        'Lesson 9 &middot; Exam Preparation Toolkit',
        f'Use these tips and revision tricks to walk into the <strong>{course_title}</strong> '
        f'exam confident and prepared.',
    )
    body += '<h2>Top exam tips</h2>'
    body += '<ul>' + ''.join(f'<li>{t}</li>' for t in exam_tips) + '</ul>'

    body += '<h2>Quick-recall glossary</h2>'
    body += table(['Term', 'Definition'], glossary)

    body += '<h2>A 7-day revision plan</h2>'
    body += grid([
        {'icon': 'fa-calendar-day', 'title': 'Day 1-2',
         'body': 'Re-read every lesson summary; rewrite the key idea in 1 sentence each.'},
        {'icon': 'fa-pen-fancy',    'title': 'Day 3-4',
         'body': 'Redo every Try-this and quiz from memory; mark with a friend.'},
        {'icon': 'fa-stopwatch',    'title': 'Day 5',
         'body': 'Sit one full past paper under exam conditions.'},
        {'icon': 'fa-comments',     'title': 'Day 6',
         'body': 'Discuss tricky topics with a study partner; teach them = you learn it.'},
        {'icon': 'fa-bed',          'title': 'Day 7',
         'body': 'Light review only. Pack your stationery. Sleep early.'},
    ])

    body += callout(
        'key', 'fa-trophy',
        'Mark-grabbing checklist',
        'Read every question twice. Answer the easy ones first. Show working. '
        'Save / submit early. Re-check before time runs out.',
    )

    body += '<h3>Self-check</h3><ul>'
    body += '<li>Can you explain every glossary term without looking?</li>'
    body += '<li>Can you list the top 3 mistakes from Lesson 8?</li>'
    body += '<li>Have you done at least one full past paper?</li>'
    body += '</ul>'
    return body


def make_mastery_quiz(course_title, glossary, short_answer, mistakes, exam_tips):
    """Build a 10-question mastery quiz mixing question types."""
    questions = []

    # Q1-3: glossary as multiple-choice
    for i, (term, definition) in enumerate(glossary[:3]):
        wrong = [g[0] for g in glossary if g[0] != term][:3]
        opts = wrong + [term]
        # deterministic "shuffle"
        opts = sorted(opts)
        questions.append({
            'question_type': 'multiple_choice',
            'question_text': f'Which term is best described as: <em>{definition}</em>',
            'options': opts,
            'correct_answer': term,
            'explanation': f'<strong>{term}</strong> &mdash; {definition}',
        })

    # Q4: match columns from glossary (4 items)
    pick = glossary[:4]
    questions.append({
        'question_type': 'match_columns', 'points': 4,
        'question_text': 'Match each term with its definition.',
        'options': {
            'column_a': [t for t, _ in pick],
            'column_b': [d for _, d in pick],
        },
        'correct_answer': {t: d for t, d in pick},
        'explanation': 'Each definition belongs to exactly one term.',
    })

    # Q5-6: troubleshooting as multiple-choice
    for symptom, cause, fix in mistakes[:2]:
        wrong = [m[2] for m in mistakes if m[2] != fix][:3]
        opts = wrong + [fix]
        opts = sorted(opts)
        questions.append({
            'question_type': 'multiple_choice', 'points': 2,
            'question_text': f'Best fix for: <em>{symptom}</em>',
            'options': opts,
            'correct_answer': fix,
            'explanation': f'Cause: {cause} &mdash; Fix: {fix}',
        })

    # Q7: true/false from an exam tip
    if exam_tips:
        tip = exam_tips[0]
        questions.append({
            'question_type': 'true_false',
            'question_text': f'For the exam: &ldquo;{tip}&rdquo; &mdash; is this good advice?',
            'options': ['True', 'False'],
            'correct_answer': 'True',
            'explanation': 'Yes &mdash; this is one of the recommended exam tips.',
        })

    # Q8: drag-drop ordering: troubleshooting routine
    questions.append({
        'question_type': 'drag_drop', 'points': 3,
        'question_text': 'Order the troubleshooting routine from first to last.',
        'options': ['Document the fix', 'Reproduce the problem',
                    'Isolate the cause', 'Research the error', 'Try one fix at a time'],
        'correct_answer': ['Reproduce the problem', 'Isolate the cause',
                           'Research the error', 'Try one fix at a time',
                           'Document the fix'],
        'explanation': 'Reproduce &rarr; Isolate &rarr; Research &rarr; Try one fix &rarr; Document.',
    })

    # Q9: short answer from pack
    sa_q, sa_a = short_answer
    questions.append({
        'question_type': 'short_answer', 'points': 2,
        'question_text': sa_q,
        'options': [],
        'correct_answer': sa_a,
        'explanation': f'Correct answer: <strong>{sa_a}</strong>.',
    })

    # Q10: scenario MCQ
    if mistakes:
        symptom, cause, fix = mistakes[-1]
        wrong = [m[2] for m in mistakes if m[2] != fix][:3]
        opts = sorted(wrong + [fix])
        questions.append({
            'question_type': 'multiple_choice', 'points': 2,
            'question_text': f'Scenario question: while working you notice &mdash; <em>{symptom}</em> '
                             'What should you do first?',
            'options': opts,
            'correct_answer': fix,
            'explanation': f'Root cause: {cause}.',
        })

    return {
        'title': f'{course_title} — Mastery Quiz',
        'description': (f'Final mastery check for {course_title}. '
                        'Mixed question types testing concepts, troubleshooting and exam-ready knowledge.'),
        'quiz_type': 'quiz',
        'time_limit_minutes': 25,
        'pass_percentage': 65.0,
        'order': 3,
        'questions': [
            {'order': i + 1, 'points': q.get('points', 1), **q}
            for i, q in enumerate(questions)
        ],
    }


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------
def seed():
    summary = {
        'lessons_added': 0,
        'lessons_skipped': 0,
        'quizzes_added': 0,
        'quizzes_skipped': 0,
        'questions_added': 0,
        'courses_processed': 0,
        'courses_missing': 0,
    }

    with app.app_context():
        for course_title, pack in PACKS.items():
            course = Course.query.filter_by(title=course_title).first()
            if not course:
                summary['courses_missing'] += 1
                print(f'  ! course not found: {course_title}')
                continue
            summary['courses_processed'] += 1

            # ---------- Lesson 8 ----------
            lesson_defs = [
                (8, 25, 'Common Mistakes &amp; Troubleshooting',
                 mistakes_lesson(course_title, pack['mistakes'])),
                (9, 30, 'Exam Preparation Toolkit',
                 exam_lesson(course_title, pack['exam_tips'], pack['glossary'])),
            ]
            for order, duration, title, content in lesson_defs:
                exists = Lesson.query.filter_by(
                    course_id=course.id, order=order).first()
                if exists:
                    summary['lessons_skipped'] += 1
                    continue
                db.session.add(Lesson(
                    course_id=course.id, order=order, title=title,
                    content=content, duration_minutes=duration,
                ))
                summary['lessons_added'] += 1

            # ---------- Mastery quiz ----------
            quiz_data = make_mastery_quiz(
                course_title, pack['glossary'], pack['short_answer'],
                pack['mistakes'], pack['exam_tips'],
            )
            existing_quiz = Quiz.query.filter_by(
                course_id=course.id, title=quiz_data['title']).first()
            if existing_quiz:
                summary['quizzes_skipped'] += 1
            else:
                quiz = Quiz(
                    course_id=course.id,
                    title=quiz_data['title'],
                    description=quiz_data['description'],
                    quiz_type=quiz_data['quiz_type'],
                    time_limit_minutes=quiz_data['time_limit_minutes'],
                    pass_percentage=quiz_data['pass_percentage'],
                    order=quiz_data['order'],
                )
                db.session.add(quiz)
                db.session.flush()
                for q in quiz_data['questions']:
                    db.session.add(Question(
                        quiz_id=quiz.id,
                        question_text=q['question_text'],
                        question_type=q['question_type'],
                        options=json.dumps(q['options']),
                        correct_answer=json.dumps(q['correct_answer']),
                        points=q.get('points', 1),
                        order=q['order'],
                        explanation=q.get('explanation', ''),
                    ))
                    summary['questions_added'] += 1
                summary['quizzes_added'] += 1

        db.session.commit()

    print('=' * 60)
    print('Mastery-content seeder — summary')
    print('=' * 60)
    for k, v in summary.items():
        print(f'  {k:.<30} {v}')
    print('=' * 60)


if __name__ == '__main__':
    seed()
