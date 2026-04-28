"""
Seed all CAPS-aligned content + quizzes for the remaining 17 CAT courses
(Grade 10 Word Processing is handled separately by seed_grade10_word.py).

Per course: 5 lessons + 1 quiz with 8 mixed-type questions.
Idempotent: safe to re-run.

Run:
    python seed_caps_content.py
"""
import json
from app import app, db, Grade, Course, Lesson, Quiz, Question


# ---------------------------------------------------------------------------
# Tiny HTML helpers
# ---------------------------------------------------------------------------
def kbd(*keys):
    parts = []
    for i, k in enumerate(keys):
        if i:
            parts.append('<span class="plus">+</span>')
        parts.append(f'<span class="kbd">{k}</span>')
    return '<span class="kbd-combo">' + ''.join(parts) + '</span>'


def intro(label, text):
    return f'<div class="lesson-intro"><div class="label">{label}</div><p>{text}</p></div>'


def callout(kind, icon, title, body):
    return (f'<div class="callout {kind}"><div class="ico"><i class="fas {icon}"></i></div>'
            f'<div class="body"><strong>{title}</strong>{body}</div></div>')


def grid(items):
    cards = ''.join(
        f'<div class="card-mini"><h4><i class="fas {it["icon"]}"></i> {it["title"]}</h4>'
        f'<p>{it["body"]}</p></div>'
        for it in items
    )
    return f'<div class="lesson-grid">{cards}</div>'


# ---------------------------------------------------------------------------
# Quiz template — every course shares the same metadata; questions vary.
# ---------------------------------------------------------------------------
def make_quiz(title, description, questions):
    return {
        'title': title,
        'description': description,
        'quiz_type': 'quiz',
        'time_limit_minutes': 20,
        'pass_percentage': 60.0,
        'order': 1,
        'questions': [
            {'order': i + 1, 'points': q.get('points', 1), **q}
            for i, q in enumerate(questions)
        ],
    }


# ===========================================================================
# GRADE 10 — remaining 5 courses (Word Processing already seeded)
# ===========================================================================

G10_SPREADSHEETS = {
    'grade': 10, 'course_title': 'Spreadsheets',
    'lessons': [
        {'order': 1, 'duration_minutes': 25, 'title': 'Introduction to Spreadsheets',
         'content': intro('Lesson 1 &middot; Get Started',
            'A spreadsheet organises numbers, text and formulas in a grid of <strong>rows</strong> and <strong>columns</strong>. Microsoft Excel is the most widely used.') + """
<h2>Anatomy of a workbook</h2>
<table>
  <tr><th>Term</th><th>Meaning</th></tr>
  <tr><td>Workbook</td><td>The whole <code>.xlsx</code> file.</td></tr>
  <tr><td>Worksheet</td><td>One tab inside a workbook.</td></tr>
  <tr><td>Cell</td><td>A single box where a row and column meet, e.g. <code>B4</code>.</td></tr>
  <tr><td>Range</td><td>A group of cells, e.g. <code>A1:C10</code>.</td></tr>
  <tr><td>Active cell</td><td>The one with the dark border &mdash; ready for input.</td></tr>
</table>
""" + callout('info', 'fa-lightbulb', 'Did you know?',
              'Excel can hold over <strong>17 billion cells</strong> per worksheet (1 048 576 rows &times; 16 384 columns)!') + """
<h3>Why use a spreadsheet?</h3>
""" + grid([
    {'icon': 'fa-calculator', 'title': 'Auto-calculate', 'body': 'Change a number &mdash; every formula updates instantly.'},
    {'icon': 'fa-chart-column', 'title': 'Visualise', 'body': 'Turn rows of data into charts in two clicks.'},
    {'icon': 'fa-filter', 'title': 'Sort &amp; filter', 'body': 'Find the data you need fast.'},
    {'icon': 'fa-table-cells', 'title': 'Organise', 'body': 'Budgets, marks, stocktakes &mdash; all in neat rows.'},
])},
        {'order': 2, 'duration_minutes': 30, 'title': 'Cells, Ranges and Data Entry',
         'content': intro('Lesson 2 &middot; Filling in Data',
            'Every spreadsheet starts the same way &mdash; click a cell and type. But knowing the difference between text, numbers and dates saves hours later.') + """
<h2>Three kinds of data</h2>
<table>
  <tr><th>Type</th><th>Example</th><th>Lines up</th></tr>
  <tr><td>Text (label)</td><td>Name, Subject</td><td>Left</td></tr>
  <tr><td>Number</td><td>42, 3.14, 1000</td><td>Right</td></tr>
  <tr><td>Date / Time</td><td>2026/04/22, 14:30</td><td>Right</td></tr>
</table>
<h3>Selecting ranges</h3>
<ul>
  <li>Drag from one corner to another.</li>
  <li>""" + kbd('Ctrl') + """ + click to add non-adjacent cells.</li>
  <li>""" + kbd('Ctrl', 'A') + """ to select the whole sheet.</li>
</ul>
<h3>The Fill Handle</h3>
<p>The little square in the bottom-right of a selected cell. Drag it to:</p>
<ul>
  <li>Copy a value to many cells.</li>
  <li>Continue a series: type <strong>Mon</strong> then drag &rarr; Tue, Wed, Thu&hellip;</li>
  <li>Continue a number pattern: select <strong>2, 4</strong> then drag &rarr; 6, 8, 10&hellip;</li>
</ul>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Double-click the fill handle to copy a formula <em>all the way down</em> to where the column on its left ends.')},
        {'order': 3, 'duration_minutes': 35, 'title': 'Formulas and Operators',
         'content': intro('Lesson 3 &middot; Make Excel Do the Maths',
            'A <strong>formula</strong> always starts with <code>=</code>. It tells Excel to calculate something using cell references and operators.') + """
<h2>Basic operators</h2>
<table>
  <tr><th>Operator</th><th>Means</th><th>Example</th></tr>
  <tr><td><code>+</code></td><td>Add</td><td><code>=A1+B1</code></td></tr>
  <tr><td><code>-</code></td><td>Subtract</td><td><code>=A1-B1</code></td></tr>
  <tr><td><code>*</code></td><td>Multiply</td><td><code>=A1*B1</code></td></tr>
  <tr><td><code>/</code></td><td>Divide</td><td><code>=A1/B1</code></td></tr>
  <tr><td><code>^</code></td><td>Power</td><td><code>=A1^2</code> (squared)</td></tr>
</table>
<h3>Order of operations &mdash; BODMAS</h3>
<p>Excel follows <strong>B</strong>rackets, <strong>O</strong>rders (powers), <strong>D</strong>ivision/<strong>M</strong>ultiplication, <strong>A</strong>ddition/<strong>S</strong>ubtraction.</p>
""" + callout('warn', 'fa-triangle-exclamation', 'Watch out',
              '<code>=2+3*4</code> gives <strong>14</strong>, not 20. Use brackets: <code>=(2+3)*4</code> for 20.') + """
<h3>Cell references</h3>
<p>Always click cells instead of typing numbers. If the value changes later, your formula stays correct.</p>
""" + callout('try', 'fa-rocket', 'Try it!',
              'In cell B1 type <code>=A1*15%</code>. Now change A1 to any number &mdash; B1 calculates 15% automatically.')},
        {'order': 4, 'duration_minutes': 35, 'title': 'Built-in Functions: SUM, AVERAGE, MAX, MIN, COUNT',
         'content': intro('Lesson 4 &middot; The Five Friends',
            'Excel has hundreds of functions, but five do most of the work. Learn these and you can solve 80% of school tasks.') + """
<table>
  <tr><th>Function</th><th>What it does</th><th>Example</th></tr>
  <tr><td><code>SUM</code></td><td>Adds all numbers in a range</td><td><code>=SUM(B2:B11)</code></td></tr>
  <tr><td><code>AVERAGE</code></td><td>Mean of all numbers</td><td><code>=AVERAGE(B2:B11)</code></td></tr>
  <tr><td><code>MAX</code></td><td>Largest number</td><td><code>=MAX(B2:B11)</code></td></tr>
  <tr><td><code>MIN</code></td><td>Smallest number</td><td><code>=MIN(B2:B11)</code></td></tr>
  <tr><td><code>COUNT</code></td><td>How many <em>numbers</em> in the range</td><td><code>=COUNT(B2:B11)</code></td></tr>
  <tr><td><code>COUNTA</code></td><td>How many <em>non-empty</em> cells</td><td><code>=COUNTA(A2:A11)</code></td></tr>
</table>
""" + callout('key', 'fa-key', 'Key idea',
              'A range like <code>B2:B11</code> means "every cell from B2 to B11 inclusive". The colon means <em>through</em>.') + """
<h3>AutoSum shortcut</h3>
<p>Click an empty cell at the bottom of a column of numbers, then press """ + kbd('Alt', '=') + """. Excel guesses the range and inserts <code>=SUM(...)</code> for you.</p>
"""},
        {'order': 5, 'duration_minutes': 30, 'title': 'Charts and Basic Formatting',
         'content': intro('Lesson 5 &middot; Show, Don\'t Tell',
            'A good chart turns a wall of numbers into an instant story. Pick the right chart for your data.') + """
<h2>Which chart for which job?</h2>
""" + grid([
    {'icon': 'fa-chart-column', 'title': 'Column / Bar', 'body': 'Compare values across categories (marks per subject).'},
    {'icon': 'fa-chart-line', 'title': 'Line', 'body': 'Show change over <strong>time</strong> (sales per month).'},
    {'icon': 'fa-chart-pie', 'title': 'Pie', 'body': 'Parts of a <strong>whole</strong>. Use only with 2&ndash;6 slices.'},
    {'icon': 'fa-braille', 'title': 'Scatter', 'body': 'Relationship between two number variables.'},
]) + """
<h3>Insert a chart in 3 steps</h3>
<ol class="steps">
  <li>Select the data including the headings.</li>
  <li>Go to <strong>Insert &rarr; Charts</strong> and pick a type.</li>
  <li>Use the green <em>+</em> button next to the chart to add a title, data labels and legend.</li>
</ol>
<h3>Cell formatting basics</h3>
<ul>
  <li><strong>Number format</strong>: Currency, %, Date &mdash; Home tab &rarr; Number group.</li>
  <li><strong>Borders</strong> &amp; <strong>fill colour</strong> for headers and totals.</li>
  <li><strong>Merge &amp; Center</strong> to span a heading across columns.</li>
</ul>
""" + callout('warn', 'fa-triangle-exclamation', 'Best practice',
              'Every chart needs a clear <strong>title</strong>, labelled <strong>axes</strong> and units. A chart without these loses marks.')},
    ],
    'quiz': make_quiz(
        'Spreadsheets — Knowledge Check',
        'Tests cells, formulas, functions and charts.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'What does every Excel formula start with?',
             'options': ['#', '=', '@', '*'], 'correct_answer': '=',
             'explanation': 'The equals sign tells Excel to calculate.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which function returns the largest number in a range?',
             'options': ['SUM', 'AVERAGE', 'MAX', 'COUNT'], 'correct_answer': 'MAX',
             'explanation': 'MAX returns the largest value.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which result does <code>=2+3*4</code> give?',
             'options': ['20', '14', '10', '24'], 'correct_answer': '14',
             'explanation': 'Multiplication happens before addition (BODMAS).'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Which chart type best shows parts of a whole?',
             'options': ['Line chart', 'Pie chart', 'Scatter chart', 'Column chart'],
             'correct_answer': 'Pie chart',
             'explanation': 'Pie charts are for portions of a single total.'},
            {'question_type': 'multiple_choice',
             'question_text': 'What does <code>B2:B11</code> mean?',
             'options': ['Cell B2 OR cell B11', 'All cells from B2 through B11',
                         'Cell B2 minus cell B11', 'Two separate cells'],
             'correct_answer': 'All cells from B2 through B11',
             'explanation': 'The colon (:) defines an inclusive range.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each function to its purpose.',
             'options': {
                 'column_a': ['SUM', 'AVERAGE', 'COUNT', 'MIN'],
                 'column_b': ['Adds numbers', 'Mean of numbers',
                              'Counts numeric cells', 'Smallest number']
             },
             'correct_answer': {'SUM': 'Adds numbers', 'AVERAGE': 'Mean of numbers',
                                'COUNT': 'Counts numeric cells', 'MIN': 'Smallest number'},
             'explanation': 'These five functions cover most CAPS Grade 10 spreadsheet tasks.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Arrange these steps to insert a chart.',
             'options': ['Click Insert &rarr; Charts and pick a type',
                         'Add a chart title and axis labels',
                         'Select the data including headings'],
             'correct_answer': ['Select the data including headings',
                                'Click Insert &rarr; Charts and pick a type',
                                'Add a chart title and axis labels'],
             'explanation': 'Always select data first, insert next, then label.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which keyboard shortcut inserts AutoSum?',
             'options': [kbd('Ctrl', 'S'), kbd('Alt', '='), kbd('Ctrl', '+'), kbd('F4')],
             'correct_answer': kbd('Alt', '='),
             'explanation': 'Alt + = inserts =SUM(...) automatically.'},
        ]
    ),
}


G10_PRESENTATIONS = {
    'grade': 10, 'course_title': 'Presentations',
    'lessons': [
        {'order': 1, 'duration_minutes': 25, 'title': 'What is a Presentation?',
         'content': intro('Lesson 1 &middot; Why slides?',
            'Microsoft PowerPoint is a <strong>presentation programme</strong> for showing information visually using a sequence of slides.') + """
<h2>When to use a presentation</h2>
""" + grid([
    {'icon': 'fa-chalkboard-user', 'title': 'Teach', 'body': 'Lessons, training, demos.'},
    {'icon': 'fa-handshake', 'title': 'Pitch', 'body': 'Sell an idea or product.'},
    {'icon': 'fa-graduation-cap', 'title': 'Report back', 'body': 'School orals, project reports.'},
    {'icon': 'fa-bullhorn', 'title': 'Inform', 'body': 'Announcements at assembly.'},
]) + """
<h3>Common file formats</h3>
<table>
  <tr><th>Extension</th><th>Use</th></tr>
  <tr><td><code>.pptx</code></td><td>Default editable PowerPoint format.</td></tr>
  <tr><td><code>.ppsx</code></td><td>Opens straight in slideshow mode.</td></tr>
  <tr><td><code>.pdf</code></td><td>Read-only handout.</td></tr>
</table>
""" + callout('info', 'fa-lightbulb', 'Did you know?',
              'The "10/20/30" rule says: <strong>10 slides</strong>, <strong>20 minutes</strong>, font size at least <strong>30 pt</strong>.')},
        {'order': 2, 'duration_minutes': 30, 'title': 'Slides, Layouts and Templates',
         'content': intro('Lesson 2 &middot; Building Blocks',
            'Every slide uses a <strong>layout</strong>: a ready-made arrangement of placeholders for title, content, image and so on.') + """
<h2>Common layouts</h2>
<ul>
  <li><strong>Title slide</strong> &mdash; the first slide.</li>
  <li><strong>Title and content</strong> &mdash; heading plus bullets.</li>
  <li><strong>Two content</strong> &mdash; two-column comparison.</li>
  <li><strong>Picture with caption</strong> &mdash; image-led slide.</li>
  <li><strong>Blank</strong> &mdash; design from scratch.</li>
</ul>
<h3>Themes vs templates</h3>
<table>
  <tr><th>Theme</th><th>Template</th></tr>
  <tr><td>Just colours, fonts and effects.</td><td>Theme + ready content (e.g. CV, Pitch deck).</td></tr>
</table>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Apply a theme <em>before</em> typing content so all your text matches the theme automatically.') + """
<h3>Slide Master &mdash; the boss slide</h3>
<p>Open <strong>View &rarr; Slide Master</strong> to change the logo, footer or font for <em>every slide at once</em>.</p>
"""},
        {'order': 3, 'duration_minutes': 30, 'title': 'Adding Text, Images and Tables',
         'content': intro('Lesson 3 &middot; Filling Slides',
            'A presentation is only as good as the content on each slide. Keep it visual, keep it short.') + """
<h2>Text placeholders</h2>
<p>Click "Click to add title" or "Click to add text" and start typing. Use the <strong>Outline View</strong> to type all your bullet text in one go.</p>
<h3>Inserting images</h3>
<ol class="steps">
  <li><strong>Insert &rarr; Pictures</strong> &rarr; This Device or Online Pictures.</li>
  <li>Drag a corner handle to resize <em>proportionally</em>.</li>
  <li>Use the <strong>Picture Format</strong> tab for borders, effects and cropping.</li>
</ol>
""" + callout('warn', 'fa-triangle-exclamation', 'Copyright',
              'Use <strong>royalty-free</strong> images or your own photos. Pixabay and Unsplash are good free sources.') + """
<h3>Tables, SmartArt and icons</h3>
<ul>
  <li><strong>Table</strong>: Insert &rarr; Table for grid data.</li>
  <li><strong>SmartArt</strong>: turn bullets into a diagram (process, cycle, hierarchy).</li>
  <li><strong>Icons</strong>: Insert &rarr; Icons for free flat illustrations.</li>
</ul>
"""},
        {'order': 4, 'duration_minutes': 30, 'title': 'Transitions and Animations',
         'content': intro('Lesson 4 &middot; Movement on Slides',
            '<strong>Transitions</strong> happen <em>between</em> slides. <strong>Animations</strong> happen <em>inside</em> a slide.') + """
<h2>Transitions</h2>
<p>Open the <strong>Transitions</strong> tab. Pick something subtle like <em>Fade</em>, <em>Push</em> or <em>Wipe</em>. Use <strong>Apply To All</strong> for a consistent feel.</p>
<h3>Animations</h3>
<table>
  <tr><th>Type</th><th>What it does</th></tr>
  <tr><td>Entrance</td><td>How an object appears (Fly In, Fade).</td></tr>
  <tr><td>Emphasis</td><td>Draws attention (Pulse, Spin).</td></tr>
  <tr><td>Exit</td><td>How an object leaves the slide.</td></tr>
  <tr><td>Motion path</td><td>Move an object along a custom path.</td></tr>
</table>
""" + callout('warn', 'fa-triangle-exclamation', 'Less is more',
              'Avoid spinning text and bouncing pictures. <strong>Fade</strong> and <strong>Appear</strong> look the most professional.') + """
<h3>Timing the slideshow</h3>
<p>Use <strong>Slide Show &rarr; Rehearse Timings</strong> to record how long you spend on each slide, then play it back automatically.</p>
"""},
        {'order': 5, 'duration_minutes': 25, 'title': 'Delivering Your Presentation',
         'content': intro('Lesson 5 &middot; Show Time!',
            'A great slide deck still needs a great speaker. Here\'s how to use PowerPoint while you talk.') + """
<h2>Starting the show</h2>
<ul>
  <li>""" + kbd('F5') + """ &mdash; from the beginning.</li>
  <li>""" + kbd('Shift', 'F5') + """ &mdash; from the current slide.</li>
  <li>""" + kbd('Esc') + """ &mdash; exit the show.</li>
</ul>
<h3>Presenter View</h3>
<p>If you have two screens, Presenter View shows your <strong>notes</strong>, a timer and the next slide on your laptop, while the audience only sees the current slide.</p>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Press <strong>B</strong> for a black screen during a discussion, <strong>W</strong> for white. Press the same key to come back.') + """
<h3>Printing handouts</h3>
<p><strong>File &rarr; Print &rarr; Handouts</strong> &mdash; choose 3 or 6 slides per page so the audience can take notes.</p>
"""},
    ],
    'quiz': make_quiz(
        'Presentations — Knowledge Check',
        'Tests slides, transitions, animations and delivery.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Which file extension opens directly in slideshow mode?',
             'options': ['.pptx', '.ppsx', '.pdf', '.docx'], 'correct_answer': '.ppsx',
             'explanation': 'PowerPoint Show files start the slideshow on opening.'},
            {'question_type': 'multiple_choice',
             'question_text': 'What is the difference between a transition and an animation?',
             'options': ['No difference', 'Transition is between slides; animation is inside a slide',
                         'Animation is between slides', 'Transitions only work on text'],
             'correct_answer': 'Transition is between slides; animation is inside a slide',
             'explanation': 'Transitions = between slides. Animations = on objects.'},
            {'question_type': 'multiple_choice',
             'question_text': 'What does pressing F5 do during editing?',
             'options': ['Saves the file', 'Starts the slideshow from the beginning',
                         'Inserts a new slide', 'Closes PowerPoint'],
             'correct_answer': 'Starts the slideshow from the beginning',
             'explanation': 'F5 starts from slide 1; Shift+F5 starts from current slide.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Which feature lets you change the logo on every slide at once?',
             'options': ['Themes', 'Slide Master', 'Animations', 'Transitions'],
             'correct_answer': 'Slide Master',
             'explanation': 'Edits in Slide Master apply to every slide.'},
            {'question_type': 'multiple_choice',
             'question_text': 'According to the 10/20/30 rule, what is the minimum font size?',
             'options': ['10 pt', '20 pt', '30 pt', '40 pt'], 'correct_answer': '30 pt',
             'explanation': 'Guy Kawasaki\'s rule: 10 slides, 20 minutes, 30 pt minimum.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each animation type with its purpose.',
             'options': {
                 'column_a': ['Entrance', 'Emphasis', 'Exit', 'Motion Path'],
                 'column_b': ['Object appears on slide', 'Object draws attention',
                              'Object leaves slide', 'Object follows a path']
             },
             'correct_answer': {'Entrance': 'Object appears on slide',
                                'Emphasis': 'Object draws attention',
                                'Exit': 'Object leaves slide',
                                'Motion Path': 'Object follows a path'},
             'explanation': 'PowerPoint groups animations into these four categories.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Arrange these steps to insert and resize a picture.',
             'options': ['Drag a corner handle to keep proportions',
                         'Use Picture Format tab for borders or effects',
                         'Click Insert &rarr; Pictures &rarr; This Device'],
             'correct_answer': ['Click Insert &rarr; Pictures &rarr; This Device',
                                'Drag a corner handle to keep proportions',
                                'Use Picture Format tab for borders or effects'],
             'explanation': 'Insert first, resize second, format last.'},
            {'question_type': 'short_answer',
             'question_text': 'Name any one source of royalty-free images.',
             'options': [], 'correct_answer': 'Pixabay',
             'explanation': 'Pixabay, Unsplash, and Pexels all offer free-to-use images.'},
        ]
    ),
}


G10_HARDWARE = {
    'grade': 10, 'course_title': 'Computer Hardware',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'The Four-Phase Information Processing Cycle',
         'content': intro('Lesson 1 &middot; How Computers Work',
            'Every computer task &mdash; from playing a game to printing an essay &mdash; follows the same four steps: <strong>Input &rarr; Processing &rarr; Output &rarr; Storage</strong>.') + """
<h2>The cycle</h2>
""" + grid([
    {'icon': 'fa-keyboard', 'title': 'Input', 'body': 'Get data <em>into</em> the computer (typing, clicking, scanning).'},
    {'icon': 'fa-microchip', 'title': 'Processing', 'body': 'CPU manipulates the data using instructions.'},
    {'icon': 'fa-display', 'title': 'Output', 'body': 'Show results to the user (screen, speaker, printer).'},
    {'icon': 'fa-hard-drive', 'title': 'Storage', 'body': 'Save data for later (HDD, SSD, USB).'},
]) + """
<h3>Communication &mdash; the often-forgotten 5th step</h3>
<p>Modern computers also <strong>communicate</strong> with other devices via networks. This is sometimes added as a 5th phase.</p>
""" + callout('key', 'fa-key', 'Key term',
              '<strong>Data</strong> = raw facts (e.g. 75). <strong>Information</strong> = data that has been processed and given meaning (e.g. "75% in maths test").')},
        {'order': 2, 'duration_minutes': 35, 'title': 'Input and Output Devices',
         'content': intro('Lesson 2 &middot; Talking to the Computer',
            'Input devices send data <strong>in</strong>. Output devices send results <strong>out</strong>. Some, like a touchscreen, do both.') + """
<h2>Common input devices</h2>
<table>
  <tr><th>Device</th><th>Used for</th></tr>
  <tr><td>Keyboard</td><td>Typing text and shortcuts.</td></tr>
  <tr><td>Mouse / trackpad</td><td>Pointing and clicking.</td></tr>
  <tr><td>Scanner</td><td>Capturing paper documents.</td></tr>
  <tr><td>Microphone</td><td>Voice input, dictation.</td></tr>
  <tr><td>Webcam</td><td>Video calls, photos.</td></tr>
  <tr><td>Barcode reader</td><td>Stock and POS systems.</td></tr>
</table>
<h2>Common output devices</h2>
<table>
  <tr><th>Device</th><th>Type of output</th></tr>
  <tr><td>Monitor</td><td>Soft copy (visual).</td></tr>
  <tr><td>Printer</td><td>Hard copy (paper).</td></tr>
  <tr><td>Speakers / headphones</td><td>Sound.</td></tr>
  <tr><td>Projector</td><td>Large screen visual.</td></tr>
</table>
""" + callout('info', 'fa-lightbulb', 'Soft vs hard copy',
              '<strong>Soft copy</strong> = on a screen. <strong>Hard copy</strong> = printed on paper.')},
        {'order': 3, 'duration_minutes': 35, 'title': 'The CPU, RAM and Motherboard',
         'content': intro('Lesson 3 &middot; Inside the Box',
            'The motherboard is the main circuit board. The CPU is its brain. RAM is its short-term memory. Together they make every program run.') + """
<h2>The CPU</h2>
<p>The <strong>Central Processing Unit</strong> performs the calculations and follows the instructions of every program. CPU speed is measured in <strong>GHz</strong> (gigahertz).</p>
<h3>Cores and threads</h3>
<p>A modern CPU has <strong>multiple cores</strong> &mdash; each core can run an instruction at the same time. More cores = better multitasking.</p>
<h2>RAM &mdash; Random Access Memory</h2>
""" + callout('key', 'fa-key', 'Volatile memory',
              'RAM is <strong>volatile</strong>: when the power goes off, everything in RAM is lost. That\'s why you save to storage.') + """
<table>
  <tr><th>Memory</th><th>Speed</th><th>Stays after shutdown?</th></tr>
  <tr><td>Cache (inside CPU)</td><td>Fastest</td><td>No</td></tr>
  <tr><td>RAM</td><td>Very fast</td><td>No</td></tr>
  <tr><td>SSD</td><td>Fast</td><td>Yes</td></tr>
  <tr><td>HDD</td><td>Slow</td><td>Yes</td></tr>
</table>
<h3>The motherboard</h3>
<p>Connects the CPU, RAM, storage, GPU and ports. It includes the <strong>BIOS/UEFI</strong> firmware that boots the computer.</p>
"""},
        {'order': 4, 'duration_minutes': 30, 'title': 'Storage Devices',
         'content': intro('Lesson 4 &middot; Where Files Live',
            'Storage keeps your data even when the power is off. There are several types &mdash; each with a sweet spot.') + """
<h2>Internal storage</h2>
""" + grid([
    {'icon': 'fa-hard-drive', 'title': 'HDD', 'body': 'Hard Disk Drive. Spinning magnetic platters. Cheap per GB but slow.'},
    {'icon': 'fa-bolt', 'title': 'SSD', 'body': 'Solid State Drive. Flash memory. <strong>5-10x faster</strong> than HDD, no moving parts.'},
    {'icon': 'fa-microchip', 'title': 'NVMe', 'body': 'A faster type of SSD that plugs straight into the motherboard.'},
]) + """
<h2>External / portable</h2>
<table>
  <tr><th>Device</th><th>Typical capacity</th></tr>
  <tr><td>USB flash drive</td><td>16 GB &ndash; 1 TB</td></tr>
  <tr><td>External HDD/SSD</td><td>1 TB &ndash; 10 TB</td></tr>
  <tr><td>Memory card (SD/microSD)</td><td>32 GB &ndash; 1 TB</td></tr>
  <tr><td>Optical (CD/DVD/Blu-ray)</td><td>700 MB / 4.7 GB / 25 GB</td></tr>
</table>
<h3>Cloud storage</h3>
<p>Files saved on the internet (OneDrive, Google Drive, Dropbox). Accessible anywhere, but needs a connection.</p>
""" + callout('warn', 'fa-triangle-exclamation', 'Always back up',
              'Use the <strong>3-2-1 rule</strong>: 3 copies of your data, on 2 different media, 1 of which is off-site.')},
        {'order': 5, 'duration_minutes': 25, 'title': 'Basic Troubleshooting',
         'content': intro('Lesson 5 &middot; When Things Break',
            'Small problems can usually be fixed without calling a technician. A calm, step-by-step approach works best.') + """
<h2>The golden rules</h2>
<ol class="steps">
  <li><strong>Stay calm</strong> and observe. What changed just before the problem started?</li>
  <li>Try the easy fix first: <em>save your work and restart</em>.</li>
  <li>Check cables and power. Loose cable = no signal.</li>
  <li>Search the exact error message online &mdash; in quotes.</li>
  <li>Document what you tried so you don\'t repeat steps.</li>
</ol>
<h3>Common problems &amp; fixes</h3>
<table>
  <tr><th>Symptom</th><th>First thing to check</th></tr>
  <tr><td>Computer won\'t turn on</td><td>Power cable, plug socket, surge protector switch.</td></tr>
  <tr><td>No display</td><td>Monitor cable secure; correct input source.</td></tr>
  <tr><td>Very slow</td><td>Too many tabs/programs open; check Task Manager.</td></tr>
  <tr><td>Printer not printing</td><td>Paper, ink, USB/network cable, default printer.</td></tr>
  <tr><td>Internet down</td><td>Restart the router; check Wi-Fi signal.</td></tr>
</table>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Open <strong>Task Manager</strong> with ' + kbd('Ctrl', 'Shift', 'Esc') + ' to see what is using your CPU or RAM.')},
    ],
    'quiz': make_quiz(
        'Computer Hardware — Knowledge Check',
        'Tests the IPOS cycle, devices, CPU/RAM, storage and troubleshooting.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Which of these is NOT one of the four phases of the information processing cycle?',
             'options': ['Input', 'Processing', 'Marketing', 'Storage'],
             'correct_answer': 'Marketing',
             'explanation': 'The four phases are Input, Processing, Output and Storage.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which is an output device?',
             'options': ['Scanner', 'Microphone', 'Printer', 'Webcam'],
             'correct_answer': 'Printer',
             'explanation': 'A printer produces hard copy output.'},
            {'question_type': 'multiple_choice',
             'question_text': 'What does it mean that RAM is "volatile"?',
             'options': ['It explodes if overheated', 'It loses contents when power is off',
                         'It is the fastest memory', 'It is removable'],
             'correct_answer': 'It loses contents when power is off',
             'explanation': 'Volatile memory needs constant power to keep data.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Which statement about an SSD is TRUE?',
             'options': ['It has spinning magnetic platters', 'It is slower than an HDD',
                         'It has no moving parts and is faster than HDD',
                         'It only stores 1 GB'],
             'correct_answer': 'It has no moving parts and is faster than HDD',
             'explanation': 'SSDs use flash memory; HDDs use spinning platters.'},
            {'question_type': 'multiple_choice',
             'question_text': 'CPU speed is measured in:',
             'options': ['Megabytes (MB)', 'Gigahertz (GHz)', 'Pixels (px)', 'Volts (V)'],
             'correct_answer': 'Gigahertz (GHz)',
             'explanation': 'GHz measures clock cycles per second.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each phase of the information processing cycle to its example.',
             'options': {
                 'column_a': ['Input', 'Processing', 'Output', 'Storage'],
                 'column_b': ['Typing on a keyboard', 'CPU calculates a sum',
                              'Printing a report', 'Saving to a USB drive']
             },
             'correct_answer': {'Input': 'Typing on a keyboard',
                                'Processing': 'CPU calculates a sum',
                                'Output': 'Printing a report',
                                'Storage': 'Saving to a USB drive'},
             'explanation': 'Each phase has typical real-world examples.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these storage media from FASTEST to SLOWEST.',
             'options': ['HDD', 'RAM', 'SSD'],
             'correct_answer': ['RAM', 'SSD', 'HDD'],
             'explanation': 'RAM is fastest, SSD is in between, HDD is slowest.'},
            {'question_type': 'multiple_choice',
             'question_text': 'You see a "no signal" message on the monitor. What should you check FIRST?',
             'options': ['Reinstall Windows', 'The monitor cable and input source',
                         'Buy a new monitor', 'Update the BIOS'],
             'correct_answer': 'The monitor cable and input source',
             'explanation': 'Always check the simple physical things first.'},
        ]
    ),
}


