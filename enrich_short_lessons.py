"""
Enrich short lessons with extra rich-HTML sections.

Any lesson whose content length is below THRESHOLD characters gets a
generic "Deep Dive / Worked Example / Vocabulary / Self-Check" block
appended. The block is wrapped in a marker so re-runs are idempotent
(no double-append).

Run:
    python enrich_short_lessons.py
"""
from app import app, db, Course, Grade, Lesson


THRESHOLD = 2000  # characters
MARKER_OPEN = '<!-- ENRICHED:v1 -->'
MARKER_CLOSE = '<!-- /ENRICHED:v1 -->'


def kbd(*keys):
    parts = []
    for i, k in enumerate(keys):
        if i:
            parts.append('<span class="plus">+</span>')
        parts.append(f'<span class="kbd">{k}</span>')
    return '<span class="kbd-combo">' + ''.join(parts) + '</span>'


# ---------------------------------------------------------------------------
# Topic-specific enrichment packs.
# Lookup is by course title; each pack is a dict that may contain:
#   deep_dive  -> HTML
#   example    -> HTML
#   vocab      -> [(term, definition), ...]
#   checks     -> [question, ...]
#   tips       -> [tip, ...]
# A generic fallback is used if the course is not in PACKS.
# ---------------------------------------------------------------------------

