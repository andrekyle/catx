"""
Seed Grade 10 Word Processing lessons + activities.
CAPS-aligned (Computer Applications Technology, Grade 10 - Word Processing module).

Idempotent: safe to re-run; only adds missing lessons/quizzes/questions.

Run:
    python seed_grade10_word.py
"""
import json
from app import app, db, Grade, Course, Lesson, Quiz, Question


# ---------------------------------------------------------------------------
# LESSONS  (rendered as raw HTML in templates/lesson.html via |safe)
# ---------------------------------------------------------------------------

def _kbd(*keys):
    """Helper to render a keyboard combo like Ctrl + S."""
    parts = []
    for i, k in enumerate(keys):
        if i: parts.append('<span class="plus">+</span>')
        parts.append(f'<span class="kbd">{k}</span>')
    return '<span class="kbd-combo">' + ''.join(parts) + '</span>'


LESSONS = [
    {
        'order': 1,
        'duration_minutes': 25,
        'title': 'Introduction to Microsoft Word',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 1 &middot; Get Started</div>
  <p>Microsoft Word is the most popular tool in the world for typing documents. By the end of this lesson you'll know what Word is, why people use it, and how to recognise the different file types.</p>
</div>

<h2>What is Microsoft Word?</h2>
<p>Microsoft Word is a <strong>word processing application</strong> used to create, edit, format and print text-based documents such as letters, reports, CVs and assignments. It is part of the <em>Microsoft Office</em> family.</p>

<div class="callout info">
  <div class="ico"><i class="fas fa-lightbulb"></i></div>
  <div class="body"><strong>Did you know?</strong>Word was first released in 1983 &mdash; older than most of your teachers! Today over <strong>1.2 billion people</strong> use it.</div>
</div>

<h3>Why use a word processor?</h3>
<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-pen"></i> Easy editing</h4><p>Fix mistakes without retyping. Move whole paragraphs around in seconds.</p></div>
  <div class="card-mini"><h4><i class="fas fa-spell-check"></i> Spell &amp; grammar</h4><p>Wavy red and blue lines spot mistakes as you type.</p></div>
  <div class="card-mini"><h4><i class="fas fa-paint-brush"></i> Professional look</h4><p>Headings, fonts, colours, tables and pictures &mdash; all built in.</p></div>
  <div class="card-mini"><h4><i class="fas fa-share-nodes"></i> Easy to share</h4><p>Email, print or save as PDF and send to anyone.</p></div>
</div>

<h3>Common file extensions</h3>
<table>
  <tr><th>Extension</th><th>What it is</th></tr>
  <tr><td><code>.docx</code></td><td>Default Word format (2007 onwards). XML-based and compact.</td></tr>
  <tr><td><code>.doc</code></td><td>Older Word 97&ndash;2003 format.</td></tr>
  <tr><td><code>.pdf</code></td><td>Portable Document Format &mdash; read-only, layout preserved.</td></tr>
  <tr><td><code>.rtf</code></td><td>Rich Text Format &mdash; works across word processors.</td></tr>
  <tr><td><code>.txt</code></td><td>Plain text only. <strong>No</strong> formatting.</td></tr>
</table>

<div class="callout key">
  <div class="ico"><i class="fas fa-key"></i></div>
  <div class="body"><strong>Key term</strong><strong>Word processor</strong> = software for creating documents made mostly of text.</div>
</div>

<h3>Starting Word</h3>
<ol class="steps">
  <li>Click the <strong>Start</strong> button (Windows logo) at the bottom-left.</li>
  <li>Type "Word" and press """ + _kbd('Enter') + """.</li>
  <li>Choose <strong>Blank document</strong>, or pick a ready-made <strong>template</strong> like CV or report.</li>
</ol>

<div class="callout try">
  <div class="ico"><i class="fas fa-rocket"></i></div>
  <div class="body"><strong>Try it!</strong>Open Word right now and create a blank document. Type your name and the date. You've made your first Word document!</div>
</div>
"""
    },
    {
        'order': 2,
        'duration_minutes': 30,
        'title': 'The Word Interface',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 2 &middot; The Workspace</div>
  <p>Knowing what every part of the Word window does is like knowing where the buttons are in a car &mdash; once you do, you drive much faster.</p>
</div>

<h2>Touring the Word window</h2>
<p>The Word screen has several parts. Each one has a job:</p>

<table>
  <tr><th>Part</th><th>What it does</th></tr>
  <tr><td><strong>Title Bar</strong></td><td>Shows the document name at the very top.</td></tr>
  <tr><td><strong>Quick Access Toolbar</strong></td><td>Tiny toolbar with Save, Undo, Redo. You can add your favourites.</td></tr>
  <tr><td><strong>Ribbon</strong></td><td>Wide toolbar with tabs (Home, Insert, Layout, References, Mailings, Review, View). Each tab is split into <em>groups</em>.</td></tr>
  <tr><td><strong>File tab (Backstage)</strong></td><td>New, Open, Save, Save As, Print, Share, Options.</td></tr>
  <tr><td><strong>Document area</strong></td><td>The white "page" where you type.</td></tr>
  <tr><td><strong>Insertion point</strong></td><td>Flashing line that shows where text will appear.</td></tr>
  <tr><td><strong>Rulers</strong></td><td>Used for margins, tabs and indents.</td></tr>
  <tr><td><strong>Scroll bars</strong></td><td>Move through long documents.</td></tr>
  <tr><td><strong>Status bar</strong></td><td>Page number, word count, language, zoom slider, view buttons.</td></tr>
</table>

<h3>The three main views</h3>
<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-print"></i> Print Layout</h4><p>How the page will look when printed. Most common view.</p></div>
  <div class="card-mini"><h4><i class="fas fa-book-open"></i> Read Mode</h4><p>Clean, full-screen view for reading without distractions.</p></div>
  <div class="card-mini"><h4><i class="fas fa-globe"></i> Web Layout</h4><p>How the document would look as a web page.</p></div>
</div>

<div class="callout tip">
  <div class="ico"><i class="fas fa-bolt"></i></div>
  <div class="body"><strong>Pro tip</strong>Press """ + _kbd('Ctrl', 'F1') + """ to hide or show the Ribbon and get more screen space.</div>
</div>

<div class="callout key">
  <div class="ico"><i class="fas fa-key"></i></div>
  <div class="body"><strong>Key terms</strong><strong>Ribbon</strong> = the strip of tabs and buttons at the top.<br><strong>Tab</strong> = one section of the Ribbon (e.g. Home).<br><strong>Group</strong> = related buttons inside a tab (e.g. Font group).</div>
</div>
"""
    },
    {
        'order': 3,
        'duration_minutes': 30,
        'title': 'Creating, Opening and Saving Documents',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 3 &middot; File Skills</div>
  <p>Computers crash. Power goes off. The single most important habit in Word is <strong>save, save, save</strong>. Let's learn the right way.</p>
</div>

<h2>Working with documents</h2>

<h3>Create a new document</h3>
<p>Click <strong>File &rarr; New &rarr; Blank document</strong> or press """ + _kbd('Ctrl', 'N') + """.</p>

<h3>Open an existing document</h3>
<p>Click <strong>File &rarr; Open</strong> (""" + _kbd('Ctrl', 'O') + """) and browse to the folder. Recent documents appear under <em>Recent</em> for one-click access.</p>

<h3>Save vs Save As &mdash; what's the difference?</h3>
<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-floppy-disk"></i> Save (""" + _kbd('Ctrl', 'S') + """)</h4><p>Updates the existing file with your latest changes. Same name, same place.</p></div>
  <div class="card-mini"><h4><i class="fas fa-copy"></i> Save As (""" + _kbd('F12') + """)</h4><p>Creates a <strong>new copy</strong>. Lets you change the name, the folder, or the file type.</p></div>
</div>

<div class="callout warn">
  <div class="ico"><i class="fas fa-triangle-exclamation"></i></div>
  <div class="body"><strong>Watch out</strong>The <strong>first</strong> time you save a brand-new document, Save and Save&nbsp;As both ask you for a name and location. After that, plain Save just overwrites silently.</div>
</div>

<h3>Saving in another format</h3>
<p>In <strong>Save As &rarr; Save as type</strong> you can choose:</p>
<ul>
  <li><code>.pdf</code> &ndash; for sharing a read-only copy that looks the same on every computer.</li>
  <li><code>.doc</code> &ndash; for opening on older versions of Word.</li>
  <li><code>.txt</code> &ndash; plain text only (loses all formatting).</li>
</ul>

<h3>AutoSave &amp; AutoRecover &mdash; your safety net</h3>
<p>If you save your document to <strong>OneDrive</strong>, AutoSave saves your changes every few seconds. AutoRecover keeps a backup so you don't lose work if Word crashes.</p>

<div class="callout tip">
  <div class="ico"><i class="fas fa-bolt"></i></div>
  <div class="body"><strong>Pro tip</strong>Get into the habit of pressing """ + _kbd('Ctrl', 'S') + """ every time you finish a paragraph. Future you will thank you!</div>
</div>

<h3>Closing &amp; exiting</h3>
<ul>
  <li>Close just this document: """ + _kbd('Ctrl', 'W') + """.</li>
  <li>Exit Word completely: """ + _kbd('Alt', 'F4') + """ or click the <strong>X</strong> at the top-right.</li>
</ul>
"""
    },
    {
        'order': 4,
        'duration_minutes': 35,
        'title': 'Editing Text: Selecting, Moving and Copying',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 4 &middot; The Power of Editing</div>
  <p>You'll edit text 100x more often than you'll type fresh. Master selection, the clipboard and undo &mdash; and you become a Word ninja.</p>
</div>

<h2>Selecting text the smart way</h2>
<table>
  <tr><th>Action</th><th>What it selects</th></tr>
  <tr><td>Click and drag</td><td>Any range you sweep over.</td></tr>
  <tr><td>Double-click</td><td>One <strong>word</strong>.</td></tr>
  <tr><td>Triple-click</td><td>An entire <strong>paragraph</strong>.</td></tr>
  <tr><td>""" + _kbd('Ctrl', 'A') + """</td><td>The <strong>whole document</strong>.</td></tr>
  <tr><td>""" + _kbd('Shift') + """ + click</td><td>Extend the current selection to where you click.</td></tr>
</table>

<h2>The clipboard &mdash; cut, copy, paste</h2>
<p>Think of the <strong>clipboard</strong> as a temporary holding area. When you cut or copy, your text waits there until you paste it somewhere.</p>

<table>
  <tr><th>Action</th><th>Shortcut</th><th>What it does</th></tr>
  <tr><td>Cut</td><td>""" + _kbd('Ctrl', 'X') + """</td><td>Removes the selection and stores it on the clipboard.</td></tr>
  <tr><td>Copy</td><td>""" + _kbd('Ctrl', 'C') + """</td><td>Copies the selection (original stays in place).</td></tr>
  <tr><td>Paste</td><td>""" + _kbd('Ctrl', 'V') + """</td><td>Inserts the clipboard contents at the cursor.</td></tr>
</table>

<h2>Undo and Redo &mdash; your time machine</h2>
<p>Pressed Delete by accident? No problem.</p>
<ul>
  <li>""" + _kbd('Ctrl', 'Z') + """ &ndash; <strong>Undo</strong> the last action. Press it many times to step back further.</li>
  <li>""" + _kbd('Ctrl', 'Y') + """ &ndash; <strong>Redo</strong> something you just undid.</li>
</ul>

<div class="callout tip">
  <div class="ico"><i class="fas fa-bolt"></i></div>
  <div class="body"><strong>Pro tip</strong>If something just went wrong, hit """ + _kbd('Ctrl', 'Z') + """ <em>first</em>, then think. Don't try to "fix" it manually.</div>
</div>

<h2>Find &amp; Replace</h2>
<ul>
  <li>""" + _kbd('Ctrl', 'F') + """ &ndash; <strong>Find</strong>: locate every occurrence of a word.</li>
  <li>""" + _kbd('Ctrl', 'H') + """ &ndash; <strong>Replace</strong>: swap one word for another. Use <em>Replace All</em> with care!</li>
</ul>

<h2>Spell &amp; grammar check</h2>
<p>Red squiggly = spelling error. Blue/green squiggly = grammar issue. Right-click for suggestions, or press """ + _kbd('F7') + """ to step through them all.</p>

<div class="callout warn">
  <div class="ico"><i class="fas fa-triangle-exclamation"></i></div>
  <div class="body"><strong>Watch out</strong>Spell check can't tell <em>their</em>, <em>there</em> and <em>they're</em> apart in every case. Always proofread yourself.</div>
</div>
"""
    },
    {
        'order': 5,
        'duration_minutes': 35,
        'title': 'Character Formatting',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 5 &middot; Make It Look Good</div>
  <p>Character formatting changes how individual letters and words <em>look</em>. The right font and size can turn a plain assignment into a professional document.</p>
</div>

<h2>Common character options</h2>
<p>All of these live on the <strong>Home</strong> tab in the <strong>Font</strong> group.</p>

<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-font"></i> Font</h4><p>The <em>typeface</em> &mdash; e.g. Calibri, Arial, Times New Roman.</p></div>
  <div class="card-mini"><h4><i class="fas fa-text-height"></i> Size</h4><p>Measured in <strong>points</strong> (pt). Body = 11&ndash;12 pt, headings 14&ndash;18 pt.</p></div>
  <div class="card-mini"><h4><i class="fas fa-palette"></i> Colour</h4><p>Pick from the colour palette or "More Colors&hellip;" for any shade.</p></div>
  <div class="card-mini"><h4><i class="fas fa-bold"></i> Style</h4><p><strong>Bold</strong>, <em>italic</em>, <u>underline</u>, strikethrough, sub/superscript.</p></div>
</div>

<h3>Essential shortcuts</h3>
<table>
  <tr><th>Effect</th><th>Shortcut</th></tr>
  <tr><td><strong>Bold</strong></td><td>""" + _kbd('Ctrl', 'B') + """</td></tr>
  <tr><td><em>Italic</em></td><td>""" + _kbd('Ctrl', 'I') + """</td></tr>
  <tr><td><u>Underline</u></td><td>""" + _kbd('Ctrl', 'U') + """</td></tr>
  <tr><td>Subscript (H<sub>2</sub>O)</td><td>""" + _kbd('Ctrl', '=') + """</td></tr>
  <tr><td>Superscript (x<sup>2</sup>)</td><td>""" + _kbd('Ctrl', 'Shift', '+') + """</td></tr>
</table>

<h3>Change Case</h3>
<p>Found a paragraph in CAPS LOCK? Don't retype it! Select it and use <strong>Home &rarr; Aa &rarr; Change Case</strong>: Sentence case, lowercase, UPPERCASE, Capitalize Each Word, tOGGLE cASE.</p>

<h3>Format Painter &mdash; the magic paintbrush</h3>
<p>Click on text that's already formatted, click the <strong>Format Painter</strong> (paintbrush icon), then drag over other text to copy the formatting.</p>

<div class="callout tip">
  <div class="ico"><i class="fas fa-bolt"></i></div>
  <div class="body"><strong>Pro tip</strong><strong>Double-click</strong> the Format Painter to keep it on, then apply to several places. Press """ + _kbd('Esc') + """ to turn it off.</div>
</div>

<div class="callout warn">
  <div class="ico"><i class="fas fa-triangle-exclamation"></i></div>
  <div class="body"><strong>Best practice</strong>Use no more than <strong>2 fonts</strong> per document &mdash; one for headings, one for body. Keep body text 11&ndash;12 pt.</div>
</div>
"""
    },
    {
        'order': 6,
        'duration_minutes': 35,
        'title': 'Paragraph Formatting',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 6 &middot; Layout &amp; Spacing</div>
  <p>A "paragraph" in Word is anything that ends with """ + _kbd('Enter') + """. Paragraph formatting changes whole blocks at once &mdash; alignment, spacing, indents and more.</p>
</div>

<h2>Alignment</h2>
<table>
  <tr><th>Alignment</th><th>Shortcut</th><th>Use it for</th></tr>
  <tr><td>Left</td><td>""" + _kbd('Ctrl', 'L') + """</td><td>Default body text.</td></tr>
  <tr><td>Centre</td><td>""" + _kbd('Ctrl', 'E') + """</td><td>Headings, titles.</td></tr>
  <tr><td>Right</td><td>""" + _kbd('Ctrl', 'R') + """</td><td>Dates, addresses on letters.</td></tr>
  <tr><td>Justify</td><td>""" + _kbd('Ctrl', 'J') + """</td><td>Newspaper-style straight edges both sides.</td></tr>
</table>

<h2>Line and paragraph spacing</h2>
<p>Use <strong>Home &rarr; Paragraph &rarr; Line and Paragraph Spacing</strong> to set 1.0, 1.5 or 2.0 (double). You can also add <em>Space Before</em> and <em>Space After</em> for breathing room between paragraphs.</p>

<h2>Indents &mdash; pushing text in</h2>
<div class="lesson-grid">
  <div class="card-mini"><h4>Left / Right indent</h4><p>Pushes the <strong>whole paragraph</strong> in from the side.</p></div>
  <div class="card-mini"><h4>First line indent</h4><p>Only the <strong>first line</strong> is pushed in (essay style).</p></div>
  <div class="card-mini"><h4>Hanging indent</h4><p>First line stays, the <strong>rest</strong> is indented (used in bibliographies).</p></div>
  <div class="card-mini"><h4>Negative indent</h4><p>Pushes text <em>outside</em> the margin.</p></div>
</div>

<h2>Borders and shading</h2>
<p>Add a coloured background or a frame around any paragraph using <strong>Home &rarr; Paragraph &rarr; Borders</strong> and <strong>Shading</strong>. Great for highlighting a quote or warning.</p>

<h2>Tab stops</h2>
<p>Press """ + _kbd('Tab') + """ to jump to the next tab stop (default every 1.27 cm). Click on the ruler to set your own custom tabs &mdash; left, centre, right or decimal.</p>

<div class="callout key">
  <div class="ico"><i class="fas fa-key"></i></div>
  <div class="body"><strong>Key idea</strong>Use <strong>tabs</strong>, not multiple spaces, to line up text. Tabs always line up perfectly &mdash; spaces don't.</div>
</div>
"""
    },
    {
        'order': 7,
        'duration_minutes': 25,
        'title': 'Bulleted, Numbered and Multilevel Lists',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 7 &middot; Organising Information</div>
  <p>Lists turn long, hard-to-read sentences into clear, scannable points. Pick the right type and your reader will thank you.</p>
</div>

<h2>When to use which list</h2>
<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-circle"></i> Bulleted</h4><p>For items with <strong>no order</strong>: shopping lists, features, ingredients.</p></div>
  <div class="card-mini"><h4><i class="fas fa-list-ol"></i> Numbered</h4><p>For items in a <strong>specific order</strong>: recipe steps, instructions.</p></div>
  <div class="card-mini"><h4><i class="fas fa-sitemap"></i> Multilevel</h4><p>For items with <strong>sub-items</strong> like 1, 1.1, 1.1.1.</p></div>
</div>

<h2>Creating a list</h2>
<ol class="steps">
  <li>Click where the list must start.</li>
  <li>On the <strong>Home</strong> tab, click <em>Bullets</em>, <em>Numbering</em> or <em>Multilevel List</em>.</li>
  <li>Type your first item and press """ + _kbd('Enter') + """ for the next line.</li>
  <li>Press """ + _kbd('Enter') + """ <strong>twice</strong> to end the list.</li>
</ol>

<h2>Changing levels (sub-lists)</h2>
<table>
  <tr><th>Action</th><th>Key</th></tr>
  <tr><td><strong>Demote</strong> (push deeper)</td><td>""" + _kbd('Tab') + """</td></tr>
  <tr><td><strong>Promote</strong> (pull back out)</td><td>""" + _kbd('Shift', 'Tab') + """</td></tr>
</table>

<h2>Customising bullets / numbers</h2>
<p>Click the small arrow next to <em>Bullets</em> or <em>Numbering</em> to choose a different symbol (&bull; &#9658; &#10003;) or number style (1, A, i, I).</p>

<div class="callout tip">
  <div class="ico"><i class="fas fa-bolt"></i></div>
  <div class="body"><strong>Pro tip</strong>If a numbered list mysteriously restarts at 1, right-click the offending item and choose <strong>Continue Numbering</strong>.</div>
</div>
"""
    },
    {
        'order': 8,
        'duration_minutes': 30,
        'title': 'Page Layout: Margins, Orientation and Size',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 8 &middot; The Big Picture</div>
  <p>Page layout settings decide how your document fits on the printed page. All of them live on the <strong>Layout</strong> tab.</p>
</div>

<h2>Margins &mdash; the white space around the edge</h2>
<p>Word offers presets:</p>
<ul>
  <li><strong>Normal</strong> &ndash; 2.54 cm all round (default).</li>
  <li><strong>Narrow</strong> &ndash; 1.27 cm. Good for fitting more text.</li>
  <li><strong>Moderate</strong>, <strong>Wide</strong> &ndash; pre-set values.</li>
  <li><strong>Custom Margins&hellip;</strong> &ndash; type your own values.</li>
</ul>

<h2>Orientation</h2>
<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-mobile-screen"></i> Portrait</h4><p>Taller than wide. Used for letters, essays and most documents.</p></div>
  <div class="card-mini"><h4><i class="fas fa-mobile-screen" style="transform:rotate(90deg);"></i> Landscape</h4><p>Wider than tall. Used for wide tables, posters and certificates.</p></div>
</div>

<h2>Paper size</h2>
<p>South African schools and offices use <strong>A4</strong> (21 cm &times; 29.7 cm). Other options: Letter, Legal, A3, A5.</p>

<h2>Columns</h2>
<p><strong>Layout &rarr; Columns</strong> splits text into 1, 2 or 3 columns &mdash; great for newsletters and brochures.</p>

<h2>Page and section breaks</h2>
<table>
  <tr><th>Break</th><th>Shortcut</th><th>Effect</th></tr>
  <tr><td>Page break</td><td>""" + _kbd('Ctrl', 'Enter') + """</td><td>Forces text onto a new page.</td></tr>
  <tr><td>Section break</td><td>Layout &rarr; Breaks</td><td>Allows different layout (e.g. landscape) for part of the document.</td></tr>
</table>

<div class="callout key">
  <div class="ico"><i class="fas fa-key"></i></div>
  <div class="body"><strong>Key term</strong><strong>Section break</strong> = an invisible divider that lets you change page settings (margins, orientation, headers) for just one part of a document.</div>
</div>

<h2>Watermarks, page colour and borders</h2>
<p>On the <strong>Design</strong> tab you can add a page <em>watermark</em> ("DRAFT", "CONFIDENTIAL"), a background <em>colour</em>, or a decorative <em>page border</em>.</p>
"""
    },
    {
        'order': 9,
        'duration_minutes': 25,
        'title': 'Headers, Footers and Page Numbers',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 9 &middot; Top &amp; Bottom of Every Page</div>
  <p>Information that should appear on <strong>every page</strong> &mdash; like your name, the document title or page numbers &mdash; belongs in the header or footer.</p>
</div>

<h2>What's the difference?</h2>
<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-arrow-up"></i> Header</h4><p>Appears at the <strong>top</strong> of every page.</p></div>
  <div class="card-mini"><h4><i class="fas fa-arrow-down"></i> Footer</h4><p>Appears at the <strong>bottom</strong> of every page.</p></div>
</div>

<h2>Inserting a header or footer</h2>
<ol class="steps">
  <li>Click <strong>Insert &rarr; Header</strong> (or <strong>Footer</strong>).</li>
  <li>Choose a built-in design, or pick <em>Edit Header / Edit Footer</em> to start blank.</li>
  <li>Type your information.</li>
  <li>Click <strong>Close Header and Footer</strong> (or double-click in the body).</li>
</ol>

<h2>Useful items to put there</h2>
<ul>
  <li>Document title or your name and grade.</li>
  <li><strong>Date &amp; Time</strong> &mdash; can update automatically.</li>
  <li><strong>Page Number</strong>: <em>Insert &rarr; Page Number</em>. Choose 1, 2, 3 or i, ii, iii or "Page X of Y".</li>
  <li>School logo &mdash; insert a small picture.</li>
</ul>

<h2>Different first page or odd/even pages</h2>
<p>In <strong>Header &amp; Footer Tools &rarr; Design</strong>, tick:</p>
<ul>
  <li><strong>Different First Page</strong> &mdash; cover page has no header.</li>
  <li><strong>Different Odd &amp; Even Pages</strong> &mdash; book-style layout.</li>
</ul>

<div class="callout tip">
  <div class="ico"><i class="fas fa-bolt"></i></div>
  <div class="body"><strong>Pro tip</strong>For a school assignment, put your <strong>name + grade</strong> in the header and the <strong>page number</strong> in the footer. Easy marks!</div>
</div>
"""
    },
    {
        'order': 10,
        'duration_minutes': 35,
        'title': 'Working with Tables',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 10 &middot; Rows, Columns &amp; Cells</div>
  <p>Tables organise information into <strong>rows</strong> and <strong>columns</strong>. The intersection of a row and a column is a <strong>cell</strong>.</p>
</div>

<h2>Inserting a table</h2>
<ol class="steps">
  <li>Click where the table must go.</li>
  <li>Click <strong>Insert &rarr; Table</strong>.</li>
  <li>Drag across the grid to choose how many rows and columns &mdash; <em>or</em> click <strong>Insert Table&hellip;</strong> to type exact numbers.</li>
</ol>

<h2>Moving around in a table</h2>
<table>
  <tr><th>Key</th><th>What it does</th></tr>
  <tr><td>""" + _kbd('Tab') + """</td><td>Move to the <strong>next</strong> cell. (Creates a new row at the end!)</td></tr>
  <tr><td>""" + _kbd('Shift', 'Tab') + """</td><td>Move to the <strong>previous</strong> cell.</td></tr>
  <tr><td>Arrow keys</td><td>Move character by character.</td></tr>
</table>

<h2>Editing tables &mdash; the Layout tab</h2>
<p>When the cursor is in a table, two extra tabs appear: <strong>Table Design</strong> and <strong>Layout</strong>. From here you can:</p>
<ul>
  <li><strong>Insert</strong> rows or columns above, below, left or right.</li>
  <li><strong>Delete</strong> a cell, row, column or the whole table.</li>
  <li><strong>Merge cells</strong> &mdash; combine selected cells into one big one.</li>
  <li><strong>Split cells</strong> &mdash; divide one cell into many.</li>
  <li><strong>AutoFit</strong> &mdash; resize to contents or window.</li>
  <li><strong>Sort</strong> data alphabetically or numerically.</li>
</ul>

<h2>Formatting your table</h2>
<p>Apply a ready-made <strong>Table Style</strong> from the gallery for instant good looks. Then tweak <strong>Borders</strong>, <strong>Shading</strong> and cell <strong>alignment</strong> (top-left, centre, bottom-right etc.).</p>

<div class="callout warn">
  <div class="ico"><i class="fas fa-triangle-exclamation"></i></div>
  <div class="body"><strong>Watch out</strong>Pressing """ + _kbd('Tab') + """ in the <em>last</em> cell creates a brand-new row. Press """ + _kbd('Enter') + """ instead to add a line <em>inside</em> the cell.</div>
</div>

<div class="callout key">
  <div class="ico"><i class="fas fa-key"></i></div>
  <div class="body"><strong>Key terms</strong><strong>Row</strong> = horizontal line of cells. <strong>Column</strong> = vertical line of cells. <strong>Cell</strong> = where they meet.</div>
</div>
"""
    },
    {
        'order': 11,
        'duration_minutes': 30,
        'title': 'Inserting Pictures, Shapes and SmartArt',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 11 &middot; Make It Visual</div>
  <p>"A picture tells a thousand words." Adding visuals makes a document more interesting <em>and</em> easier to understand.</p>
</div>

<h2>Insert a picture</h2>
<ol class="steps">
  <li>Click where the picture must go.</li>
  <li><strong>Insert &rarr; Pictures</strong>.</li>
  <li>Choose <em>This Device</em> (file you saved) or <em>Online Pictures</em> (search the web).</li>
  <li>Pick the picture and click <strong>Insert</strong>.</li>
</ol>

<h2>Resizing and rotating</h2>
<p>Click the picture to select it, then:</p>
<ul>
  <li>Drag a <strong>corner handle</strong> to resize <em>proportionally</em> (no squashing).</li>
  <li>Drag a <strong>side handle</strong> to stretch in only one direction.</li>
  <li>Drag the <strong>green circular handle</strong> on top to rotate.</li>
</ul>

<h2>Text wrapping &mdash; how text flows around the picture</h2>
<table>
  <tr><th>Wrap option</th><th>Effect</th></tr>
  <tr><td>In Line with Text</td><td>Picture sits inside the line, like a giant character. (Default)</td></tr>
  <tr><td>Square / Tight</td><td>Text flows around the picture on all sides.</td></tr>
  <tr><td>Behind Text</td><td>Picture sits <em>behind</em> the words.</td></tr>
  <tr><td>In Front of Text</td><td>Picture sits <em>on top</em> of the words.</td></tr>
</table>

<h2>Picture tools</h2>
<p>The <strong>Picture Format</strong> tab gives you:</p>
<ul>
  <li><strong>Crop</strong> &mdash; chop off unwanted edges.</li>
  <li>Brightness, contrast, colour adjustments.</li>
  <li>Artistic effects (pencil sketch, blur, glow).</li>
  <li>Picture borders and styles.</li>
</ul>

<h2>Shapes, Icons, SmartArt and WordArt</h2>
<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-shapes"></i> Shapes</h4><p>Lines, arrows, rectangles, callouts, stars.</p></div>
  <div class="card-mini"><h4><i class="fas fa-icons"></i> Icons</h4><p>Modern symbols (recolour them in Picture Format).</p></div>
  <div class="card-mini"><h4><i class="fas fa-diagram-project"></i> SmartArt</h4><p>Ready-made diagrams: lists, processes, hierarchies, cycles.</p></div>
  <div class="card-mini"><h4><i class="fas fa-w"></i> WordArt</h4><p>Stylised, decorative text for posters and titles.</p></div>
</div>

<div class="callout warn">
  <div class="ico"><i class="fas fa-triangle-exclamation"></i></div>
  <div class="body"><strong>Watch out</strong>Always credit the source of online pictures. Using copyright-protected images without permission is <strong>plagiarism</strong>.</div>
</div>
"""
    },
    {
        'order': 12,
        'duration_minutes': 35,
        'title': 'Styles, Table of Contents and Mail Merge',
        'content': """
<div class="lesson-intro">
  <div class="label">Lesson 12 &middot; Pro-Level Word</div>
  <p>These three features separate beginners from power users. Master them and you'll save <em>hours</em> on every long document.</p>
</div>

<h2>Styles &mdash; consistent formatting in one click</h2>
<p>A <strong>style</strong> is a saved package of formatting (font, size, colour, spacing). Word's built-in styles include <em>Normal</em>, <em>Heading 1</em>, <em>Heading 2</em>, <em>Title</em> and <em>Quote</em>.</p>

<div class="callout key">
  <div class="ico"><i class="fas fa-key"></i></div>
  <div class="body"><strong>Why use styles?</strong>One consistent look throughout. Change a style once and every paragraph using it updates instantly. <strong>Required</strong> for an automatic Table of Contents.</div>
</div>

<h2>Automatic Table of Contents (TOC)</h2>
<ol class="steps">
  <li>Apply <strong>Heading 1, 2, 3</strong> styles to your headings.</li>
  <li>Click where the TOC must appear (usually after the cover page).</li>
  <li><strong>References &rarr; Table of Contents</strong> and pick a style.</li>
  <li>If headings change, click the TOC and choose <strong>Update Table</strong>.</li>
</ol>

<h2>Mail Merge &mdash; one letter, hundreds of names</h2>
<p><strong>Mail merge</strong> creates many personalised copies of one document by combining a <em>main document</em> with a <em>data source</em> (a list of names and details).</p>

<h3>The five steps</h3>
<ol class="steps">
  <li><strong>Mailings &rarr; Start Mail Merge</strong> &mdash; choose Letters, Envelopes, Labels or Email.</li>
  <li><strong>Select Recipients</strong> &mdash; type a new list, or use an existing Excel/Access file.</li>
  <li>Type the letter and <strong>Insert Merge Field</strong> wherever a name/address must appear (e.g. &laquo;FirstName&raquo;).</li>
  <li>Click <strong>Preview Results</strong> to see real names.</li>
  <li><strong>Finish &amp; Merge</strong> &rarr; Print, Email, or Edit Individual Documents.</li>
</ol>

<div class="callout try">
  <div class="ico"><i class="fas fa-rocket"></i></div>
  <div class="body"><strong>Try it!</strong>Create a short letter inviting someone to your party, then mail-merge it with a list of 5 friends. Watch Word produce 5 personalised letters in seconds.</div>
</div>

<h2>Other power tools to know</h2>
<div class="lesson-grid">
  <div class="card-mini"><h4><i class="fas fa-palette"></i> Themes</h4><p>(Design tab) Change all fonts and colours at once.</p></div>
  <div class="card-mini"><h4><i class="fas fa-asterisk"></i> Footnotes &amp; Endnotes</h4><p>(References) For citations and references.</p></div>
  <div class="card-mini"><h4><i class="fas fa-pen-to-square"></i> Track Changes</h4><p>(Review) See edits made by others.</p></div>
  <div class="card-mini"><h4><i class="fas fa-comment"></i> Comments</h4><p>Add notes for collaborators without changing the text.</p></div>
</div>

<div class="callout tip">
  <div class="ico"><i class="fas fa-bolt"></i></div>
  <div class="body"><strong>You did it!</strong>You've now covered the full Grade 10 CAPS Word Processing module. Time to test yourself with the assessments!</div>
</div>
"""
    },
]