G10_NETWORKS = {
    'grade': 10, 'course_title': 'Networks & Internet',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'What is a Network?',
         'content': intro('Lesson 1 &middot; Connected Computers',
            'A <strong>network</strong> is two or more computers connected to share data and resources like files, printers and an internet connection.') + """
<h2>Network sizes</h2>
""" + grid([
    {'icon': 'fa-house', 'title': 'PAN', 'body': '<em>Personal</em>: Bluetooth between your phone and earphones.'},
    {'icon': 'fa-building', 'title': 'LAN', 'body': '<em>Local</em>: a single school, office or home.'},
    {'icon': 'fa-city', 'title': 'MAN', 'body': '<em>Metropolitan</em>: a whole city.'},
    {'icon': 'fa-globe', 'title': 'WAN', 'body': '<em>Wide</em>: across countries (the Internet is the largest WAN).'},
]) + """
<h3>Why network?</h3>
<ul>
  <li>Share an internet line.</li>
  <li>Share files and printers.</li>
  <li>Communicate (chat, video calls).</li>
  <li>Centralised user accounts and backups.</li>
</ul>
"""},
        {'order': 2, 'duration_minutes': 30, 'title': 'Network Hardware: NIC, Switch, Router, Wi-Fi',
         'content': intro('Lesson 2 &middot; The Plumbing',
            'A few simple pieces of hardware make every network possible.') + """
<table>
  <tr><th>Device</th><th>Job</th></tr>
  <tr><td>NIC (Network Interface Card)</td><td>Lets a computer connect &mdash; built into every modern PC and phone.</td></tr>
  <tr><td>Switch</td><td>Connects many computers in a LAN; sends data only to the right port.</td></tr>
  <tr><td>Router</td><td>Connects your LAN to other networks (the internet).</td></tr>
  <tr><td>WAP (Wireless Access Point)</td><td>Provides Wi-Fi to wireless devices.</td></tr>
  <tr><td>Modem</td><td>Converts signals between your ISP and your router (often built into router).</td></tr>
</table>
<h3>Cables vs Wi-Fi</h3>
""" + grid([
    {'icon': 'fa-ethernet', 'title': 'Wired (UTP/RJ-45)', 'body': 'Faster, more reliable, but cables get in the way.'},
    {'icon': 'fa-wifi', 'title': 'Wireless', 'body': 'Convenient, mobile, but slower and can be jammed.'},
]) + callout('info', 'fa-lightbulb', 'IP address',
              'Every device on a network has a unique <strong>IP address</strong>, e.g. <code>192.168.1.10</code>.')},
        {'order': 3, 'duration_minutes': 30, 'title': 'The Internet, Browsers and Search',
         'content': intro('Lesson 3 &middot; The World Wide Web',
            'The <strong>internet</strong> is the global network. The <strong>World Wide Web (WWW)</strong> is the collection of websites you browse on it.') + """
<h2>Key terms</h2>
<table>
  <tr><th>Term</th><th>Meaning</th></tr>
  <tr><td>URL</td><td>Web address, e.g. <code>https://www.gov.za</code></td></tr>
  <tr><td>HTTP / HTTPS</td><td>Protocol for transferring web pages. The <strong>S</strong> = Secure.</td></tr>
  <tr><td>Browser</td><td>Software for viewing websites (Chrome, Edge, Firefox).</td></tr>
  <tr><td>Search engine</td><td>Website that finds other websites (Google, Bing).</td></tr>
  <tr><td>ISP</td><td>Internet Service Provider &mdash; sells you the connection.</td></tr>
</table>
<h3>Smarter searching</h3>
<ul>
  <li>Use <strong>quotes</strong> for an exact phrase: <code>"information processing cycle"</code>.</li>
  <li>Use <strong>minus</strong> to exclude: <code>jaguar -car</code>.</li>
  <li>Use <strong>site:</strong> to search one site only: <code>matric site:education.gov.za</code>.</li>
  <li>Use <strong>filetype:</strong> for specific files: <code>budget filetype:xlsx</code>.</li>
</ul>
"""},
        {'order': 4, 'duration_minutes': 30, 'title': 'Email and Online Communication',
         'content': intro('Lesson 4 &middot; Communicating Online',
            'Email remains the most important formal online communication tool. Knowing the parts and rules will set you apart.') + """
<h2>Parts of an email address</h2>
<p><code>thabo<strong>@</strong>gmail<strong>.</strong>com</code> &mdash; username, then <strong>@</strong>, then domain.</p>
<h3>Email fields</h3>
<table>
  <tr><th>Field</th><th>Use</th></tr>
  <tr><td>To</td><td>Main recipient(s).</td></tr>
  <tr><td>Cc</td><td>Carbon copy &mdash; informational copy, all see each other.</td></tr>
  <tr><td>Bcc</td><td>Blind carbon copy &mdash; recipients don\'t see each other.</td></tr>
  <tr><td>Subject</td><td>Short summary &mdash; <strong>never leave blank</strong>.</td></tr>
  <tr><td>Attachment</td><td>File sent with the email.</td></tr>
</table>
""" + callout('warn', 'fa-triangle-exclamation', 'Email etiquette',
              'Use a clear subject line, greet the person, write properly (no SMS speak) and sign off with your name.') + """
<h3>Other tools</h3>
<ul>
  <li><strong>Instant messaging</strong> (WhatsApp, Teams chat) for quick replies.</li>
  <li><strong>Video calling</strong> (Zoom, Google Meet, Teams) for meetings.</li>
  <li><strong>Forums</strong> and social media for community discussion.</li>
</ul>
"""},
        {'order': 5, 'duration_minutes': 25, 'title': 'Online Safety and Netiquette',
         'content': intro('Lesson 5 &middot; Stay Safe Online',
            'Being online means thinking about your privacy, your security and how you treat others.') + """
<h2>Threats</h2>
""" + grid([
    {'icon': 'fa-fish', 'title': 'Phishing', 'body': 'Fake email or site tricking you into giving passwords.'},
    {'icon': 'fa-bug', 'title': 'Malware', 'body': 'Viruses, worms, ransomware that damage your device.'},
    {'icon': 'fa-user-secret', 'title': 'Identity theft', 'body': 'Criminal pretends to be you online.'},
    {'icon': 'fa-comment-slash', 'title': 'Cyberbullying', 'body': 'Hurtful messages or images shared online.'},
]) + """
<h3>Stay safe</h3>
<ul>
  <li>Use <strong>strong, unique passwords</strong> and a password manager.</li>
  <li>Turn on <strong>two-factor authentication (2FA)</strong>.</li>
  <li>Never click suspicious links; check the URL first.</li>
  <li>Keep your OS and antivirus <strong>up to date</strong>.</li>
</ul>
""" + callout('key', 'fa-key', 'Netiquette',
              'Treat people online as you would face-to-face. <em>Think before you post</em> &mdash; the internet remembers everything.')},
    ],
    'quiz': make_quiz(
        'Networks & Internet — Knowledge Check',
        'Tests network sizes, hardware, the web, email and online safety.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'A network covering one school is best described as a:',
             'options': ['PAN', 'LAN', 'MAN', 'WAN'], 'correct_answer': 'LAN',
             'explanation': 'LAN = Local Area Network, like a school or office.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which device connects your home network to the internet?',
             'options': ['Switch', 'Router', 'NIC', 'Monitor'], 'correct_answer': 'Router',
             'explanation': 'A router connects two networks (LAN to ISP).'},
            {'question_type': 'multiple_choice',
             'question_text': 'In <code>https://www.gov.za</code>, what does the "S" stand for?',
             'options': ['Slow', 'Secure', 'Server', 'Static'], 'correct_answer': 'Secure',
             'explanation': 'HTTPS encrypts the connection.'},
            {'question_type': 'multiple_choice',
             'question_text': 'You send an email and want others to NOT see who else got it. Use:',
             'options': ['To', 'Cc', 'Bcc', 'Subject'], 'correct_answer': 'Bcc',
             'explanation': 'Bcc hides recipients from each other.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'A bank email asks you to "verify your password" via a link. What is this most likely?',
             'options': ['Spam', 'Phishing', 'Adware', 'Hardware failure'],
             'correct_answer': 'Phishing',
             'explanation': 'Banks never ask for your password by email.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each acronym to its meaning.',
             'options': {
                 'column_a': ['LAN', 'WAN', 'ISP', 'URL'],
                 'column_b': ['Local Area Network', 'Wide Area Network',
                              'Internet Service Provider', 'Uniform Resource Locator']
             },
             'correct_answer': {'LAN': 'Local Area Network',
                                'WAN': 'Wide Area Network',
                                'ISP': 'Internet Service Provider',
                                'URL': 'Uniform Resource Locator'},
             'explanation': 'These are core CAPS networking acronyms.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these search techniques from MOST to LEAST specific.',
             'options': ['google one word search', 'site:gov.za matric exam',
                         '"matric exam timetable"'],
             'correct_answer': ['site:gov.za matric exam',
                                '"matric exam timetable"',
                                'google one word search'],
             'explanation': 'site: limits to one domain (most specific); quotes find exact phrases; one word is broadest.'},
            {'question_type': 'short_answer',
             'question_text': 'Name one way to make your online accounts more secure.',
             'options': [], 'correct_answer': 'two-factor authentication',
             'explanation': 'Strong passwords, 2FA, and not reusing passwords are all good answers.'},
        ]
    ),
}


