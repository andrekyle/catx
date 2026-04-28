"""
Seed *additional* CAPS-aligned lessons + a second quiz for every course.

For each course this adds (idempotent — safe to re-run):
  * Lesson at order 6  -> "Practical Skills"
  * Lesson at order 7  -> "Real-World Applications"
  * A second Quiz (order 2) titled "<Course> -- Extension Quiz" with 8 questions

Existing lessons / quizzes are never overwritten — entries are skipped if a
record with the same (course_id, order) for lessons or (course_id, title) for
quizzes is already present.

Run:
    python seed_extra_content.py
"""
import json

from app import app, db, Grade, Course, Lesson, Quiz, Question


# ---------------------------------------------------------------------------
# HTML helpers (mirror style used by seed_caps_content.py / seed_grade10_word.py)
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
# Generic lesson / quiz factories
# ---------------------------------------------------------------------------
def practical_lesson(topic, tasks, tip):
    """Build a 'Practical Skills' lesson body (lesson 6)."""
    body = intro('Lesson 6 &middot; Practical Skills',
                 f'Time to put theory into practice. Work through the activities below to build real <strong>{topic}</strong> skills.')
    body += '<h2>Hands-on activities</h2>'
    body += steps(tasks)
    body += callout('try', 'fa-rocket', 'Mini-project',
                    f'Create a small {topic.lower()} project that uses at least three of the techniques above. Save it as <code>practice_01</code>.')
    body += callout('info', 'fa-lightbulb', 'Pro tip', tip)
    return body


def application_lesson(topic, scenarios, takeaway):
    """Build a 'Real-World Applications' lesson body (lesson 7)."""
    body = intro('Lesson 7 &middot; Real-World Applications',
                 f'See how {topic} is used in the workplace, in school and in everyday life.')
    body += '<h2>Where you will see this</h2>'
    body += grid(scenarios)
    body += callout('key', 'fa-key', 'Takeaway', takeaway)
    body += '<h3>Discussion questions</h3><ul>'
    body += '<li>Which application above is closest to a job you would like to do?</li>'
    body += '<li>What new skill would you need to learn to do that job well?</li>'
    body += '<li>How could you start practising that skill this week?</li>'
    body += '</ul>'
    return body


def make_quiz(title, description, questions):
    return {
        'title': title,
        'description': description,
        'quiz_type': 'quiz',
        'time_limit_minutes': 20,
        'pass_percentage': 60.0,
        'order': 2,
        'questions': [
            {'order': i + 1, 'points': q.get('points', 1), **q}
            for i, q in enumerate(questions)
        ],
    }