# ---------------------------------------------------------------------------
# QUIZZES (one per 4-lesson block) + their questions
# ---------------------------------------------------------------------------
QUIZZES = [
    {
        'title': 'Quiz 1: Word Basics',
        'description': 'Covers lessons 1-4: introduction, interface, files and editing.',
        'quiz_type': 'quiz',
        'time_limit_minutes': 15,
        'pass_percentage': 50,
        'order': 1,
        'questions': [
            {
                'order': 1, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'What is the default file extension of a Microsoft Word 2016 document?',
                'options': ['.doc', '.docx', '.txt', '.pdf'],
                'correct_answer': '.docx',
                'explanation': '.docx is the modern XML-based format used by Word 2007 and later.'
            },
            {
                'order': 2, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Which keyboard shortcut SAVES the current document?',
                'options': ['Ctrl + P', 'Ctrl + S', 'Ctrl + N', 'Ctrl + O'],
                'correct_answer': 'Ctrl + S',
                'explanation': 'Ctrl + S saves; Ctrl + N = New, Ctrl + O = Open, Ctrl + P = Print.'
            },
            {
                'order': 3, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Which tab in Word leads to the Backstage view (New, Open, Save, Print)?',
                'options': ['Home', 'Insert', 'File', 'View'],
                'correct_answer': 'File',
                'explanation': 'The File tab opens the Backstage view for document-level operations.'
            },
            {
                'order': 4, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'You want to make a copy of a file with a different name. Which option do you use?',
                'options': ['Save', 'Save As', 'Open', 'Close'],
                'correct_answer': 'Save As',
                'explanation': 'Save updates the existing file; Save As lets you rename or change the file type.'
            },
            {
                'order': 5, 'points': 2, 'question_type': 'multiple_choice',
                'question_text': 'What is the quickest way to select an entire paragraph?',
                'options': ['Single click in the paragraph', 'Double-click anywhere in the paragraph',
                            'Triple-click anywhere in the paragraph', 'Press Ctrl + A'],
                'correct_answer': 'Triple-click anywhere in the paragraph',
                'explanation': 'Double-click selects a word; triple-click selects a paragraph; Ctrl+A selects all.'
            },
            {
                'order': 6, 'points': 2, 'question_type': 'match_columns',
                'question_text': 'Match each keyboard shortcut with the action it performs.',
                'options': {
                    'column_a': ['Ctrl + C', 'Ctrl + X', 'Ctrl + V', 'Ctrl + Z'],
                    'column_b': ['Copy', 'Cut', 'Paste', 'Undo']
                },
                'correct_answer': {'Ctrl + C': 'Copy', 'Ctrl + X': 'Cut',
                                   'Ctrl + V': 'Paste', 'Ctrl + Z': 'Undo'},
                'explanation': 'These four shortcuts form the basic clipboard / undo workflow.'
            },
            {
                'order': 7, 'points': 2, 'question_type': 'drag_drop',
                'question_text': 'Place these steps in the correct order to open an existing document.',
                'options': ['Click Open', 'Open Microsoft Word', 'Click File',
                            'Browse and select the document'],
                'correct_answer': ['Open Microsoft Word', 'Click File', 'Click Open',
                                   'Browse and select the document'],
                'explanation': 'You must launch Word first, then go to File > Open and pick the file.'
            },
        ]
    },

    {
        'title': 'Quiz 2: Formatting Text and Paragraphs',
        'description': 'Covers lessons 5-7: characters, paragraphs and lists.',
        'quiz_type': 'quiz',
        'time_limit_minutes': 15,
        'pass_percentage': 50,
        'order': 2,
        'questions': [
            {
                'order': 1, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Font size is measured in which units?',
                'options': ['Pixels', 'Points', 'Centimetres', 'Inches'],
                'correct_answer': 'Points',
                'explanation': 'Font size uses points (pt). Body text is usually 11 or 12 pt.'
            },
            {
                'order': 2, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Which alignment makes BOTH the left and right edges of a paragraph straight?',
                'options': ['Left', 'Centre', 'Right', 'Justify'],
                'correct_answer': 'Justify',
                'explanation': 'Justify spaces words so both edges are straight (like in newspapers).'
            },
            {
                'order': 3, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'You want to copy formatting from one piece of text to another. Which tool do you use?',
                'options': ['Format Painter', 'Clear Formatting', 'Highlighter', 'Styles'],
                'correct_answer': 'Format Painter',
                'explanation': 'The Format Painter (paintbrush icon) copies formatting between selections.'
            },
            {
                'order': 4, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Which list type should be used for a step-by-step recipe?',
                'options': ['Bulleted list', 'Numbered list', 'Multilevel list', 'No list'],
                'correct_answer': 'Numbered list',
                'explanation': 'Numbered lists are for items in a definite order (e.g. step 1, step 2).'
            },
            {
                'order': 5, 'points': 2, 'question_type': 'multiple_choice',
                'question_text': 'Inside a numbered list, which key DEMOTES an item to a sub-level?',
                'options': ['Enter', 'Tab', 'Shift + Tab', 'Backspace'],
                'correct_answer': 'Tab',
                'explanation': 'Tab demotes (one level deeper); Shift+Tab promotes (back out).'
            },
            {
                'order': 6, 'points': 2, 'question_type': 'match_columns',
                'question_text': 'Match each effect to its keyboard shortcut.',
                'options': {
                    'column_a': ['Bold', 'Italic', 'Underline', 'Centre'],
                    'column_b': ['Ctrl + B', 'Ctrl + I', 'Ctrl + U', 'Ctrl + E']
                },
                'correct_answer': {'Bold': 'Ctrl + B', 'Italic': 'Ctrl + I',
                                   'Underline': 'Ctrl + U', 'Centre': 'Ctrl + E'},
                'explanation': 'Ctrl with the first letter is the convention (E for cEntre because C is Copy).'
            },
            {
                'order': 7, 'points': 2, 'question_type': 'drag_drop',
                'question_text': 'Place these CASE options in the order shown in the Change Case menu.',
                'options': ['UPPERCASE', 'Sentence case', 'Capitalize Each Word', 'lowercase'],
                'correct_answer': ['Sentence case', 'lowercase', 'UPPERCASE', 'Capitalize Each Word'],
                'explanation': 'Word lists them in this order: Sentence case, lowercase, UPPERCASE, Capitalize Each Word, tOGGLE cASE.'
            },
        ]
    },

    {
        'title': 'Exam: Word Processing (Grade 10)',
        'description': 'End-of-module assessment covering all 12 lessons.',
        'quiz_type': 'exam',
        'time_limit_minutes': 30,
        'pass_percentage': 50,
        'order': 3,
        'questions': [
            {
                'order': 1, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Which page orientation is wider than it is tall?',
                'options': ['Portrait', 'Landscape', 'A4', 'Letter'],
                'correct_answer': 'Landscape',
                'explanation': 'Landscape is wider than tall; Portrait is taller than wide.'
            },
            {
                'order': 2, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'What is the standard paper size used in South African schools?',
                'options': ['A3', 'A4', 'A5', 'Letter'],
                'correct_answer': 'A4',
                'explanation': 'A4 (21 cm x 29.7 cm) is the South African standard.'
            },
            {
                'order': 3, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Where do you put information that must appear at the TOP of every page?',
                'options': ['Header', 'Footer', 'Footnote', 'Comment'],
                'correct_answer': 'Header',
                'explanation': 'Headers appear at the top of every page; footers at the bottom.'
            },
            {
                'order': 4, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Which key combination forces text onto a new page?',
                'options': ['Enter', 'Ctrl + Enter', 'Shift + Enter', 'Alt + Enter'],
                'correct_answer': 'Ctrl + Enter',
                'explanation': 'Ctrl + Enter inserts a page break.'
            },
            {
                'order': 5, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'In a table, which key moves the cursor to the NEXT cell?',
                'options': ['Enter', 'Tab', 'Spacebar', 'Arrow Right'],
                'correct_answer': 'Tab',
                'explanation': 'Tab moves to the next cell and creates a new row at the end of the table.'
            },
            {
                'order': 6, 'points': 1, 'question_type': 'multiple_choice',
                'question_text': 'Which text-wrapping option lets text flow AROUND a picture on all sides?',
                'options': ['In Line with Text', 'Behind Text', 'Square', 'In Front of Text'],
                'correct_answer': 'Square',
                'explanation': 'Square (or Tight) wraps text around the picture; In Line with Text treats it as a character.'
            },
            {
                'order': 7, 'points': 2, 'question_type': 'multiple_choice',
                'question_text': 'Which feature lets you create many personalised letters from one template and a list of names?',
                'options': ['Track Changes', 'Mail Merge', 'Styles', 'Find &amp; Replace'],
                'correct_answer': 'Mail Merge',
                'explanation': 'Mail Merge combines a main document with a data source to produce personalised copies.'
            },
            {
                'order': 8, 'points': 2, 'question_type': 'multiple_choice',
                'question_text': 'For an automatic Table of Contents to work, headings must be formatted using which feature?',
                'options': ['Bold and a larger font', 'Heading styles (Heading 1, 2, 3)',
                            'Underline', 'WordArt'],
                'correct_answer': 'Heading styles (Heading 1, 2, 3)',
                'explanation': 'Word builds the TOC from text marked with the built-in Heading styles.'
            },
            {
                'order': 9, 'points': 3, 'question_type': 'match_columns',
                'question_text': 'Match each Ribbon tab with a typical task you would do there.',
                'options': {
                    'column_a': ['Insert', 'Layout', 'References', 'Mailings'],
                    'column_b': ['Add a picture or table', 'Change margins and orientation',
                                 'Insert a Table of Contents', 'Start a Mail Merge']
                },
                'correct_answer': {
                    'Insert': 'Add a picture or table',
                    'Layout': 'Change margins and orientation',
                    'References': 'Insert a Table of Contents',
                    'Mailings': 'Start a Mail Merge'
                },
                'explanation': 'Each Ribbon tab groups related commands by purpose.'
            },
            {
                'order': 10, 'points': 3, 'question_type': 'drag_drop',
                'question_text': 'Arrange these mail-merge steps in the correct order.',
                'options': ['Insert merge fields into the letter',
                            'Finish &amp; Merge',
                            'Start Mail Merge and choose document type',
                            'Select recipients (data source)',
                            'Preview results'],
                'correct_answer': ['Start Mail Merge and choose document type',
                                   'Select recipients (data source)',
                                   'Insert merge fields into the letter',
                                   'Preview results',
                                   'Finish &amp; Merge'],
                'explanation': 'The Mailings tab follows this exact order from left to right.'
            },
        ]
    },
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------
def seed():
    with app.app_context():
        course = (Course.query.join(Grade)
                  .filter(Grade.number == 10, Course.title == 'Word Processing')
                  .first())
        if not course:
            print("ERROR: Grade 10 'Word Processing' course not found. Run init_db() first.")
            return

        added_lessons = 0
        updated_lessons = 0
        for ld in LESSONS:
            existing = Lesson.query.filter_by(course_id=course.id, order=ld['order']).first()
            if existing:
                existing.title = ld['title']
                existing.content = ld['content']
                existing.duration_minutes = ld['duration_minutes']
                updated_lessons += 1
                continue
            db.session.add(Lesson(course_id=course.id, **ld))
            added_lessons += 1

        added_quizzes = 0
        added_questions = 0
        for qd in QUIZZES:
            quiz = Quiz.query.filter_by(course_id=course.id, title=qd['title']).first()
            if not quiz:
                quiz = Quiz(
                    course_id=course.id,
                    title=qd['title'],
                    description=qd['description'],
                    quiz_type=qd['quiz_type'],
                    time_limit_minutes=qd['time_limit_minutes'],
                    pass_percentage=qd['pass_percentage'],
                    order=qd['order'],
                )
                db.session.add(quiz)
                db.session.flush()  # get quiz.id
                added_quizzes += 1

            for qq in qd['questions']:
                exists = Question.query.filter_by(quiz_id=quiz.id, order=qq['order']).first()
                if exists:
                    continue
                db.session.add(Question(
                    quiz_id=quiz.id,
                    question_text=qq['question_text'],
                    question_type=qq['question_type'],
                    options=json.dumps(qq['options']),
                    correct_answer=json.dumps(qq['correct_answer']),
                    points=qq['points'],
                    order=qq['order'],
                    explanation=qq.get('explanation', ''),
                ))
                added_questions += 1

        db.session.commit()
        print(f"Seeded Grade 10 Word Processing:")
        print(f"   + {added_lessons} new lessons, {updated_lessons} updated (total now: "
              f"{Lesson.query.filter_by(course_id=course.id).count()})")
        print(f"   + {added_quizzes} new quizzes (total now: "
              f"{Quiz.query.filter_by(course_id=course.id).count()})")
        print(f"   + {added_questions} new questions")


if __name__ == '__main__':
    seed()