G10_INFO = {
    'grade': 10, 'course_title': 'Information Management',
    'lessons': [
        {'order': 1, 'duration_minutes': 25, 'title': 'Data, Information and Knowledge',
         'content': intro('Lesson 1 &middot; The DIK Pyramid',
            'Information starts as raw <strong>data</strong>, becomes useful <strong>information</strong>, and grows into <strong>knowledge</strong> when applied.') + """
<table>
  <tr><th>Term</th><th>Definition</th><th>Example</th></tr>
  <tr><td>Data</td><td>Raw, unprocessed facts.</td><td>75</td></tr>
  <tr><td>Information</td><td>Processed data with meaning.</td><td>Thabo scored 75% in his Maths test.</td></tr>
  <tr><td>Knowledge</td><td>Information understood and applied.</td><td>Thabo passes Maths and can choose Maths Lit or Pure Maths next year.</td></tr>
</table>
""" + callout('info', 'fa-lightbulb', 'GIGO',
              '<strong>Garbage In, Garbage Out</strong> &mdash; bad data leads to bad information, no matter how powerful the computer.')},
        {'order': 2, 'duration_minutes': 30, 'title': 'Defining a Task and Finding Sources',
         'content': intro('Lesson 2 &middot; The Research Process',
            'Good research starts with a clear question. Then you find <em>credible</em> sources to answer it.') + """
<h2>Step 1: Define the task</h2>
<ul>
  <li>What exactly is the question or assignment?</li>
  <li>What is the audience and the format (essay, presentation, poster)?</li>
  <li>What is the deadline?</li>
</ul>
<h2>Step 2: Find sources</h2>
""" + grid([
    {'icon': 'fa-book', 'title': 'Print', 'body': 'Books, magazines, newspapers, encyclopaedias.'},
    {'icon': 'fa-globe', 'title': 'Internet', 'body': 'Websites, online journals, e-books.'},
    {'icon': 'fa-user', 'title': 'People', 'body': 'Interviews, experts, surveys.'},
    {'icon': 'fa-video', 'title': 'Multimedia', 'body': 'Documentaries, podcasts, videos.'},
]) + """
<h3>Primary vs secondary sources</h3>
<table>
  <tr><th>Primary</th><th>Secondary</th></tr>
  <tr><td>First-hand: interviews, experiments, original documents.</td><td>Second-hand: textbooks summarising others\' research.</td></tr>
</table>
"""},
        {'order': 3, 'duration_minutes': 35, 'title': 'Evaluating Information',
         'content': intro('Lesson 3 &middot; Can You Trust It?',
            'Anyone can publish anything online. You must evaluate every source before you trust it.') + """
<h2>The CRAAP test</h2>
<table>
  <tr><th>Letter</th><th>Question</th></tr>
  <tr><td><strong>C</strong>urrency</td><td>How recent is the information?</td></tr>
  <tr><td><strong>R</strong>elevance</td><td>Does it actually answer my question?</td></tr>
  <tr><td><strong>A</strong>uthority</td><td>Who wrote it? What are their qualifications?</td></tr>
  <tr><td><strong>A</strong>ccuracy</td><td>Can the facts be checked elsewhere?</td></tr>
  <tr><td><strong>P</strong>urpose</td><td>Why was it written? Inform, persuade, sell?</td></tr>
</table>
""" + callout('warn', 'fa-triangle-exclamation', 'Red flags',
              'No author, no date, full of ads, lots of CAPITAL LETTERS, or sites ending in <code>.info</code> with no contact details.') + """
<h3>Bias</h3>
<p>Information can be slanted to support one view. Read multiple sources and look for differences.</p>
"""},
        {'order': 4, 'duration_minutes': 30, 'title': 'File and Folder Management',
         'content': intro('Lesson 4 &middot; Stay Organised',
            'A well-named, well-sorted folder structure saves time and prevents lost work.') + """
<h2>Naming files well</h2>
<ul>
  <li>Be <strong>descriptive</strong>: <code>CAT_Project_Final.docx</code>, not <code>untitled.docx</code>.</li>
  <li>Use the <strong>date</strong> in <code>YYYY-MM-DD</code> for sorting: <code>2026-04-22_notes.docx</code>.</li>
  <li>Avoid spaces if possible &mdash; use <code>_</code> or <code>-</code>.</li>
  <li>Don\'t use slashes <code>/</code>, <code>\\</code>, <code>:</code> &mdash; they are illegal in filenames.</li>
</ul>
<h2>Folder structure</h2>
<p>Group by year &rarr; subject &rarr; topic. Example:</p>
<pre>School/
  Grade10/
    CAT/
      Term1/
      Term2/
    Maths/
    English/</pre>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Use <strong>OneDrive</strong> or another cloud folder so your files automatically back up and you can access them from any device.')},
        {'order': 5, 'duration_minutes': 25, 'title': 'Citing Sources and Avoiding Plagiarism',
         'content': intro('Lesson 5 &middot; Give Credit',
            '<strong>Plagiarism</strong> is using someone\'s words or ideas without saying so. It is a form of theft and can fail you.') + """
<h2>How to avoid plagiarism</h2>
<ul>
  <li>Take notes in your <em>own words</em>.</li>
  <li>Use quotation marks for direct quotes.</li>
  <li>Always include an in-text citation and a bibliography.</li>
  <li>Use <strong>References &rarr; Citations &amp; Bibliography</strong> in Word to manage sources.</li>
</ul>
<h3>A simple bibliography entry</h3>
<p><code>Smith, J. 2024. <em>Computers Today</em>. 3rd ed. Cape Town: Acme Press.</code></p>
""" + callout('key', 'fa-key', 'Key term',
              '<strong>Bibliography</strong> = full list of every source you used, at the end of your work.')},
    ],
    'quiz': make_quiz(
        'Information Management — Knowledge Check',
        'Tests data vs information, source evaluation, file management, plagiarism.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Which is an example of <em>information</em> rather than data?',
             'options': ['75', '"Thabo scored 75% in Maths"', 'A blank cell', 'A telephone number with no name'],
             'correct_answer': '"Thabo scored 75% in Maths"',
             'explanation': 'Information has meaning attached.'},
            {'question_type': 'multiple_choice',
             'question_text': 'GIGO stands for:',
             'options': ['Good Input, Good Output', 'Garbage In, Garbage Out',
                         'Go In, Go Out', 'General Information, General Output'],
             'correct_answer': 'Garbage In, Garbage Out',
             'explanation': 'Bad input always produces bad output.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which is a primary source?',
             'options': ['A textbook chapter', 'A Wikipedia summary',
                         'An interview you recorded yourself', 'A magazine review'],
             'correct_answer': 'An interview you recorded yourself',
             'explanation': 'Primary = first-hand from the source.'},
            {'question_type': 'multiple_choice',
             'question_text': 'In the CRAAP test, what does the "A" for Authority check?',
             'options': ['How long the article is', 'Who wrote it and their qualifications',
                         'How many ads it has', 'The website colour scheme'],
             'correct_answer': 'Who wrote it and their qualifications',
             'explanation': 'Authority = credentials of the author/publisher.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Which filename is the BEST for finding your work later?',
             'options': ['untitled.docx', 'doc1.docx',
                         '2026-04-22_CAT_Research_Final.docx', 'final final FINAL.docx'],
             'correct_answer': '2026-04-22_CAT_Research_Final.docx',
             'explanation': 'Date + subject + descriptive label = easy to find and sort.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each CRAAP letter to what it tests.',
             'options': {
                 'column_a': ['Currency', 'Relevance', 'Authority', 'Accuracy'],
                 'column_b': ['Is it recent?', 'Does it answer my question?',
                              'Who wrote it?', 'Can the facts be verified?']
             },
             'correct_answer': {'Currency': 'Is it recent?',
                                'Relevance': 'Does it answer my question?',
                                'Authority': 'Who wrote it?',
                                'Accuracy': 'Can the facts be verified?'},
             'explanation': 'CRAAP = Currency, Relevance, Authority, Accuracy, Purpose.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Arrange these research steps in the correct order.',
             'options': ['Evaluate sources', 'Define the task', 'Find sources',
                         'Process and present information'],
             'correct_answer': ['Define the task', 'Find sources',
                                'Evaluate sources', 'Process and present information'],
             'explanation': 'Task &rarr; Find &rarr; Evaluate &rarr; Process is the standard cycle.'},
            {'question_type': 'short_answer',
             'question_text': 'What is the term for using someone\'s words or ideas without crediting them?',
             'options': [], 'correct_answer': 'plagiarism',
             'explanation': 'Plagiarism is academic theft.'},
        ]
    ),
}


# ===========================================================================
# GRADE 11 — 6 courses
# ===========================================================================

G11_ADV_WORD = {
    'grade': 11, 'course_title': 'Advanced Word Processing',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'Styles and the Styles Pane',
         'content': intro('Lesson 1 &middot; Styles Save Hours',
            'A <strong>style</strong> is a saved bundle of formatting (font, size, colour, spacing). Apply it once to format whole sections at once.') + """
<h2>Why use styles?</h2>
""" + grid([
    {'icon': 'fa-bolt', 'title': 'Speed', 'body': 'One click instead of 5 menu choices.'},
    {'icon': 'fa-equals', 'title': 'Consistency', 'body': 'Every Heading 1 looks identical.'},
    {'icon': 'fa-list', 'title': 'Auto TOC', 'body': 'Word builds the Table of Contents from heading styles.'},
    {'icon': 'fa-paint-roller', 'title': 'Easy redesign', 'body': 'Change the style once &mdash; every paragraph updates.'},
]) + """
<h3>Built-in styles you must know</h3>
<table>
  <tr><th>Style</th><th>Use for</th></tr>
  <tr><td>Title</td><td>Document title (only one per doc).</td></tr>
  <tr><td>Heading 1</td><td>Main section headings.</td></tr>
  <tr><td>Heading 2 / 3</td><td>Sub-headings.</td></tr>
  <tr><td>Normal</td><td>Body text.</td></tr>
  <tr><td>Quote</td><td>Block quotations.</td></tr>
</table>
<h3>Modifying a style</h3>
<p>Right-click the style in the Styles pane &rarr; <strong>Modify</strong>. Change the formatting once &mdash; every paragraph using it updates automatically.</p>
"""},
        {'order': 2, 'duration_minutes': 35, 'title': 'Sections and Page Layout',
         'content': intro('Lesson 2 &middot; Mixing Page Layouts',
            'A <strong>section break</strong> lets one document have different page settings on different pages &mdash; e.g. a landscape table in a portrait report.') + """
<h2>Section break types</h2>
<table>
  <tr><th>Type</th><th>What it does</th></tr>
  <tr><td>Next Page</td><td>Starts the new section on a new page.</td></tr>
  <tr><td>Continuous</td><td>Starts a new section on the same page.</td></tr>
  <tr><td>Even / Odd Page</td><td>Starts on the next even or odd page (for book layouts).</td></tr>
</table>
<h3>What you can change per section</h3>
<ul>
  <li>Margins, page size, orientation.</li>
  <li>Headers and footers (link or unlink with <em>Link to Previous</em>).</li>
  <li>Page numbers and number style (Roman vs Arabic).</li>
  <li>Number of columns.</li>
</ul>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Turn on the <strong>&para;</strong> button (<em>Show/Hide formatting marks</em>) to see exactly where your section breaks are.')},
        {'order': 3, 'duration_minutes': 35, 'title': 'Headers, Footers and Page Numbers',
         'content': intro('Lesson 3 &middot; Top &amp; Bottom of Every Page',
            'Headers and footers repeat on every page. Page numbers, document title, your name, the date &mdash; all live here.') + """
<h2>Inserting a header or footer</h2>
<ol class="steps">
  <li><strong>Insert &rarr; Header</strong> (or Footer).</li>
  <li>Pick a built-in design or "Edit Header" for blank.</li>
  <li>Use the <strong>Header &amp; Footer Tools</strong> tab to:
    <ul>
      <li>Insert page numbers, date, document info.</li>
      <li>Differentiate first page or odd/even pages.</li>
    </ul>
  </li>
</ol>
<h3>Page number styles</h3>
<p>Use <strong>Insert &rarr; Page Number &rarr; Format Page Numbers</strong> to switch between 1, 2, 3 / i, ii, iii / a, b, c. Useful when the cover page should not show a number and the TOC uses Roman numerals.</p>
""" + callout('warn', 'fa-triangle-exclamation', 'Common mistake',
              'Don\'t type "Page 4" by hand &mdash; insert it as a field. Otherwise it won\'t update when you add or remove pages.')},
        {'order': 4, 'duration_minutes': 30, 'title': 'Table of Contents, Captions and Cross-references',
         'content': intro('Lesson 4 &middot; Long-Document Tools',
            'Long documents need a <strong>TOC</strong>, numbered figures and a way to refer back to them. Word builds these automatically.') + """
<h2>Generating a Table of Contents</h2>
<ol class="steps">
  <li>Apply Heading 1, 2, 3 styles throughout the document.</li>
  <li>Click where the TOC should go (usually after the cover page).</li>
  <li><strong>References &rarr; Table of Contents</strong> &rarr; pick a style.</li>
</ol>
<p>If you add or rename headings later, right-click the TOC &rarr; <strong>Update Field &rarr; Update entire table</strong>.</p>
<h3>Captions for figures and tables</h3>
<p>Right-click a picture or table &rarr; <strong>Insert Caption</strong>. Word numbers them automatically (Figure 1, Figure 2&hellip;).</p>
<h3>Cross-references</h3>
<p><strong>References &rarr; Cross-reference</strong> lets you say "see Figure 3 on page 12" &mdash; the page and figure number update automatically.</p>
"""},
        {'order': 5, 'duration_minutes': 30, 'title': 'Citations, Bibliography and References',
         'content': intro('Lesson 5 &middot; Academic Honesty',
            'Word can manage your sources and produce a perfectly formatted bibliography in any style.') + """
<h2>Add a source</h2>
<ol class="steps">
  <li><strong>References &rarr; Insert Citation &rarr; Add New Source</strong>.</li>
  <li>Choose the source type (Book, Journal Article, Website&hellip;).</li>
  <li>Fill in author, title, year, publisher.</li>
  <li>Click OK &mdash; an in-text citation appears.</li>
</ol>
<h3>Choose a referencing style</h3>
<p><strong>References &rarr; Style</strong> &mdash; APA, Harvard, MLA, Chicago. Whichever your school uses.</p>
<h3>Insert the bibliography</h3>
<p>At the end of the document, <strong>References &rarr; Bibliography</strong>. Word builds it from every source you cited.</p>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Use <strong>Manage Sources</strong> to copy your master list between assignments &mdash; never type out a reference twice.')},
    ],
    'quiz': make_quiz(
        'Advanced Word Processing — Knowledge Check',
        'Tests styles, sections, TOC, citations, captions.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Why use built-in heading styles?',
             'options': ['They look fancier', 'They make the document smaller',
                         'Word can build a TOC and outline from them',
                         'They translate to other languages'],
             'correct_answer': 'Word can build a TOC and outline from them',
             'explanation': 'Heading styles drive automatic TOC, navigation pane and outline.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which break would you use to put one landscape page in the middle of a portrait report?',
             'options': ['Page break', 'Column break', 'Section break (Next Page)',
                         'Line break'],
             'correct_answer': 'Section break (Next Page)',
             'explanation': 'Only section breaks let you change orientation mid-document.'},
            {'question_type': 'multiple_choice',
             'question_text': 'You renamed three headings. The TOC still shows the old titles. What do you do?',
             'options': ['Re-create the TOC from scratch', 'Right-click TOC &rarr; Update Field',
                         'Restart Word', 'Save as PDF'],
             'correct_answer': 'Right-click TOC &rarr; Update Field',
             'explanation': 'Update Field re-reads the headings.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Where do you change between APA and Harvard reference style?',
             'options': ['Home tab', 'References tab &rarr; Style', 'Insert tab',
                         'Layout tab'],
             'correct_answer': 'References tab &rarr; Style',
             'explanation': 'The References tab manages all citation work.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Captions for figures should be inserted by:',
             'options': ['Typing "Figure 1" manually', 'Using References &rarr; Insert Caption',
                         'Using bullet lists', 'Cropping the image'],
             'correct_answer': 'Using References &rarr; Insert Caption',
             'explanation': 'Auto-captions renumber if you add or remove figures.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each long-document feature with its purpose.',
             'options': {
                 'column_a': ['Heading 1 style', 'Section break', 'Caption', 'Bibliography'],
                 'column_b': ['Marks main headings for the TOC', 'Mixes layouts in one document',
                              'Numbers figures automatically', 'Lists every cited source']
             },
             'correct_answer': {'Heading 1 style': 'Marks main headings for the TOC',
                                'Section break': 'Mixes layouts in one document',
                                'Caption': 'Numbers figures automatically',
                                'Bibliography': 'Lists every cited source'},
             'explanation': 'These four features make professional reports manageable.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Arrange the steps to add a citation correctly.',
             'options': ['Insert Citation in your text',
                         'References &rarr; Add New Source &rarr; fill in details',
                         'Insert Bibliography at end of document',
                         'References &rarr; Style &rarr; choose APA / Harvard'],
             'correct_answer': ['References &rarr; Style &rarr; choose APA / Harvard',
                                'References &rarr; Add New Source &rarr; fill in details',
                                'Insert Citation in your text',
                                'Insert Bibliography at end of document'],
             'explanation': 'Set style, add the source, cite where needed, then build bibliography.'},
            {'question_type': 'short_answer',
             'question_text': 'What feature lets you write "see Figure 3" so the number updates automatically?',
             'options': [], 'correct_answer': 'cross-reference',
             'explanation': 'Cross-references update if figures are renumbered.'},
        ]
    ),
}


G11_ADV_SPREAD = {
    'grade': 11, 'course_title': 'Advanced Spreadsheets',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'Absolute vs Relative Cell References',
         'content': intro('Lesson 1 &middot; The Dollar Sign Trick',
            'When you copy a formula, cell references move with it &mdash; unless you "lock" them with <code>$</code>. This is one of the most important Excel skills.') + """
<h2>The three types</h2>
<table>
  <tr><th>Type</th><th>Looks like</th><th>What changes when copied</th></tr>
  <tr><td>Relative</td><td><code>A1</code></td><td>Both row and column shift.</td></tr>
  <tr><td>Absolute</td><td><code>$A$1</code></td><td>Nothing changes &mdash; locked.</td></tr>
  <tr><td>Mixed (col locked)</td><td><code>$A1</code></td><td>Row shifts, column stays.</td></tr>
  <tr><td>Mixed (row locked)</td><td><code>A$1</code></td><td>Column shifts, row stays.</td></tr>
</table>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Press ' + kbd('F4') + ' while editing a formula to cycle: <code>A1</code> &rarr; <code>$A$1</code> &rarr; <code>A$1</code> &rarr; <code>$A1</code>.') + """
<h3>Classic example: VAT calculation</h3>
<p>Cell <code>F1</code> contains <code>15%</code>. Your formula in C2 should be <code>=B2*$F$1</code>. When copied down to C3, C4, C5 it becomes <code>=B3*$F$1</code>, <code>=B4*$F$1</code> &mdash; <strong>F1 stays locked</strong> while B moves.</p>
"""},
        {'order': 2, 'duration_minutes': 35, 'title': 'Logical Functions: IF, AND, OR, IFS',
         'content': intro('Lesson 2 &middot; Decisions in Excel',
            '<strong>IF</strong> lets your spreadsheet make decisions: "if this is true, do A; otherwise do B."') + """
<h2>The IF syntax</h2>
<p><code>=IF(test, value_if_true, value_if_false)</code></p>
<h3>Example: pass / fail</h3>
<p><code>=IF(B2&gt;=50, "Pass", "Fail")</code></p>
<h2>AND / OR for multiple conditions</h2>
<table>
  <tr><th>Function</th><th>Returns TRUE when&hellip;</th></tr>
  <tr><td><code>AND(c1, c2, &hellip;)</code></td><td>ALL conditions are true.</td></tr>
  <tr><td><code>OR(c1, c2, &hellip;)</code></td><td>ANY condition is true.</td></tr>
</table>
<p>Example: <code>=IF(AND(B2&gt;=50, C2&gt;=80%), "Distinction", "Other")</code> &mdash; mark must be &ge; 50 AND attendance &ge; 80%.</p>
<h2>IFS &mdash; replacing nested IFs</h2>
<p>Instead of <code>=IF(A&gt;=80,"A",IF(A&gt;=70,"B",IF(A&gt;=60,"C","D")))</code> use:</p>
<p><code>=IFS(A&gt;=80,"A", A&gt;=70,"B", A&gt;=60,"C", TRUE,"D")</code></p>
""" + callout('warn', 'fa-triangle-exclamation', 'Watch your brackets',
              'Every <code>(</code> needs a matching <code>)</code>. Excel colour-codes them to help.')},
        {'order': 3, 'duration_minutes': 35, 'title': 'Lookup Functions: VLOOKUP, HLOOKUP, XLOOKUP',
         'content': intro('Lesson 3 &middot; Find a Value in a Table',
            'Lookup functions search for a value in one column and return the matching value from another column. They are the heart of any data system.') + """
<h2>VLOOKUP &mdash; vertical lookup</h2>
<p><code>=VLOOKUP(lookup_value, table_array, col_index, [exact])</code></p>
<table>
  <tr><th>Argument</th><th>Meaning</th></tr>
  <tr><td>lookup_value</td><td>What you\'re looking for (e.g. learner ID).</td></tr>
  <tr><td>table_array</td><td>The whole table to search.</td></tr>
  <tr><td>col_index</td><td>Which column to return (1 = first).</td></tr>
  <tr><td>FALSE / 0</td><td>Exact match. (Almost always use this.)</td></tr>
</table>
<h3>Example</h3>
<p><code>=VLOOKUP(A2, Learners!A:D, 3, FALSE)</code> &mdash; finds learner A2 in Learners sheet, returns column 3.</p>
<h2>HLOOKUP</h2>
<p>Same idea but searches the <strong>top row</strong> instead of the left column &mdash; rare in practice.</p>
<h2>XLOOKUP &mdash; the modern replacement</h2>
<p><code>=XLOOKUP(lookup_value, lookup_array, return_array)</code></p>
<p>No column number, can return values to the LEFT, doesn\'t need sorted data.</p>
""" + callout('key', 'fa-key', 'Common error',
              '<code>#N/A</code> = "value not found". Double-check spelling and the lookup column.')},
        {'order': 4, 'duration_minutes': 35, 'title': 'Conditional Functions: SUMIF, COUNTIF, AVERAGEIF',
         'content': intro('Lesson 4 &middot; Counting and Adding with Conditions',
            'These functions let you SUM, COUNT or AVERAGE only the cells that meet a rule.') + """
<h2>The "IF" family</h2>
<table>
  <tr><th>Function</th><th>Use it for</th></tr>
  <tr><td><code>COUNTIF(range, criteria)</code></td><td>How many cells match a rule.</td></tr>
  <tr><td><code>SUMIF(range, criteria, [sum_range])</code></td><td>Add only the cells that match.</td></tr>
  <tr><td><code>AVERAGEIF(range, criteria, [avg_range])</code></td><td>Average only matching cells.</td></tr>
</table>
<h3>Examples</h3>
<ul>
  <li><code>=COUNTIF(B2:B100, "Pass")</code> &mdash; how many learners passed?</li>
  <li><code>=SUMIF(D2:D100, "Maths", E2:E100)</code> &mdash; total marks where subject is Maths.</li>
  <li><code>=AVERAGEIF(B2:B100, "&gt;=50")</code> &mdash; average of marks 50 or higher.</li>
</ul>
<h2>Multiple criteria: COUNTIFS, SUMIFS</h2>
<p>Use the <em>plural</em> versions for two or more rules: <code>=COUNTIFS(B:B, "Maths", C:C, "&gt;=80")</code>.</p>
"""},
        {'order': 5, 'duration_minutes': 30, 'title': 'Sorting, Filtering and Pivot Tables',
         'content': intro('Lesson 5 &middot; Analysing Data',
            'Real datasets have hundreds of rows. Sorting, filtering and pivot tables let you make sense of them in seconds.') + """
<h2>Sort</h2>
<p>Click any cell in the data &rarr; <strong>Data &rarr; Sort</strong>. You can sort on multiple levels (e.g. by Subject, then by Mark).</p>
<h2>Filter</h2>
<p><strong>Data &rarr; Filter</strong> adds drop-down arrows. Tick what you want to see; the rest hides.</p>
<h2>Pivot tables &mdash; the killer feature</h2>
<ol class="steps">
  <li>Select your data (must have headings).</li>
  <li><strong>Insert &rarr; PivotTable</strong>.</li>
  <li>Drag fields into the <em>Rows</em>, <em>Columns</em>, <em>Values</em> and <em>Filters</em> areas.</li>
  <li>Excel summarises &mdash; e.g. <em>average mark per subject per grade</em>.</li>
</ol>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Right-click a pivot table value &rarr; <strong>Show Values As &rarr; % of Grand Total</strong> for instant percentage analysis.')},
    ],
    'quiz': make_quiz(
        'Advanced Spreadsheets — Knowledge Check',
        'Tests references, IF, VLOOKUP, SUMIF and pivot tables.',
        [
            {'question_type': 'multiple_choice',
             'question_text': '<code>$A$1</code> is what type of reference?',
             'options': ['Relative', 'Absolute', 'Mixed (row locked)', 'Mixed (col locked)'],
             'correct_answer': 'Absolute',
             'explanation': 'Both column A and row 1 are locked with $.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which formula gives "Pass" if B2 is 50 or more, otherwise "Fail"?',
             'options': ['=PASSFAIL(B2)', '=IF(B2&gt;=50,"Pass","Fail")',
                         '=IF(B2,Pass,Fail)', '=B2&gt;=50'],
             'correct_answer': '=IF(B2&gt;=50,"Pass","Fail")',
             'explanation': 'IF takes test, value-if-true, value-if-false.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which result does <code>=COUNTIF(B2:B10,"Pass")</code> give?',
             'options': ['Sum of marks', 'Number of cells equal to "Pass"',
                         'Average mark', 'Highest mark'],
             'correct_answer': 'Number of cells equal to "Pass"',
             'explanation': 'COUNTIF counts cells matching the criteria.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'In <code>=VLOOKUP(A2, Learners!A:D, 3, FALSE)</code>, what does the 3 mean?',
             'options': ['The number of matches', 'The third column of the table to return',
                         'Three decimal places', 'Round up to 3'],
             'correct_answer': 'The third column of the table to return',
             'explanation': 'col_index is 1-based from the leftmost column of the table.'},
            {'question_type': 'multiple_choice',
             'question_text': 'You see <code>#N/A</code> in a VLOOKUP. The most likely cause is:',
             'options': ['The file is too big', 'Excel is offline',
                         'The lookup value was not found', 'Wrong font'],
             'correct_answer': 'The lookup value was not found',
             'explanation': '#N/A means "not available / not found".'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each function with what it does.',
             'options': {
                 'column_a': ['IF', 'COUNTIF', 'SUMIF', 'AVERAGEIF'],
                 'column_b': ['Returns one of two values based on a test',
                              'Counts cells that match a criterion',
                              'Adds cells that match a criterion',
                              'Averages cells that match a criterion']
             },
             'correct_answer': {
                 'IF': 'Returns one of two values based on a test',
                 'COUNTIF': 'Counts cells that match a criterion',
                 'SUMIF': 'Adds cells that match a criterion',
                 'AVERAGEIF': 'Averages cells that match a criterion'},
             'explanation': 'These cover almost all CAPS conditional analysis tasks.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Arrange the steps to create a pivot table.',
             'options': ['Drag fields to Rows / Values / Columns',
                         'Insert &rarr; PivotTable',
                         'Select your data with headings'],
             'correct_answer': ['Select your data with headings',
                                'Insert &rarr; PivotTable',
                                'Drag fields to Rows / Values / Columns'],
             'explanation': 'Always select first, then insert, then arrange fields.'},
            {'question_type': 'short_answer',
             'question_text': 'Which function key cycles through reference types ($A$1 / A$1 / $A1)?',
             'options': [], 'correct_answer': 'F4',
             'explanation': 'F4 toggles absolute/mixed/relative while editing a formula.'},
        ]
    ),
}


G11_DB = {
    'grade': 11, 'course_title': 'Database Concepts',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'What is a Database?',
         'content': intro('Lesson 1 &middot; Beyond Spreadsheets',
            'A <strong>database</strong> is an organised collection of related data, designed for fast searching, updating and analysis.') + """
<h2>Database vs spreadsheet</h2>
<table>
  <tr><th>Spreadsheet</th><th>Database</th></tr>
  <tr><td>Best for &lt; 1000 rows.</td><td>Handles millions of rows.</td></tr>
  <tr><td>One flat sheet.</td><td>Many <em>related</em> tables.</td></tr>
  <tr><td>One user at a time.</td><td>Many users at once.</td></tr>
  <tr><td>Easy to break with bad data.</td><td>Validation rules built in.</td></tr>
</table>
""" + callout('info', 'fa-lightbulb', 'Examples around you',
              'Your school\'s learner records, the bank\'s account system, Takealot\'s product catalogue &mdash; all databases.') + """
<h3>DBMS</h3>
<p>A <strong>Database Management System</strong> is the software that runs the database. Examples: <em>Microsoft Access</em>, MySQL, PostgreSQL, SQL Server.</p>
"""},
        {'order': 2, 'duration_minutes': 35, 'title': 'Tables, Records and Fields',
         'content': intro('Lesson 2 &middot; The Basic Building Blocks',
            'A database is made of <strong>tables</strong>. Each table has <strong>records</strong> (rows) and <strong>fields</strong> (columns).') + """
<table>
  <tr><th>Term</th><th>Meaning</th><th>Spreadsheet equivalent</th></tr>
  <tr><td>Table</td><td>One subject (e.g. Learners)</td><td>Worksheet</td></tr>
  <tr><td>Record</td><td>One item / one person</td><td>Row</td></tr>
  <tr><td>Field</td><td>One attribute (e.g. Surname)</td><td>Column</td></tr>
</table>
<h3>Field data types</h3>
<table>
  <tr><th>Type</th><th>Use for</th></tr>
  <tr><td>Short Text</td><td>Names, addresses (max 255 chars).</td></tr>
  <tr><td>Long Text (Memo)</td><td>Notes, paragraphs.</td></tr>
  <tr><td>Number</td><td>Quantities, prices.</td></tr>
  <tr><td>Date/Time</td><td>Birth dates, timestamps.</td></tr>
  <tr><td>Yes/No</td><td>Boolean (paid? active?).</td></tr>
  <tr><td>AutoNumber</td><td>Unique IDs, generated automatically.</td></tr>
  <tr><td>Currency</td><td>Money &mdash; always 2 decimals.</td></tr>
</table>
""" + callout('key', 'fa-key', 'Primary key',
              'A <strong>primary key</strong> is a field that uniquely identifies each record (e.g. Learner ID). Every table needs one.')},
        {'order': 3, 'duration_minutes': 35, 'title': 'Relationships and Normalisation',
         'content': intro('Lesson 3 &middot; Linking Tables',
            'Relational databases avoid duplicating data by splitting it into related tables. <strong>Normalisation</strong> is the process of designing them well.') + """
<h2>Three relationship types</h2>
""" + grid([
    {'icon': 'fa-arrows-left-right', 'title': 'One-to-One', 'body': 'One person, one ID document.'},
    {'icon': 'fa-arrows-up-down', 'title': 'One-to-Many', 'body': 'One teacher, many subjects.'},
    {'icon': 'fa-arrows-spin', 'title': 'Many-to-Many', 'body': 'Many learners take many subjects (needs a junction table).'},
]) + """
<h3>Foreign key</h3>
<p>A <strong>foreign key</strong> in one table refers to the primary key of another table. Example: <code>SubjectID</code> in the Marks table refers to the <code>SubjectID</code> primary key in the Subjects table.</p>
<h3>Why normalise?</h3>
<ul>
  <li>No duplicated data &rarr; less storage, fewer mistakes.</li>
  <li>Update one place, everywhere updates.</li>
  <li>Easier to query and maintain.</li>
</ul>
""" + callout('warn', 'fa-triangle-exclamation', 'Common pitfall',
              'Storing "Cape Town, Western Cape" in one field. Split into <em>City</em> and <em>Province</em> for sortable, searchable data.')},
        {'order': 4, 'duration_minutes': 35, 'title': 'Queries: Asking Questions of Your Data',
         'content': intro('Lesson 4 &middot; Find Exactly What You Need',
            'A <strong>query</strong> retrieves a subset of records that meet your criteria.') + """
<h2>Types of queries (Access)</h2>
<table>
  <tr><th>Type</th><th>What it does</th></tr>
  <tr><td>Select</td><td>Retrieves matching records (most common).</td></tr>
  <tr><td>Parameter</td><td>Asks the user for input each time it runs.</td></tr>
  <tr><td>Update</td><td>Changes data in many records at once.</td></tr>
  <tr><td>Delete</td><td>Removes matching records.</td></tr>
  <tr><td>Append</td><td>Adds records to another table.</td></tr>
</table>
<h3>Common criteria</h3>
<table>
  <tr><th>Criteria</th><th>Meaning</th></tr>
  <tr><td><code>"Maths"</code></td><td>Exactly equal to Maths.</td></tr>
  <tr><td><code>&gt;=50</code></td><td>50 or more.</td></tr>
  <tr><td><code>Like "T*"</code></td><td>Starts with T.</td></tr>
  <tr><td><code>Between 50 And 75</code></td><td>Inclusive range.</td></tr>
  <tr><td><code>Is Null</code></td><td>Field is empty.</td></tr>
</table>
"""},
        {'order': 5, 'duration_minutes': 30, 'title': 'Forms and Reports',
         'content': intro('Lesson 5 &middot; Friendly Faces for Data',
            '<strong>Forms</strong> are input screens; <strong>reports</strong> are formatted printable output.') + """
<h2>Forms</h2>
<ul>
  <li>Easier &amp; safer than typing into the table directly.</li>
  <li>Can include drop-downs, validation, buttons.</li>
  <li>Built with <strong>Create &rarr; Form Wizard</strong> in Access.</li>
</ul>
<h2>Reports</h2>
<ul>
  <li>Designed for printing or PDF export.</li>
  <li>Group records (e.g. by Grade), add totals and averages.</li>
  <li>Built with <strong>Create &rarr; Report Wizard</strong>.</li>
</ul>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Base reports on <em>queries</em> (not directly on tables) so you can filter exactly which records appear.')},
    ],
    'quiz': make_quiz(
        'Database Concepts — Knowledge Check',
        'Tests tables, fields, keys, relationships, queries and reports.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'In a database, a <strong>record</strong> is the same as a:',
             'options': ['Field', 'Row', 'Table', 'Database'],
             'correct_answer': 'Row',
             'explanation': 'A record is one row (one item).'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which field uniquely identifies a record?',
             'options': ['Foreign key', 'Primary key', 'Index', 'Caption'],
             'correct_answer': 'Primary key',
             'explanation': 'Primary keys must be unique within the table.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Storing prices is best done with which data type?',
             'options': ['Short Text', 'Yes/No', 'Currency', 'AutoNumber'],
             'correct_answer': 'Currency',
             'explanation': 'Currency formats with two decimals and a symbol.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A teacher can teach many subjects but each subject is taught by one teacher. This is a:',
             'options': ['One-to-One', 'One-to-Many', 'Many-to-Many', 'No relationship'],
             'correct_answer': 'One-to-Many',
             'explanation': 'One teacher to many subjects = 1:M.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Which criterion finds learners whose surname starts with T?',
             'options': ['"T"', '&gt;T', 'Like "T*"', 'Between T And Z'],
             'correct_answer': 'Like "T*"',
             'explanation': 'The Like operator with * wildcard matches a pattern.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each database object with its job.',
             'options': {
                 'column_a': ['Table', 'Query', 'Form', 'Report'],
                 'column_b': ['Stores the data', 'Asks questions of the data',
                              'Input screen for users', 'Formatted printable output']
             },
             'correct_answer': {'Table': 'Stores the data',
                                'Query': 'Asks questions of the data',
                                'Form': 'Input screen for users',
                                'Report': 'Formatted printable output'},
             'explanation': 'These are the four main object types in Access.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these database design steps.',
             'options': ['Identify the entities (tables)',
                         'Define fields and data types',
                         'Set primary keys',
                         'Create relationships between tables'],
             'correct_answer': ['Identify the entities (tables)',
                                'Define fields and data types',
                                'Set primary keys',
                                'Create relationships between tables'],
             'explanation': 'Standard relational design order.'},
            {'question_type': 'short_answer',
             'question_text': 'What is the term for a field in one table that links to a primary key in another?',
             'options': [], 'correct_answer': 'foreign key',
             'explanation': 'Foreign keys enforce relationships between tables.'},
        ]
    ),
}


G11_ADV_PRES = {
    'grade': 11, 'course_title': 'Advanced Presentations',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'Slide Master and Custom Templates',
         'content': intro('Lesson 1 &middot; One Place to Rule Them All',
            'The <strong>Slide Master</strong> controls fonts, colours, logos and layouts for every slide. Master it and your decks become consistent and quick to update.') + """
<h2>Anatomy</h2>
<ul>
  <li><strong>Master</strong> &mdash; the parent slide. Changes here affect everything below it.</li>
  <li><strong>Layouts</strong> &mdash; child slides for Title, Content, Two Content, etc.</li>
  <li><strong>Placeholders</strong> &mdash; reserved areas for title, text, image.</li>
</ul>
<h3>Editing the Master</h3>
<ol class="steps">
  <li><strong>View &rarr; Slide Master</strong>.</li>
  <li>Click the topmost (largest) slide thumbnail to edit the master.</li>
  <li>Change the theme fonts, colours and add a logo.</li>
  <li>Click <strong>Close Master View</strong> when done.</li>
</ol>
""" + callout('tip', 'fa-bolt', 'Save as template',
              '<strong>File &rarr; Save As &rarr; PowerPoint Template (.potx)</strong> &mdash; reuse your design forever.')},
        {'order': 2, 'duration_minutes': 30, 'title': 'Custom Animations and Triggers',
         'content': intro('Lesson 2 &middot; Beyond Fade and Fly-In',
            'Advanced animations let you build interactive infographics, click-to-reveal answers and walk-throughs.') + """
<h2>The Animation Pane</h2>
<p><strong>Animations &rarr; Animation Pane</strong> &mdash; reorder, time and group every animation in one panel.</p>
<h3>Start options</h3>
<table>
  <tr><th>Option</th><th>Meaning</th></tr>
  <tr><td>On Click</td><td>Waits for a mouse click.</td></tr>
  <tr><td>With Previous</td><td>Plays at the same time as the one above.</td></tr>
  <tr><td>After Previous</td><td>Plays right after the one above ends.</td></tr>
</table>
<h2>Triggers</h2>
<p>An animation can be triggered by clicking <em>another object</em>. Use it for click-the-question-to-show-the-answer activities.</p>
""" + callout('warn', 'fa-triangle-exclamation', 'Don\'t overdo it',
              'A presentation isn\'t a music video. Animate to <em>guide attention</em>, not to entertain.')},
        {'order': 3, 'duration_minutes': 30, 'title': 'Hyperlinks and Action Buttons',
         'content': intro('Lesson 3 &middot; Make Slides Interactive',
            'Hyperlinks turn presentations into <em>navigable</em> documents &mdash; menus, quizzes and branching scenarios.') + """
<h2>Linking</h2>
<table>
  <tr><th>Link target</th><th>How</th></tr>
  <tr><td>Another slide</td><td>Insert &rarr; Link &rarr; Place in This Document.</td></tr>
  <tr><td>A website</td><td>Insert &rarr; Link &rarr; Existing File or Web Page.</td></tr>
  <tr><td>A file (PDF, Word)</td><td>Same as above &mdash; pick the file.</td></tr>
  <tr><td>An email address</td><td>Insert &rarr; Link &rarr; E-mail Address.</td></tr>
</table>
<h3>Action Buttons</h3>
<p><strong>Insert &rarr; Shapes &rarr; Action Buttons</strong> &mdash; ready-made Home, Back, Next, Help, Information buttons.</p>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Set the action to <strong>Mouse Over</strong> for hover-style menus.')},
        {'order': 4, 'duration_minutes': 30, 'title': 'Embedding Audio and Video',
         'content': intro('Lesson 4 &middot; Multimedia',
            'Sound effects, narration and video clips make slides come alive &mdash; if used sparingly.') + """
<h2>Inserting media</h2>
<ul>
  <li><strong>Insert &rarr; Audio</strong> &mdash; from your computer or record narration.</li>
  <li><strong>Insert &rarr; Video</strong> &mdash; from device or online (YouTube link).</li>
</ul>
<h3>Playback options</h3>
<table>
  <tr><th>Option</th><th>What it does</th></tr>
  <tr><td>Start Automatically</td><td>Plays as soon as the slide opens.</td></tr>
  <tr><td>Loop until Stopped</td><td>Restarts when finished.</td></tr>
  <tr><td>Hide During Show</td><td>Hides the speaker icon during slideshow.</td></tr>
  <tr><td>Trim</td><td>Cut a clip to just the bit you want.</td></tr>
</table>
""" + callout('warn', 'fa-triangle-exclamation', 'File size',
              'Embedded videos make files huge. Use <strong>File &rarr; Compress Media</strong> for smaller emails.')},
        {'order': 5, 'duration_minutes': 25, 'title': 'Packaging and Sharing Presentations',
         'content': intro('Lesson 5 &middot; Get It to Your Audience',
            'Once your masterpiece is ready, share it in the right format for the situation.') + """
<h2>Export options</h2>
<table>
  <tr><th>Format</th><th>Use case</th></tr>
  <tr><td>.pptx</td><td>Editable PowerPoint file.</td></tr>
  <tr><td>.ppsx</td><td>Opens straight in slideshow.</td></tr>
  <tr><td>.pdf</td><td>Read-only handout, prints reliably.</td></tr>
  <tr><td>Video (.mp4)</td><td>Auto-playing presentation, share anywhere.</td></tr>
  <tr><td>Package for CD</td><td>Bundles fonts and linked files.</td></tr>
</table>
<h3>OneDrive sharing</h3>
<p>Save in OneDrive and use <strong>File &rarr; Share</strong> to send a link &mdash; recipients can co-edit in their browser.</p>
""" + callout('key', 'fa-key', 'Best practice',
              'Send a <strong>PDF</strong> for read-only audiences and a <strong>.pptx</strong> only for collaborators.')},
    ],
    'quiz': make_quiz(
        'Advanced Presentations — Knowledge Check',
        'Tests Slide Master, animations, links, multimedia, sharing.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'You want one logo on every slide. Best place to add it:',
             'options': ['Each slide individually', 'Slide Master', 'A header',
                         'A text box on slide 1'],
             'correct_answer': 'Slide Master',
             'explanation': 'The Master applies to every slide automatically.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A trigger animation plays:',
             'options': ['On a timer', 'When you click a specific other object',
                         'When the file opens', 'During every slide'],
             'correct_answer': 'When you click a specific other object',
             'explanation': 'Triggers tie an animation to a particular object click.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which file format opens directly in slideshow mode?',
             'options': ['.pptx', '.ppsx', '.pdf', '.docx'],
             'correct_answer': '.ppsx',
             'explanation': 'PowerPoint Show files start the slideshow.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Your presentation file is too big to email. The best fix is:',
             'options': ['Delete slides', 'Save as PDF', 'Compress Media', 'Re-record audio'],
             'correct_answer': 'Compress Media',
             'explanation': 'File &rarr; Compress Media reduces video/audio size.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which Animation Pane option plays an effect immediately after the previous one with no click?',
             'options': ['On Click', 'With Previous', 'After Previous', 'On Hover'],
             'correct_answer': 'After Previous',
             'explanation': 'After Previous chains effects automatically.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each Slide Master concept with its description.',
             'options': {
                 'column_a': ['Master slide', 'Layout', 'Placeholder', 'Theme'],
                 'column_b': ['Parent that controls all slides',
                              'Pre-arranged child slide design',
                              'Reserved area for content',
                              'Bundle of fonts, colours and effects']
             },
             'correct_answer': {'Master slide': 'Parent that controls all slides',
                                'Layout': 'Pre-arranged child slide design',
                                'Placeholder': 'Reserved area for content',
                                'Theme': 'Bundle of fonts, colours and effects'},
             'explanation': 'Knowing each part lets you redesign efficiently.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these steps to make a slide-jump menu.',
             'options': ['Insert action button shape',
                         'Right-click button &rarr; Link &rarr; Place in This Document',
                         'Pick the destination slide'],
             'correct_answer': ['Insert action button shape',
                                'Right-click button &rarr; Link &rarr; Place in This Document',
                                'Pick the destination slide'],
             'explanation': 'Insert, link, choose destination.'},
            {'question_type': 'short_answer',
             'question_text': 'In which file format would you save a presentation as a self-playing video?',
             'options': [], 'correct_answer': 'mp4',
             'explanation': 'Export &rarr; Create a Video produces an MP4.'},
        ]
    ),
}


