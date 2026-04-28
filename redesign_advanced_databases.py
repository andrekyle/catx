"""Redesign the Grade 12 Advanced Databases course around Microsoft Access (CAPS).

Run once:
    python redesign_advanced_databases.py

It rewrites the title + content of all 9 lessons in the "Advanced Databases"
course. Idempotent: running again simply overwrites the same lessons with
the same content.
"""
from app import app, db, Course, Lesson


def L1_design():
    return """
<div class="lesson-intro"><div class="label">Lesson 1 &middot; Designing for Microsoft Access</div>
<p>Before you open Access you <strong>design on paper</strong>. A clean design saves hours of fixing later.</p></div>

<h2>Step 1 &mdash; Find the entities</h2>
<p>An <strong>entity</strong> is a real-world thing the database must remember: a Learner, a Subject, a Book, an Order. Each entity becomes a <strong>table</strong> in Access.</p>

<h2>Step 2 &mdash; List the attributes</h2>
<p>An <strong>attribute</strong> is a fact about an entity (a column / field). Pick the smallest sensible pieces &mdash; store <em>FirstName</em> and <em>Surname</em> separately, not "FullName".</p>

<table>
  <tr><th>Entity</th><th>Attributes (fields)</th></tr>
  <tr><td>Learner</td><td>LearnerID (PK), FirstName, Surname, DOB, Grade, ClassID (FK)</td></tr>
  <tr><td>Class</td><td>ClassID (PK), ClassName, TeacherID (FK)</td></tr>
  <tr><td>Teacher</td><td>TeacherID (PK), Name, Subject, Email</td></tr>
</table>

<h2>Step 3 &mdash; Pick a primary key</h2>
<p>A <strong>primary key (PK)</strong> uniquely identifies one record. In Access the safest choice is an <code>AutoNumber</code> field called e.g. <code>LearnerID</code>. Never use a person's ID number or surname as the PK.</p>

<h2>Step 4 &mdash; Link with foreign keys</h2>
<p>A <strong>foreign key (FK)</strong> in one table points to the PK of another. <code>Learner.ClassID</code> is the FK that links each learner to one class.</p>

<div class="callout tip"><div class="ico"><i class="fas fa-lightbulb"></i></div><div class="body"><strong>Cardinality</strong>
<ul>
<li><strong>One-to-many (1:M)</strong> &mdash; one Class has many Learners. Most common.</li>
<li><strong>Many-to-many (M:M)</strong> &mdash; a Learner takes many Subjects, a Subject has many Learners. In Access you build a <em>junction table</em> (e.g. <code>LearnerSubject</code>) holding both FKs.</li>
<li><strong>One-to-one (1:1)</strong> &mdash; rare, e.g. Learner &harr; MedicalRecord.</li>
</ul>
</div></div>

<h2>Step 5 &mdash; Draw the ER diagram</h2>
<p>An <strong>Entity-Relationship Diagram</strong> shows every table as a box, every PK underlined, and joins as lines with <em>1</em> and <em>&infin;</em> on the ends. Show this diagram to your teacher <em>before</em> you build anything in Access.</p>

<div class="callout warn"><div class="ico"><i class="fas fa-triangle-exclamation"></i></div><div class="body"><strong>Common design sins</strong>
<ul>
<li>Storing a list (e.g. "Maths, Science, English") in one field. Make a junction table.</li>
<li>Repeating a teacher's name in 30 learner rows. Move it to a Teachers table and link with a FK.</li>
<li>Using "Name" as a primary key. Two people can share a name &mdash; use <code>AutoNumber</code>.</li>
</ul>
</div></div>

<h2>Step 6 &mdash; Create the .accdb</h2>
<p>In Access: <strong>File &rarr; New &rarr; Blank database</strong>. Save it as <code>SchoolDB.accdb</code> in your PAT folder. You are now ready for Lesson 2.</p>
"""