PACKS = {
    'Word Processing': {
        'deep_dive': """
<p>Word remembers <strong>everything you do</strong> on a hidden timeline. That is why <strong>Undo</strong> (""" + kbd('Ctrl', 'Z') + """) and <strong>Redo</strong> (""" + kbd('Ctrl', 'Y') + """) are so powerful &mdash; you can step back through dozens of changes without losing any work.</p>
<p>The same idea powers <strong>AutoRecover</strong>: every few minutes Word saves a snapshot of your document. If your computer crashes, the next time you open Word it offers to bring those documents back.</p>
""",
        'example': """
<p>You typed an essay and accidentally pressed """ + kbd('Ctrl', 'A') + """ then """ + kbd('Delete') + """ &mdash; the whole essay vanished!</p>
<ol class="steps">
  <li>Stay calm. <strong>Do not close the file.</strong></li>
  <li>Press """ + kbd('Ctrl', 'Z') + """ <em>once</em>. The text comes straight back.</li>
  <li>Save immediately with """ + kbd('Ctrl', 'S') + """.</li>
</ol>
""",
        'vocab': [
            ('Cursor', 'The blinking line that shows where the next character will appear.'),
            ('Ribbon', 'The strip of tabs and tools across the top of Word.'),
            ('Status bar', 'The bar at the very bottom showing page count, word count and zoom.'),
            ('AutoRecover', 'Word\'s automatic background save in case of a crash.'),
        ],
        'tips': [
            'Press ' + kbd('Ctrl', 'S') + ' every time you finish a paragraph &mdash; it becomes a habit.',
            'Use ' + kbd('Ctrl', 'F') + ' to find any word in seconds.',
        ],
    },
    'Spreadsheets': {
        'deep_dive': """
<p>Every cell holds one of three things: <strong>text</strong>, a <strong>number</strong>, or a <strong>formula</strong>. Excel decides automatically based on what you type. To force text (e.g. for a phone number starting with 0), type a single quote first: <code>'0824567890</code>.</p>
<p>Formulas always start with <code>=</code> and follow the BODMAS rule of mathematics &mdash; brackets first, then orders, then division &amp; multiplication, then addition &amp; subtraction.</p>
""",
        'example': """
<p>You want to add a 15% VAT column to a price list:</p>
<ol class="steps">
  <li>In <code>B2</code> type the price, e.g. <code>100</code>.</li>
  <li>In <code>C2</code> type <code>=B2*0.15</code> &mdash; this is the VAT amount.</li>
  <li>In <code>D2</code> type <code>=B2+C2</code> &mdash; this is the total.</li>
  <li>Select <code>C2:D2</code> and drag the <strong>fill handle</strong> down to copy the formulas.</li>
</ol>
""",
        'vocab': [
            ('Cell reference', 'The address of a cell, e.g. B2.'),
            ('Range', 'A group of cells written with a colon, e.g. A1:A10.'),
            ('Fill handle', 'The small square at the bottom-right of a selected cell.'),
            ('Function', 'A built-in formula like =SUM() or =AVERAGE().'),
        ],
        'tips': [
            'Press ' + kbd('Ctrl', '`') + ' to switch between formulas and results.',
            'Double-click the fill handle to copy a formula down a whole column.',
        ],
    },
    'Presentations': {
        'deep_dive': """
<p>A great slide deck is the visual support for what you <em>say</em>. Audiences read 250 words per minute but listen at only 150 words per minute &mdash; if your slide is full of text, they stop listening to you to read it.</p>
<p>That is why designers use the <strong>10/20/30 rule</strong>: at most 10 slides, 20 minutes, 30-point font.</p>
""",
        'example': """
<p>Plan a 5-slide pitch for a school car-wash fundraiser:</p>
<ol class="steps">
  <li><strong>Title</strong> &mdash; Project name + your name + date.</li>
  <li><strong>Problem</strong> &mdash; "Our class needs R5 000 for the camp."</li>
  <li><strong>Solution</strong> &mdash; Saturday car-wash, R30 per car.</li>
  <li><strong>Plan</strong> &mdash; Date, helpers, equipment.</li>
  <li><strong>Ask</strong> &mdash; "Please approve and tell your friends."</li>
</ol>
""",
        'vocab': [
            ('Slide', 'A single page in a presentation.'),
            ('Layout', 'A pre-made arrangement of placeholders on a slide.'),
            ('Theme', 'A coordinated set of fonts, colours and backgrounds.'),
            ('Transition', 'The visual change between two slides.'),
        ],
        'tips': [
            'Rehearse out loud with a stopwatch &mdash; you are usually 30% slower than you think.',
            'Press ' + kbd('B') + ' during a slideshow to black out the screen so the audience looks at you.',
        ],
    },
    'Computer Hardware': {
        'deep_dive': """
<p>A modern computer has four functional units: <strong>input</strong>, <strong>processing</strong>, <strong>storage</strong> and <strong>output</strong>. Information flows in, the CPU and RAM work on it, the result is shown or saved, and storage keeps it for next time.</p>
<p>Speed is measured in <strong>Hertz</strong> (cycles per second). 1 GHz = 1 billion cycles per second &mdash; a modern CPU performs several operations per cycle on multiple cores.</p>
""",
        'example': """
<p>Choosing a laptop for school work:</p>
<table>
  <tr><th>Component</th><th>Minimum</th><th>Comfortable</th></tr>
  <tr><td>CPU</td><td>Intel i3 / AMD Ryzen 3</td><td>Intel i5 / AMD Ryzen 5</td></tr>
  <tr><td>RAM</td><td>4 GB</td><td>8 GB+</td></tr>
  <tr><td>Storage</td><td>128 GB SSD</td><td>256 GB SSD+</td></tr>
  <tr><td>Battery</td><td>4 hours</td><td>8 hours+</td></tr>
</table>
""",
        'vocab': [
            ('CPU', 'Central Processing Unit &mdash; the "brain" that runs instructions.'),
            ('RAM', 'Volatile working memory; loses data when power is cut.'),
            ('SSD', 'Solid-State Drive &mdash; fast flash storage with no moving parts.'),
            ('GPU', 'Graphics Processing Unit &mdash; renders images for the display.'),
        ],
        'tips': [
            'When buying RAM, match the same speed (e.g. DDR4-3200) to all sticks.',
            'Heat kills electronics &mdash; never block the laptop\'s cooling vents.',
        ],
    },
    'Networks & Internet': {
        'deep_dive': """
<p>A network exists so that two or more computers can <strong>share</strong> something &mdash; a file, a printer, an internet connection. The internet itself is just a network of networks, all using one common language called <strong>TCP/IP</strong>.</p>
<p>Every device on a network needs a unique <strong>IP address</strong>, just like every house needs a unique street address.</p>
""",
        'example': """
<p>Watch what happens when you visit <code>example.co.za</code>:</p>
<ol class="steps">
  <li>Your browser asks the <strong>DNS</strong> "What is the IP for example.co.za?"</li>
  <li>DNS replies (e.g. <code>196.25.1.10</code>).</li>
  <li>Your computer opens a <strong>TCP</strong> connection to that IP on port 443.</li>
  <li>It sends an HTTPS request and the server returns the page.</li>
  <li>Your browser renders the HTML, CSS and JavaScript.</li>
</ol>
""",
        'vocab': [
            ('Bandwidth', 'How much data a connection can transfer per second.'),
            ('Latency', 'How long it takes for a single packet to make a round trip (ping).'),
            ('Packet', 'A small chunk of data sent across the network.'),
            ('Firewall', 'Software or hardware that controls which traffic is allowed in or out.'),
        ],
        'tips': [
            'Wired connections are usually faster and more stable than Wi-Fi.',
            'Restart your router occasionally &mdash; it clears memory leaks.',
        ],
    },
    'Information Management': {
        'deep_dive': """
<p>We are drowning in data but starving for knowledge. The job of information management is to turn raw <strong>data</strong> (facts) into <strong>information</strong> (organised facts) into <strong>knowledge</strong> (information you can act on).</p>
<p>That is why naming files clearly, choosing trustworthy sources and citing them properly are foundational skills, not optional extras.</p>
""",
        'example': """
<p>Folder layout for a school research project:</p>
<pre><code>research/
  ozone-layer/
    01-plan/
      questions.docx
    02-sources/
      unep-2024.pdf
      nasa-2025.pdf
    03-notes/
      summary.docx
    04-final/
      report.docx
      report.pdf</code></pre>
""",
        'vocab': [
            ('Source', 'Where a piece of information came from.'),
            ('Citation', 'A short reference acknowledging a source.'),
            ('Bibliography', 'A list of all sources used in a piece of work.'),
            ('Plagiarism', 'Using someone else\'s words or ideas without credit.'),
        ],
        'tips': [
            'Save sources as PDFs the day you find them &mdash; web pages disappear.',
            'A good filename includes the date: <code>budget_2026-04-22.xlsx</code>.',
        ],
    },
    'Advanced Word Processing': {
        'deep_dive': """
<p>Long documents (10+ pages) need <strong>structure</strong> &mdash; styles, sections and references. Without them, every formatting change becomes a manual nightmare.</p>
<p>Apply Heading 1 / 2 / 3 styles consistently and Word can build a Table of Contents, a navigation pane and a list of figures automatically.</p>
""",
        'example': """
<p>Build a 6-page report skeleton in 2 minutes:</p>
<ol class="steps">
  <li>Type six headings, one per page (use """ + kbd('Ctrl', 'Enter') + """ for a page break).</li>
  <li>Apply <strong>Heading 1</strong> to each (""" + kbd('Ctrl', 'Alt', '1') + """).</li>
  <li>Insert &rarr; Cover Page &rarr; pick a style.</li>
  <li>References &rarr; Table of Contents &rarr; Automatic Table 1.</li>
</ol>
""",
        'vocab': [
            ('Style', 'A reusable bundle of font, size, colour and spacing.'),
            ('Section break', 'A divider that lets parts of a document have different page setup.'),
            ('Cross-reference', 'An auto-updating link to a heading, figure or page.'),
            ('Track Changes', 'Records insertions and deletions for review.'),
        ],
        'tips': [
            'Right-click a style &rarr; <em>Modify</em> to change every paragraph that uses it.',
            'Use the <strong>Navigation Pane</strong> (' + kbd('Ctrl', 'F') + ') to jump between headings.',
        ],
    },
    'Advanced Spreadsheets': {
        'deep_dive': """
<p>Once you go beyond simple SUM and AVERAGE, the most powerful Excel features are the <strong>conditional</strong> family of functions: <code>IF</code>, <code>SUMIF</code>, <code>COUNTIF</code>, <code>AVERAGEIF</code> and <code>IFS</code>.</p>
<p>They let you say "give me the total <em>only when</em> a condition is met". This is how mark sheets, sales reports and budget summaries are built.</p>
""",
        'example': """
<p>Count how many learners passed:</p>
<pre><code>=COUNTIF(E2:E31,"&gt;=50")</code></pre>
<p>Average mark for learners who passed:</p>
<pre><code>=AVERAGEIF(E2:E31,"&gt;=50")</code></pre>
<p>Total fees collected from Grade 11 only:</p>
<pre><code>=SUMIF(B2:B100,"Grade 11",C2:C100)</code></pre>
""",
        'vocab': [
            ('Absolute reference', 'Cell reference fixed with $, e.g. $A$1.'),
            ('Mixed reference', 'Either row or column locked, e.g. $A1 or A$1.'),
            ('Named range', 'A friendly name like "Prices" instead of D2:D50.'),
            ('Goal Seek', 'Find the input that produces a desired output.'),
        ],
        'tips': [
            'Press ' + kbd('F4') + ' while editing a reference to cycle through $ combinations.',
            'Define a named range so formulas read like English: <code>=SUMIF(Class,"11",Fees)</code>.',
        ],
    },
    'Database Concepts': {
        'deep_dive': """
<p>A database is more than a fancy spreadsheet. It enforces <strong>structure</strong> (every record has the same fields), <strong>integrity</strong> (no duplicates, no orphans) and supports <strong>multiple users</strong> at the same time.</p>
<p>The most common type is the <strong>relational</strong> database: data lives in tables, and tables are linked by keys.</p>
""",
        'example': """
<p>A simple library database has three tables:</p>
<table>
  <tr><th>Table</th><th>Sample fields</th></tr>
  <tr><td>Books</td><td>BookID*, Title, Author, ISBN</td></tr>
  <tr><td>Members</td><td>MemberID*, Name, Grade, JoinDate</td></tr>
  <tr><td>Loans</td><td>LoanID*, BookID, MemberID, OutDate, DueDate</td></tr>
</table>
<p>* = primary key. Loans.BookID and Loans.MemberID are <strong>foreign keys</strong>.</p>
""",
        'vocab': [
            ('Record', 'One row in a table (e.g. one learner).'),
            ('Field', 'One column in a table (e.g. surname).'),
            ('Primary key', 'A field whose value uniquely identifies each record.'),
            ('Foreign key', 'A field that links to another table\'s primary key.'),
        ],
        'tips': [
            'Always design tables on paper first.',
            'Pick the <em>simplest</em> data type that does the job &mdash; smaller fields = faster queries.',
        ],
    },
    'Advanced Presentations': {
        'deep_dive': """
<p>Animations and triggers can make a slide come alive &mdash; but they can also drown your message in motion. The rule is: each animation must <strong>add meaning</strong>, never just decorate.</p>
<p><strong>Triggers</strong> let an animation start when you click a specific shape, so you can build interactive quizzes and "click to reveal" answers right inside PowerPoint.</p>
""",
        'example': """
<p>Build a one-question interactive quiz:</p>
<ol class="steps">
  <li>Insert the question text and three answer shapes.</li>
  <li>Select the wrong answer &rarr; Animations &rarr; <strong>Wipe</strong> + colour change to red.</li>
  <li>Trigger &rarr; <strong>On Click of</strong> &rarr; that same shape.</li>
  <li>Repeat for the right answer with a green colour.</li>
  <li>Run the slideshow and click the answers.</li>
</ol>
""",
        'vocab': [
            ('Trigger', 'Starts an animation when a chosen object is clicked.'),
            ('Animation pane', 'Shows every animation on the slide in order.'),
            ('Action button', 'Pre-made shapes that link to other slides or files.'),
            ('Kiosk mode', 'Self-running show that loops without user input.'),
        ],
        'tips': [
            'Keep animation duration under 1 second &mdash; long animations bore the audience.',
            'Use the same animation style throughout one presentation for a polished look.',
        ],
    },
    'System Software': {
        'deep_dive': """
<p>System software is the <strong>middle layer</strong> between the bare hardware and the apps you use every day. Without it, every application would have to talk to every device directly &mdash; impossible.</p>
<p>The <strong>operating system</strong> handles five core jobs: managing the CPU, memory, storage, devices and security.</p>
""",
        'example': """
<p>What happens when you open a Word document?</p>
<ol class="steps">
  <li>You double-click the file &rarr; the <strong>OS file manager</strong> looks up which app handles <code>.docx</code>.</li>
  <li>The OS asks the <strong>process manager</strong> to start Word.</li>
  <li>The OS loads Word into <strong>RAM</strong> and gives it CPU time.</li>
  <li>Word asks the OS to read the file from <strong>disk</strong>.</li>
  <li>The OS sends the document to the <strong>display driver</strong> so you see it on screen.</li>
</ol>
""",
        'vocab': [
            ('Kernel', 'The core of the OS that talks directly to the hardware.'),
            ('Driver', 'Software that lets the OS talk to a specific device.'),
            ('Utility', 'Small support tool (antivirus, backup, defragmenter, etc.).'),
            ('File system', 'How files are organised on disk (NTFS, FAT32, EXT4, APFS).'),
        ],
        'tips': [
            'Keep the OS updated &mdash; most updates fix security flaws.',
            'Schedule weekly automatic backups; you only miss them when you need them.',
        ],
    },
    'Internet & Social Implications': {
        'deep_dive': """
<p>Every online action leaves a permanent trace called your <strong>digital footprint</strong>. Recruiters, universities and even insurance companies search this footprint before deciding about you.</p>
<p>Privacy is not "having nothing to hide" &mdash; it is having control over what others know about you.</p>
""",
        'example': """
<p>Audit your own digital footprint:</p>
<ol class="steps">
  <li>Google your full name in quotes ("Lerato Smith").</li>
  <li>Open Google Image search and search the same name.</li>
  <li>List 5 things you would NOT want a future employer to see.</li>
  <li>Delete or untag yourself from those 5 things today.</li>
  <li>Set up a Google Alert for your name to catch new mentions.</li>
</ol>
""",
        'vocab': [
            ('Phishing', 'Tricking someone into revealing data via fake messages.'),
            ('Malware', 'Any malicious software (virus, worm, ransomware, etc.).'),
            ('Encryption', 'Scrambling data so only the holder of the key can read it.'),
            ('2FA', 'Two-factor authentication &mdash; password + a second proof.'),
        ],
        'tips': [
            'Never reuse the same password on more than one site.',
            'Hover over a link before clicking to check the real URL.',
        ],
    },
    'Integrated Document Handling': {
        'deep_dive': """
<p>Office apps were designed to work together. With <strong>OLE</strong> (Object Linking and Embedding), data can flow from Excel into Word into PowerPoint &mdash; one update at the source ripples everywhere.</p>
<p>The trick is choosing wisely: <strong>link</strong> when the source file will stay in place, <strong>embed</strong> when the document must travel on its own.</p>
""",
        'example': """
<p>Build a quotation that always shows the latest price:</p>
<ol class="steps">
  <li>In Excel build a price list and save it as <code>prices.xlsx</code>.</li>
  <li>In Word, copy the price cell.</li>
  <li>In Word: Home &rarr; Paste &rarr; <strong>Paste Special</strong> &rarr; <em>Paste link</em> &rarr; Microsoft Excel Worksheet Object.</li>
  <li>Update the price in Excel and save.</li>
  <li>Right-click the price in Word &rarr; <em>Update Link</em> &mdash; the new value appears.</li>
</ol>
""",
        'vocab': [
            ('OLE', 'Object Linking and Embedding &mdash; how Office apps share content.'),
            ('Link', 'Reference to data stored elsewhere; updates automatically.'),
            ('Embed', 'A copy stored inside the file; independent of the source.'),
            ('Mail merge', 'Combine a template document with a data source.'),
        ],
        'tips': [
            'For final delivery, export to PDF so links cannot break.',
            'Always test your linked document on a different computer before submitting.',
        ],
    },
    'Advanced Spreadsheet Functions': {
        'deep_dive': """
<p>The most powerful Excel users combine functions inside other functions. <code>=IF(VLOOKUP(...)&gt;100, "high", "low")</code> reads as: <em>look up a value, then decide what to print based on it</em>.</p>
<p>Excel evaluates from the <strong>inside out</strong>, just like maths brackets. Use the <strong>Formulas &rarr; Evaluate Formula</strong> button to step through one piece at a time.</p>
""",
        'example': """
<p>Calculate a 10% bonus only for sales people who beat their target:</p>
<pre><code>=IF(B2&gt;=Target, B2*0.10, 0)</code></pre>
<p>Lookup the sales person's region from a master list:</p>
<pre><code>=INDEX(Regions[Region], MATCH(A2, Regions[ID], 0))</code></pre>
<p>Combine both into a single formula:</p>
<pre><code>=IF(B2&gt;=Target, B2*0.10, 0) &amp; " &mdash; " &amp; INDEX(Regions[Region], MATCH(A2, Regions[ID], 0))</code></pre>
""",
        'vocab': [
            ('Nested function', 'A function used as an argument inside another function.'),
            ('Array formula', 'One formula that operates on a whole range at once.'),
            ('Macro', 'A recorded set of actions stored as VBA code.'),
            ('VBA', 'Visual Basic for Applications &mdash; the programming language behind macros.'),
        ],
        'tips': [
            'Build complex formulas one layer at a time and check each layer\'s output.',
            'Use named ranges to keep nested formulas readable.',
        ],
    },
    'Advanced Databases': {
        'deep_dive': """
<p>The point of <strong>relationships</strong> in Microsoft Access is to remove repetition. If "Maths" is the subject for 30 learners, you store the word "Maths" <strong>once</strong> in a Subjects table and link to it from each learner record using a <strong>foreign key</strong>.</p>
<p>That is called <strong>normalisation</strong>. Done well, it makes a database smaller, faster, and almost impossible to leave inconsistent. In Access you set this up in the <strong>Relationships window</strong> (Database Tools &rarr; Relationships) by dragging the primary key of one table onto the matching field in another.</p>
""",
        'example': """
<p>A query in Microsoft Access &mdash; built in <strong>Query Design view</strong> &mdash; that joins two tables to show every order over R500, newest first:</p>
<ol class="steps">
<li>Create &rarr; <strong>Query Design</strong>.</li>
<li>Add the <em>Customers</em> and <em>Orders</em> tables. Access automatically draws the join line on <code>CustomerID</code>.</li>
<li>Drag these fields into the design grid:
  <ul>
    <li><code>Customers.Name</code></li>
    <li><code>Orders.OrderDate</code></li>
    <li><code>Orders.Total</code></li>
  </ul>
</li>
<li>In the <em>Criteria</em> row under <code>Total</code> type: <code>&gt;500</code></li>
<li>In the <em>Sort</em> row under <code>OrderDate</code> choose <strong>Descending</strong>.</li>
<li>Click <strong>Run</strong> (the red <code>!</code> on the ribbon) to see the results.</li>
</ol>
<p>Save the query as <code>qryBigOrders</code>. You can re-open it any time, and it will always show the latest data.</p>
""",
        'vocab': [
            ('Relationship', 'A link between two Access tables based on matching fields.'),
            ('Query Design view', 'The Access screen where you build queries with a visual grid.'),
            ('Criteria row', 'Row in the design grid where you type filter conditions.'),
            ('Normalisation', 'Splitting data into related tables to remove duplication.'),
        ],
        'tips': [
            'Always test a query in Datasheet view before basing a form or report on it.',
            'Back up the .accdb file before running an Update or Delete query.',
        ],
    },
    'Web & HTML Basics': {
        'deep_dive': """
<p>The web rests on three layers: <strong>HTML</strong> (structure), <strong>CSS</strong> (style) and <strong>JavaScript</strong> (behaviour). Browsers turn these three text files into the rich pages you scroll through every day.</p>
<p>Every browser is just a very fancy program for asking servers for HTML and rendering it. The same page can look different in different browsers if you don't follow the standards.</p>
""",
        'example': """
<p>A complete tiny web page:</p>
<pre><code>&lt;!DOCTYPE html&gt;
&lt;html lang="en"&gt;
&lt;head&gt;
  &lt;meta charset="utf-8"&gt;
  &lt;title&gt;My First Page&lt;/title&gt;
  &lt;style&gt;
    body { font-family: sans-serif; background: #f0f8ff; }
    h1   { color: #0078D4; }
  &lt;/style&gt;
&lt;/head&gt;
&lt;body&gt;
  &lt;h1&gt;Hello, web!&lt;/h1&gt;
  &lt;p&gt;This page was built in 10 lines.&lt;/p&gt;
&lt;/body&gt;
&lt;/html&gt;</code></pre>
""",
        'vocab': [
            ('HTML', 'HyperText Markup Language &mdash; the structure of a page.'),
            ('CSS', 'Cascading Style Sheets &mdash; the visual style of a page.'),
            ('Element', 'A pair of opening + closing tags and what is between them.'),
            ('Attribute', 'Extra information on a tag, e.g. href="..." inside &lt;a&gt;.'),
        ],
        'tips': [
            'Press ' + kbd('F12') + ' in any browser to open Developer Tools.',
            'Validate your HTML at <code>validator.w3.org</code> before publishing.',
        ],
    },
    'Solution Development': {
        'deep_dive': """
<p>Every great app started with a <strong>problem worth solving</strong>. The Software Development Life Cycle (SDLC) is just a structured way to make sure you keep solving the right problem.</p>
<p>Modern teams iterate in short cycles: <em>plan, build a small piece, show it to users, learn, repeat</em>. This is called <strong>agile</strong>.</p>
""",
        'example': """
<p>Plan your PAT in five sentences:</p>
<table>
  <tr><th>Stage</th><th>Question to answer</th></tr>
  <tr><td>Investigation</td><td>What real problem am I solving and for whom?</td></tr>
  <tr><td>Analysis</td><td>What inputs, processes and outputs are needed?</td></tr>
  <tr><td>Design</td><td>What does the screen look like and which functions are required?</td></tr>
  <tr><td>Implementation</td><td>How do I build the smallest working version?</td></tr>
  <tr><td>Testing</td><td>Does it solve the problem for a real user?</td></tr>
</table>
""",
        'vocab': [
            ('SDLC', 'Software Development Life Cycle.'),
            ('Prototype', 'Early throw-away version used to learn quickly.'),
            ('User story', 'Short sentence describing what a user wants to do and why.'),
            ('Iteration', 'One short cycle of plan-build-test-learn.'),
        ],
        'tips': [
            'Write the problem statement on paper before opening any software.',
            'Show your prototype to a real user as early as possible.',
        ],
    },
    'ICT & Society': {
        'deep_dive': """
<p>Technology amplifies human choices &mdash; both good and bad. The same smartphone that connects a rural learner to a world-class library can also spread misinformation in seconds.</p>
<p>Becoming a thoughtful <strong>digital citizen</strong> is no longer optional &mdash; it is one of the most important life skills of the 21st century.</p>
""",
        'example': """
<p>Three real-world dilemmas to discuss in class:</p>
<ol class="steps">
  <li>Should a self-driving car save its passenger or two pedestrians?</li>
  <li>Should governments be allowed to read encrypted messages to fight crime?</li>
  <li>If an AI writes your essay, who owns the words &mdash; you, the AI, or its creators?</li>
</ol>
""",
        'vocab': [
            ('Digital divide', 'Gap between people with and without ICT access.'),
            ('E-waste', 'Discarded electronic equipment.'),
            ('Green IT', 'Using ICT in a way that reduces environmental impact.'),
            ('Algorithmic bias', 'When an AI gives unfair results because of biased training data.'),
        ],
        'tips': [
            'Recycle old electronics through registered e-waste programmes only.',
            'Switch off devices when not in use &mdash; even standby uses power.',
        ],
    },
}