G11_SYS = {
    'grade': 11, 'course_title': 'System Software',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'Operating Systems &mdash; The Manager',
         'content': intro('Lesson 1 &middot; OS Basics',
            'The <strong>Operating System (OS)</strong> is the software that runs the computer &mdash; managing hardware, files, security and every application.') + """
<h2>Main jobs of an OS</h2>
""" + grid([
    {'icon': 'fa-microchip', 'title': 'Manage hardware', 'body': 'Talks to CPU, RAM, storage, printer, screen.'},
    {'icon': 'fa-folder', 'title': 'File management', 'body': 'Organises files in folders; tracks where data lives.'},
    {'icon': 'fa-user-shield', 'title': 'User accounts &amp; security', 'body': 'Logins, permissions, passwords.'},
    {'icon': 'fa-circle-nodes', 'title': 'Process management', 'body': 'Decides which program gets CPU time.'},
]) + """
<h3>Common operating systems</h3>
<table>
  <tr><th>OS</th><th>Used on</th></tr>
  <tr><td>Windows</td><td>Most school and office PCs.</td></tr>
  <tr><td>macOS</td><td>Apple Mac computers.</td></tr>
  <tr><td>Linux (Ubuntu, Mint)</td><td>Servers, developers, free desktops.</td></tr>
  <tr><td>Android / iOS</td><td>Mobile phones and tablets.</td></tr>
  <tr><td>Chrome OS</td><td>Chromebooks &mdash; cloud-first.</td></tr>
</table>
"""},
        {'order': 2, 'duration_minutes': 30, 'title': 'GUI vs CLI &mdash; Two Ways to Talk to a Computer',
         'content': intro('Lesson 2 &middot; Pointing vs Typing',
            'Most people use a <strong>Graphical User Interface (GUI)</strong>. Power users and admins also use a <strong>Command Line Interface (CLI)</strong>.') + """
<table>
  <tr><th>GUI</th><th>CLI</th></tr>
  <tr><td>Visual: windows, icons, menus, pointer.</td><td>Text-only commands typed at a prompt.</td></tr>
  <tr><td>Easier for beginners.</td><td>Faster for experts.</td></tr>
  <tr><td>Uses more system resources.</td><td>Lightweight &mdash; runs on tiny servers.</td></tr>
</table>
<h3>Useful CLI examples</h3>
<table>
  <tr><th>Windows (PowerShell)</th><th>What it does</th></tr>
  <tr><td><code>dir</code></td><td>List files in current folder.</td></tr>
  <tr><td><code>cd Documents</code></td><td>Change directory to Documents.</td></tr>
  <tr><td><code>copy file.txt new.txt</code></td><td>Copy a file.</td></tr>
  <tr><td><code>ipconfig</code></td><td>Show network info.</td></tr>
</table>
"""},
        {'order': 3, 'duration_minutes': 35, 'title': 'Utility Software',
         'content': intro('Lesson 3 &middot; Helpers Behind the Scenes',
            '<strong>Utility software</strong> performs maintenance tasks &mdash; cleaning, securing, backing up and optimising.') + """
""" + grid([
    {'icon': 'fa-shield-virus', 'title': 'Antivirus', 'body': 'Detects and removes malware.'},
    {'icon': 'fa-broom', 'title': 'Disk Cleanup', 'body': 'Removes temp files to free space.'},
    {'icon': 'fa-puzzle-piece', 'title': 'Defragmenter (HDD only)', 'body': 'Re-orders files for faster reads.'},
    {'icon': 'fa-cloud-arrow-up', 'title': 'Backup', 'body': 'Copies your data to safe storage.'},
    {'icon': 'fa-file-zipper', 'title': 'Compression (ZIP)', 'body': 'Shrinks files for sharing.'},
    {'icon': 'fa-screwdriver-wrench', 'title': 'Diagnostic tools', 'body': 'Test RAM, drives, network.'},
]) + callout('warn', 'fa-triangle-exclamation', 'SSDs',
              'Never defrag an <strong>SSD</strong>. It shortens its life. SSDs use <em>TRIM</em> instead, automatically.')},
        {'order': 4, 'duration_minutes': 30, 'title': 'Installing and Updating Software',
         'content': intro('Lesson 4 &middot; Adding and Removing Programs',
            'Knowing how to install software safely &mdash; and remove the bloatware that comes with it &mdash; is an essential skill.') + """
<h2>Where to get software</h2>
<ul>
  <li><strong>Microsoft Store</strong> / <strong>Mac App Store</strong> &mdash; vetted apps.</li>
  <li>Official vendor websites &mdash; e.g. <code>microsoft.com</code>, <code>mozilla.org</code>.</li>
  <li><strong>Avoid</strong> random "free download" sites &mdash; often laced with malware.</li>
</ul>
<h3>Installation steps</h3>
<ol class="steps">
  <li>Download the installer (<code>.exe</code> on Windows, <code>.dmg</code> on Mac).</li>
  <li>Right-click &rarr; <em>Properties &rarr; Unblock</em> if Windows warns.</li>
  <li>Run the installer; read each screen &mdash; <strong>untick add-on toolbars</strong>.</li>
  <li>Restart if requested.</li>
</ol>
<h3>Updates</h3>
""" + callout('key', 'fa-key', 'Why update?',
              'Updates fix <strong>security holes</strong> as well as bugs. Set Windows Update to install automatically.')},
        {'order': 5, 'duration_minutes': 25, 'title': 'Backups, Recovery and Maintenance',
         'content': intro('Lesson 5 &middot; Don\'t Lose Your Work',
            'Hardware fails, files corrupt, laptops get stolen. A good backup means your photos and projects survive.') + """
<h2>The 3-2-1 rule</h2>
<ul>
  <li><strong>3</strong> copies of your data.</li>
  <li>On <strong>2</strong> different types of storage.</li>
  <li><strong>1</strong> copy off-site (cloud or different building).</li>
</ul>
<h3>Backup options</h3>
<table>
  <tr><th>Tool</th><th>Type</th></tr>
  <tr><td>OneDrive / Google Drive</td><td>Cloud sync.</td></tr>
  <tr><td>External hard drive</td><td>Local full backup.</td></tr>
  <tr><td>Windows File History</td><td>Versioned backup of personal folders.</td></tr>
</table>
<h3>System Restore</h3>
<p>Windows can roll back to an earlier <strong>restore point</strong> if a bad install or update breaks your computer. <em>Doesn\'t affect personal files</em>.</p>
"""},
    ],
    'quiz': make_quiz(
        'System Software — Knowledge Check',
        'Tests OS, GUI/CLI, utilities, installation and backups.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Which of these is NOT an operating system?',
             'options': ['Windows', 'Linux', 'macOS', 'Microsoft Word'],
             'correct_answer': 'Microsoft Word',
             'explanation': 'Word is application software; the others are OSes.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A GUI uses:',
             'options': ['Only typed commands', 'Windows, icons, menus, pointer',
                         'Voice only', 'Punched cards'],
             'correct_answer': 'Windows, icons, menus, pointer',
             'explanation': 'GUI = WIMP interface.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which utility scans for and removes viruses?',
             'options': ['Defragmenter', 'Antivirus', 'Compression tool', 'File Explorer'],
             'correct_answer': 'Antivirus',
             'explanation': 'Antivirus protects against malware.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Which storage device should NEVER be defragmented?',
             'options': ['HDD', 'SSD', 'External hard drive', 'CD'],
             'correct_answer': 'SSD',
             'explanation': 'Defrag wears out flash memory; SSDs use TRIM.'},
            {'question_type': 'multiple_choice',
             'question_text': 'The 3-2-1 backup rule says you should have:',
             'options': ['3 hard drives', '3 copies, 2 media, 1 off-site',
                         '3 antivirus programs', '3 user accounts'],
             'correct_answer': '3 copies, 2 media, 1 off-site',
             'explanation': '3-2-1 is the standard backup strategy.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each utility with its purpose.',
             'options': {
                 'column_a': ['Disk Cleanup', 'Defragmenter', 'Backup', 'Compression'],
                 'column_b': ['Frees space by removing temp files',
                              'Re-orders files on an HDD',
                              'Copies your data to safe storage',
                              'Shrinks files for sharing']
             },
             'correct_answer': {'Disk Cleanup': 'Frees space by removing temp files',
                                'Defragmenter': 'Re-orders files on an HDD',
                                'Backup': 'Copies your data to safe storage',
                                'Compression': 'Shrinks files for sharing'},
             'explanation': 'Each utility solves a specific maintenance problem.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these steps for safely installing new software.',
             'options': ['Download from official source',
                         'Read installer screens; untick toolbars',
                         'Run the installer',
                         'Restart if requested'],
             'correct_answer': ['Download from official source',
                                'Run the installer',
                                'Read installer screens; untick toolbars',
                                'Restart if requested'],
             'explanation': 'Always source officially, then read every install step carefully.'},
            {'question_type': 'short_answer',
             'question_text': 'What feature lets Windows roll back to a previous working state without affecting personal files?',
             'options': [], 'correct_answer': 'system restore',
             'explanation': 'System Restore reverts system files only.'},
        ]
    ),
}