def L2_tables():
    return """
<div class="lesson-intro"><div class="label">Lesson 2 &middot; Tables, Field Properties &amp; Relationships</div>
<p>This is where your paper design becomes a real Access database.</p></div>

<h2>Two views of every table</h2>
<table>
  <tr><th>View</th><th>What you do here</th><th>How to switch</th></tr>
  <tr><td><strong>Datasheet view</strong></td><td>Type, view and edit data in rows.</td><td>Home &rarr; View &rarr; Datasheet View</td></tr>
  <tr><td><strong>Design view</strong></td><td>Define field names, data types and properties.</td><td>Home &rarr; View &rarr; Design View</td></tr>
</table>

<h2>Choosing the right data type</h2>
<table>
  <tr><th>Data type</th><th>Use for</th><th>Example field</th></tr>
  <tr><td>Short Text (max 255)</td><td>Names, codes, addresses</td><td>FirstName</td></tr>
  <tr><td>Long Text</td><td>Paragraphs, notes</td><td>Comments</td></tr>
  <tr><td>Number</td><td>Whole or decimal numbers used in maths</td><td>Quantity</td></tr>
  <tr><td>Currency</td><td>Money &mdash; auto-formats with R</td><td>Price</td></tr>
  <tr><td>Date/Time</td><td>Dates, times</td><td>DOB</td></tr>
  <tr><td>Yes/No</td><td>True/false flag</td><td>Paid</td></tr>
  <tr><td>AutoNumber</td><td>Primary keys</td><td>LearnerID</td></tr>
  <tr><td>Hyperlink</td><td>Web or email links</td><td>Website</td></tr>
  <tr><td>Attachment</td><td>Photos, PDFs stored inside the .accdb</td><td>LearnerPhoto</td></tr>
</table>

<h2>Field Properties (the bottom panel in Design view)</h2>
<ul>
  <li><strong>Field Size</strong> &mdash; e.g. limit Surname to 40 characters.</li>
  <li><strong>Format</strong> &mdash; e.g. <code>dd mmm yyyy</code> for dates, <code>R#,##0.00</code> for currency.</li>
  <li><strong>Default Value</strong> &mdash; e.g. <code>=Date()</code> auto-fills today.</li>
  <li><strong>Validation Rule</strong> &mdash; <code>&gt;=0</code> blocks negative prices. <code>Between 8 AND 12</code> for Grade.</li>
  <li><strong>Validation Text</strong> &mdash; the error message Access shows when the rule fails.</li>
  <li><strong>Input Mask</strong> &mdash; a typing template, e.g. <code>0000\\-000\\-0000</code> for cell numbers.</li>
  <li><strong>Required</strong> &mdash; if Yes, the field cannot be left blank.</li>
  <li><strong>Indexed</strong> &mdash; speed up searches, optionally enforce <em>No Duplicates</em>.</li>
</ul>

<div class="callout tip"><div class="ico"><i class="fas fa-lightbulb"></i></div><div class="body"><strong>Lookup Wizard</strong>
<p>Choose <em>Lookup Wizard</em> as the data type to turn a foreign-key field into a friendly drop-down list pulled from another table. The user sees the class name; Access stores the ClassID.</p></div></div>

<h2>The Relationships window</h2>
<p>Open <strong>Database Tools &rarr; Relationships</strong>. Drag tables onto the canvas, then drag the PK of one table onto the matching FK in another. Tick:</p>
<ul>
  <li><strong>Enforce Referential Integrity</strong> &mdash; you cannot link to a class that does not exist.</li>
  <li><strong>Cascade Update Related Fields</strong> &mdash; renaming the PK updates all FKs.</li>
  <li><strong>Cascade Delete Related Records</strong> &mdash; deleting a class deletes its learners (use with care!).</li>
</ul>

<div class="callout try"><div class="ico"><i class="fas fa-rocket"></i></div><div class="body"><strong>Try this</strong>
<ol class="steps">
<li>Open <code>SchoolDB.accdb</code>.</li>
<li>Create three tables (Design view): <em>Class</em>, <em>Learner</em>, <em>Teacher</em> &mdash; with the fields from Lesson 1.</li>
<li>On <em>Learner.Grade</em> set Validation Rule <code>Between 8 And 12</code> and Validation Text <code>"Grade must be 8&ndash;12"</code>.</li>
<li>Open Relationships, link Class &rarr; Learner and Teacher &rarr; Class with <em>Enforce Referential Integrity</em> ticked.</li>
<li>Save and switch to Datasheet view to add 3 sample classes and 5 learners.</li>
</ol>
</div></div>
"""