# ---------------------------------------------------------------------------
# Per-course content packs
# ---------------------------------------------------------------------------
PACKS = {

    # ============================ GRADE 10 ============================

    'Word Processing': {
        'lessons': [
            (13, 30, 'Mail Merge Essentials',
             intro('Lesson 13 &middot; Mail Merge',
                   'Mail merge lets you produce many personalised letters, certificates or labels from one template plus a data source.')
             + '<h2>The five-step wizard</h2>'
             + steps([
                 'Open Word and start a new blank document.',
                 'Mailings tab &rarr; <strong>Start Mail Merge</strong> &rarr; Letters.',
                 '<strong>Select Recipients</strong> &rarr; Use an Existing List (Excel/Access).',
                 'Type your letter and use <strong>Insert Merge Field</strong> for names.',
                 '<strong>Finish &amp; Merge</strong> &rarr; Print or Edit Individual Documents.',
             ])
             + callout('info', 'fa-lightbulb', 'CAPS tip',
                       'Mail merge is regularly examined &mdash; you must know the difference between the <em>main document</em> and the <em>data source</em>.')),
            (14, 25, 'Tables of Contents &amp; Captions',
             intro('Lesson 14 &middot; Long Documents',
                   'Long documents need automatic structure — page numbers, captions and tables of contents.')
             + '<h2>Build a TOC in 3 clicks</h2>'
             + steps([
                 'Apply <strong>Heading 1</strong> and <strong>Heading 2</strong> styles to your headings.',
                 'Click where the TOC must go &rarr; References tab &rarr; <strong>Table of Contents</strong>.',
                 'Right-click the TOC &rarr; <strong>Update Field</strong> after adding new headings.',
             ])
             + '<h3>Captions for figures and tables</h3>'
             + steps([
                 'Right-click a picture &rarr; <strong>Insert Caption</strong>.',
                 'Choose label <em>Figure</em>, <em>Table</em> or create a new label.',
                 'Use References &rarr; <strong>Insert Table of Figures</strong> for an automatic list.',
             ])),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which tab is used to start a mail merge?',
             'options': ['Insert', 'Mailings', 'References', 'Review'],
             'correct_answer': 'Mailings',
             'explanation': 'All mail-merge commands live on the Mailings tab.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A mail merge needs two main components. Which pair?',
             'options': ['Header and footer', 'Main document and data source',
                         'Style and theme', 'Bookmark and hyperlink'],
             'correct_answer': 'Main document and data source',
             'explanation': 'The letter (main document) is merged with the recipient list (data source).'},
            {'question_type': 'multiple_choice',
             'question_text': 'To get an automatic Table of Contents you must first apply&hellip;',
             'options': ['Bullets', 'Heading styles', 'Page borders', 'Footnotes'],
             'correct_answer': 'Heading styles',
             'explanation': 'Word builds the TOC from text marked with Heading 1, 2, 3, etc.'},
            {'question_type': 'true_false',
             'question_text': 'After adding new headings you must update the Table of Contents manually.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Right-click the TOC &rarr; Update Field.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which shortcut prints the current document?',
             'options': [kbd('Ctrl', 'S'), kbd('Ctrl', 'P'), kbd('Ctrl', 'B'), kbd('Ctrl', 'N')],
             'correct_answer': kbd('Ctrl', 'P'),
             'explanation': 'Ctrl + P opens the Print pane.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each Word feature to its purpose.',
             'options': {
                 'column_a': ['Mail merge', 'Caption', 'TOC', 'Bookmark'],
                 'column_b': ['Personalised bulk letters',
                              'Label under a figure',
                              'Auto list of headings',
                              'Named location to jump to']
             },
             'correct_answer': {'Mail merge': 'Personalised bulk letters',
                                'Caption': 'Label under a figure',
                                'TOC': 'Auto list of headings',
                                'Bookmark': 'Named location to jump to'},
             'explanation': 'Each feature solves a different long-document problem.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these mail-merge steps from first to last.',
             'options': ['Finish &amp; Merge',
                         'Insert merge fields',
                         'Select recipients',
                         'Type the letter'],
             'correct_answer': ['Select recipients', 'Type the letter',
                                'Insert merge fields', 'Finish &amp; Merge'],
             'explanation': 'Pick recipients, write the letter, plug in fields, then merge.'},
            {'question_type': 'short_answer',
             'question_text': 'Name the file extension of a default Word 2016+ document.',
             'options': [], 'correct_answer': '.docx',
             'explanation': 'docx is the modern Open XML format.'},
        ],
    },

    'Spreadsheets': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'spreadsheet building',
                [
                    'Create a class marks workbook with names in column A and three test scores in B, C, D.',
                    'In column E use <code>=AVERAGE(B2:D2)</code> to find each learner\'s average.',
                    'In column F use <code>=IF(E2&gt;=50,"Pass","Fail")</code>.',
                    'Apply conditional formatting to highlight failing rows in red.',
                    'Insert a column chart of names vs averages and add a chart title.',
                ],
                'Lock formulas with <code>$</code> (e.g. <code>$B$2</code>) before copying so cell references do not shift.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'spreadsheets',
                [
                    {'icon': 'fa-coins', 'title': 'Personal budgets',
                     'body': 'Track income, expenses and savings each month.'},
                    {'icon': 'fa-store', 'title': 'Small business',
                     'body': 'Stock lists, invoices and VAT calculations.'},
                    {'icon': 'fa-chart-line', 'title': 'Data analysis',
                     'body': 'Charts and PivotTables uncover trends in big data.'},
                    {'icon': 'fa-school', 'title': 'School admin',
                     'body': 'Mark sheets, attendance registers and timetables.'},
                ],
                'Almost every modern office job expects basic Excel skills &mdash; absolute references, IF, SUM and charts are the foundation.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which symbol locks a cell reference?',
             'options': ['#', '@', '$', '&'], 'correct_answer': '$',
             'explanation': 'Dollar signs make a reference absolute, e.g. $A$1.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which function returns "Pass" when A1 is 50 or more?',
             'options': ['=PASSFAIL(A1)', '=IF(A1&gt;=50,"Pass","Fail")',
                         '=COUNT(A1,"Pass")', '=SUM(A1,"Pass")'],
             'correct_answer': '=IF(A1&gt;=50,"Pass","Fail")',
             'explanation': 'IF tests a condition and returns one of two values.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which feature highlights cells that meet a rule (e.g. fail marks)?',
             'options': ['Filter', 'Conditional formatting',
                         'Sort', 'Data validation'],
             'correct_answer': 'Conditional formatting',
             'explanation': 'Conditional formatting changes look based on cell value.'},
            {'question_type': 'true_false',
             'question_text': 'Copying =A1+B1 down one row becomes =A2+B2.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Relative references update when copied.'},
            {'question_type': 'multiple_choice',
             'question_text': '<code>=COUNTA(A1:A20)</code> counts&hellip;',
             'options': ['Only numbers', 'All non-empty cells',
                         'Only text', 'Only empty cells'],
             'correct_answer': 'All non-empty cells',
             'explanation': 'COUNTA counts cells that are not empty (text or numbers).'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each error to its meaning.',
             'options': {
                 'column_a': ['#DIV/0!', '#NAME?', '#REF!', '#####'],
                 'column_b': ['Divided by zero', 'Unknown function name',
                              'Cell reference deleted', 'Column too narrow']
             },
             'correct_answer': {'#DIV/0!': 'Divided by zero',
                                '#NAME?': 'Unknown function name',
                                '#REF!': 'Cell reference deleted',
                                '#####': 'Column too narrow'},
             'explanation': 'Recognising errors helps you debug formulas quickly.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these steps to make a chart.',
             'options': ['Add chart title and axis labels',
                         'Choose chart type from Insert tab',
                         'Select data including headings'],
             'correct_answer': ['Select data including headings',
                                'Choose chart type from Insert tab',
                                'Add chart title and axis labels'],
             'explanation': 'Select &rarr; Insert &rarr; Label.'},
            {'question_type': 'short_answer',
             'question_text': 'Which keyboard shortcut copies the selected cells?',
             'options': [], 'correct_answer': 'Ctrl+C',
             'explanation': 'Ctrl + C copies; Ctrl + V pastes.'},
        ],
    },

    'Presentations': {
        'lessons': [
            (6, 25, 'Practical Skills', practical_lesson(
                'PowerPoint design',
                [
                    'Create a 6-slide presentation about your favourite hobby.',
                    'Pick one <strong>theme</strong> from the Design tab and stay consistent.',
                    'Use the <strong>Slide Master</strong> to set fonts and add a logo.',
                    'Add at least one image, one shape and one icon.',
                    'Apply ONE transition style and ONE simple animation per slide.',
                    'Run the slideshow with ' + kbd('F5') + ' and check timing.',
                ],
                'Less is more &mdash; aim for 5-7 short bullets per slide, never paragraphs.')),
            (7, 20, 'Real-World Applications', application_lesson(
                'presentations',
                [
                    {'icon': 'fa-chalkboard-teacher', 'title': 'Lessons',
                     'body': 'Teachers use slides to teach new content with images and video.'},
                    {'icon': 'fa-handshake', 'title': 'Pitches',
                     'body': 'Entrepreneurs pitch ideas to investors with crisp slide decks.'},
                    {'icon': 'fa-bullhorn', 'title': 'Marketing',
                     'body': 'Companies present new products to clients and at trade shows.'},
                    {'icon': 'fa-graduation-cap', 'title': 'Oral exams',
                     'body': 'You will use slides to support your own oral assessments.'},
                ],
                'A great slide deck supports your voice &mdash; it should never replace it.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which view lets you change all slides at once?',
             'options': ['Normal', 'Slide Sorter', 'Slide Master', 'Reading'],
             'correct_answer': 'Slide Master',
             'explanation': 'The Slide Master controls the look of every slide.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which key starts the slideshow from slide 1?',
             'options': [kbd('Esc'), kbd('F5'), kbd('Tab'), kbd('Enter')],
             'correct_answer': kbd('F5'),
             'explanation': 'F5 starts from the beginning; Shift+F5 from the current slide.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A <em>transition</em> is&hellip;',
             'options': ['Movement of an object on a slide',
                         'The change between two slides',
                         'A type of chart',
                         'A speaker note'],
             'correct_answer': 'The change between two slides',
             'explanation': 'Transitions = between slides. Animations = within a slide.'},
            {'question_type': 'true_false',
             'question_text': 'Speaker notes are visible to the audience during the slideshow.',
             'options': ['True', 'False'], 'correct_answer': 'False',
             'explanation': 'Notes show only on the presenter\'s screen.'},
            {'question_type': 'multiple_choice',
             'question_text': 'What does the 6&times;6 rule recommend?',
             'options': ['6 fonts and 6 colours', '6 bullets, 6 words each',
                         '6 slides, 6 images', '6 animations per slide'],
             'correct_answer': '6 bullets, 6 words each',
             'explanation': 'Keep slides short and scannable.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each file extension to its meaning.',
             'options': {
                 'column_a': ['.pptx', '.ppsx', '.pdf', '.mp4'],
                 'column_b': ['Editable presentation', 'Self-running show',
                              'Read-only export', 'Recorded video']
             },
             'correct_answer': {'.pptx': 'Editable presentation',
                                '.ppsx': 'Self-running show',
                                '.pdf': 'Read-only export',
                                '.mp4': 'Recorded video'},
             'explanation': 'PowerPoint can save the same content in many formats.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Place these design steps in the best order.',
             'options': ['Add transitions and animations',
                         'Apply theme and master fonts',
                         'Plan content on paper'],
             'correct_answer': ['Plan content on paper',
                                'Apply theme and master fonts',
                                'Add transitions and animations'],
             'explanation': 'Plan &rarr; design &rarr; polish.'},
            {'question_type': 'short_answer',
             'question_text': 'Which tab contains Theme, Variants and Slide Size?',
             'options': [], 'correct_answer': 'Design',
             'explanation': 'The Design tab controls the overall look.'},
        ],
    },

    'Computer Hardware': {
        'lessons': [
            (6, 25, 'Practical Skills', practical_lesson(
                'hardware identification',
                [
                    'Open the case of a switched-off, unplugged desktop and identify the CPU, RAM, PSU, motherboard and storage drive.',
                    'Use Device Manager (Windows) to list every connected device.',
                    'Check Task Manager &rarr; Performance to see CPU, RAM and disk usage in real time.',
                    'Plug in a USB device and watch how it is detected and assigned a drive letter.',
                    'Run <code>msinfo32</code> to view a full system spec report.',
                ],
                'Always wear an anti-static wrist strap before touching internal components.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'hardware knowledge',
                [
                    {'icon': 'fa-screwdriver-wrench', 'title': 'PC technician',
                     'body': 'Diagnoses faulty parts and upgrades systems for clients.'},
                    {'icon': 'fa-server', 'title': 'IT support',
                     'body': 'Keeps office computers, printers and networks running.'},
                    {'icon': 'fa-microchip', 'title': 'Embedded engineer',
                     'body': 'Designs hardware for cars, fridges and smart devices.'},
                    {'icon': 'fa-recycle', 'title': 'E-waste',
                     'body': 'Old hardware must be recycled responsibly &mdash; not dumped.'},
                ],
                'Choosing the right hardware for the job saves money and energy &mdash; you would not buy a gaming PC just to send emails.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which component is called the brain of the computer?',
             'options': ['RAM', 'CPU', 'GPU', 'PSU'], 'correct_answer': 'CPU',
             'explanation': 'The Central Processing Unit executes instructions.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which type of memory is volatile?',
             'options': ['ROM', 'SSD', 'RAM', 'Hard drive'],
             'correct_answer': 'RAM',
             'explanation': 'RAM loses its contents when power is switched off.'},
            {'question_type': 'multiple_choice',
             'question_text': '1 GB equals about how many MB?',
             'options': ['10', '100', '1 000', '1 000 000'],
             'correct_answer': '1 000',
             'explanation': '1 GB = 1024 MB (often rounded to 1 000).'},
            {'question_type': 'true_false',
             'question_text': 'An SSD has no moving parts and is faster than an HDD.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Solid-state drives use flash memory, no spinning disks.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which port is most commonly used to connect a modern monitor?',
             'options': ['VGA', 'PS/2', 'HDMI', 'Parallel'],
             'correct_answer': 'HDMI',
             'explanation': 'HDMI carries high-definition video and audio.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each device to its category.',
             'options': {
                 'column_a': ['Keyboard', 'Monitor', 'Printer', 'Touch screen'],
                 'column_b': ['Input', 'Output', 'Output', 'Both']
             },
             'correct_answer': {'Keyboard': 'Input', 'Monitor': 'Output',
                                'Printer': 'Output', 'Touch screen': 'Both'},
             'explanation': 'A touch screen displays AND accepts input.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these storage media from fastest to slowest.',
             'options': ['Magnetic tape', 'SSD', 'HDD', 'RAM'],
             'correct_answer': ['RAM', 'SSD', 'HDD', 'Magnetic tape'],
             'explanation': 'RAM &gt; SSD &gt; HDD &gt; tape, by access time.'},
            {'question_type': 'short_answer',
             'question_text': 'What does PSU stand for?',
             'options': [], 'correct_answer': 'Power Supply Unit',
             'explanation': 'The PSU converts AC mains power to DC for the PC.'},
        ],
    },

    'Networks & Internet': {
        'lessons': [
            (6, 25, 'Practical Skills', practical_lesson(
                'connecting and testing networks',
                [
                    'Find your computer\'s IP address with <code>ipconfig</code> (Windows) or <code>ifconfig</code> (Linux/macOS).',
                    'Use <code>ping google.com</code> to test internet reachability.',
                    'Run <code>tracert google.com</code> and count the hops.',
                    'Open the router admin page (often <code>192.168.0.1</code>) and view connected devices.',
                    'Compare a download speed test on Wi-Fi vs cable.',
                ],
                'Disconnect from public Wi-Fi when you are not using it &mdash; open networks are a security risk.')),
            (7, 20, 'Real-World Applications', application_lesson(
                'networks and the internet',
                [
                    {'icon': 'fa-cloud', 'title': 'Cloud apps',
                     'body': 'Google Docs, Gmail and WhatsApp run on networks 24/7.'},
                    {'icon': 'fa-video', 'title': 'Streaming',
                     'body': 'Netflix and YouTube need fast, low-latency internet.'},
                    {'icon': 'fa-money-check-dollar', 'title': 'Online banking',
                     'body': 'Encrypted connections (HTTPS) keep your money safe.'},
                    {'icon': 'fa-house-laptop', 'title': 'Remote work',
                     'body': 'VPNs let employees work safely from home.'},
                ],
                'Almost every modern app depends on the internet &mdash; even offline-looking ones sync data in the background.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which device routes traffic between networks?',
             'options': ['Switch', 'Hub', 'Router', 'Repeater'],
             'correct_answer': 'Router',
             'explanation': 'A router decides the best path to forward packets.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which acronym means a Local Area Network?',
             'options': ['WAN', 'LAN', 'MAN', 'PAN'], 'correct_answer': 'LAN',
             'explanation': 'LAN covers a small area such as a home or school.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which command tests if a server can be reached?',
             'options': ['ping', 'cd', 'dir', 'echo'], 'correct_answer': 'ping',
             'explanation': 'Ping sends ICMP echo requests and shows reply time.'},
            {'question_type': 'true_false',
             'question_text': 'HTTPS encrypts traffic between your browser and the website.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'The "S" stands for secure (TLS encryption).'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which network speed unit is the largest?',
             'options': ['Kbps', 'Mbps', 'Gbps', 'bps'],
             'correct_answer': 'Gbps',
             'explanation': '1 Gbps = 1000 Mbps = 1 000 000 Kbps.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each acronym to its meaning.',
             'options': {
                 'column_a': ['URL', 'ISP', 'DNS', 'IP'],
                 'column_b': ['Web address', 'Provides internet access',
                              'Translates names to IPs', 'Unique device address']
             },
             'correct_answer': {'URL': 'Web address',
                                'ISP': 'Provides internet access',
                                'DNS': 'Translates names to IPs',
                                'IP': 'Unique device address'},
             'explanation': 'These four are core building blocks of the internet.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Put these network ranges in order from smallest to largest.',
             'options': ['MAN', 'PAN', 'WAN', 'LAN'],
             'correct_answer': ['PAN', 'LAN', 'MAN', 'WAN'],
             'explanation': 'Personal &rarr; Local &rarr; Metropolitan &rarr; Wide.'},
            {'question_type': 'short_answer',
             'question_text': 'Which protocol delivers email between mail servers?',
             'options': [], 'correct_answer': 'SMTP',
             'explanation': 'SMTP = Simple Mail Transfer Protocol.'},
        ],
    },

    'Information Management': {
        'lessons': [
            (6, 25, 'Practical Skills', practical_lesson(
                'finding and judging information',
                [
                    'Pick a research question (e.g. "Why is the ozone layer recovering?").',
                    'Run a Google search using two <strong>quotation phrases</strong> and the <code>site:</code> operator.',
                    'Open three sources and write down their author, date and domain.',
                    'Apply the <strong>CRAAP test</strong> (Currency, Relevance, Authority, Accuracy, Purpose).',
                    'Save findings in a clearly named folder &mdash; <code>research/topic_yyyymmdd</code>.',
                ],
                'Always note your sources as you go &mdash; tracking them down later wastes hours.')),
            (7, 20, 'Real-World Applications', application_lesson(
                'information management',
                [
                    {'icon': 'fa-newspaper', 'title': 'Journalism',
                     'body': 'Reporters verify multiple sources before publishing.'},
                    {'icon': 'fa-flask', 'title': 'Research',
                     'body': 'Scientists rely on peer-reviewed databases.'},
                    {'icon': 'fa-gavel', 'title': 'Law',
                     'body': 'Lawyers must cite cases accurately.'},
                    {'icon': 'fa-shield-halved', 'title': 'Fact-checkers',
                     'body': 'Combat fake news on social media.'},
                ],
                'Good information management is what separates knowledge from rumour.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'What does the C in CRAAP stand for?',
             'options': ['Clarity', 'Currency', 'Citation', 'Copyright'],
             'correct_answer': 'Currency',
             'explanation': 'Currency means how recent the information is.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which Google operator searches one specific website?',
             'options': ['file:', 'site:', 'web:', 'host:'],
             'correct_answer': 'site:',
             'explanation': 'Example: <code>site:gov.za matric results</code>.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which is the most reliable source for academic facts?',
             'options': ['A random blog', 'A peer-reviewed journal',
                         'A WhatsApp forward', 'A Wikipedia talk page'],
             'correct_answer': 'A peer-reviewed journal',
             'explanation': 'Peer review checks claims before publication.'},
            {'question_type': 'true_false',
             'question_text': 'Copy-pasting text without citing the author is plagiarism.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Always credit the original author.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Putting words in quotes ("solar power") tells Google to&hellip;',
             'options': ['Ignore them', 'Find that exact phrase',
                         'Translate them', 'Search images only'],
             'correct_answer': 'Find that exact phrase',
             'explanation': 'Quotes force exact-phrase matching.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each step of the research process.',
             'options': {
                 'column_a': ['Plan', 'Find', 'Process', 'Present'],
                 'column_b': ['Decide what to search for',
                              'Locate sources',
                              'Select and summarise',
                              'Share findings clearly']
             },
             'correct_answer': {'Plan': 'Decide what to search for',
                                'Find': 'Locate sources',
                                'Process': 'Select and summarise',
                                'Present': 'Share findings clearly'},
             'explanation': 'Plan &rarr; Find &rarr; Process &rarr; Present.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these citation parts as they appear in APA style.',
             'options': ['Year', 'Author surname', 'Page'],
             'correct_answer': ['Author surname', 'Year', 'Page'],
             'explanation': 'APA in-text: (Author, Year, p. Page).'},
            {'question_type': 'short_answer',
             'question_text': 'Name one peer-reviewed academic search engine.',
             'options': [], 'correct_answer': 'Google Scholar',
             'explanation': 'Google Scholar, JSTOR and Scopus are common ones.'},
        ],
    },

    # ============================ GRADE 11 ============================

    'Advanced Word Processing': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'professional document layout',
                [
                    'Build a 6-page report with cover page, automatic TOC and footer page numbers.',
                    'Create and apply a custom <strong>Style</strong> for body text and headings.',
                    'Insert a section break and switch to landscape for a wide table.',
                    'Add a footnote and a citation using References &rarr; Insert Citation.',
                    'Track changes while a partner reviews your document.',
                ],
                'Use Styles, never manual formatting &mdash; one click later updates the whole document.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'advanced word processing',
                [
                    {'icon': 'fa-file-contract', 'title': 'Contracts',
                     'body': 'Lawyers use Track Changes to negotiate clauses.'},
                    {'icon': 'fa-book', 'title': 'Authors',
                     'body': 'Long-document features power 300-page books.'},
                    {'icon': 'fa-envelopes-bulk', 'title': 'Bulk mail',
                     'body': 'Mail merge for newsletters and certificates.'},
                    {'icon': 'fa-file-shield', 'title': 'Compliance',
                     'body': 'Permission and protection lock final versions.'},
                ],
                'Mastering Styles, Sections and References will put you ahead in any office job.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which feature lets two reviewers see who changed what?',
             'options': ['Track Changes', 'Compare', 'Combine', 'Restrict Editing'],
             'correct_answer': 'Track Changes',
             'explanation': 'Found on the Review tab.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A <strong>Style</strong> in Word is&hellip;',
             'options': ['A clipart picture',
                         'A saved set of formatting options',
                         'An animation',
                         'A protection password'],
             'correct_answer': 'A saved set of formatting options',
             'explanation': 'Styles bundle font, size, colour and spacing.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which break starts new page numbering or a new orientation?',
             'options': ['Page break', 'Column break',
                         'Section break', 'Text wrap break'],
             'correct_answer': 'Section break',
             'explanation': 'Sections control headers, footers and orientation.'},
            {'question_type': 'true_false',
             'question_text': 'Footnotes appear at the bottom of the page; endnotes at the end of the document.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Both add citations &mdash; choose where to place them.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which references feature inserts a numbered list of figures?',
             'options': ['Index', 'Bibliography',
                         'Table of Figures', 'Cross-reference'],
             'correct_answer': 'Table of Figures',
             'explanation': 'It is generated from your captions.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each Word feature to its tab.',
             'options': {
                 'column_a': ['Mail Merge', 'Macros', 'Citations', 'Find &amp; Replace'],
                 'column_b': ['Mailings', 'View', 'References', 'Home']
             },
             'correct_answer': {'Mail Merge': 'Mailings', 'Macros': 'View',
                                'Citations': 'References', 'Find &amp; Replace': 'Home'},
             'explanation': 'Knowing which tab to look on saves time.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these long-document steps.',
             'options': ['Insert TOC',
                         'Apply Heading 1 / 2 styles',
                         'Update TOC after edits'],
             'correct_answer': ['Apply Heading 1 / 2 styles',
                                'Insert TOC',
                                'Update TOC after edits'],
             'explanation': 'Style &rarr; insert &rarr; refresh.'},
            {'question_type': 'short_answer',
             'question_text': 'Which shortcut applies the Heading 1 style?',
             'options': [], 'correct_answer': 'Ctrl+Alt+1',
             'explanation': 'Ctrl+Alt+1 / 2 / 3 apply the first three heading levels.'},
        ],
    },

    'Advanced Spreadsheets': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'advanced Excel formulas',
                [
                    'Build a marks book with VLOOKUP to fetch each learner\'s class from a separate sheet.',
                    'Use nested IF or IFS to award symbols A&ndash;F.',
                    'Use COUNTIF and SUMIF to summarise pass rates per subject.',
                    'Insert a PivotTable to compare averages per class.',
                    'Protect a worksheet and lock specific cells with a password.',
                ],
                'When a formula breaks, click <strong>Formulas &rarr; Evaluate Formula</strong> to step through it.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'advanced spreadsheets',
                [
                    {'icon': 'fa-coins', 'title': 'Finance',
                     'body': 'Loan repayment, interest and budgeting models.'},
                    {'icon': 'fa-chart-pie', 'title': 'Business intelligence',
                     'body': 'PivotTables turn raw data into board-room insights.'},
                    {'icon': 'fa-truck-fast', 'title': 'Logistics',
                     'body': 'VLOOKUP feeds delivery routes from a master list.'},
                    {'icon': 'fa-flask-vial', 'title': 'Science',
                     'body': 'Researchers chart experiment results.'},
                ],
                'Excel skills are some of the most in-demand on every job board worldwide.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which function looks up a value in a table and returns a matching value?',
             'options': ['SUMIF', 'VLOOKUP', 'INDEX', 'COUNT'],
             'correct_answer': 'VLOOKUP',
             'explanation': 'VLOOKUP searches the leftmost column.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which result does <code>=SUMIF(A1:A5,"&gt;10")</code> give if A1:A5 = 5,12,8,15,3?',
             'options': ['12', '15', '27', '20'], 'correct_answer': '27',
             'explanation': '12 + 15 = 27 (only values greater than 10).'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which feature summarises large data with rows, columns and values?',
             'options': ['PivotTable', 'AutoFilter', 'Macro', 'Goal Seek'],
             'correct_answer': 'PivotTable',
             'explanation': 'PivotTables aggregate data interactively.'},
            {'question_type': 'true_false',
             'question_text': '<code>=A$1</code> locks only the row, not the column.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'A mixed reference: column changes, row stays.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Goal Seek answers the question:',
             'options': ['"What if I add 10%?"',
                         '"What input gives this output?"',
                         '"How many records match?"',
                         '"What font is best?"'],
             'correct_answer': '"What input gives this output?"',
             'explanation': 'Goal Seek changes one input until a target value is reached.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each function to what it returns.',
             'options': {
                 'column_a': ['IFS', 'COUNTIF', 'CONCAT', 'NOW'],
                 'column_b': ['First true result',
                              'Cells matching a rule',
                              'Joined text',
                              'Current date and time']
             },
             'correct_answer': {'IFS': 'First true result',
                                'COUNTIF': 'Cells matching a rule',
                                'CONCAT': 'Joined text',
                                'NOW': 'Current date and time'},
             'explanation': 'Each handles a different common need.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order steps to build a PivotTable.',
             'options': ['Drag fields into Rows / Values',
                         'Insert tab &rarr; PivotTable',
                         'Select the source data range'],
             'correct_answer': ['Select the source data range',
                                'Insert tab &rarr; PivotTable',
                                'Drag fields into Rows / Values'],
             'explanation': 'Select &rarr; Insert &rarr; Drop.'},
            {'question_type': 'short_answer',
             'question_text': 'Which function returns todays date with no time?',
             'options': [], 'correct_answer': 'TODAY',
             'explanation': '=TODAY() updates each time the workbook opens.'},
        ],
    },

    'Database Concepts': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'building a small database',
                [
                    'In Access, create a new blank database called <code>school.accdb</code>.',
                    'Add a table <strong>Learners</strong> with fields LearnerID (PK), Name, Grade, DOB.',
                    'Set Grade as a Number with a Validation Rule <code>Between 8 And 12</code>.',
                    'Build a Form so users can capture new learners.',
                    'Build a Query that lists Grade 11 learners ordered by Name.',
                    'Build a Report that prints all learners grouped by Grade.',
                ],
                'Always set a Primary Key &mdash; it stops duplicates and lets tables relate.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'databases',
                [
                    {'icon': 'fa-hospital', 'title': 'Healthcare',
                     'body': 'Patient records, prescriptions and bookings.'},
                    {'icon': 'fa-bank', 'title': 'Banking',
                     'body': 'Every transaction is a database write.'},
                    {'icon': 'fa-people-group', 'title': 'Government',
                     'body': 'IDs, taxes and grants are all tracked in databases.'},
                    {'icon': 'fa-cart-shopping', 'title': 'E-commerce',
                     'body': 'Products, customers and orders are linked tables.'},
                ],
                'Every meaningful app has a database behind it &mdash; learning these concepts opens many doors.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'A field that uniquely identifies each record is called&hellip;',
             'options': ['Foreign key', 'Primary key', 'Index', 'Lookup'],
             'correct_answer': 'Primary key',
             'explanation': 'Each table needs exactly one primary key.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which data type would best store a price like R49.95?',
             'options': ['Text', 'Number (Integer)', 'Currency', 'Yes/No'],
             'correct_answer': 'Currency',
             'explanation': 'Currency stores money with two decimal places and a symbol.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A query in Access is mainly used to&hellip;',
             'options': ['Print invoices',
                         'Ask questions about the data',
                         'Capture new records',
                         'Backup the database'],
             'correct_answer': 'Ask questions about the data',
             'explanation': 'Queries filter, sort and combine data.'},
            {'question_type': 'true_false',
             'question_text': 'Reports are designed for screen entry, while forms are designed for printing.',
             'options': ['True', 'False'], 'correct_answer': 'False',
             'explanation': 'It is the other way round &mdash; forms = entry, reports = print.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A validation rule like <code>&gt;0</code> is used to&hellip;',
             'options': ['Encrypt the field',
                         'Reject invalid input',
                         'Format text',
                         'Index the field'],
             'correct_answer': 'Reject invalid input',
             'explanation': 'Validation rules stop bad data at entry time.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each Access object to its purpose.',
             'options': {
                 'column_a': ['Table', 'Form', 'Query', 'Report'],
                 'column_b': ['Stores data',
                              'Captures data',
                              'Asks a question',
                              'Prints data']
             },
             'correct_answer': {'Table': 'Stores data', 'Form': 'Captures data',
                                'Query': 'Asks a question', 'Report': 'Prints data'},
             'explanation': 'These four are the building blocks of every database.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these database design steps.',
             'options': ['Add forms / queries / reports',
                         'Decide what data to store',
                         'Design tables and relationships'],
             'correct_answer': ['Decide what data to store',
                                'Design tables and relationships',
                                'Add forms / queries / reports'],
             'explanation': 'Plan &rarr; structure &rarr; build interface.'},
            {'question_type': 'short_answer',
             'question_text': 'What does SQL stand for?',
             'options': [], 'correct_answer': 'Structured Query Language',
             'explanation': 'SQL is the standard language for relational databases.'},
        ],
    },

    'Advanced Presentations': {
        'lessons': [
            (6, 25, 'Practical Skills', practical_lesson(
                'multimedia presentations',
                [
                    'Insert a SmartArt graphic and convert a bullet list into it.',
                    'Embed a short video and trim it inside PowerPoint.',
                    'Record a voice-over for one slide.',
                    'Add a hyperlink to jump from a menu slide to a content slide.',
                    'Save your slideshow as a self-running <code>.ppsx</code> file.',
                ],
                'Always test multimedia on the actual presentation computer the day before.')),
            (7, 20, 'Real-World Applications', application_lesson(
                'advanced presentations',
                [
                    {'icon': 'fa-video', 'title': 'E-learning',
                     'body': 'Recorded slides become online courses.'},
                    {'icon': 'fa-store', 'title': 'Trade shows',
                     'body': 'Self-running kiosks loop product demos.'},
                    {'icon': 'fa-microphone', 'title': 'Podcasts',
                     'body': 'Audio + slides become picture podcasts.'},
                    {'icon': 'fa-handshake', 'title': 'Sales',
                     'body': 'Branded decks pitch products to clients.'},
                ],
                'A polished, well-rehearsed presentation can win jobs, contracts and investors.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which file extension is a self-running show?',
             'options': ['.pptx', '.ppsx', '.pdf', '.docx'],
             'correct_answer': '.ppsx',
             'explanation': '.ppsx opens directly in slideshow mode.'},
            {'question_type': 'multiple_choice',
             'question_text': 'SmartArt is best used for&hellip;',
             'options': ['Storing photos',
                         'Showing relationships visually',
                         'Editing video',
                         'Running macros'],
             'correct_answer': 'Showing relationships visually',
             'explanation': 'SmartArt turns lists into diagrams.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A hyperlink in PowerPoint can link to&hellip;',
             'options': ['Only the next slide',
                         'Only the internet',
                         'Slides, files, websites and email',
                         'Only PowerPoint files'],
             'correct_answer': 'Slides, files, websites and email',
             'explanation': 'Insert &rarr; Hyperlink offers all four targets.'},
            {'question_type': 'true_false',
             'question_text': 'Embedded videos make the file size larger than linked videos.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Embedding stores the video inside the .pptx.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which view shows speaker notes plus the next slide?',
             'options': ['Normal', 'Reading', 'Presenter', 'Slide Sorter'],
             'correct_answer': 'Presenter',
             'explanation': 'Presenter View needs two displays.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each animation type to its effect.',
             'options': {
                 'column_a': ['Entrance', 'Emphasis', 'Exit', 'Motion path'],
                 'column_b': ['Object appears',
                              'Object pulses or grows',
                              'Object disappears',
                              'Object moves along a line']
             },
             'correct_answer': {'Entrance': 'Object appears',
                                'Emphasis': 'Object pulses or grows',
                                'Exit': 'Object disappears',
                                'Motion path': 'Object moves along a line'},
             'explanation': 'Animations come in four families.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these tasks for a polished kiosk slideshow.',
             'options': ['Save as .ppsx',
                         'Set up Show &rarr; Loop continuously',
                         'Add timed slide transitions'],
             'correct_answer': ['Add timed slide transitions',
                                'Set up Show &rarr; Loop continuously',
                                'Save as .ppsx'],
             'explanation': 'Timing first, then loop, then save.'},
            {'question_type': 'short_answer',
             'question_text': 'Which shortcut starts the slideshow from the current slide?',
             'options': [], 'correct_answer': 'Shift+F5',
             'explanation': 'Shift + F5 begins from where you are; F5 starts at slide 1.'},
        ],
    },

    'System Software': {
        'lessons': [
            (6, 25, 'Practical Skills', practical_lesson(
                'using the operating system',
                [
                    'Open <strong>Task Manager</strong> and end a frozen application.',
                    'Use <strong>Disk Cleanup</strong> to free space.',
                    'Schedule a backup with <strong>File History</strong>.',
                    'Install a free utility from the Microsoft Store.',
                    'Create and switch to a new user account.',
                ],
                'Restart before installing or uninstalling &mdash; many issues vanish after a fresh boot.')),
            (7, 20, 'Real-World Applications', application_lesson(
                'system software',
                [
                    {'icon': 'fa-mobile-screen', 'title': 'Smartphones',
                     'body': 'Android and iOS are mobile operating systems.'},
                    {'icon': 'fa-server', 'title': 'Servers',
                     'body': 'Linux runs the majority of internet servers.'},
                    {'icon': 'fa-car', 'title': 'Cars',
                     'body': 'Modern cars run real-time operating systems.'},
                    {'icon': 'fa-tv', 'title': 'Smart TVs',
                     'body': 'webOS, Tizen and Android TV power your screen.'},
                ],
                'An OS is everywhere &mdash; if it has a chip, it has system software.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which is NOT system software?',
             'options': ['Windows 11', 'Microsoft Word', 'Linux', 'Device driver'],
             'correct_answer': 'Microsoft Word',
             'explanation': 'Word is application software.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A device driver is software that&hellip;',
             'options': ['Browses the web',
                         'Lets the OS talk to a hardware device',
                         'Plays music',
                         'Creates spreadsheets'],
             'correct_answer': 'Lets the OS talk to a hardware device',
             'explanation': 'No driver, no working device.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which utility shows running processes and CPU use?',
             'options': ['Notepad', 'Task Manager', 'Calculator', 'Paint'],
             'correct_answer': 'Task Manager',
             'explanation': 'Press Ctrl + Shift + Esc.'},
            {'question_type': 'true_false',
             'question_text': 'Linux is a free, open-source operating system.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Anyone can use, study and change the source code.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which file system does modern Windows use by default?',
             'options': ['FAT16', 'FAT32', 'NTFS', 'EXT4'],
             'correct_answer': 'NTFS',
             'explanation': 'NTFS supports large files, security and journaling.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each OS to its main use.',
             'options': {
                 'column_a': ['Windows', 'macOS', 'Android', 'Linux'],
                 'column_b': ['Most desktop PCs',
                              'Apple Macs',
                              'Most smartphones',
                              'Most servers']
             },
             'correct_answer': {'Windows': 'Most desktop PCs',
                                'macOS': 'Apple Macs',
                                'Android': 'Most smartphones',
                                'Linux': 'Most servers'},
             'explanation': 'Each OS dominates a different niche.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order the boot sequence.',
             'options': ['OS loads', 'POST hardware check', 'BIOS / UEFI starts'],
             'correct_answer': ['BIOS / UEFI starts', 'POST hardware check', 'OS loads'],
             'explanation': 'Firmware &rarr; self-test &rarr; OS.'},
            {'question_type': 'short_answer',
             'question_text': 'Name one type of utility software.',
             'options': [], 'correct_answer': 'antivirus',
             'explanation': 'Antivirus, backup, file compression, defragmenter, etc.'},
        ],
    },

    'Internet & Social Implications': {
        'lessons': [
            (6, 25, 'Practical Skills', practical_lesson(
                'staying safe online',
                [
                    'Set a strong unique password and store it in a password manager.',
                    'Turn on <strong>two-factor authentication</strong> for your email.',
                    'Review your social-media privacy settings.',
                    'Spot a phishing email by checking sender, links and tone.',
                    'Report a fake account to the platform.',
                ],
                'A password manager + 2FA stops the vast majority of account hijacks.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'internet and society',
                [
                    {'icon': 'fa-shield-halved', 'title': 'Cyber-security analyst',
                     'body': 'Defends companies from hackers.'},
                    {'icon': 'fa-laptop-medical', 'title': 'Telemedicine',
                     'body': 'Doctors consult patients remotely via secure video.'},
                    {'icon': 'fa-school', 'title': 'Online learning',
                     'body': 'Whole degrees can be earned via the internet.'},
                    {'icon': 'fa-balance-scale', 'title': 'Cyber-law',
                     'body': 'Lawyers handle online crime and privacy cases.'},
                ],
                'The internet has reshaped almost every industry &mdash; the rules and laws are still catching up.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Phishing is a kind of&hellip;',
             'options': ['Malware', 'Social engineering attack',
                         'Backup method', 'Network protocol'],
             'correct_answer': 'Social engineering attack',
             'explanation': 'It tricks the user into revealing data.'},
            {'question_type': 'multiple_choice',
             'question_text': '2FA most often combines a password with&hellip;',
             'options': ['Another password',
                         'A code from your phone',
                         'A lucky guess',
                         'Your address'],
             'correct_answer': 'A code from your phone',
             'explanation': 'Something you know + something you have.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A digital footprint is&hellip;',
             'options': ['Your typing speed',
                         'The data trail you leave online',
                         'A computer virus',
                         'A server log file'],
             'correct_answer': 'The data trail you leave online',
             'explanation': 'Posts, likes, searches all leave a trace.'},
            {'question_type': 'true_false',
             'question_text': 'Public Wi-Fi without a password is a security risk.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Anyone on the network can sniff traffic.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which act protects personal information in South Africa?',
             'options': ['POPIA', 'BBBEE', 'NCA', 'COIDA'],
             'correct_answer': 'POPIA',
             'explanation': 'Protection of Personal Information Act, 2013.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each threat to its meaning.',
             'options': {
                 'column_a': ['Virus', 'Worm', 'Ransomware', 'Spyware'],
                 'column_b': ['Attaches to a host file',
                              'Spreads on its own across networks',
                              'Encrypts files for money',
                              'Secretly watches the user']
             },
             'correct_answer': {'Virus': 'Attaches to a host file',
                                'Worm': 'Spreads on its own across networks',
                                'Ransomware': 'Encrypts files for money',
                                'Spyware': 'Secretly watches the user'},
             'explanation': 'Knowing the difference helps you defend appropriately.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these password practices from worst to best.',
             'options': ['Same password everywhere',
                         'Unique password + 2FA in a manager',
                         'Strong unique password per site'],
             'correct_answer': ['Same password everywhere',
                                'Strong unique password per site',
                                'Unique password + 2FA in a manager'],
             'explanation': 'Always layer your defences.'},
            {'question_type': 'short_answer',
             'question_text': 'What does VPN stand for?',
             'options': [], 'correct_answer': 'Virtual Private Network',
             'explanation': 'A VPN encrypts your traffic and hides your IP.'},
        ],
    },

    # ============================ GRADE 12 ============================

    'Integrated Document Handling': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'integrating Office apps',
                [
                    'In Excel build a small budget table.',
                    'Copy the table into Word using <strong>Paste Special &rarr; Link</strong>.',
                    'Update a value in Excel and refresh the Word document &mdash; the figure must change.',
                    'Embed (not link) the same chart into a PowerPoint slide.',
                    'Compare file sizes of linked vs embedded versions.',
                ],
                'Linking saves space; embedding makes the file portable. Choose based on whether the source file will move.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'integrated documents',
                [
                    {'icon': 'fa-file-invoice-dollar', 'title': 'Quotations',
                     'body': 'Word quote pulls live prices from Excel.'},
                    {'icon': 'fa-chart-line', 'title': 'Annual reports',
                     'body': 'Word report links to Excel charts that update automatically.'},
                    {'icon': 'fa-display', 'title': 'Live dashboards',
                     'body': 'PowerPoint slides update as the underlying data changes.'},
                    {'icon': 'fa-database', 'title': 'Mail-merge from DB',
                     'body': 'Word certificates pulled directly from an Access query.'},
                ],
                'Integration removes copy-paste mistakes and saves hours of repetitive work.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which paste option keeps a live link to the Excel source?',
             'options': ['Paste', 'Paste Special &rarr; Link', 'Paste as picture',
                         'Paste keep text only'],
             'correct_answer': 'Paste Special &rarr; Link',
             'explanation': 'A linked object updates when the source changes.'},
            {'question_type': 'true_false',
             'question_text': 'An embedded chart updates automatically when the source workbook changes.',
             'options': ['True', 'False'], 'correct_answer': 'False',
             'explanation': 'Embedded copies are independent of the source.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which acronym describes Office object linking and embedding?',
             'options': ['OLE', 'XML', 'HTML', 'CSS'], 'correct_answer': 'OLE',
             'explanation': 'OLE = Object Linking and Embedding.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Mail merge data sources can be&hellip;',
             'options': ['Only Excel files',
                         'Excel, Access, Outlook contacts and more',
                         'Only typed inside Word',
                         'Only CSV files'],
             'correct_answer': 'Excel, Access, Outlook contacts and more',
             'explanation': 'Word accepts many sources via Mailings &rarr; Select Recipients.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A PivotTable can be created from data in&hellip;',
             'options': ['Only the same workbook',
                         'External sources too (Access, CSV, etc.)',
                         'Only PowerPoint',
                         'Only Outlook'],
             'correct_answer': 'External sources too (Access, CSV, etc.)',
             'explanation': 'Use Get &amp; Transform / Power Query.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each integration choice to its best use.',
             'options': {
                 'column_a': ['Linked', 'Embedded', 'Picture', 'Hyperlink'],
                 'column_b': ['Auto-updates from source',
                              'Travel with the file',
                              'No editing needed',
                              'Open another file on demand']
             },
             'correct_answer': {'Linked': 'Auto-updates from source',
                                'Embedded': 'Travel with the file',
                                'Picture': 'No editing needed',
                                'Hyperlink': 'Open another file on demand'},
             'explanation': 'Each style has trade-offs in size and freshness.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these mail-merge integration steps.',
             'options': ['Insert merge fields in the letter',
                         'Connect Word letter to Excel data',
                         'Finish &amp; merge to printer'],
             'correct_answer': ['Connect Word letter to Excel data',
                                'Insert merge fields in the letter',
                                'Finish &amp; merge to printer'],
             'explanation': 'Connect &rarr; insert &rarr; merge.'},
            {'question_type': 'short_answer',
             'question_text': 'Which file format is best for sharing a final read-only report?',
             'options': [], 'correct_answer': 'PDF',
             'explanation': 'PDF preserves layout and is read-only by default.'},
        ],
    },

    'Advanced Spreadsheet Functions': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'powerful Excel functions',
                [
                    'Build an order sheet using INDEX + MATCH instead of VLOOKUP.',
                    'Add an IFERROR wrapper so missing values show "&mdash;" instead of #N/A.',
                    'Use TEXT(value,"R#,##0.00") to format an inline currency value.',
                    'Use SUMPRODUCT to count rows that meet two conditions.',
                    'Record a Macro that formats a sales report in one click.',
                ],
                'INDEX + MATCH is faster and more flexible than VLOOKUP &mdash; learn it well for your PAT.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'advanced spreadsheet functions',
                [
                    {'icon': 'fa-coins', 'title': 'Accountants',
                     'body': 'Live tax and finance models.'},
                    {'icon': 'fa-chart-bar', 'title': 'Data analysts',
                     'body': 'Cleanse, aggregate and visualise data.'},
                    {'icon': 'fa-dna', 'title': 'Healthcare',
                     'body': 'Track patient outcomes across many spreadsheets.'},
                    {'icon': 'fa-truck', 'title': 'Supply chain',
                     'body': 'Optimise stock levels and reorder points.'},
                ],
                'Powerful functions turn Excel into a mini-database engine.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which combo is more flexible than VLOOKUP?',
             'options': ['SUM + IF', 'INDEX + MATCH', 'COUNT + LEN', 'IF + IF'],
             'correct_answer': 'INDEX + MATCH',
             'explanation': 'It can look both left and right.'},
            {'question_type': 'multiple_choice',
             'question_text': 'IFERROR(formula, "n/a") returns "n/a" when&hellip;',
             'options': ['The formula is correct',
                         'The formula returns any error',
                         'A cell is empty',
                         'Excel is offline'],
             'correct_answer': 'The formula returns any error',
             'explanation': 'IFERROR catches #N/A, #DIV/0!, #VALUE!, etc.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A Macro is&hellip;',
             'options': ['A type of chart',
                         'A recorded set of actions you can replay',
                         'A worksheet protection',
                         'A pivot field'],
             'correct_answer': 'A recorded set of actions you can replay',
             'explanation': 'Macros automate repetitive tasks.'},
            {'question_type': 'true_false',
             'question_text': 'Macros are stored in xlsx files only.',
             'options': ['True', 'False'], 'correct_answer': 'False',
             'explanation': 'Macros need .xlsm or .xlsb files.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which function joins text values with a separator?',
             'options': ['JOIN', 'TEXTJOIN', 'CONCAT', 'MERGE'],
             'correct_answer': 'TEXTJOIN',
             'explanation': 'TEXTJOIN supports a delimiter and ignores empties.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each function to its task.',
             'options': {
                 'column_a': ['LEFT', 'LEN', 'TRIM', 'PROPER'],
                 'column_b': ['First N chars', 'Length of text',
                              'Strips extra spaces', 'Title-Case Each Word']
             },
             'correct_answer': {'LEFT': 'First N chars', 'LEN': 'Length of text',
                                'TRIM': 'Strips extra spaces',
                                'PROPER': 'Title-Case Each Word'},
             'explanation': 'These four are the workhorse text functions.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order steps to record a macro.',
             'options': ['Stop recording',
                         'Perform actions',
                         'Click Record Macro and name it'],
             'correct_answer': ['Click Record Macro and name it',
                                'Perform actions',
                                'Stop recording'],
             'explanation': 'Start &rarr; do &rarr; stop.'},
            {'question_type': 'short_answer',
             'question_text': 'Which file extension keeps macros enabled?',
             'options': [], 'correct_answer': '.xlsm',
             'explanation': '.xlsm = Excel Macro-Enabled Workbook.'},
        ],
    },

    'Advanced Databases': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'multi-table databases',
                [
                    'Create two related tables: <strong>Customers</strong> and <strong>Orders</strong>.',
                    'Set a one-to-many relationship enforcing referential integrity.',
                    'Build a query that joins both tables to list customer names with their orders.',
                    'Add a calculated field <code>Total: [Qty]*[Price]</code>.',
                    'Group orders by customer in a report with sub-totals.',
                ],
                'Always enforce referential integrity &mdash; it stops "orphan" records.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'advanced databases',
                [
                    {'icon': 'fa-shop', 'title': 'Online stores',
                     'body': 'Customers, products, orders and reviews are all linked tables.'},
                    {'icon': 'fa-school-flag', 'title': 'School systems',
                     'body': 'Learners, subjects, marks and reports.'},
                    {'icon': 'fa-people-group', 'title': 'HR systems',
                     'body': 'Employees, leave, payroll and assets.'},
                    {'icon': 'fa-microscope', 'title': 'Research',
                     'body': 'Massive scientific datasets are stored in databases.'},
                ],
                'A normalised database is the foundation of every reliable software system.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'A field that links to another table\'s primary key is called a&hellip;',
             'options': ['Lookup field', 'Foreign key', 'Index', 'Composite key'],
             'correct_answer': 'Foreign key',
             'explanation': 'FKs create relationships between tables.'},
            {'question_type': 'multiple_choice',
             'question_text': '"One customer can have many orders" is&hellip;',
             'options': ['One-to-one', 'One-to-many',
                         'Many-to-many', 'Many-to-one only'],
             'correct_answer': 'One-to-many',
             'explanation': 'The most common database relationship.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Referential integrity prevents&hellip;',
             'options': ['Slow queries',
                         'Orphan records',
                         'Backups',
                         'Logging in'],
             'correct_answer': 'Orphan records',
             'explanation': 'You cannot have an order with no matching customer.'},
            {'question_type': 'true_false',
             'question_text': 'A query can include calculated fields like Total = Qty * Price.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'Use the Field row in design view.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which SQL keyword retrieves data?',
             'options': ['INSERT', 'UPDATE', 'DELETE', 'SELECT'],
             'correct_answer': 'SELECT',
             'explanation': 'SELECT is the data-retrieval verb.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each SQL clause to its purpose.',
             'options': {
                 'column_a': ['WHERE', 'ORDER BY', 'GROUP BY', 'JOIN'],
                 'column_b': ['Filters rows',
                              'Sorts rows',
                              'Groups rows for aggregation',
                              'Combines tables']
             },
             'correct_answer': {'WHERE': 'Filters rows',
                                'ORDER BY': 'Sorts rows',
                                'GROUP BY': 'Groups rows for aggregation',
                                'JOIN': 'Combines tables'},
             'explanation': 'Each does one job and can combine in one query.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Place clauses in correct SQL order.',
             'options': ['ORDER BY name', 'FROM customers', 'SELECT name'],
             'correct_answer': ['SELECT name', 'FROM customers', 'ORDER BY name'],
             'explanation': 'SELECT &rarr; FROM &rarr; ORDER BY.'},
            {'question_type': 'short_answer',
             'question_text': 'Name the process of removing data redundancy.',
             'options': [], 'correct_answer': 'Normalisation',
             'explanation': 'Normalisation splits data into related tables.'},
        ],
    },

    'Web & HTML Basics': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'building a small web page',
                [
                    'Create <code>index.html</code> with proper <code>&lt;!DOCTYPE html&gt;</code> declaration.',
                    'Add a heading, paragraph, image and bullet list.',
                    'Add a hyperlink to your school website.',
                    'Add a CSS <code>&lt;style&gt;</code> block to set the body font and background colour.',
                    'Open the file in two different browsers and compare.',
                ],
                'Always close the tags you open &mdash; mismatched tags cause hard-to-find layout bugs.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'the web',
                [
                    {'icon': 'fa-globe', 'title': 'Front-end developer',
                     'body': 'Builds the visible part of every website.'},
                    {'icon': 'fa-mobile-screen', 'title': 'Mobile sites',
                     'body': 'Most web traffic now comes from phones.'},
                    {'icon': 'fa-bullhorn', 'title': 'Digital marketing',
                     'body': 'SEO, analytics and landing pages.'},
                    {'icon': 'fa-shop', 'title': 'E-commerce',
                     'body': 'WooCommerce / Shopify run on web tech.'},
                ],
                'Every business now needs a website &mdash; HTML is the foundation it stands on.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'Which tag creates a hyperlink?',
             'options': ['&lt;link&gt;', '&lt;a&gt;', '&lt;href&gt;', '&lt;url&gt;'],
             'correct_answer': '&lt;a&gt;',
             'explanation': '<code>&lt;a href="..."&gt;text&lt;/a&gt;</code>.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which tag inserts an image?',
             'options': ['&lt;img&gt;', '&lt;image&gt;', '&lt;pic&gt;', '&lt;src&gt;'],
             'correct_answer': '&lt;img&gt;',
             'explanation': '<code>&lt;img src="cat.jpg" alt="cat"&gt;</code> &mdash; self-closing.'},
            {'question_type': 'multiple_choice',
             'question_text': 'CSS is used to&hellip;',
             'options': ['Store data',
                         'Style web pages',
                         'Make pages interactive',
                         'Send email'],
             'correct_answer': 'Style web pages',
             'explanation': 'Cascading Style Sheets handle colour, layout and fonts.'},
            {'question_type': 'true_false',
             'question_text': 'HTML elements must always be lowercase.',
             'options': ['True', 'False'], 'correct_answer': 'False',
             'explanation': 'Lowercase is recommended; HTML is technically case-insensitive.'},
            {'question_type': 'multiple_choice',
             'question_text': 'The largest heading tag is&hellip;',
             'options': ['&lt;h1&gt;', '&lt;h6&gt;', '&lt;head&gt;', '&lt;heading&gt;'],
             'correct_answer': '&lt;h1&gt;',
             'explanation': 'h1 is the biggest; h6 is the smallest.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each tag to its purpose.',
             'options': {
                 'column_a': ['&lt;p&gt;', '&lt;ul&gt;', '&lt;table&gt;', '&lt;br&gt;'],
                 'column_b': ['Paragraph', 'Bullet list',
                              'Tabular data', 'Line break']
             },
             'correct_answer': {'&lt;p&gt;': 'Paragraph', '&lt;ul&gt;': 'Bullet list',
                                '&lt;table&gt;': 'Tabular data', '&lt;br&gt;': 'Line break'},
             'explanation': 'These are HTML\'s most common content tags.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these inside an HTML document.',
             'options': ['&lt;body&gt;', '&lt;head&gt;', '&lt;!DOCTYPE html&gt;'],
             'correct_answer': ['&lt;!DOCTYPE html&gt;', '&lt;head&gt;', '&lt;body&gt;'],
             'explanation': 'Doctype on top, then head, then body.'},
            {'question_type': 'short_answer',
             'question_text': 'Which attribute holds the URL inside an &lt;a&gt; tag?',
             'options': [], 'correct_answer': 'href',
             'explanation': 'href = hypertext reference.'},
        ],
    },

    'Solution Development': {
        'lessons': [
            (6, 30, 'Practical Skills', practical_lesson(
                'planning your PAT solution',
                [
                    'Write a clear problem statement in two sentences.',
                    'List the inputs, processes and outputs (IPO chart).',
                    'Sketch your data on paper before opening Excel/Access.',
                    'Build a working prototype that handles ONE happy-path scenario.',
                    'Get feedback from a classmate and write down THREE improvements.',
                ],
                'Iterate fast: a rough working prototype beats a perfect plan that never ships.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'solution development',
                [
                    {'icon': 'fa-laptop-code', 'title': 'Software dev',
                     'body': 'Apps follow agile cycles of plan-build-test-deliver.'},
                    {'icon': 'fa-people-arrows', 'title': 'Consulting',
                     'body': 'Consultants design business solutions for clients.'},
                    {'icon': 'fa-chart-gantt', 'title': 'Project management',
                     'body': 'Tools like Gantt charts plan complex projects.'},
                    {'icon': 'fa-flask', 'title': 'Engineering',
                     'body': 'Prototype, test, refine, repeat.'},
                ],
                'Every great product was once just a problem someone decided to solve.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'IPO stands for&hellip;',
             'options': ['Input, Process, Output',
                         'Internet, Page, Object',
                         'Input, Print, Output',
                         'Internal, Public, Open'],
             'correct_answer': 'Input, Process, Output',
             'explanation': 'IPO is the simplest model of any system.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A prototype is best described as&hellip;',
             'options': ['A finished product',
                         'A throw-away first version',
                         'A type of database',
                         'An installation file'],
             'correct_answer': 'A throw-away first version',
             'explanation': 'Prototypes test feasibility before full build.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Phase ONE of the SDLC is&hellip;',
             'options': ['Design', 'Investigation', 'Implementation', 'Maintenance'],
             'correct_answer': 'Investigation',
             'explanation': 'You first investigate the problem.'},
            {'question_type': 'true_false',
             'question_text': 'Testing should happen only at the end of the project.',
             'options': ['True', 'False'], 'correct_answer': 'False',
             'explanation': 'Test continuously to catch bugs early.'},
            {'question_type': 'multiple_choice',
             'question_text': 'Which document captures who will use the system and how?',
             'options': ['User manual',
                         'Requirements specification',
                         'Backup log',
                         'Receipt'],
             'correct_answer': 'Requirements specification',
             'explanation': 'It is the contract between developer and client.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each SDLC phase to its main activity.',
             'options': {
                 'column_a': ['Investigation', 'Design', 'Implementation', 'Maintenance'],
                 'column_b': ['Find out the problem',
                              'Plan the solution',
                              'Build the solution',
                              'Fix and improve over time']
             },
             'correct_answer': {'Investigation': 'Find out the problem',
                                'Design': 'Plan the solution',
                                'Implementation': 'Build the solution',
                                'Maintenance': 'Fix and improve over time'},
             'explanation': 'These are the four classic SDLC stages.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these PAT steps.',
             'options': ['Build prototype',
                         'Document and present',
                         'Define problem'],
             'correct_answer': ['Define problem',
                                'Build prototype',
                                'Document and present'],
             'explanation': 'Define &rarr; build &rarr; document.'},
            {'question_type': 'short_answer',
             'question_text': 'What does PAT stand for?',
             'options': [], 'correct_answer': 'Practical Assessment Task',
             'explanation': 'The PAT is the major Grade 12 CAT/IT project.'},
        ],
    },

    'ICT & Society': {
        'lessons': [
            (6, 25, 'Practical Skills', practical_lesson(
                'reducing your digital impact',
                [
                    'Calculate your weekly screen time and set a daily limit.',
                    'Audit your apps and uninstall those you have not used in 30 days.',
                    'Switch one device to dark-mode and energy-saver to save battery.',
                    'Recycle one old electronic device through a registered e-waste programme.',
                    'Donate unused storage space to an open citizen-science project.',
                ],
                'Small habits across millions of users add up to massive savings of energy and e-waste.')),
            (7, 25, 'Real-World Applications', application_lesson(
                'ICT and society',
                [
                    {'icon': 'fa-people-arrows', 'title': 'Digital divide',
                     'body': 'Not everyone has equal internet access &mdash; bridging this gap is a major project.'},
                    {'icon': 'fa-leaf', 'title': 'Green IT',
                     'body': 'Data centres are racing to run on renewable energy.'},
                    {'icon': 'fa-vote-yea', 'title': 'E-government',
                     'body': 'Online services for IDs, taxes and grants.'},
                    {'icon': 'fa-brain', 'title': 'AI ethics',
                     'body': 'Society is debating fair, explainable AI.'},
                ],
                'Technology is never neutral &mdash; the choices we make as users shape its impact.')),
        ],
        'quiz_questions': [
            {'question_type': 'multiple_choice',
             'question_text': 'The "digital divide" refers to&hellip;',
             'options': ['Two screens on a laptop',
                         'Inequality in access to ICT',
                         'A type of cyberattack',
                         'A keyboard layout'],
             'correct_answer': 'Inequality in access to ICT',
             'explanation': 'Some people have less access to internet, devices and skills.'},
            {'question_type': 'multiple_choice',
             'question_text': 'E-waste is&hellip;',
             'options': ['Spam email',
                         'Discarded electronics',
                         'Encrypted email',
                         'Browser cache'],
             'correct_answer': 'Discarded electronics',
             'explanation': 'Old phones, PCs and TVs need responsible recycling.'},
            {'question_type': 'multiple_choice',
             'question_text': 'A green-IT practice is&hellip;',
             'options': ['Leaving PCs on overnight',
                         'Buying new devices each year',
                         'Using cloud servers powered by renewables',
                         'Disabling power-save mode'],
             'correct_answer': 'Using cloud servers powered by renewables',
             'explanation': 'Renewable-powered data centres lower IT\'s carbon footprint.'},
            {'question_type': 'true_false',
             'question_text': 'AI bias can come from biased training data.',
             'options': ['True', 'False'], 'correct_answer': 'True',
             'explanation': 'A model is only as fair as the data behind it.'},
            {'question_type': 'multiple_choice',
             'question_text': 'POPIA in South Africa protects&hellip;',
             'options': ['Cars',
                         'Personal information',
                         'Land',
                         'Trademarks'],
             'correct_answer': 'Personal information',
             'explanation': 'Protection of Personal Information Act.'},
            {'question_type': 'match_columns', 'points': 3,
             'question_text': 'Match each issue to its category.',
             'options': {
                 'column_a': ['Hacking', 'Plagiarism', 'E-waste', 'Digital divide'],
                 'column_b': ['Security', 'Ethics',
                              'Environment', 'Equity']
             },
             'correct_answer': {'Hacking': 'Security', 'Plagiarism': 'Ethics',
                                'E-waste': 'Environment',
                                'Digital divide': 'Equity'},
             'explanation': 'Each issue ties ICT to a different societal area.'},
            {'question_type': 'drag_drop', 'points': 3,
             'question_text': 'Order these from least to most impact on energy use.',
             'options': ['One streaming HD movie',
                         'One Google search',
                         'Mining one Bitcoin'],
             'correct_answer': ['One Google search',
                                'One streaming HD movie',
                                'Mining one Bitcoin'],
             'explanation': 'Bitcoin mining uses thousands of times more energy.'},
            {'question_type': 'short_answer',
             'question_text': 'Name one law in South Africa that addresses cybercrime.',
             'options': [], 'correct_answer': 'Cybercrimes Act',
             'explanation': 'The Cybercrimes Act, 19 of 2020.'},
        ],
    },
}


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------
def seed():
    with app.app_context():
        totals = {'lessons_added': 0, 'lessons_skipped': 0,
                  'quizzes_added': 0, 'quizzes_skipped': 0,
                  'questions_added': 0, 'courses_processed': 0,
                  'courses_missing': 0}

        for course_title, pack in PACKS.items():
            course = Course.query.filter_by(title=course_title).first()
            if not course:
                print(f"  [skip] Course not found: {course_title}")
                totals['courses_missing'] += 1
                continue

            # ---- Lessons ----
            for order, duration, title, content in pack['lessons']:
                exists = Lesson.query.filter_by(
                    course_id=course.id, order=order
                ).first()
                if exists:
                    totals['lessons_skipped'] += 1
                    continue
                db.session.add(Lesson(
                    course_id=course.id,
                    order=order,
                    title=title,
                    content=content,
                    duration_minutes=duration,
                ))
                totals['lessons_added'] += 1

            # ---- Quiz ----
            quiz_title = f"{course_title} \u2014 Extension Quiz"
            quiz = Quiz.query.filter_by(
                course_id=course.id, title=quiz_title
            ).first()
            if quiz:
                totals['quizzes_skipped'] += 1
            else:
                quiz = Quiz(
                    course_id=course.id,
                    title=quiz_title,
                    description=f"Extra practice for {course_title}: 8 mixed-type questions.",
                    quiz_type='quiz',
                    time_limit_minutes=20,
                    pass_percentage=60.0,
                    order=2,
                )
                db.session.add(quiz)
                db.session.flush()
                totals['quizzes_added'] += 1

                for i, q in enumerate(pack['quiz_questions'], start=1):
                    db.session.add(Question(
                        quiz_id=quiz.id,
                        question_text=q['question_text'],
                        question_type=q['question_type'],
                        options=json.dumps(q['options']),
                        correct_answer=json.dumps(q['correct_answer']),
                        points=q.get('points', 1),
                        order=i,
                        explanation=q.get('explanation', ''),
                    ))
                    totals['questions_added'] += 1

            totals['courses_processed'] += 1

        db.session.commit()

        print('=' * 60)
        print('Extra-content seeder \u2014 summary')
        print('=' * 60)
        for k, v in totals.items():
            print(f"  {k:.<30} {v}")
        print('=' * 60)


if __name__ == '__main__':
    seed()