G11_INTERNET_SOC = {
    'grade': 11, 'course_title': 'Internet & Social Implications',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'E-Commerce',
         'content': intro('Lesson 1 &middot; Buying and Selling Online',
            '<strong>E-commerce</strong> is buying and selling goods or services over the internet. South Africans use it daily &mdash; from Takealot to Uber Eats.') + """
<h2>E-commerce models</h2>
<table>
  <tr><th>Model</th><th>Meaning</th><th>Example</th></tr>
  <tr><td>B2C</td><td>Business to Consumer</td><td>Takealot &rarr; you</td></tr>
  <tr><td>B2B</td><td>Business to Business</td><td>Wholesaler &rarr; spaza</td></tr>
  <tr><td>C2C</td><td>Consumer to Consumer</td><td>Gumtree, Yaga</td></tr>
  <tr><td>C2B</td><td>Consumer to Business</td><td>Influencer selling ads to a brand</td></tr>
</table>
<h3>Pros &amp; cons</h3>
""" + grid([
    {'icon': 'fa-thumbs-up', 'title': 'Pro: Convenience', 'body': 'Shop 24/7 from anywhere.'},
    {'icon': 'fa-thumbs-up', 'title': 'Pro: Choice', 'body': 'Wider selection than any physical shop.'},
    {'icon': 'fa-thumbs-down', 'title': 'Con: Can\'t touch', 'body': 'No way to feel quality before buying.'},
    {'icon': 'fa-thumbs-down', 'title': 'Con: Risk', 'body': 'Scams, fake sites, delivery issues.'},
])},
        {'order': 2, 'duration_minutes': 30, 'title': 'Cyber Crime and Cyber Security',
         'content': intro('Lesson 2 &middot; Threats Online',
            'Cyber crime costs South Africa billions every year. Knowing the threats is the first step to staying safe.') + """
<h2>Common cyber crimes</h2>
<table>
  <tr><th>Crime</th><th>What it is</th></tr>
  <tr><td>Phishing</td><td>Fake messages tricking you into sharing info.</td></tr>
  <tr><td>Identity theft</td><td>Criminal pretends to be you online.</td></tr>
  <tr><td>Ransomware</td><td>Malware that locks files until you pay.</td></tr>
  <tr><td>Hacking</td><td>Unauthorised access to systems.</td></tr>
  <tr><td>Pharming</td><td>Redirects you to a fake site even when you type the real URL.</td></tr>
  <tr><td>Online fraud</td><td>Fake shops, "Nigerian prince" scams.</td></tr>
</table>
<h3>Defences</h3>
<ul>
  <li><strong>Strong unique passwords</strong> per site.</li>
  <li><strong>Two-factor authentication</strong> on every important account.</li>
  <li><strong>Antivirus &amp; updates</strong> kept current.</li>
  <li><strong>Encryption</strong> &mdash; HTTPS, encrypted backups.</li>
  <li><strong>Be sceptical</strong> &mdash; if it looks too good, it is.</li>
</ul>
""" + callout('info', 'fa-lightbulb', 'POPIA',
              'South Africa\'s <strong>Protection of Personal Information Act (POPIA)</strong> requires companies to safeguard your personal data.')},
        {'order': 3, 'duration_minutes': 30, 'title': 'Social Media: Benefits and Risks',
         'content': intro('Lesson 3 &middot; The Two-Edged Sword',
            'Social media connects you with friends, news and opportunities &mdash; but it has a dark side too.') + """
<h2>Benefits</h2>
""" + grid([
    {'icon': 'fa-comments', 'title': 'Communication', 'body': 'Stay in touch globally.'},
    {'icon': 'fa-graduation-cap', 'title': 'Learning', 'body': 'Free tutorials and communities.'},
    {'icon': 'fa-briefcase', 'title': 'Networking', 'body': 'LinkedIn for jobs, careers.'},
    {'icon': 'fa-bullhorn', 'title': 'Awareness', 'body': 'News, social causes spread quickly.'},
]) + """
<h2>Risks</h2>
""" + grid([
    {'icon': 'fa-comment-slash', 'title': 'Cyberbullying', 'body': 'Harassment that follows you home.'},
    {'icon': 'fa-newspaper', 'title': 'Fake news', 'body': 'Misinformation spreads faster than facts.'},
    {'icon': 'fa-eye', 'title': 'Privacy loss', 'body': 'Posts can resurface years later.'},
    {'icon': 'fa-clock', 'title': 'Addiction', 'body': 'Algorithms designed to keep you scrolling.'},
]) + callout('key', 'fa-key', 'Digital footprint',
              'Everything you post online &mdash; the trail of likes, photos and comments &mdash; is your <strong>digital footprint</strong>. It can affect future jobs and relationships.')},
        {'order': 4, 'duration_minutes': 30, 'title': 'Digital Citizenship and Netiquette',
         'content': intro('Lesson 4 &middot; Be a Good Online Citizen',
            '<strong>Netiquette</strong> = "internet etiquette". Polite, ethical online behaviour.') + """
<h2>The basics</h2>
<ul>
  <li>Treat others as you\'d like to be treated.</li>
  <li>Don\'t TYPE IN ALL CAPS &mdash; it reads as shouting.</li>
  <li>Respect privacy &mdash; don\'t share photos of others without permission.</li>
  <li>Verify before you share &mdash; don\'t spread fake news.</li>
  <li>Cite sources &mdash; don\'t plagiarise.</li>
</ul>
<h3>The grandmother test</h3>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Before posting, ask: "Would I be comfortable if my <strong>grandmother</strong> and a future <strong>employer</strong> read this?"') + """
<h3>Reporting and blocking</h3>
<p>Every platform has report and block tools. Use them. If something is illegal (threats, child abuse), report to the police and the South African <strong>SAPS Cybercrime Division</strong>.</p>
"""},
        {'order': 5, 'duration_minutes': 25, 'title': 'The Digital Divide and Green Computing',
         'content': intro('Lesson 5 &middot; Bigger Picture',
            'Computers don\'t exist in a vacuum &mdash; they affect society and the planet.') + """
<h2>The digital divide</h2>
<p>The gap between people who have <strong>good access</strong> to digital tools and those who don\'t. In South Africa it follows lines of geography, income and language.</p>
<h3>Causes</h3>
<ul>
  <li>Cost of devices and data.</li>
  <li>Patchy network coverage in rural areas.</li>
  <li>Lack of computer skills training.</li>
  <li>Load shedding!</li>
</ul>
<h2>Green computing</h2>
""" + grid([
    {'icon': 'fa-bolt', 'title': 'Save power', 'body': 'Sleep mode, LED screens, switching off at night.'},
    {'icon': 'fa-recycle', 'title': 'E-waste recycling', 'body': 'Drop old electronics at certified centres &mdash; never in regular bins.'},
    {'icon': 'fa-print', 'title': 'Less paper', 'body': 'Print double-sided; use PDFs.'},
    {'icon': 'fa-handshake', 'title': 'Donate', 'body': 'Working older devices help schools and NGOs.'},
])},
    ],
    'quiz': make_quiz(
        'Internet & Social Implications — Knowledge Check',
        'Tests e-commerce, cyber crime, social media, netiquette and green IT.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Buying from Takealot is which e-commerce model?',
             'options': ['B2B', 'B2C', 'C2C', 'C2B'], 'correct_answer': 'B2C',
             'explanation': 'A business sells to a consumer.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which is malware that locks your files until you pay?',
             'options': ['Phishing', 'Adware', 'Ransomware', 'Spyware'],
             'correct_answer': 'Ransomware',
             'explanation': 'Ransom + ware = pay to get your files back.'},
            {'question_type': 'multiple_choice',
             'question_text': 'POPIA is a South African law that protects:',
             'options': ['Wildlife', 'Personal information', 'Pirated software', 'Passwords only'],
             'correct_answer': 'Personal information',
             'explanation': 'Protection of Personal Information Act, 2013.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'The trail of posts, likes and photos you leave online is your:',
             'options': ['IP address', 'Digital footprint', 'Username', 'Cookie'],
             'correct_answer': 'Digital footprint',
             'explanation': 'Digital footprint can be tracked indefinitely.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Typing IN ALL CAPS in an email is considered:',
             'options': ['Polite', 'Shouting', 'Encryption', 'A virus'],
             'correct_answer': 'Shouting',
             'explanation': 'A core rule of netiquette.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each cyber crime with its description.',
             'options': {
                 'column_a': ['Phishing', 'Identity theft', 'Pharming', 'Hacking'],
                 'column_b': ['Fake message tricking you into giving info',
                              'Pretending to be someone else online',
                              'Redirecting to a fake website',
                              'Unauthorised access to a system']
             },
             'correct_answer': {'Phishing': 'Fake message tricking you into giving info',
                                'Identity theft': 'Pretending to be someone else online',
                                'Pharming': 'Redirecting to a fake website',
                                'Hacking': 'Unauthorised access to a system'},
             'explanation': 'Each is a distinct cyber crime category.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these green computing actions from MOST to LEAST direct power saving.',
             'options': ['Switch off the PC at night',
                         'Sleep mode after 10 minutes',
                         'Recycle old e-waste'],
             'correct_answer': ['Switch off the PC at night',
                                'Sleep mode after 10 minutes',
                                'Recycle old e-waste'],
             'explanation': 'Switching off uses zero power; sleep saves a lot; recycling is indirect.'},
            {'question_type': 'short_answer',
             'question_text': 'Name a security feature that requires a code from your phone in addition to your password.',
             'options': [], 'correct_answer': 'two-factor authentication',
             'explanation': '2FA adds a second proof of identity.'},
        ]
    ),
}


# ===========================================================================
# GRADE 12 — 6 courses
# ===========================================================================

G12_INTEGRATED = {
    'grade': 12, 'course_title': 'Integrated Document Handling',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'Mail Merge: Word + Excel',
         'content': intro('Lesson 1 &middot; One Letter, Many Recipients',
            '<strong>Mail Merge</strong> combines a template document (Word) with a data source (often an Excel spreadsheet) to produce many personalised copies.') + """
<h2>Where mail merge is used</h2>
<ul>
  <li>Personalised letters to parents.</li>
  <li>Bulk envelopes and address labels.</li>
  <li>Personalised certificates of attendance.</li>
  <li>Email campaigns.</li>
</ul>
<h3>The five-step wizard</h3>
<ol class="steps">
  <li><strong>Mailings &rarr; Start Mail Merge</strong> &mdash; pick document type (letters, labels, envelopes).</li>
  <li><strong>Select Recipients</strong> &mdash; usually <em>Use an Existing List</em> &rarr; browse to your Excel file.</li>
  <li><strong>Insert Merge Fields</strong> like <code>&laquo;FirstName&raquo;</code> in the body.</li>
  <li><strong>Preview Results</strong> to step through individual records.</li>
  <li><strong>Finish &amp; Merge</strong> &rarr; Print, Edit Individual Documents, or Send Email Messages.</li>
</ol>
""" + callout('warn', 'fa-triangle-exclamation', 'Common mistake',
              'Make sure your Excel file has clear column <strong>headings in row 1</strong> &mdash; Word uses these as the field names.')},
        {'order': 2, 'duration_minutes': 30, 'title': 'Linking Excel Charts and Data into Word',
         'content': intro('Lesson 2 &middot; Live Updates Across Apps',
            'When data lives in Excel but the report is in Word, you can <strong>link</strong> instead of paste &mdash; so the Word report updates when the Excel changes.') + """
<h2>Paste options</h2>
<table>
  <tr><th>Option</th><th>Behaviour</th></tr>
  <tr><td>Paste (default)</td><td>Static copy. No link.</td></tr>
  <tr><td>Paste Special &rarr; Paste</td><td>Embeds an editable mini-Excel inside Word.</td></tr>
  <tr><td>Paste Special &rarr; Paste <strong>Link</strong></td><td>Live-updates from the source Excel file.</td></tr>
  <tr><td>Picture</td><td>Just an image &mdash; small file, can\'t edit.</td></tr>
</table>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Linked objects only update if the Excel file is in the <em>same folder path</em> when Word opens. Keep both together.') + """
<h3>Updating links</h3>
<p>In Word: <strong>File &rarr; Info &rarr; Edit Links to Files</strong>. You can also right-click a linked object &rarr; <strong>Update Link</strong>.</p>
"""},
        {'order': 3, 'duration_minutes': 30, 'title': 'Importing and Exporting Database Data',
         'content': intro('Lesson 3 &middot; Moving Data Between Apps',
            'You can move data between Excel, Access and CSV files. Knowing the right format prevents lost or corrupted data.') + """
<h2>CSV &mdash; the universal format</h2>
<p><strong>Comma-Separated Values</strong>: a plain-text file where each row is a record and commas separate the fields. Almost every program reads it.</p>
<h3>Excel &harr; Access</h3>
<table>
  <tr><th>Direction</th><th>How</th></tr>
  <tr><td>Excel &rarr; Access</td><td>Access &rarr; External Data &rarr; New Data Source &rarr; From File &rarr; Excel.</td></tr>
  <tr><td>Access &rarr; Excel</td><td>External Data &rarr; Export &rarr; Excel.</td></tr>
  <tr><td>Database &rarr; CSV</td><td>Export &rarr; Text File &rarr; tick "Delimited" &rarr; comma.</td></tr>
</table>
""" + callout('warn', 'fa-triangle-exclamation', 'Encoding',
              'For names with accented characters or non-English scripts, choose <strong>UTF-8</strong> when exporting CSV.')},
        {'order': 4, 'duration_minutes': 30, 'title': 'OLE: Embedding vs Linking',
         'content': intro('Lesson 4 &middot; OLE Explained',
            '<strong>OLE</strong> stands for <em>Object Linking and Embedding</em>. It is the technology that lets one Office program show content from another.') + """
<table>
  <tr><th></th><th>Embedded</th><th>Linked</th></tr>
  <tr><td>Stored in&hellip;</td><td>The destination file (Word).</td><td>The source file (Excel) only.</td></tr>
  <tr><td>Updates if source changes?</td><td>No.</td><td>Yes.</td></tr>
  <tr><td>File size</td><td>Larger.</td><td>Smaller.</td></tr>
  <tr><td>Works without source file?</td><td>Yes.</td><td>No.</td></tr>
</table>
<h3>When to use which?</h3>
<ul>
  <li><strong>Embed</strong> if you\'re emailing the file and the recipient won\'t have the source.</li>
  <li><strong>Link</strong> if you want the report to always show the latest data and you control both files.</li>
</ul>
"""},
        {'order': 5, 'duration_minutes': 25, 'title': 'PDF: Sharing the Final Product',
         'content': intro('Lesson 5 &middot; The Universal Output',
            '<strong>PDF</strong> (Portable Document Format) keeps your layout perfect on every device, every time.') + """
<h2>Why PDF?</h2>
<ul>
  <li>Layout never changes &mdash; what you see is what they see.</li>
  <li>Read on any device without Office installed.</li>
  <li>Smaller file than the editable original.</li>
  <li>Can be password-protected.</li>
</ul>
<h3>Saving as PDF</h3>
<p><strong>File &rarr; Save As</strong> &rarr; choose PDF in the file type list. Or <strong>File &rarr; Export &rarr; Create PDF/XPS</strong>.</p>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Use the <strong>"Standard"</strong> option for printing and <strong>"Minimum size"</strong> for emailing.') + """
<h3>Editing PDFs</h3>
<p>Word can <em>open</em> PDFs and turn them back into editable documents &mdash; with some loss of formatting.</p>
"""},
    ],
    'quiz': make_quiz(
        'Integrated Document Handling — Knowledge Check',
        'Tests mail merge, OLE, importing, exporting and PDF.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Which Office app is used to manage the mail merge PROCESS?',
             'options': ['Excel', 'Access', 'Word', 'Outlook'],
             'correct_answer': 'Word',
             'explanation': 'Word hosts the merge; Excel/Access usually supplies the data.'},
            {'question_type': 'multiple_choice',
             'question_text': 'What goes into the data source for mail merge?',
             'options': ['The recipient list', 'The letter template',
                         'The fonts', 'The page size'],
             'correct_answer': 'The recipient list',
             'explanation': 'The data source is the list (e.g. Excel sheet of names).'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which paste option lets the Excel chart in Word UPDATE when Excel changes?',
             'options': ['Paste', 'Paste as Picture', 'Paste Link', 'Embed'],
             'correct_answer': 'Paste Link',
             'explanation': 'Linked objects re-read the source.'},
            {'question_type': 'multiple_choice',
             'question_text': 'The universal text format for moving table data between programs is:',
             'options': ['.docx', '.xlsx', '.csv', '.mp3'],
             'correct_answer': '.csv',
             'explanation': 'CSV = comma-separated values, supported almost everywhere.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'You email a Word doc with an EMBEDDED Excel chart to a friend who has no Excel file. They will see:',
             'options': ['Nothing', 'A broken icon', 'The chart correctly',
                         'A blank page'],
             'correct_answer': 'The chart correctly',
             'explanation': 'Embedded objects are stored inside the Word document.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each format/term with its best use.',
             'options': {
                 'column_a': ['CSV', 'PDF', 'XLSX', 'DOCX'],
                 'column_b': ['Universal text data', 'Read-only sharing',
                              'Spreadsheet calculations', 'Editable letter']
             },
             'correct_answer': {'CSV': 'Universal text data',
                                'PDF': 'Read-only sharing',
                                'XLSX': 'Spreadsheet calculations',
                                'DOCX': 'Editable letter'},
             'explanation': 'Pick the format for the audience and purpose.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Arrange the mail-merge steps in the correct order.',
             'options': ['Insert merge fields',
                         'Finish &amp; Merge',
                         'Start Mail Merge &rarr; choose document type',
                         'Select Recipients (data source)',
                         'Preview Results'],
             'correct_answer': ['Start Mail Merge &rarr; choose document type',
                                'Select Recipients (data source)',
                                'Insert merge fields',
                                'Preview Results',
                                'Finish &amp; Merge'],
             'explanation': 'Set up &rarr; data &rarr; fields &rarr; preview &rarr; finish.'},
            {'question_type': 'short_answer',
             'question_text': 'What does the acronym OLE stand for?',
             'options': [], 'correct_answer': 'object linking and embedding',
             'explanation': 'OLE is the technology behind cross-app linking.'},
        ]
    ),
}


G12_ADV_FUNC = {
    'grade': 12, 'course_title': 'Advanced Spreadsheet Functions',
    'lessons': [
        {'order': 1, 'duration_minutes': 35, 'title': 'Nested Functions and Complex Logic',
         'content': intro('Lesson 1 &middot; Functions Inside Functions',
            'You can use the result of one function as an argument to another &mdash; this is <strong>nesting</strong>.') + """
<h2>Example</h2>
<p><code>=IF(VLOOKUP(A2, Stock!A:C, 3, FALSE) &lt; 10, "REORDER", "OK")</code></p>
<p>The <code>VLOOKUP</code> finds the stock level; the <code>IF</code> compares it to 10.</p>
<h3>Tips for nesting</h3>
<ul>
  <li>Build the inner function <em>first</em>, get it working, then wrap it.</li>
  <li>Use the <strong>fx</strong> Insert Function dialog for complex argument lists.</li>
  <li>Press """ + kbd('Alt', 'Enter') + """ inside the formula bar to break a long formula across lines.</li>
</ul>
""" + callout('warn', 'fa-triangle-exclamation', 'Bracket trap',
              'Excel allows up to <strong>64 levels</strong> of nesting, but anything past 3 is hard to debug. Consider using helper cells.')},
        {'order': 2, 'duration_minutes': 30, 'title': 'Date and Text Functions',
         'content': intro('Lesson 2 &middot; Wrangling Strings and Dates',
            'Real spreadsheets always need to manipulate text and work with dates &mdash; like splitting full names or counting days to deadline.') + """
<h2>Date functions</h2>
<table>
  <tr><th>Function</th><th>Returns</th></tr>
  <tr><td><code>TODAY()</code></td><td>Current date.</td></tr>
  <tr><td><code>NOW()</code></td><td>Current date AND time.</td></tr>
  <tr><td><code>YEAR(date)</code> / <code>MONTH(date)</code> / <code>DAY(date)</code></td><td>Extracts each part.</td></tr>
  <tr><td><code>DATEDIF(start, end, "Y")</code></td><td>Years between two dates.</td></tr>
  <tr><td><code>NETWORKDAYS(start, end)</code></td><td>Workdays only (excludes weekends).</td></tr>
</table>
<h2>Text functions</h2>
<table>
  <tr><th>Function</th><th>Use</th></tr>
  <tr><td><code>LEFT(text, n)</code></td><td>First n characters.</td></tr>
  <tr><td><code>RIGHT(text, n)</code></td><td>Last n characters.</td></tr>
  <tr><td><code>MID(text, start, n)</code></td><td>n characters from a position.</td></tr>
  <tr><td><code>LEN(text)</code></td><td>Number of characters.</td></tr>
  <tr><td><code>UPPER / LOWER / PROPER</code></td><td>Case conversions.</td></tr>
  <tr><td><code>CONCAT</code> / <code>&amp;</code></td><td>Joins text together.</td></tr>
  <tr><td><code>TEXTSPLIT</code></td><td>Splits text by a delimiter (Excel 365).</td></tr>
</table>
"""},
        {'order': 3, 'duration_minutes': 35, 'title': 'Conditional Formatting',
         'content': intro('Lesson 3 &middot; Cells That Highlight Themselves',
            '<strong>Conditional formatting</strong> changes a cell\'s look based on its value &mdash; instant visual analysis.') + """
<h2>Built-in rules</h2>
<table>
  <tr><th>Rule</th><th>Use</th></tr>
  <tr><td>Highlight Cell Rules</td><td>Greater than, less than, between, equal to, text containing.</td></tr>
  <tr><td>Top/Bottom Rules</td><td>Top 10 items, above average, etc.</td></tr>
  <tr><td>Data Bars</td><td>In-cell horizontal bar showing value.</td></tr>
  <tr><td>Color Scales</td><td>Cells coloured red &rarr; green by value (heat map).</td></tr>
  <tr><td>Icon Sets</td><td>Arrows, traffic lights, stars.</td></tr>
</table>
<h3>Custom formula rules</h3>
<p>Use <strong>New Rule &rarr; Use a formula to determine which cells to format</strong>. Example: highlight rows where column F = "OVERDUE":</p>
<p><code>=$F2="OVERDUE"</code></p>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Lock the column with <code>$</code> when formatting an entire row based on one cell\'s value.')},
        {'order': 4, 'duration_minutes': 30, 'title': 'Data Validation and Drop-Down Lists',
         'content': intro('Lesson 4 &middot; Stopping Bad Data at the Door',
            '<strong>Data Validation</strong> rejects invalid input as the user types &mdash; the cheapest way to keep your data clean.') + """
<h2>Setting it up</h2>
<ol class="steps">
  <li>Select the cells.</li>
  <li><strong>Data &rarr; Data Validation</strong>.</li>
  <li>Pick what is allowed: Whole number, Decimal, List, Date, Text length.</li>
  <li>Optionally add an Input Message and an Error Alert.</li>
</ol>
<h3>Common validations</h3>
<table>
  <tr><th>Allow</th><th>Use case</th></tr>
  <tr><td>Whole number between 0 and 100</td><td>Marks.</td></tr>
  <tr><td>List: <code>Maths,Science,English</code></td><td>Drop-down for subject choice.</td></tr>
  <tr><td>Date &gt;= TODAY()</td><td>Future deadlines only.</td></tr>
  <tr><td>Text length = 13</td><td>South African ID numbers.</td></tr>
</table>
"""},
        {'order': 5, 'duration_minutes': 30, 'title': 'Macros and Basic Automation',
         'content': intro('Lesson 5 &middot; Excel That Does Itself',
            'A <strong>macro</strong> is a saved sequence of actions you can replay with one click.') + """
<h2>Recording a macro</h2>
<ol class="steps">
  <li>Enable <strong>Developer</strong> tab: File &rarr; Options &rarr; Customize Ribbon.</li>
  <li><strong>Developer &rarr; Record Macro</strong>. Give it a name and shortcut key.</li>
  <li>Do the actions you want recorded.</li>
  <li><strong>Stop Recording</strong>.</li>
  <li>Run by pressing the shortcut or <strong>Developer &rarr; Macros</strong>.</li>
</ol>
""" + callout('warn', 'fa-triangle-exclamation', 'Macro security',
              'Files with macros use the <strong>.xlsm</strong> extension. Only run macros from sources you trust &mdash; they can contain harmful code.') + """
<h3>VBA &mdash; the language behind macros</h3>
<p>Press """ + kbd('Alt', 'F11') + """ to open the <strong>Visual Basic Editor</strong>. Recorded macros become editable VBA code you can extend.</p>
"""},
    ],
    'quiz': make_quiz(
        'Advanced Spreadsheet Functions — Knowledge Check',
        'Tests nested functions, dates, conditional formatting, validation, macros.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Which function returns the number of weekdays between two dates?',
             'options': ['DATEDIF', 'NETWORKDAYS', 'TODAY', 'NOW'],
             'correct_answer': 'NETWORKDAYS',
             'explanation': 'NETWORKDAYS excludes Saturdays and Sundays.'},
            {'question_type': 'multiple_choice',
             'question_text': '<code>=LEFT("CAPS", 2)</code> returns:',
             'options': ['CA', 'PS', 'CAPS', '2'],
             'correct_answer': 'CA',
             'explanation': 'LEFT returns the leftmost N characters.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Conditional formatting that colours cells red &rarr; green by value is called:',
             'options': ['Data Bars', 'Color Scales', 'Icon Sets', 'AutoSum'],
             'correct_answer': 'Color Scales',
             'explanation': 'Color Scales create a heat-map effect.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which Excel feature creates a drop-down list in a cell?',
             'options': ['Conditional Formatting', 'Data Validation',
                         'Pivot Table', 'Format Cells'],
             'correct_answer': 'Data Validation',
             'explanation': 'Data Validation &rarr; Allow: List makes drop-downs.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'A workbook containing macros must be saved as:',
             'options': ['.xlsx', '.xlsm', '.xls', '.csv'],
             'correct_answer': '.xlsm',
             'explanation': 'The "m" stands for macro-enabled.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each text/date function with its purpose.',
             'options': {
                 'column_a': ['LEN', 'PROPER', 'TODAY', 'YEAR'],
                 'column_b': ['Number of characters', 'Capitalises First Letter Of Each Word',
                              'Returns current date', 'Extracts year from date']
             },
             'correct_answer': {'LEN': 'Number of characters',
                                'PROPER': 'Capitalises First Letter Of Each Word',
                                'TODAY': 'Returns current date',
                                'YEAR': 'Extracts year from date'},
             'explanation': 'Common helper functions for text and dates.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these steps to record a macro.',
             'options': ['Stop Recording', 'Perform the actions to record',
                         'Developer &rarr; Record Macro &rarr; name + shortcut'],
             'correct_answer': ['Developer &rarr; Record Macro &rarr; name + shortcut',
                                'Perform the actions to record',
                                'Stop Recording'],
             'explanation': 'Start &rarr; do &rarr; stop.'},
            {'question_type': 'short_answer',
             'question_text': 'What keyboard shortcut opens the Visual Basic Editor in Excel?',
             'options': [], 'correct_answer': 'Alt+F11',
             'explanation': 'Alt + F11 opens the VBA editor.'},
        ]
    ),
}