def L3_queries():
    return """
<div class="lesson-intro"><div class="label">Lesson 3 &middot; Queries with the Access Query Designer</div>
<p>A <strong>query</strong> answers a question about your data. In Access you build queries visually in <strong>Query Design view</strong> &mdash; Access writes the SQL for you behind the scenes.</p></div>

<h2>Five query types you must know</h2>
<table>
  <tr><th>Type</th><th>What it does</th><th>When to use</th></tr>
  <tr><td><strong>Select</strong></td><td>Returns rows that match criteria</td><td>"All Grade 12 learners"</td></tr>
  <tr><td><strong>Parameter</strong></td><td>Asks the user for a value when run</td><td>"Show learners in grade [Enter Grade]"</td></tr>
  <tr><td><strong>Totals</strong> (aggregate)</td><td>Group + Sum/Avg/Count/Min/Max</td><td>"Average mark per subject"</td></tr>
  <tr><td><strong>Update</strong></td><td>Changes existing rows in bulk</td><td>"Add 5% to every price"</td></tr>
  <tr><td><strong>Delete</strong></td><td>Removes matching rows</td><td>"Delete inactive members"</td></tr>
</table>

<h2>Building a Select query</h2>
<ol class="steps">
<li><strong>Create &rarr; Query Design</strong>.</li>
<li>Add the tables you need; Access draws the join lines automatically.</li>
<li>Drag fields down into the <em>design grid</em>.</li>
<li>Type a condition in the <em>Criteria</em> row.</li>
<li>Click <strong>Run</strong> (red <i class="fas fa-play"></i>) to view the results.</li>
<li><strong>File &rarr; Save</strong> with a name that starts with <code>qry</code> e.g. <code>qryGrade12</code>.</li>
</ol>

<h2>Common criteria patterns</h2>
<table>
  <tr><th>You want&hellip;</th><th>Type in Criteria</th></tr>
  <tr><td>Exactly Grade 12</td><td><code>12</code></td></tr>
  <tr><td>Mark above 75</td><td><code>&gt;75</code></td></tr>
  <tr><td>Mark from 60 to 79</td><td><code>Between 60 And 79</code></td></tr>
  <tr><td>Surname starts with "M"</td><td><code>Like "M*"</code></td></tr>
  <tr><td>Born in 2007</td><td><code>Between #2007/01/01# And #2007/12/31#</code></td></tr>
  <tr><td>Empty / no value</td><td><code>Is Null</code></td></tr>
  <tr><td>Maths or Science</td><td><code>"Maths" Or "Science"</code></td></tr>
  <tr><td>Asks the user</td><td><code>[Enter grade:]</code></td></tr>
</table>

<h2>Calculated fields</h2>
<p>In an empty column of the grid type a name, a colon, then the expression:</p>
<p><code>Total: [Price]*[Quantity]</code></p>
<p><code>FullName: [FirstName] &amp; " " &amp; [Surname]</code></p>
<p><code>Age: DateDiff("yyyy",[DOB],Date())</code></p>

<h2>Totals (aggregate) queries</h2>
<p>Click the <strong>&Sigma; Totals</strong> button on the ribbon. A new <em>Total</em> row appears. Set it to <strong>Group By</strong> for the field you want to group on, and <strong>Sum / Avg / Count</strong> for the value field.</p>

<div class="callout warn"><div class="ico"><i class="fas fa-triangle-exclamation"></i></div><div class="body"><strong>Action queries change data!</strong>
<p>Update and Delete queries write to your tables. Always:</p>
<ol>
<li>Run as a Select query first to <em>see</em> the affected rows.</li>
<li><strong>Compact &amp; Repair</strong> a backup of the .accdb.</li>
<li>Then convert to Update / Delete and run.</li>
</ol>
</div></div>

<h2>SQL view (peek under the bonnet)</h2>
<p>Right-click any query tab &rarr; <strong>SQL View</strong>. Access shows you the equivalent SQL it generated. You don't have to write SQL by hand for CAPS, but recognising it helps:</p>
<p><code>SELECT Surname, Grade FROM Learner WHERE Grade=12 ORDER BY Surname;</code></p>

<div class="callout try"><div class="ico"><i class="fas fa-rocket"></i></div><div class="body"><strong>Try this</strong>
<ol class="steps">
<li>Build <code>qryTopMarks</code> &mdash; show learner FullName and Mark, criteria <code>&gt;=75</code>, sorted descending.</li>
<li>Build <code>qryByGrade</code> &mdash; with criteria <code>[Enter grade:]</code> so the user is asked.</li>
<li>Build a Totals query <code>qryAvgPerSubject</code> &mdash; Group By Subject, Avg on Mark.</li>
</ol>
</div></div>
"""


