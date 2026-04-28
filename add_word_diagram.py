"""Inject an annotated Word Interface diagram into Lesson 2 content."""
import re
from app import app, db, Lesson

START_MARKER = "<!-- WD-DIAGRAM-START -->"
END_MARKER   = "<!-- WD-DIAGRAM-END -->"

DIAGRAM_HTML = START_MARKER + """
<style>
  .wd-pin{position:absolute;width:28px;height:28px;background:#e53935;color:#fff!important;
          border-radius:50%;font-size:11px;font-weight:800;display:flex;
          align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,.55);
          border:2px solid #fff;z-index:10;transform:translate(-50%,-50%);
          pointer-events:all;line-height:1;cursor:default;}
  .wd-pin::after{content:attr(data-label);position:absolute;bottom:calc(100% + 8px);left:50%;
          transform:translateX(-50%);background:#111;color:#fff;font-size:12px;font-weight:600;
          white-space:nowrap;padding:5px 10px;border-radius:6px;pointer-events:none;
          box-shadow:0 2px 10px rgba(0,0,0,.5);opacity:0;transition:opacity .15s ease;
          font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:0;}
  .wd-pin:hover{transform:translate(-50%,-50%) scale(1.2);}
  .wd-pin:hover::after{opacity:1;}
  .wd-zoom-hint{display:flex;align-items:center;gap:6px;font-size:12.5px;
                color:#666;margin-bottom:6px;}
  .wd-zoom-hint svg{flex-shrink:0;}
  .wd-img-wrap{position:relative;display:block;width:100%;cursor:zoom-in;overflow:visible;}
  .wd-img-wrap img{width:100%!important;height:auto!important;display:block!important;
                   border-radius:10px;
                   image-rendering:crisp-edges;image-rendering:-webkit-optimize-contrast;}
  #wd-dialog{padding:0;border:none;outline:none;border-radius:0;background:#111;
             max-width:95vw;max-height:95vh;overflow:hidden;
             position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);margin:0;}
  #wd-dialog::backdrop{background:rgba(0,0,0,0.85);}
</style>

<!-- Native dialog -->
<dialog id="wd-dialog" onclick="this.close();">
  <img id="wd-dialog-img" src="" alt="Word Interface"
       style="display:block;max-width:90vw;max-height:90vh;
              width:auto;height:auto;image-rendering:crisp-edges;"
       onclick="event.stopPropagation();">
</dialog>

<div class="wd-diagram-wrap" style="margin:24px 0 32px;">
  <div class="wd-zoom-hint">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="2.2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
    Click the image to zoom in
  </div>
  <div class="wd-img-wrap"
       onclick="document.getElementById('wd-dialog-img').src=this.querySelector('img').src;document.getElementById('wd-dialog').showModal();">
    <img src="/static/images/Word%20Docment.PNG" alt="Microsoft Word Interface">
    <div class="wd-pin" data-label="Quick Access Toolbar" style="left:2%;top:4%;">1</div>
    <div class="wd-pin" data-label="Title Bar" style="left:46%;top:4%;">2</div>
    <div class="wd-pin" data-label="File Tab" style="left:2.5%;top:11%;">3</div>
    <div class="wd-pin" data-label="Ribbon Tabs" style="left:25%;top:11%;">4</div>
    <div class="wd-pin" data-label="Tell Me / Search Bar" style="left:68%;top:11%;">5</div>
    <div class="wd-pin" data-label="Window Controls" style="left:95%;top:4%;">6</div>
    <div class="wd-pin" data-label="Clipboard Group" style="left:4%;top:21.5%;">7</div>
    <div class="wd-pin" data-label="Font Group" style="left:18%;top:21.5%;">8</div>
    <div class="wd-pin" data-label="Paragraph Group" style="left:37%;top:21.5%;">9</div>
    <div class="wd-pin" data-label="Styles Group" style="left:60%;top:21.5%;">10</div>
    <div class="wd-pin" data-label="Editing Group" style="left:81%;top:21.5%;">11</div>
    <div class="wd-pin" data-label="Horizontal Ruler" style="left:46%;top:27%;">12</div>
    <div class="wd-pin" data-label="Vertical Ruler" style="left:1.2%;top:50%;">13</div>
    <div class="wd-pin" data-label="Insertion Point (Cursor)" style="left:17%;top:55%;">14</div>
    <div class="wd-pin" data-label="Document Area" style="left:56%;top:60%;">15</div>
    <div class="wd-pin" data-label="Vertical Scroll Bar" style="left:97%;top:55%;">16</div>
    <div class="wd-pin" data-label="View Buttons" style="left:80%;top:97%;">17</div>
    <div class="wd-pin" data-label="Zoom Slider" style="left:92%;top:97%;">18</div>
    <div class="wd-pin" data-label="Status Bar" style="left:15%;top:97%;">19</div>
  </div>
</div>

<table style="width:100%;border-collapse:collapse;margin-bottom:32px;
              background:#2a2a2a;border-radius:10px;overflow:hidden;font-size:14.5px;">
  <thead>
    <tr style="background:#1e1e1e;">
      <th style="text-align:left;padding:14px 20px;color:#ccc;font-size:11px;font-weight:700;
                 letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid #3a3a3a;width:28%;">Part</th>
      <th style="text-align:left;padding:14px 20px;color:#ccc;font-size:11px;font-weight:700;
                 letter-spacing:1.5px;text-transform:uppercase;border-bottom:1px solid #3a3a3a;">What it does</th>
    </tr>
  </thead>
  <tbody>""" + "".join([
    f"""
    <tr style="border-bottom:1px solid #3a3a3a;">
      <td style="padding:14px 20px;vertical-align:middle;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="flex-shrink:0;color:#888;font-size:13px;font-weight:700;min-width:20px;">{n}.</span>
          <span style="color:#fff;font-weight:700;">{name}</span>
        </div>
      </td>
      <td style="padding:14px 20px;color:#ccc;vertical-align:middle;">{desc}</td>
    </tr>"""
    for n, name, desc in [
        (1,  "Quick Access Toolbar",    "One-click Save <kbd>Ctrl+S</kbd>, Undo <kbd>Ctrl+Z</kbd> and Redo at the top-left."),
        (2,  "Title Bar",               "Shows the document name and &ldquo;Word&rdquo; in the centre of the screen."),
        (3,  "File Tab",                "Opens Backstage view: New, Open, Save, Save As, Print, Share and Options."),
        (4,  "Ribbon Tabs",             "Home, Insert, Draw, Design, Layout, References, Mailings, Review, View, Help."),
        (5,  "Tell Me / Search Bar",    "Type what you want to do and Word finds the command for you."),
        (6,  "Window Controls",         "Minimise, Restore/Maximise and Close the Word window."),
        (7,  "Clipboard Group",         "Cut, Copy, Paste and Format Painter buttons."),
        (8,  "Font Group",              "Change typeface, size, Bold, Italic, Underline, colour and more."),
        (9,  "Paragraph Group",         "Alignment, line spacing, bullets, numbering and indentation."),
        (10, "Styles Group",            "Apply ready-made text styles: Normal, Heading&nbsp;1, Heading&nbsp;2, Title."),
        (11, "Editing Group",           "Find <kbd>Ctrl+F</kbd>, Replace <kbd>Ctrl+H</kbd> and Select commands."),
        (12, "Horizontal Ruler",        "Drag to set left/right margins, tab stops and paragraph indents."),
        (13, "Vertical Ruler",          "Drag to set top and bottom margins."),
        (14, "Insertion Point (Cursor)","The flashing line showing where your typed text will appear."),
        (15, "Document Area",           "The white &ldquo;page&rdquo; canvas where you type your content."),
        (16, "Vertical Scroll Bar",     "Drag or click to move up and down through a long document."),
        (17, "View Buttons",            "Switch between Read Mode, Print Layout and Web Layout views."),
        (18, "Zoom Slider",             "Drag left/right to zoom the document in or out."),
        (19, "Status Bar",              "Shows page number, word count, language and document status."),
    ]
]) + """
  </tbody>
</table>
""" + END_MARKER

INJECT_AFTER = "<h2>Touring the Word window</h2>"

with app.app_context():
    lesson = Lesson.query.filter_by(title='The Word Interface').first()
    if not lesson:
        print("ERROR: lesson 'The Word Interface' not found.")
    else:
        # Remove ALL previous injections using markers or legacy pattern
        content = lesson.content
        content = re.sub(re.escape(START_MARKER) + r'[\s\S]*?' + re.escape(END_MARKER), '', content)
        # Also strip any legacy injection without markers
        content = re.sub(r'<style>\s*\.wd-pin[\s\S]*?</table>', '', content)

        idx = content.find(INJECT_AFTER)
        if idx == -1:
            print("ERROR: injection marker not found in content.")
        else:
            insert_at = idx + len(INJECT_AFTER)
            lesson.content = content[:insert_at] + DIAGRAM_HTML + content[insert_at:]
            db.session.commit()
            print("Done: Word diagram injected cleanly.")