G12_ADV_DB = {
    'grade': 12, 'course_title': 'Advanced Databases',
    'lessons': [
        {'order': 1, 'duration_minutes': 35, 'title': 'Database Design and ER Diagrams',
         'content': intro('Lesson 1 &middot; Plan Before You Build',
            'Good databases start with a diagram on paper. The <strong>Entity-Relationship (ER) diagram</strong> shows tables, fields and relationships before you touch a keyboard.') + """
<h2>ER diagram parts</h2>
<table>
  <tr><th>Symbol</th><th>Meaning</th></tr>
  <tr><td>Rectangle</td><td>Entity (table)</td></tr>
  <tr><td>Oval</td><td>Attribute (field)</td></tr>
  <tr><td>Diamond</td><td>Relationship</td></tr>
  <tr><td>Underlined attribute</td><td>Primary key</td></tr>
  <tr><td>Line with 1 / N</td><td>Cardinality (1, many)</td></tr>
</table>
<h3>Three normal forms (overview)</h3>
<ul>
  <li><strong>1NF</strong> &mdash; each cell holds a single value (no lists in one field).</li>
  <li><strong>2NF</strong> &mdash; 1NF + every non-key field depends on the <em>whole</em> primary key.</li>
  <li><strong>3NF</strong> &mdash; 2NF + no field depends on another non-key field.</li>
</ul>
""" + callout('key', 'fa-key', 'Why normalise?',
              'Normalised data &rarr; less duplication &rarr; smaller files, fewer update errors.')},
        {'order': 2, 'duration_minutes': 35, 'title': 'Complex Queries: Joins and Calculated Fields',
         'content': intro('Lesson 2 &middot; Combining Tables',
            'Real questions need data from multiple tables. <strong>Joins</strong> match records using the foreign key.') + """
<h2>Join types</h2>
<table>
  <tr><th>Join</th><th>Returns</th></tr>
  <tr><td>Inner join</td><td>Only records with matches in BOTH tables.</td></tr>
  <tr><td>Left (outer) join</td><td>All records from left + matching from right.</td></tr>
  <tr><td>Right (outer) join</td><td>All records from right + matching from left.</td></tr>
</table>
<h3>Calculated fields in queries</h3>
<p>In Access query design, a calculated field is created in an empty column header:</p>
<p><code>Total: [Quantity] * [UnitPrice]</code></p>
<h3>Aggregate queries</h3>
<p>Click the <strong>Totals</strong> &Sigma; button. You can then SUM, AVG, MIN, MAX, COUNT &mdash; grouped by another field (e.g. total sales per month).</p>
"""},
        {'order': 3, 'duration_minutes': 35, 'title': 'Introduction to SQL',
         'content': intro('Lesson 3 &middot; The Language of Databases',
            '<strong>SQL</strong> (Structured Query Language) is the standard language used by every relational database.') + """
<h2>The four core statements</h2>
<table>
  <tr><th>Statement</th><th>Does</th><th>Example</th></tr>
  <tr><td>SELECT</td><td>Retrieves data</td><td><code>SELECT name FROM learners;</code></td></tr>
  <tr><td>INSERT</td><td>Adds new records</td><td><code>INSERT INTO learners(name) VALUES('Thabo');</code></td></tr>
  <tr><td>UPDATE</td><td>Changes existing records</td><td><code>UPDATE learners SET grade=12 WHERE id=5;</code></td></tr>
  <tr><td>DELETE</td><td>Removes records</td><td><code>DELETE FROM learners WHERE id=5;</code></td></tr>
</table>
<h3>WHERE clauses</h3>
<p>Filter rows with conditions:</p>
<p><code>SELECT * FROM learners WHERE grade = 12 AND mark &gt;= 70;</code></p>
<h3>ORDER BY and GROUP BY</h3>
<ul>
  <li><code>ORDER BY mark DESC</code> &mdash; sort highest first.</li>
  <li><code>GROUP BY subject</code> &mdash; for aggregates per group.</li>
</ul>
""" + callout('warn', 'fa-triangle-exclamation', 'Always use WHERE',
              'A <code>DELETE FROM learners</code> without WHERE deletes <strong>every record</strong>. Test with SELECT first!')},
        {'order': 4, 'duration_minutes': 30, 'title': 'Forms, Subforms and Macros in Access',
         'content': intro('Lesson 4 &middot; Building a Real Application',
            'Access lets you build a complete app: forms for input, subforms for related data, macros for automation &mdash; all without writing code.') + """
<h2>Subforms</h2>
<p>A subform shows the <em>"many"</em> side of a one-to-many relationship inside the parent form. Example: a Learner form with a subform of Marks.</p>
<h3>Building a subform</h3>
<ol class="steps">
  <li>Open the parent form in Design View.</li>
  <li>Drag the related table from the Field List onto the form.</li>
  <li>Choose Linked Master/Child fields (the foreign key).</li>
</ol>
<h3>Access macros</h3>
<p>A list of actions like <em>OpenForm</em>, <em>RunQuery</em>, <em>MessageBox</em>. Attach to a button\'s <strong>On Click</strong> event for instant automation.</p>
"""},
        {'order': 5, 'duration_minutes': 25, 'title': 'Reports, Grouping and Totals',
         'content': intro('Lesson 5 &middot; Professional Output',
            'Reports turn database content into formatted, printable output. The <strong>Report Wizard</strong> does the heavy lifting.') + """
<h2>Grouping and sorting</h2>
<p>In the Report Wizard you can group by a field (e.g. Subject) and sort within the group (e.g. Mark, descending). Each group can have its own <strong>header</strong>, <strong>footer</strong> and totals.</p>
<h3>Summary functions in reports</h3>
<table>
  <tr><th>Function</th><th>Use</th></tr>
  <tr><td>Sum</td><td>Total per group + grand total.</td></tr>
  <tr><td>Avg</td><td>Average per group.</td></tr>
  <tr><td>Count</td><td>Number of records per group.</td></tr>
</table>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Base reports on <em>queries</em>, not directly on tables. Then you can filter and calculate before the report sees the data.')},
    ],
    'quiz': make_quiz(
        'Advanced Databases — Knowledge Check',
        'Tests ER diagrams, joins, SQL, subforms, reports.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'In an ER diagram, an entity is represented by a:',
             'options': ['Rectangle', 'Diamond', 'Oval', 'Circle'],
             'correct_answer': 'Rectangle',
             'explanation': 'Rectangles = entities (tables).'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which join returns ONLY records that exist in BOTH tables?',
             'options': ['Left join', 'Right join', 'Inner join', 'Full outer join'],
             'correct_answer': 'Inner join',
             'explanation': 'Inner join keeps only matching records.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which SQL statement removes records from a table?',
             'options': ['SELECT', 'INSERT', 'UPDATE', 'DELETE'],
             'correct_answer': 'DELETE',
             'explanation': 'DELETE FROM removes records.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'What does <code>SELECT * FROM learners WHERE grade=12;</code> do?',
             'options': ['Removes all Grade 12 learners',
                         'Returns all fields for learners in Grade 12',
                         'Inserts a new Grade 12 record',
                         'Updates grades to 12'],
             'correct_answer': 'Returns all fields for learners in Grade 12',
             'explanation': 'SELECT * = all columns; WHERE filters rows.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A subform is used to show the:',
             'options': ['One side of a 1:M relationship',
                         'Many side of a 1:M relationship',
                         'Title bar of a form',
                         'Print preview'],
             'correct_answer': 'Many side of a 1:M relationship',
             'explanation': 'Subform shows related "many" records inside the parent.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each SQL keyword to its function.',
             'options': {
                 'column_a': ['SELECT', 'INSERT', 'UPDATE', 'DELETE'],
                 'column_b': ['Read records', 'Add new records',
                              'Change existing records', 'Remove records']
             },
             'correct_answer': {'SELECT': 'Read records',
                                'INSERT': 'Add new records',
                                'UPDATE': 'Change existing records',
                                'DELETE': 'Remove records'},
             'explanation': 'These are the four CRUD operations.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these database design steps.',
             'options': ['Implement tables in DBMS',
                         'Identify entities and attributes',
                         'Define relationships and cardinality',
                         'Normalise to 3NF'],
             'correct_answer': ['Identify entities and attributes',
                                'Define relationships and cardinality',
                                'Normalise to 3NF',
                                'Implement tables in DBMS'],
             'explanation': 'Design first &mdash; build last.'},
            {'question_type': 'short_answer',
             'question_text': 'What is the term for organising tables to reduce duplication?',
             'options': [], 'correct_answer': 'normalisation',
             'explanation': 'Normalisation breaks data into related tables.'},
        ]
    ),
}


G12_WEB = {
    'grade': 12, 'course_title': 'Web & HTML Basics',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'How the Web Works',
         'content': intro('Lesson 1 &middot; Behind Every Click',
            'When you type a URL, your browser asks a server for files, then assembles them into the page you see. Knowing the moving parts helps you build, debug and stay safe.') + """
<h2>The request-response cycle</h2>
<ol class="steps">
  <li>You type <code>www.gov.za</code>.</li>
  <li>Browser asks <strong>DNS</strong> for the IP address (like a phone book).</li>
  <li>Browser sends an <strong>HTTP(S) request</strong> to that IP.</li>
  <li>The web <strong>server</strong> sends back HTML, CSS, JS, images.</li>
  <li>Browser <em>renders</em> the page.</li>
</ol>
<h3>Front end vs back end</h3>
<table>
  <tr><th>Front end</th><th>Back end</th></tr>
  <tr><td>Runs in the browser.</td><td>Runs on the server.</td></tr>
  <tr><td>HTML, CSS, JavaScript.</td><td>Python, PHP, Java, .NET, databases.</td></tr>
  <tr><td>What the user sees.</td><td>What the user can\'t see.</td></tr>
</table>
"""},
        {'order': 2, 'duration_minutes': 35, 'title': 'HTML Structure and Tags',
         'content': intro('Lesson 2 &middot; The Skeleton',
            '<strong>HTML</strong> = Hyper-Text Markup Language. It uses <strong>tags</strong> in angle brackets to mark up the content.') + """
<h2>Skeleton of every page</h2>
<pre>&lt;!DOCTYPE html&gt;
&lt;html&gt;
  &lt;head&gt;
    &lt;title&gt;My Page&lt;/title&gt;
  &lt;/head&gt;
  &lt;body&gt;
    &lt;h1&gt;Hello world&lt;/h1&gt;
    &lt;p&gt;My first page.&lt;/p&gt;
  &lt;/body&gt;
&lt;/html&gt;</pre>
<h3>Most-used tags</h3>
<table>
  <tr><th>Tag</th><th>Use</th></tr>
  <tr><td><code>&lt;h1&gt;&hellip;&lt;h6&gt;</code></td><td>Headings.</td></tr>
  <tr><td><code>&lt;p&gt;</code></td><td>Paragraph.</td></tr>
  <tr><td><code>&lt;a href="..."&gt;</code></td><td>Hyperlink.</td></tr>
  <tr><td><code>&lt;img src="..." alt="..."&gt;</code></td><td>Image.</td></tr>
  <tr><td><code>&lt;ul&gt;&lt;li&gt;</code></td><td>Bulleted list.</td></tr>
  <tr><td><code>&lt;ol&gt;&lt;li&gt;</code></td><td>Numbered list.</td></tr>
  <tr><td><code>&lt;table&gt;</code> / <code>&lt;tr&gt;</code> / <code>&lt;td&gt;</code></td><td>Table, row, cell.</td></tr>
  <tr><td><code>&lt;br&gt;</code> / <code>&lt;hr&gt;</code></td><td>Line break / horizontal rule.</td></tr>
</table>
""" + callout('key', 'fa-key', 'Always close tags',
              'Most tags come in pairs: <code>&lt;p&gt;...&lt;/p&gt;</code>. A few are <em>self-closing</em>: <code>&lt;br&gt;</code>, <code>&lt;img&gt;</code>, <code>&lt;hr&gt;</code>.')},
        {'order': 3, 'duration_minutes': 30, 'title': 'Attributes, Links and Images',
         'content': intro('Lesson 3 &middot; Adding Information to Tags',
            '<strong>Attributes</strong> add information to tags &mdash; the URL of a link, the source of an image, the size of an element.') + """
<h2>Common attributes</h2>
<table>
  <tr><th>Attribute</th><th>Used on</th><th>Example</th></tr>
  <tr><td><code>href</code></td><td>&lt;a&gt;</td><td><code>&lt;a href="https://gov.za"&gt;Gov&lt;/a&gt;</code></td></tr>
  <tr><td><code>src</code></td><td>&lt;img&gt;</td><td><code>&lt;img src="cat.jpg"&gt;</code></td></tr>
  <tr><td><code>alt</code></td><td>&lt;img&gt;</td><td><code>alt="A grey cat"</code> &mdash; for accessibility.</td></tr>
  <tr><td><code>width</code> / <code>height</code></td><td>&lt;img&gt;</td><td><code>width="300"</code></td></tr>
  <tr><td><code>title</code></td><td>any</td><td>Hover tooltip.</td></tr>
</table>
<h3>Linking</h3>
<ul>
  <li><strong>External</strong>: full URL <code>https://example.com</code>.</li>
  <li><strong>Internal</strong>: another page in the same folder <code>about.html</code>.</li>
  <li><strong>Same page</strong>: <code>#section-id</code>.</li>
  <li><strong>Email</strong>: <code>mailto:thabo@example.com</code>.</li>
</ul>
""" + callout('warn', 'fa-triangle-exclamation', 'Always include alt',
              'Screen readers read the <code>alt</code> text aloud. It\'s also shown if the image fails to load.')},
        {'order': 4, 'duration_minutes': 30, 'title': 'CSS Basics',
         'content': intro('Lesson 4 &middot; Making it Pretty',
            '<strong>CSS</strong> = Cascading Style Sheets. It tells the browser <em>how</em> things should look (colour, font, layout) while HTML says <em>what</em> they are.') + """
<h2>Three places to put CSS</h2>
<table>
  <tr><th>Where</th><th>Example</th></tr>
  <tr><td>Inline</td><td><code>&lt;p style="color:red"&gt;</code></td></tr>
  <tr><td>Internal &lt;style&gt;</td><td>In the &lt;head&gt; of one page.</td></tr>
  <tr><td>External .css file</td><td><code>&lt;link rel="stylesheet" href="style.css"&gt;</code></td></tr>
</table>
<h3>Anatomy of a rule</h3>
<pre>p {
  color: blue;
  font-size: 16px;
  text-align: center;
}</pre>
<p>Selector + declaration block. Each declaration is <em>property: value;</em>.</p>
<h3>Common properties</h3>
<ul>
  <li><code>color</code>, <code>background-color</code>, <code>font-family</code>, <code>font-size</code>.</li>
  <li><code>margin</code>, <code>padding</code>, <code>border</code>, <code>width</code>, <code>height</code>.</li>
  <li><code>text-align</code>, <code>line-height</code>, <code>display</code>.</li>
</ul>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'External CSS files are best practice &mdash; one file styles every page on your site, so changes are made in one place.')},
        {'order': 5, 'duration_minutes': 25, 'title': 'Building and Publishing a Simple Web Page',
         'content': intro('Lesson 5 &middot; From Notepad to the World',
            'You don\'t need fancy software to build a web page &mdash; Notepad and a browser will do.') + """
<h2>Build it locally</h2>
<ol class="steps">
  <li>Open Notepad / VS Code.</li>
  <li>Write your HTML &amp; CSS.</li>
  <li>Save as <code>index.html</code> (NOT .txt).</li>
  <li>Double-click to view in your browser.</li>
  <li>Edit, save, refresh (""" + kbd('F5') + """) to see changes.</li>
</ol>
<h2>Publishing options</h2>
<table>
  <tr><th>Option</th><th>Notes</th></tr>
  <tr><td>Free hosting (GitHub Pages, Netlify)</td><td>Best for students &mdash; free, fast.</td></tr>
  <tr><td>Paid web host</td><td>Custom domain, more space.</td></tr>
  <tr><td>School / company server</td><td>Used internally only.</td></tr>
</table>
""" + callout('key', 'fa-key', 'Domain name',
              'A custom domain like <code>thabo.co.za</code> is registered through a <em>registrar</em> and pointed at your hosting via DNS.')},
    ],
    'quiz': make_quiz(
        'Web & HTML Basics — Knowledge Check',
        'Tests how the web works, HTML tags, attributes, CSS and publishing.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'What does HTML stand for?',
             'options': ['HighTech Markup Language', 'Hyper Tool Modern Language',
                         'Hyper-Text Markup Language', 'Home Tag Markup Language'],
             'correct_answer': 'Hyper-Text Markup Language',
             'explanation': 'HTML = Hyper-Text Markup Language.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which tag creates the BIGGEST heading?',
             'options': ['&lt;h1&gt;', '&lt;h6&gt;', '&lt;header&gt;', '&lt;big&gt;'],
             'correct_answer': '&lt;h1&gt;',
             'explanation': 'h1 is the largest; h6 is the smallest.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which attribute on &lt;img&gt; is REQUIRED for accessibility?',
             'options': ['src', 'width', 'alt', 'title'],
             'correct_answer': 'alt',
             'explanation': 'alt text is read by screen readers.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'CSS is best stored in:',
             'options': ['Inline style attributes only',
                         'An external .css file linked from each page',
                         'The HTML &lt;body&gt;',
                         'A .docx file'],
             'correct_answer': 'An external .css file linked from each page',
             'explanation': 'External CSS lets one file style every page.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which DNS analogy is correct?',
             'options': ['DNS is a search engine',
                         'DNS is a phone book that maps names to IP addresses',
                         'DNS is an email server',
                         'DNS encrypts your traffic'],
             'correct_answer': 'DNS is a phone book that maps names to IP addresses',
             'explanation': 'DNS resolves human names to IP numbers.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each tag with what it does.',
             'options': {
                 'column_a': ['&lt;a&gt;', '&lt;img&gt;', '&lt;ul&gt;', '&lt;table&gt;'],
                 'column_b': ['Hyperlink', 'Image', 'Bulleted list', 'Tabular data']
             },
             'correct_answer': {'&lt;a&gt;': 'Hyperlink',
                                '&lt;img&gt;': 'Image',
                                '&lt;ul&gt;': 'Bulleted list',
                                '&lt;table&gt;': 'Tabular data'},
             'explanation': 'Each tag has a single semantic purpose.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these steps to publish a page on GitHub Pages.',
             'options': ['Push the .html file to your repo',
                         'Create a free GitHub account',
                         'Enable Pages in repository settings',
                         'Visit your-username.github.io to see it live'],
             'correct_answer': ['Create a free GitHub account',
                                'Push the .html file to your repo',
                                'Enable Pages in repository settings',
                                'Visit your-username.github.io to see it live'],
             'explanation': 'Account &rarr; code &rarr; enable Pages &rarr; visit URL.'},
            {'question_type': 'short_answer',
             'question_text': 'Which extension must your home page file have?',
             'options': [], 'correct_answer': '.html',
             'explanation': 'index.html is conventional for the home page.'},
        ]
    ),
}