def L4_forms():
    return """
<div class="lesson-intro"><div class="label">Lesson 4 &middot; Forms, Subforms &amp; Macros</div>
<p>Forms are the <strong>user interface</strong> of an Access database. End-users should never see raw tables.</p></div>

<h2>Three ways to create a form</h2>
<table>
  <tr><th>Method</th><th>Best for</th></tr>
  <tr><td><strong>Form</strong> button (Create tab)</td><td>Instant single-record form for the selected table.</td></tr>
  <tr><td><strong>Form Wizard</strong></td><td>Step-by-step &mdash; pick fields, layout, style. Great for subforms.</td></tr>
  <tr><td><strong>Form Design</strong> / Layout view</td><td>Full control &mdash; you place every control.</td></tr>
</table>

<h2>Form sections</h2>
<ul>
  <li><strong>Form Header</strong> &mdash; title, logo (shown once at the top).</li>
  <li><strong>Detail</strong> &mdash; the bound controls for each record.</li>
  <li><strong>Form Footer</strong> &mdash; totals, navigation buttons.</li>
</ul>

<h2>Controls you will use</h2>
<table>
  <tr><th>Control</th><th>Purpose</th></tr>
  <tr><td>Text Box</td><td>Show / edit a field.</td></tr>
  <tr><td>Label</td><td>Static caption.</td></tr>
  <tr><td>Combo Box</td><td>Drop-down lookup &mdash; pick a value from another table.</td></tr>
  <tr><td>List Box</td><td>Same idea but always visible.</td></tr>
  <tr><td>Check Box</td><td>Yes/No fields.</td></tr>
  <tr><td>Command Button</td><td>Triggers a macro: Save, Next, Print, Close.</td></tr>
  <tr><td>Subform</td><td>An embedded form &mdash; the "many" side of a 1-to-many.</td></tr>
</table>

<h2>Building a Master/Detail form with a subform</h2>
<ol class="steps">
<li><strong>Create &rarr; Form Wizard</strong>.</li>
<li>Pick fields from <em>Class</em> (parent), then <em>Learner</em> (child).</li>
<li>When the wizard asks "How do you want to view your data?" choose <strong>by Class</strong> and <strong>Form with subform(s)</strong>.</li>
<li>Pick a layout (Datasheet is most common for the subform).</li>
<li>Save as <code>frmClassWithLearners</code>.</li>
<li>The subform is automatically linked on <code>ClassID</code> &mdash; selecting a class shows only that class's learners.</li>
</ol>

<h2>Macros &mdash; no code required</h2>
<p>A <strong>macro</strong> is a recorded sequence of Access actions. Use them on button clicks instead of writing VBA.</p>

<table>
  <tr><th>Macro Action</th><th>What it does</th></tr>
  <tr><td><code>OpenForm</code></td><td>Opens another form (e.g. menu &rarr; learner entry).</td></tr>
  <tr><td><code>OpenReport</code></td><td>Opens a report (preview or print).</td></tr>
  <tr><td><code>OpenQuery</code></td><td>Runs a saved query.</td></tr>
  <tr><td><code>GoToRecord</code></td><td>First / Previous / Next / Last / New.</td></tr>
  <tr><td><code>MessageBox</code></td><td>Shows a popup message to the user.</td></tr>
  <tr><td><code>CloseWindow</code></td><td>Closes the current form/report.</td></tr>
  <tr><td><code>QuitAccess</code></td><td>Closes Access.</td></tr>
</table>

<div class="callout tip"><div class="ico"><i class="fas fa-lightbulb"></i></div><div class="body"><strong>Embedded macro on a button</strong>
<ol class="steps">
<li>In Form Design view, drop a Command Button onto the form.</li>
<li>Skip the wizard &rarr; Property Sheet &rarr; <strong>Event</strong> tab &rarr; <em>On Click</em> &rarr; <strong>[Embedded Macro]</strong>.</li>
<li>Pick the action (e.g. <code>OpenReport</code>), set arguments, save.</li>
</ol>
</div></div>

<h2>Navigation form (the menu)</h2>
<p><strong>Create &rarr; Navigation &rarr; Horizontal Tabs</strong>. Drag your other forms and reports onto each tab. Set this navigation form to open automatically: <strong>File &rarr; Options &rarr; Current Database &rarr; Display Form</strong>.</p>

<div class="callout try"><div class="ico"><i class="fas fa-rocket"></i></div><div class="body"><strong>Try this</strong>
<ol class="steps">
<li>Build <code>frmLearnerEntry</code> with the Form button.</li>
<li>Add a Combo Box bound to <code>ClassID</code> using the Lookup Wizard so users pick a class name.</li>
<li>Add three command buttons: <em>New Record</em> (GoToRecord, New), <em>Save</em> (RunMenuCommand, SaveRecord), <em>Close</em> (CloseWindow).</li>
<li>Build <code>frmMain</code> as a Navigation form with tabs for Learners, Classes, and Reports.</li>
</ol>
</div></div>
"""


def L5_reports():
    return """
<div class="lesson-intro"><div class="label">Lesson 5 &middot; Reports, Grouping &amp; Totals</div>
<p>Reports are the <strong>printed</strong> output of a database &mdash; class lists, invoices, mark sheets. They look at data; they do not change it.</p></div>

<h2>Report vs Form</h2>
<table>
  <tr><th></th><th>Form</th><th>Report</th></tr>
  <tr><td>Purpose</td><td>Capture &amp; edit data on screen</td><td>Present &amp; print data</td></tr>
  <tr><td>Editable?</td><td>Yes</td><td>No</td></tr>
  <tr><td>Page-aware?</td><td>No</td><td>Yes &mdash; headers, footers, page numbers</td></tr>
</table>

<h2>Report sections (Design view)</h2>
<ul>
  <li><strong>Report Header</strong> &mdash; title page, prints once at the start.</li>
  <li><strong>Page Header</strong> &mdash; column headings, prints on every page.</li>
  <li><strong>Group Header</strong> &mdash; e.g. "Grade 12" before its learners.</li>
  <li><strong>Detail</strong> &mdash; one row per record.</li>
  <li><strong>Group Footer</strong> &mdash; subtotal for the group.</li>
  <li><strong>Page Footer</strong> &mdash; page numbers, date.</li>
  <li><strong>Report Footer</strong> &mdash; grand total, prints once at the end.</li>
</ul>

<h2>Report Wizard &mdash; the fast path</h2>
<ol class="steps">
<li><strong>Create &rarr; Report Wizard</strong>.</li>
<li>Pick the table or query as the source. Tip: feed reports from a <em>query</em> &mdash; you can pre-filter and pre-sort.</li>
<li>Add fields. If from multiple tables, pick how to view the data (e.g. by Class).</li>
<li>Add <strong>grouping levels</strong> &mdash; e.g. group by Grade.</li>
<li>Add <strong>sort order</strong> &mdash; e.g. by Surname A&rarr;Z.</li>
<li>Click <strong>Summary Options</strong> &mdash; tick Sum, Avg, Min, Max for any numeric field.</li>
<li>Pick layout (Stepped / Block / Outline) and orientation.</li>
<li>Save as <code>rptMarksByGrade</code>.</li>
</ol>

<h2>Adding totals manually</h2>
<p>In Design view, right-click the field in the Detail section and choose <strong>Total &rarr; Sum</strong>. Access drops a control with <code>=Sum([Mark])</code> into the appropriate group/report footer.</p>

<table>
  <tr><th>Expression</th><th>Where to put it</th></tr>
  <tr><td><code>=Sum([Total])</code></td><td>Group footer for subtotal, Report footer for grand total</td></tr>
  <tr><td><code>=Avg([Mark])</code></td><td>Group footer &mdash; average per group</td></tr>
  <tr><td><code>=Count(*)</code></td><td>Group footer &mdash; "5 learners in Grade 10"</td></tr>
  <tr><td><code>=[Page] &amp; " of " &amp; [Pages]</code></td><td>Page footer &mdash; "1 of 4"</td></tr>
  <tr><td><code>=Now()</code></td><td>Page footer &mdash; print date/time</td></tr>
</table>

<h2>Conditional formatting</h2>
<p>Select a control &rarr; <strong>Format ribbon &rarr; Conditional Formatting</strong>. Add a rule like "Field Value Is &lt; 30" &rarr; bold red. Marks below 30 will stand out automatically.</p>

<div class="callout tip"><div class="ico"><i class="fas fa-lightbulb"></i></div><div class="body"><strong>Always preview before printing</strong>
<p><strong>File &rarr; Print &rarr; Print Preview</strong>. Watch the page count at the bottom &mdash; if it explodes to 80 pages your column widths are too big or you forgot landscape. Fix with Page Setup.</p></div></div>

<div class="callout try"><div class="ico"><i class="fas fa-rocket"></i></div><div class="body"><strong>Try this</strong>
<ol class="steps">
<li>Build a query <code>qryMarks</code> joining Learner, Subject and Mark.</li>
<li>Run Report Wizard on it &mdash; group by Subject, sort by Mark Descending, Summary Options &rarr; Avg(Mark).</li>
<li>In Design view add Conditional Formatting on Mark: <code>&lt;40</code> &rarr; red.</li>
<li>Add page numbers in the Page Footer using <code>=[Page] &amp; "/" &amp; [Pages]</code>.</li>
<li>Export to PDF: <strong>External Data &rarr; PDF or XPS</strong>.</li>
</ol>
</div></div>
"""