GENERIC = {
    'deep_dive': """
<p>Take a moment to connect this lesson to what you already know. Most ideas in CAT build on top of earlier ones &mdash; if you can teach this idea to a friend in your own words, you really understand it.</p>
<p>The skills you are practising here are not just for an exam. They are the same skills you will use in your first job, your studies and your daily digital life.</p>
""",
    'example': """
<p>Try this short challenge to lock the lesson into memory:</p>
<ol class="steps">
  <li>Pick the most important idea from this lesson and write it on a sticky note in your own words.</li>
  <li>Find a real example of that idea on a website, in an app or in your school.</li>
  <li>Take a screenshot or photo and explain it in one sentence in your notes.</li>
</ol>
""",
    'vocab': [
        ('Concept', 'A general idea that helps you understand new examples.'),
        ('Skill', 'Something you can do, learned through practice.'),
        ('Workflow', 'The set of steps you follow to complete a task.'),
        ('Best practice', 'A way of doing something that experts agree works well.'),
    ],
    'tips': [
        'Re-read the lesson after 24 hours &mdash; spaced repetition triples memory.',
        'Teach the idea to someone who was absent &mdash; explaining is the best test.',
    ],
}


CHECKS = [
    'Can you explain the main idea of this lesson in one sentence?',
    'What is one thing from this lesson you will use this week?',
    'Where might you see this idea in everyday life?',
    'What new word from this lesson would you teach someone else?',
    'Which step would you find hardest if you tried this on your own?',
]