G12_SOLUTION = {
    'grade': 12, 'course_title': 'Solution Development',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'The Problem-Solving Process',
         'content': intro('Lesson 1 &middot; Think Before You Type',
            'Good ICT solutions follow a structured process &mdash; understand, plan, build, test, deliver.') + """
<h2>Five-step process</h2>
<ol class="steps">
  <li><strong>Understand the problem</strong> &mdash; talk to the user; capture requirements.</li>
  <li><strong>Plan</strong> &mdash; choose tools, sketch designs, list tasks.</li>
  <li><strong>Build</strong> &mdash; develop the solution.</li>
  <li><strong>Test</strong> &mdash; with real data; fix bugs.</li>
  <li><strong>Deliver &amp; maintain</strong> &mdash; train users; iterate.</li>
</ol>
""" + callout('key', 'fa-key', 'User-centred design',
              'A solution that\'s technically perfect but no one can use is a failure. <strong>Talk to your user</strong> early and often.')},
        {'order': 2, 'duration_minutes': 35, 'title': 'Choosing the Right Tool',
         'content': intro('Lesson 2 &middot; Word, Excel, Access or Web?',
            'CAT solutions usually combine more than one tool. The skill is matching the tool to the task.') + """
<table>
  <tr><th>Tool</th><th>Best for</th></tr>
  <tr><td>Word</td><td>Documents, letters, reports.</td></tr>
  <tr><td>Excel</td><td>Calculations, charts, small data sets (&lt;1000 rows).</td></tr>
  <tr><td>Access</td><td>Multi-table data, queries, forms, reports.</td></tr>
  <tr><td>PowerPoint</td><td>Presentations, kiosks.</td></tr>
  <tr><td>Web</td><td>Public-facing info, multi-user access.</td></tr>
  <tr><td>Email / Forms</td><td>Surveys, requests, communications.</td></tr>
</table>
<h3>Real example</h3>
<p>School fundraiser:</p>
<ul>
  <li><strong>Google Form</strong> for sign-ups.</li>
  <li><strong>Excel</strong> for tracking payments and totals.</li>
  <li><strong>Word</strong> for the formal thank-you letter (mail-merged from Excel).</li>
  <li><strong>PowerPoint</strong> for the presentation at parents\' evening.</li>
</ul>
"""},
        {'order': 3, 'duration_minutes': 30, 'title': 'Requirements Gathering',
         'content': intro('Lesson 3 &middot; What Do They Actually Want?',
            'Most failed projects fail at the requirements stage. Listen carefully &mdash; and write it down.') + """
<h2>Techniques</h2>
<table>
  <tr><th>Technique</th><th>Use</th></tr>
  <tr><td>Interview</td><td>Deep, qualitative info from key people.</td></tr>
  <tr><td>Questionnaire</td><td>Quick views from many people.</td></tr>
  <tr><td>Observation</td><td>See how the work is really done.</td></tr>
  <tr><td>Document study</td><td>Forms, reports already in use.</td></tr>
</table>
<h3>Functional vs non-functional</h3>
<ul>
  <li><strong>Functional</strong>: what the system must <em>do</em> (e.g. "calculate VAT at 15%").</li>
  <li><strong>Non-functional</strong>: how it must <em>perform</em> (e.g. "must work on a 5-year-old laptop").</li>
</ul>
""" + callout('warn', 'fa-triangle-exclamation', 'Scope creep',
              'Adding "just one more thing" again and again kills projects. Stick to what you agreed.')},
        {'order': 4, 'duration_minutes': 35, 'title': 'Designing and Prototyping',
         'content': intro('Lesson 4 &middot; Sketch First',
            'Designing on paper or in a simple sketching tool is way cheaper than rebuilding a full system.') + """
<h2>What to design before you build</h2>
""" + grid([
    {'icon': 'fa-pen-ruler', 'title': 'Wireframes', 'body': 'Rough layout of each screen / page.'},
    {'icon': 'fa-diagram-project', 'title': 'Data model', 'body': 'Tables, fields and relationships.'},
    {'icon': 'fa-arrow-right-arrow-left', 'title': 'Workflow', 'body': 'Order of steps the user follows.'},
    {'icon': 'fa-vial', 'title': 'Test plan', 'body': 'List of cases to verify when done.'},
]) + """
<h3>Prototype</h3>
<p>A <strong>prototype</strong> is an early, simplified version. Show it to your user. Iterate based on feedback. <em>Cheap to change &mdash; expensive to rebuild</em>.</p>
"""},
        {'order': 5, 'duration_minutes': 30, 'title': 'Testing, Documentation and Delivery',
         'content': intro('Lesson 5 &middot; Crossing the Finish Line',
            'A solution is only "done" when it has been tested with real data and the user can run it without you.') + """
<h2>Types of testing</h2>
<table>
  <tr><th>Type</th><th>Question it answers</th></tr>
  <tr><td>Unit testing</td><td>Does this small piece work alone?</td></tr>
  <tr><td>Integration testing</td><td>Do the pieces work together?</td></tr>
  <tr><td>User Acceptance Testing</td><td>Does the user agree it solves the problem?</td></tr>
</table>
<h3>Documentation</h3>
<ul>
  <li><strong>User manual</strong> &mdash; how to operate the system.</li>
  <li><strong>Technical doc</strong> &mdash; how it was built (for future maintainers).</li>
  <li><strong>FAQ &amp; troubleshooting</strong>.</li>
</ul>
""" + callout('tip', 'fa-bolt', 'Pro tip',
              'Take screenshots and write the user manual <em>as you build</em>. It\'s much harder to catch up at the end.')},
    ],
    'quiz': make_quiz(
        'Solution Development — Knowledge Check',
        'Tests problem-solving, requirements, design and testing.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Which is the FIRST step in the problem-solving process?',
             'options': ['Build the solution', 'Understand the problem',
                         'Test', 'Deliver'],
             'correct_answer': 'Understand the problem',
             'explanation': 'Always start by understanding the user\'s need.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A school needs to store learner records and link them to subject marks. The best tool is:',
             'options': ['Word', 'Excel', 'Access', 'PowerPoint'],
             'correct_answer': 'Access',
             'explanation': 'Multi-table relational data is what Access is designed for.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A "must run on a 5-year-old laptop" requirement is:',
             'options': ['Functional', 'Non-functional', 'Decorative', 'Optional'],
             'correct_answer': 'Non-functional',
             'explanation': 'Non-functional = how it performs, not what it does.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A simplified early version of a system, used to gather feedback, is a:',
             'options': ['Bug', 'Prototype', 'Patch', 'Backup'],
             'correct_answer': 'Prototype',
             'explanation': 'Prototypes invite feedback before full build.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Adding "one more feature" again and again is called:',
             'options': ['Scope creep', 'Refactoring', 'Debugging', 'Caching'],
             'correct_answer': 'Scope creep',
             'explanation': 'Scope creep grows the project beyond what was agreed.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each requirements technique with its strength.',
             'options': {
                 'column_a': ['Interview', 'Questionnaire', 'Observation', 'Document study'],
                 'column_b': ['Deep, qualitative info', 'Many opinions quickly',
                              'See real working practice', 'Look at existing forms']
             },
             'correct_answer': {'Interview': 'Deep, qualitative info',
                                'Questionnaire': 'Many opinions quickly',
                                'Observation': 'See real working practice',
                                'Document study': 'Look at existing forms'},
             'explanation': 'Each technique reveals different information.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order the five problem-solving steps.',
             'options': ['Test', 'Plan', 'Understand the problem',
                         'Build', 'Deliver &amp; maintain'],
             'correct_answer': ['Understand the problem', 'Plan', 'Build',
                                'Test', 'Deliver &amp; maintain'],
             'explanation': 'Standard development life-cycle order.'},
            {'question_type': 'short_answer',
             'question_text': 'What documentation explains to the END USER how to operate the system?',
             'options': [], 'correct_answer': 'user manual',
             'explanation': 'User manual / user guide is for the operator.'},
        ]
    ),
}