def L6_practical():
    return """
<div class="lesson-intro"><div class="label">Lesson 6 &middot; Practical Skills (PAT-ready)</div>
<p>The skills your PAT and exam will actually test &mdash; importing data, exporting results, keeping the database healthy.</p></div>

<h2>Importing data into Access</h2>
<p>Most PATs give you a CSV or Excel spreadsheet to start with. Use <strong>External Data &rarr; New Data Source</strong>.</p>

<table>
  <tr><th>Source</th><th>Choose</th><th>Result</th></tr>
  <tr><td>Excel (.xlsx)</td><td>From File &rarr; Excel</td><td>Wizard lets you pick the sheet, set headings, choose data types and PK.</td></tr>
  <tr><td>CSV (.csv)</td><td>From File &rarr; Text File</td><td>Same wizard &mdash; tick "First Row Contains Field Names".</td></tr>
  <tr><td>Another Access DB</td><td>From Database &rarr; Access</td><td>Copy tables, queries, forms, reports.</td></tr>
</table>

<h2>Import vs Link</h2>
<ul>
  <li><strong>Import</strong> &mdash; Access copies the data <em>once</em>. Edits in Excel afterwards do not show up.</li>
  <li><strong>Link</strong> &mdash; Access reads from the live file. Updates appear, but you cannot enforce relationships on a linked table.</li>
</ul>

<h2>Exporting your results</h2>
<p>Right-click any table, query or report &rarr; <strong>Export</strong>:</p>
<ul>
  <li><strong>Excel</strong> &mdash; for further analysis.</li>
  <li><strong>PDF</strong> &mdash; for handing in (rich formatting preserved).</li>
  <li><strong>Word (RTF)</strong> &mdash; for pasting into a write-up.</li>
  <li><strong>Text file</strong> &mdash; for sharing with non-Access users.</li>
</ul>

<h2>Database maintenance</h2>
<table>
  <tr><th>Task</th><th>How</th><th>Why</th></tr>
  <tr><td>Compact &amp; Repair</td><td>File &rarr; Info &rarr; Compact &amp; Repair Database</td><td>Shrinks the .accdb after lots of edits, fixes minor corruption.</td></tr>
  <tr><td>Backup</td><td>File &rarr; Save As &rarr; Back Up Database</td><td>Adds a date stamp to the filename. Do this <em>before</em> any update/delete query.</td></tr>
  <tr><td>Trust Center</td><td>File &rarr; Options &rarr; Trust Center</td><td>Add your PAT folder so macros run without warnings.</td></tr>
</table>

<h2>Keyboard short-cuts that save you in the exam</h2>
<table>
  <tr><th>Keys</th><th>Action</th></tr>
  <tr><td><kbd>Ctrl</kbd>+<kbd>S</kbd></td><td>Save current object</td></tr>
  <tr><td><kbd>F5</kbd></td><td>Run query / refresh view</td></tr>
  <tr><td><kbd>Shift</kbd>+<kbd>F2</kbd></td><td>Zoom into a long field or expression (Zoom box)</td></tr>
  <tr><td><kbd>Ctrl</kbd>+<kbd>;</kbd></td><td>Insert today's date in a field</td></tr>
  <tr><td><kbd>Ctrl</kbd>+<kbd>'</kbd></td><td>Copy value from the record above</td></tr>
  <tr><td><kbd>Esc</kbd></td><td>Undo the change in the current field/record</td></tr>
</table>

<div class="callout warn"><div class="ico"><i class="fas fa-triangle-exclamation"></i></div><div class="body"><strong>The .accdb is one file</strong>
<p>Your tables, queries, forms, reports and macros all live inside one <code>.accdb</code>. Lose that file &mdash; you lose your whole PAT. Save daily backups to a flash drive <em>and</em> the cloud.</p></div></div>

<div class="callout try"><div class="ico"><i class="fas fa-rocket"></i></div><div class="body"><strong>Try this</strong>
<ol class="steps">
<li>Download a CSV of marks from your teacher.</li>
<li>Import it into <code>SchoolDB.accdb</code> as a new table called <code>tblMarksRaw</code>.</li>
<li>Build <code>qryCleanMarks</code> &mdash; trim spaces with <code>Trim([Surname])</code>, force case with <code>StrConv([Subject],3)</code>.</li>
<li>Export <code>qryCleanMarks</code> to PDF.</li>
<li>Compact &amp; Repair, then make a dated backup.</li>
</ol>
</div></div>
"""