def build_block(course_title):
    pack = PACKS.get(course_title, GENERIC)
    deep = pack.get('deep_dive', GENERIC['deep_dive'])
    example = pack.get('example', GENERIC['example'])
    vocab = pack.get('vocab', GENERIC['vocab'])
    tips = pack.get('tips', GENERIC['tips'])

    vocab_html = '<table><tr><th>Term</th><th>Meaning</th></tr>' + ''.join(
        f'<tr><td><strong>{t}</strong></td><td>{d}</td></tr>' for t, d in vocab
    ) + '</table>'

    tips_html = '<ul>' + ''.join(f'<li>{t}</li>' for t in tips) + '</ul>'

    checks_html = '<ol>' + ''.join(f'<li>{q}</li>' for q in CHECKS) + '</ol>'

    return f"""
{MARKER_OPEN}
<hr/>
<h2><i class="fas fa-magnifying-glass-chart"></i> Deep Dive</h2>
{deep}

<h2><i class="fas fa-flask"></i> Worked Example</h2>
<div class="callout try"><div class="ico"><i class="fas fa-rocket"></i></div><div class="body"><strong>Try this</strong>{example}</div></div>

<h2><i class="fas fa-book-bookmark"></i> Vocabulary</h2>
{vocab_html}

<h2><i class="fas fa-lightbulb"></i> Pro Tips</h2>
<div class="callout info"><div class="ico"><i class="fas fa-lightbulb"></i></div><div class="body"><strong>Remember</strong>{tips_html}</div></div>

<h2><i class="fas fa-circle-question"></i> Self-Check</h2>
<div class="callout key"><div class="ico"><i class="fas fa-key"></i></div><div class="body"><strong>Reflect</strong>{checks_html}</div></div>
{MARKER_CLOSE}
"""


def main():
    with app.app_context():
        enriched = 0
        skipped_long = 0
        already = 0

        for lesson in Lesson.query.all():
            content = lesson.content or ''

            if MARKER_OPEN in content:
                already += 1
                continue

            if len(content) >= THRESHOLD:
                skipped_long += 1
                continue

            course = Course.query.get(lesson.course_id)
            ctitle = course.title if course else ''
            block = build_block(ctitle)

            lesson.content = content + block
            enriched += 1

        db.session.commit()

        print('=' * 60)
        print('Lesson enrichment summary')
        print('=' * 60)
        print(f"  Threshold (chars).............. {THRESHOLD}")
        print(f"  Lessons enriched............... {enriched}")
        print(f"  Already enriched (skipped)..... {already}")
        print(f"  Long enough (skipped).......... {skipped_long}")
        print('=' * 60)


if __name__ == '__main__':
    main()