G12_ICT_SOC = {
    'grade': 12, 'course_title': 'ICT & Society',
    'lessons': [
        {'order': 1, 'duration_minutes': 30, 'title': 'How ICT is Changing the World',
         'content': intro('Lesson 1 &middot; The Shifts',
            'ICT (Information and Communications Technology) reshapes how we work, learn, shop, vote and stay healthy.') + """
<h2>Major impacts</h2>
""" + grid([
    {'icon': 'fa-briefcase', 'title': 'Work', 'body': 'Remote work, automation, gig economy.'},
    {'icon': 'fa-graduation-cap', 'title': 'Education', 'body': 'Online courses, e-textbooks, AI tutors.'},
    {'icon': 'fa-stethoscope', 'title': 'Health', 'body': 'Telemedicine, electronic records, wearables.'},
    {'icon': 'fa-coins', 'title': 'Money', 'body': 'Mobile banking, crypto, digital wallets.'},
    {'icon': 'fa-vote-yea', 'title': 'Government', 'body': 'e-Government services, e-filing, online IDs.'},
    {'icon': 'fa-people-arrows', 'title': 'Society', 'body': 'Social movements, news, misinformation.'},
])},
        {'order': 2, 'duration_minutes': 30, 'title': 'Emerging Technologies: AI, IoT, Blockchain',
         'content': intro('Lesson 2 &middot; What\'s Next',
            'Three technologies dominate today\'s headlines &mdash; <strong>AI</strong>, the <strong>Internet of Things</strong>, and <strong>Blockchain</strong>.') + """
<h2>Artificial Intelligence</h2>
<p>Software that learns from data to perform tasks normally done by humans &mdash; image recognition, translation, conversation (ChatGPT, Copilot).</p>
<h3>IoT &mdash; Internet of Things</h3>
<p>Everyday objects connected to the internet: smart thermostats, fitness bands, fridges, cars, factory sensors.</p>
<h3>Blockchain</h3>
<p>A shared, append-only digital ledger. Used for cryptocurrencies (Bitcoin), supply-chain tracking, digital certificates.</p>
""" + callout('warn', 'fa-triangle-exclamation', 'Hype vs reality',
              'Not every problem needs blockchain or AI. Pick the right tool, not the buzzword.')},
        {'order': 3, 'duration_minutes': 30, 'title': 'Privacy, Surveillance and Data Rights',
         'content': intro('Lesson 3 &middot; Who Owns Your Data?',
            'You leave a digital trail everywhere &mdash; with apps, cards, social media, even your face on cameras. Knowing your rights protects your future.') + """
<h2>Where your data goes</h2>
<ul>
  <li>Social media platforms (likes, location, contacts).</li>
  <li>Apps requesting permissions (camera, mic, contacts).</li>
  <li>Loyalty cards and shopping history.</li>
  <li>CCTV in public spaces.</li>
  <li>Smartphone GPS history.</li>
</ul>
<h3>Your rights under POPIA (South Africa)</h3>
<ul>
  <li>Be told why your data is collected.</li>
  <li>Access and correct it.</li>
  <li>Object to its use, especially for direct marketing.</li>
  <li>Have it deleted (right to be forgotten).</li>
</ul>
""" + callout('key', 'fa-key', 'Privacy hygiene',
              'Review app permissions monthly. Use a privacy-focused browser. Switch off location services for apps that don\'t need them.')},
        {'order': 4, 'duration_minutes': 30, 'title': 'Cyber Crime and the Law',
         'content': intro('Lesson 4 &middot; Crime Has Gone Digital',
            'South Africa\'s <strong>Cybercrimes Act, 2020</strong> defines and criminalises specific online offences.') + """
<h2>Crimes covered</h2>
<table>
  <tr><th>Offence</th><th>What it covers</th></tr>
  <tr><td>Unlawful access</td><td>Hacking into systems without permission.</td></tr>
  <tr><td>Cyber fraud</td><td>Online scams, phishing, fake invoices.</td></tr>
  <tr><td>Cyber forgery</td><td>Forging digital signatures, fake documents.</td></tr>
  <tr><td>Unlawful interception</td><td>Spying on emails / messages.</td></tr>
  <tr><td>Malicious communication</td><td>Threats, harassment, intimate-image abuse.</td></tr>
</table>
<h3>Reporting</h3>
<p>Report to <strong>SAPS</strong> and the <strong>SAPS Cybercrime Division</strong>. Banks have their own fraud lines for financial scams.</p>
""" + callout('warn', 'fa-triangle-exclamation', 'Even sharing matters',
              'Forwarding intimate images without consent is illegal. Think before you share.')},
        {'order': 5, 'duration_minutes': 25, 'title': 'Green Computing and Digital Wellbeing',
         'content': intro('Lesson 5 &middot; A Healthy Relationship with Tech',
            'Tech is a tool. Used well, it improves life. Used badly, it harms us &mdash; and the planet.') + """
<h2>Green computing</h2>
""" + grid([
    {'icon': 'fa-bolt', 'title': 'Power', 'body': 'Sleep mode, dark themes (OLED), shut down at night.'},
    {'icon': 'fa-recycle', 'title': 'E-waste', 'body': 'Donate or recycle responsibly &mdash; never landfill.'},
    {'icon': 'fa-print', 'title': 'Paper', 'body': 'Print double-sided, prefer PDF.'},
    {'icon': 'fa-cloud', 'title': 'Cloud-aware', 'body': 'Streaming and AI use server power. Limit needless usage.'},
]) + """
<h2>Digital wellbeing</h2>
<ul>
  <li>Use Screen Time / Digital Wellbeing dashboards on your phone.</li>
  <li>Turn off non-essential notifications.</li>
  <li>Tech-free time before bed.</li>
  <li>Watch posture, take breaks (20-20-20 rule for eyes).</li>
</ul>
""" + callout('key', 'fa-key', 'You are in charge',
              'Apps are designed to grab attention. Set limits &mdash; don\'t let the app set them for you.')},
    ],
    'quiz': make_quiz(
        'ICT & Society — Knowledge Check',
        'Tests impacts of ICT, emerging tech, privacy, cyber law and green IT.',
        [
            {'question_type': 'multiple_choice',
             'question_text': 'Smart fridges and connected thermostats are examples of:',
             'options': ['AI', 'Blockchain', 'Internet of Things (IoT)', 'CSS'],
             'correct_answer': 'Internet of Things (IoT)',
             'explanation': 'IoT = everyday objects with internet connectivity.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A shared, append-only digital ledger is best described as:',
             'options': ['Database', 'Spreadsheet', 'Blockchain', 'Cloud drive'],
             'correct_answer': 'Blockchain',
             'explanation': 'Blockchain underlies cryptocurrencies and supply-chain ledgers.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which SA law gives you the right to be told why your data is collected?',
             'options': ['POPIA', 'BCEA', 'COIDA', 'IRP6'],
             'correct_answer': 'POPIA',
             'explanation': 'Protection of Personal Information Act.'},
            {'question_type': 'multiple_choice', 'points': 2,
             'question_text': 'Forwarding an intimate image without consent in South Africa is:',
             'options': ['Allowed if you blur faces',
                         'A criminal offence under the Cybercrimes Act',
                         'A civil matter only',
                         'Permitted on private chats'],
             'correct_answer': 'A criminal offence under the Cybercrimes Act',
             'explanation': 'It is criminalised under the 2020 Cybercrimes Act.'},
            {'question_type': 'multiple_choice',
             'question_text': 'The 20-20-20 rule helps with:',
             'options': ['Battery life', 'Eye strain',
                         'Internet speed', 'Storage capacity'],
             'correct_answer': 'Eye strain',
             'explanation': 'Every 20 minutes, look at something 20 feet away for 20 seconds.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each emerging technology with an example.',
             'options': {
                 'column_a': ['AI', 'IoT', 'Blockchain', 'Cloud'],
                 'column_b': ['ChatGPT writing an essay',
                              'Smartwatch tracking your heart rate',
                              'Bitcoin transactions',
                              'Storing files on OneDrive']
             },
             'correct_answer': {'AI': 'ChatGPT writing an essay',
                                'IoT': 'Smartwatch tracking your heart rate',
                                'Blockchain': 'Bitcoin transactions',
                                'Cloud': 'Storing files on OneDrive'},
             'explanation': 'Each technology has signature use cases.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these e-waste disposal options from BEST to WORST.',
             'options': ['Throw in the regular bin',
                         'Donate working device to a school',
                         'Take to certified e-waste recycler'],
             'correct_answer': ['Donate working device to a school',
                                'Take to certified e-waste recycler',
                                'Throw in the regular bin'],
             'explanation': 'Reuse first, recycle responsibly second, never landfill.'},
            {'question_type': 'short_answer',
             'question_text': 'Name one digital wellbeing habit you can adopt today.',
             'options': [], 'correct_answer': 'screen time limit',
             'explanation': 'Screen-time limits, notification reduction, tech-free hours all count.'},
        ]
    ),
}


# ===========================================================================
# Master list and seeder
# ===========================================================================

ALL_COURSES = [
    G10_SPREADSHEETS, G10_PRESENTATIONS, G10_HARDWARE, G10_NETWORKS, G10_INFO,
    G11_ADV_WORD, G11_ADV_SPREAD, G11_DB, G11_ADV_PRES, G11_SYS, G11_INTERNET_SOC,
    G12_INTEGRATED, G12_ADV_FUNC, G12_ADV_DB, G12_WEB, G12_SOLUTION, G12_ICT_SOC,
]


def seed():
    with app.app_context():
        totals = {'lessons_added': 0, 'lessons_updated': 0,
                  'quizzes_added': 0, 'questions_added': 0, 'courses_done': 0}
        skipped = []

        for course_def in ALL_COURSES:
            grade_num = course_def['grade']
            title = course_def['course_title']

            course = (Course.query.join(Grade)
                      .filter(Grade.number == grade_num, Course.title == title)
                      .first())
            if not course:
                skipped.append(f"Grade {grade_num} - {title}")
                continue

            for ld in course_def['lessons']:
                existing = Lesson.query.filter_by(course_id=course.id, order=ld['order']).first()
                if existing:
                    existing.title = ld['title']
                    existing.content = ld['content']
                    existing.duration_minutes = ld['duration_minutes']
                    totals['lessons_updated'] += 1
                else:
                    db.session.add(Lesson(course_id=course.id, **ld))
                    totals['lessons_added'] += 1

            qd = course_def['quiz']
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
                db.session.flush()
                totals['quizzes_added'] += 1

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
                totals['questions_added'] += 1

            totals['courses_done'] += 1

        db.session.commit()

        print("=" * 60)
        print("CAPS Content Seeder — Summary")
        print("=" * 60)
        print(f"Courses processed:   {totals['courses_done']} / {len(ALL_COURSES)}")
        print(f"Lessons added:       {totals['lessons_added']}")
        print(f"Lessons updated:     {totals['lessons_updated']}")
        print(f"Quizzes added:       {totals['quizzes_added']}")
        print(f"Questions added:     {totals['questions_added']}")
        if skipped:
            print(f"\nSkipped (course not found, run init_db first):")
            for s in skipped:
                print(f"  - {s}")
        print("=" * 60)


if __name__ == '__main__':
    seed()