def L7_realworld():
    return """
<div class="lesson-intro"><div class="label">Lesson 7 &middot; Real-World Applications</div>
<p>Three case studies showing how the same Access skills solve very different problems.</p></div>

<h2>Case study 1 &mdash; School tuck shop</h2>
<p><strong>Problem:</strong> The tuck shop manager loses money because items run out unnoticed and stock counts are guess-work.</p>

<table>
  <tr><th>Object</th><th>Purpose</th></tr>
  <tr><td>tblProduct</td><td>ProductID, Name, Price (Currency), StockOnHand (Number), ReorderLevel</td></tr>
  <tr><td>tblSale</td><td>SaleID, ProductID (FK), Quantity, SaleDate (Default <code>=Date()</code>)</td></tr>
  <tr><td>frmSale</td><td>Capture sales quickly with a Combo Box for product.</td></tr>
  <tr><td>qryLowStock</td><td>Criteria <code>[StockOnHand]&lt;=[ReorderLevel]</code>.</td></tr>
  <tr><td>rptDailySales</td><td>Group by SaleDate, Sum(Quantity*Price).</td></tr>
</table>

<h2>Case study 2 &mdash; Clinic appointments</h2>
<p><strong>Problem:</strong> A community clinic uses paper diaries; appointments clash and patient files go missing.</p>

<table>
  <tr><th>Object</th><th>Purpose</th></tr>
  <tr><td>tblPatient</td><td>PatientID, Name, DOB, CellNo (Input Mask).</td></tr>
  <tr><td>tblAppointment</td><td>ApptID, PatientID (FK), DoctorID (FK), Date, Time, Reason.</td></tr>
  <tr><td>frmPatient with subform</td><td>Patient master + their appointments below.</td></tr>
  <tr><td>qryToday</td><td>Criteria <code>=Date()</code> on the Date field.</td></tr>
  <tr><td>rptDoctorSchedule</td><td>Parameter query: <code>[Enter doctor:]</code> &mdash; group by Date.</td></tr>
</table>

<h2>Case study 3 &mdash; Sports club membership</h2>
<p><strong>Problem:</strong> The treasurer cannot tell who has paid this season's R250 fee and who hasn't.</p>

<table>
  <tr><th>Object</th><th>Purpose</th></tr>
  <tr><td>tblMember</td><td>MemberID, Name, JoinDate, Sport (Lookup).</td></tr>
  <tr><td>tblPayment</td><td>PaymentID, MemberID (FK), Amount (Currency), PaidDate, Method.</td></tr>
  <tr><td>qryUnpaid</td><td>Members with no payment in the current season &mdash; uses an outer join + <code>Is Null</code>.</td></tr>
  <tr><td>frmMain</td><td>Navigation form with tabs: Members, Payments, Reports.</td></tr>
  <tr><td>rptStatement</td><td>Per-member statement &mdash; parameter <code>[MemberID]</code>.</td></tr>
</table>

<div class="callout tip"><div class="ico"><i class="fas fa-lightbulb"></i></div><div class="body"><strong>Pattern in all three</strong>
<ol>
<li>Tables hold the facts.</li>
<li>Relationships keep the facts consistent.</li>
<li>Queries answer the questions.</li>
<li>Forms make data capture pleasant.</li>
<li>Reports turn data into something you can hand to the boss.</li>
<li>Macros + a navigation form turn the database into an "app".</li>
</ol>
</div></div>

<h2>When Access is the wrong tool</h2>
<ul>
  <li><strong>Web / mobile users</strong> &mdash; Access is desktop only. Use a web database instead.</li>
  <li><strong>Hundreds of simultaneous users</strong> &mdash; Access locks badly above ~10 concurrent. Use SQL Server.</li>
  <li><strong>Database &gt; 2 GB</strong> &mdash; that is the .accdb file-size limit.</li>
  <li><strong>Hostile-internet exposure</strong> &mdash; Access has no real authentication; never publish the file.</li>
</ul>
"""


def L8_mistakes():
    return """
<div class="lesson-intro"><div class="label">Lesson 8 &middot; Common Mistakes &amp; Troubleshooting</div>
<p>Match the symptom to the fix &mdash; saves you in the exam and the PAT.</p></div>

<table>
  <tr><th>You see&hellip;</th><th>What it means</th><th>Fix</th></tr>
  <tr><td><code>#Type!</code> in a calculated field</td><td>You used a text field in a maths expression, or vice versa.</td><td>Wrap with <code>Val([Field])</code> or <code>CStr()</code> to convert.</td></tr>
  <tr><td><code>#Name?</code></td><td>You typed a field name that does not exist (or you renamed the field).</td><td>Open the source query/table and check the spelling. Square brackets are case-insensitive but the name must exist.</td></tr>
  <tr><td><code>#Error</code></td><td>Access cannot evaluate the expression at all.</td><td>Press <kbd>Shift</kbd>+<kbd>F2</kbd> to zoom into the expression and look for an extra bracket or quote.</td></tr>
  <tr><td>"The changes you requested to the table were not successful because they would create duplicate values&hellip;"</td><td>You tried to add a row whose PK already exists, or violated a <em>No Duplicates</em> index.</td><td>Use a different PK value (or change the PK to <code>AutoNumber</code>).</td></tr>
  <tr><td>"You cannot add or change a record because a related record is required&hellip;"</td><td>Referential integrity blocked an FK that points to a missing PK.</td><td>Add the parent row first (e.g. create the Class before the Learner).</td></tr>
  <tr><td>An unexpected "Enter Parameter Value" popup</td><td>You misspelled a field name in a query &mdash; Access thinks the unknown name is a parameter.</td><td>Click Cancel, open the query in Design view, fix the spelling.</td></tr>
  <tr><td>Date criteria does not match anything</td><td>You wrote <code>"2024/03/15"</code> instead of <code>#2024/03/15#</code>.</td><td>Wrap dates with <code>#</code>; use <code>Between #d1# And #d2#</code>.</td></tr>
  <tr><td>Update query "would result in a key violation"</td><td>You tried to set an FK to a value that doesn't exist in the parent table.</td><td>Add the missing parent record first, or temporarily disable the relationship.</td></tr>
  <tr><td>Form shows <code>(New)</code> but won't save</td><td>A <strong>Required</strong> field is blank, or a <strong>Validation Rule</strong> is failing.</td><td>Read the Validation Text. Check the form's status bar at the bottom.</td></tr>
  <tr><td>Report runs forever or has thousands of pages</td><td>You forgot to filter the source query, or columns are too wide and wrap.</td><td>Feed the report from a query, narrow columns, switch to Landscape.</td></tr>
  <tr><td>"This database is in an inconsistent state&hellip;"</td><td>Access crashed mid-write.</td><td><strong>Compact &amp; Repair</strong>. If that fails, restore your latest backup.</td></tr>
</table>

<div class="callout warn"><div class="ico"><i class="fas fa-triangle-exclamation"></i></div><div class="body"><strong>Golden rules</strong>
<ol>
<li>Back up before any Update/Delete query.</li>
<li>Test action queries as Select queries first.</li>
<li>Compact &amp; Repair weekly.</li>
<li>Never store calculated values in tables &mdash; calculate them in queries.</li>
</ol>
</div></div>
"""


def L9_exam():
    return """
<div class="lesson-intro"><div class="label">Lesson 9 &middot; Exam Preparation Toolkit</div>
<p>Everything you need on the day &mdash; terms, criteria patterns, exam tactics.</p></div>

<h2>Terminology you must define</h2>
<table>
  <tr><th>Term</th><th>One-line definition</th></tr>
  <tr><td>Entity</td><td>A real-world thing the database stores &mdash; becomes a table.</td></tr>
  <tr><td>Attribute</td><td>A property of an entity &mdash; becomes a field/column.</td></tr>
  <tr><td>Primary key</td><td>Field that uniquely identifies each record (often <code>AutoNumber</code>).</td></tr>
  <tr><td>Foreign key</td><td>Field in one table that holds the PK of another table.</td></tr>
  <tr><td>Relationship</td><td>Defined link between two tables in the Relationships window.</td></tr>
  <tr><td>Referential integrity</td><td>Rule that an FK must point to an existing PK.</td></tr>
  <tr><td>Normalisation</td><td>Removing repetition by splitting data into related tables.</td></tr>
  <tr><td>Query</td><td>A saved question that returns rows from one or more tables.</td></tr>
  <tr><td>Calculated field</td><td>A column built from an expression: <code>Total: [Price]*[Qty]</code>.</td></tr>
  <tr><td>Parameter query</td><td>A query that prompts the user for a value at run time.</td></tr>
  <tr><td>Action query</td><td>An Update, Delete, Append or Make-Table query that <em>changes</em> data.</td></tr>
  <tr><td>Form</td><td>A visual interface for capturing/editing one record at a time.</td></tr>
  <tr><td>Subform</td><td>A form embedded in another form, linked by a key.</td></tr>
  <tr><td>Report</td><td>A printable, read-only presentation of data.</td></tr>
  <tr><td>Macro</td><td>A stored sequence of Access actions triggered by an event.</td></tr>
</table>

<h2>Criteria cheat sheet</h2>
<table>
  <tr><th>Question</th><th>Criteria</th></tr>
  <tr><td>Field equals exactly</td><td><code>"Maths"</code> or <code>12</code></td></tr>
  <tr><td>Greater / less than</td><td><code>&gt;75</code> &nbsp; <code>&lt;=30</code></td></tr>
  <tr><td>Between two values</td><td><code>Between 60 And 79</code></td></tr>
  <tr><td>List of values</td><td><code>In ("Maths","Science")</code></td></tr>
  <tr><td>Wildcard text</td><td><code>Like "M*"</code> &nbsp; <code>Like "*son"</code></td></tr>
  <tr><td>Date range</td><td><code>Between #2024/01/01# And #2024/12/31#</code></td></tr>
  <tr><td>Today / this year</td><td><code>=Date()</code> &nbsp; <code>Year([DOB])=2007</code></td></tr>
  <tr><td>Empty</td><td><code>Is Null</code></td></tr>
  <tr><td>Not empty</td><td><code>Is Not Null</code></td></tr>
  <tr><td>Ask the user</td><td><code>[Enter grade:]</code></td></tr>
</table>

<h2>Functions worth memorising</h2>
<table>
  <tr><th>Function</th><th>Returns</th></tr>
  <tr><td><code>Date()</code> / <code>Now()</code></td><td>Today / current date+time</td></tr>
  <tr><td><code>Year()</code>, <code>Month()</code>, <code>Day()</code></td><td>Parts of a date</td></tr>
  <tr><td><code>DateDiff("yyyy",[DOB],Date())</code></td><td>Age in years</td></tr>
  <tr><td><code>Format([Total],"Currency")</code></td><td>Formatted text</td></tr>
  <tr><td><code>UCase()</code>, <code>LCase()</code></td><td>Change case</td></tr>
  <tr><td><code>Left([F],3)</code>, <code>Right()</code>, <code>Mid()</code></td><td>Slice text</td></tr>
  <tr><td><code>Trim([F])</code></td><td>Strip leading/trailing spaces</td></tr>
  <tr><td><code>IIf([Mark]&gt;=50,"Pass","Fail")</code></td><td>If-then-else</td></tr>
  <tr><td><code>Nz([F],0)</code></td><td>Replace Null with a default</td></tr>
  <tr><td><code>Sum()</code>, <code>Avg()</code>, <code>Count()</code>, <code>Max()</code>, <code>Min()</code></td><td>Totals (group footer of report or Totals query)</td></tr>
</table>

<h2>Exam-day tactics</h2>
<ol class="steps">
<li><strong>Read every question first</strong> &mdash; some questions tell you what later questions expect.</li>
<li><strong>Open the data file and Save As immediately</strong> with your name. Never edit the original.</li>
<li><strong>Build queries before reports</strong> &mdash; reports nearly always read from a query.</li>
<li>If a question says "save as <code>qry_3_2</code>", <em>use that exact name</em>. Markers search by name.</li>
<li><strong>Run every query</strong> &mdash; a query that compiles but returns 0 rows usually scores 0.</li>
<li>Check the Number of Records bar at the bottom &mdash; the question often hints at the expected count.</li>
<li><strong>Compact &amp; Repair</strong> at the end &mdash; some markers reject .accdb files over a size limit.</li>
<li>Do a final <strong>Backup</strong> to your exam flash drive AND the network drive.</li>
</ol>

<div class="callout tip"><div class="ico"><i class="fas fa-lightbulb"></i></div><div class="body"><strong>Three things examiners love</strong>
<ul>
<li>Correct primary keys and foreign keys with referential integrity ticked.</li>
<li>Queries with sensible names (<code>qry</code>&hellip;), reports (<code>rpt</code>&hellip;), forms (<code>frm</code>&hellip;).</li>
<li>Reports that fit on the page with totals in the right footer.</li>
</ul>
</div></div>
"""


LESSONS = [
    (1, "Database Design and ER Diagrams",                       L1_design),
    (2, "Tables, Field Properties &amp; Relationships in Access", L2_tables),
    (3, "Queries with the Access Query Designer",                L3_queries),
    (4, "Forms, Subforms and Macros in Access",                  L4_forms),
    (5, "Reports, Grouping and Totals",                          L5_reports),
    (6, "Practical Skills (PAT-ready)",                          L6_practical),
    (7, "Real-World Applications",                               L7_realworld),
    (8, "Common Mistakes &amp; Troubleshooting",                  L8_mistakes),
    (9, "Exam Preparation Toolkit",                              L9_exam),
]


def main():
    with app.app_context():
        course = Course.query.filter_by(title="Advanced Databases").first()
        if not course:
            print("ERROR: 'Advanced Databases' course not found.")
            return
        updated = 0
        for order, title, builder in LESSONS:
            lesson = Lesson.query.filter_by(course_id=course.id, order=order).first()
            if not lesson:
                print(f"  - lesson order={order} not found, skipping")
                continue
            lesson.title = title
            lesson.content = builder().strip()
            updated += 1
            print(f"  + Lesson {order}: {title}  ({len(lesson.content)} chars)")
        db.session.commit()
        print(f"\nDone. Redesigned {updated} lessons.")


if __name__ == "__main__":
    main()
