/* --------------------------------------------------------------------------
   rowExpand.js - tall tables made short

   A long note forces its table row to two or three lines, so a table of sets
   becomes a wall. This clamps the notes cell to a single line and lets you
   open one row at a time by tapping it.

   Rules:
     - tap a row            -> it opens, any other open row closes
     - tap it again         -> it closes
     - tap anywhere else    -> the open row closes
     - Esc                  -> same

   Opt in per table:
     <table class="table ... wd-rows">
   and make sure the note text sits in a div so it can be clamped:
     <td class="wd-notes"><div>{{ data.notes }}</div></td>

   Two ways to open, chosen per table:
     wd-rows                 the notes cell itself unclamps in place. Fine when
                             the column is wide enough to read in.
     wd-rows wd-wide-note    the note opens into its own full-width row below,
                             left aligned with reading line-height. On a 390px
                             phone that is ~44 characters per line instead of
                             ~12, and 4 lines instead of 12.

   Then one line before </body>:
     <script src="{{ url_for('static', filename='js/rowExpand.js') }}"></script>

   Only rows that are actually hiding something become tappable. A note that
   already fits on one line, or is empty, or is just a "-" placeholder, gets no
   pointer cursor and ignores taps - there is nothing to reveal.
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  var TABLE = "table.wd-rows";
  var ROW = TABLE + " > tbody > tr";
  var PLACEHOLDERS = ["", "-", "--", "–", "—", "None"];
  var EDGE = "2px solid rgba(13,110,253,.55)";   // the highlight around an open note

  function injectCss() {
    var css = document.createElement("style");
    css.textContent =
      // --- density: shorter rows than Bootstrap's default .5rem padding
      TABLE + " > thead > tr > th," +
      TABLE + " > tbody > tr > td{padding:.3rem .4rem;vertical-align:middle}" +

      // --- the note itself: one line, ellipsis, no effect on column width
      TABLE + " .wd-notes > div{display:-webkit-box;-webkit-box-orient:vertical;" +
        "-webkit-line-clamp:1;line-clamp:1;overflow:hidden;word-break:break-word;" +
        // notes can contain real newlines - honour them when opened
        "white-space:pre-line}" +

      // --- in-place mode: the cell unclamps where it sits
      TABLE + ":not(.wd-wide-note) > tbody > tr.wd-open .wd-notes > div{" +
        "-webkit-line-clamp:unset;line-clamp:unset;overflow:visible}" +

      // --- wide mode: the cell stays clamped (so the table keeps its shape) and
      //     the note opens into a full width row underneath, set for reading:
      //     left aligned, roomy line-height, capped line length.
      TABLE + " > tbody > tr.wd-note-row > td{text-align:left;padding:.6rem .85rem}" +
      TABLE + " .wd-note-text{line-height:1.6;max-width:70ch;white-space:pre-line;" +
        "word-break:break-word;cursor:text}" +

      // --- only rows that actually hold a hidden note look and behave tappable
      TABLE + " > tbody > tr.wd-can-open{cursor:pointer}" +
      "@media (hover:hover){" + TABLE + " > tbody > tr.wd-can-open:not(.wd-open):hover{" +
        "outline:1px solid rgba(13,110,253,.3);outline-offset:-1px}}" +

      // The highlight is drawn as cell borders rather than an outline on the row,
      // so that in wide mode the open row and the note underneath it close into a
      // single box - top and sides on the row, sides and bottom on the note, and
      // no line between them. An outline per row would draw that dividing line.
      // In-place mode has no second row, so the row closes the box itself.
      TABLE + ":not(.wd-wide-note) > tbody > tr.wd-open > td{border-top:" + EDGE +
        ";border-bottom:" + EDGE + "}" +
      TABLE + ".wd-wide-note > tbody > tr.wd-open > td{border-top:" + EDGE +
        ";border-bottom:0}" +
      TABLE + " > tbody > tr.wd-open > td:first-child{border-left:" + EDGE + "}" +
      TABLE + " > tbody > tr.wd-open > td:last-child{border-right:" + EDGE + "}" +
      TABLE + " > tbody > tr.wd-note-row > td{border:" + EDGE + ";border-top:0}";
    document.head.appendChild(css);
  }

  // Is this note hiding anything worth a tap?
  function isExpandable(div, row) {
    var text = div.textContent.trim();
    for (var i = 0; i < PLACEHOLDERS.length; i++) {
      if (text === PLACEHOLDERS[i]) { return false; }
    }
    // An open row in in-place mode measures as "fits" by definition.
    if (row.classList.contains("wd-open")) { return true; }
    // offsetParent is null inside a closed Bootstrap collapse, where nothing can
    // be measured. Assume expandable there and re-check once it is shown.
    if (div.offsetParent === null) { return true; }
    return div.scrollHeight - div.clientHeight > 1;
  }

  function markRows() {
    var rows = document.querySelectorAll(ROW);
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].classList.contains("wd-note-row")) { continue; }

      // wd-editable tables (opt-in, see progressEdit.js) open every row that
      // carries a data-entry-id, note or not - the point is "is there
      // something to edit", not "does the note overflow".
      var table = rows[i].closest("table");
      if (table && table.classList.contains("wd-editable")) {
        rows[i].classList.toggle("wd-can-open", rows[i].hasAttribute("data-entry-id"));
        continue;
      }

      var note = rows[i].querySelector(".wd-notes > div");
      rows[i].classList.toggle("wd-can-open", !!note && isExpandable(note, rows[i]));
    }
  }

  function openRow(row) {
    row.classList.add("wd-open");

    var table = row.closest("table");
    if (!table || !table.classList.contains("wd-wide-note")) { return; }

    var note = row.querySelector(".wd-notes > div");
    if (!note) { return; }

    var tr = document.createElement("tr");
    tr.className = "wd-note-row";

    var td = document.createElement("td");
    // Count visible cells, not all cells: a column hidden by a media query is
    // still in row.cells, and a colSpan wider than the table is asking for
    // trouble.
    var span = 0;
    for (var i = 0; i < row.cells.length; i++) {
      if (row.cells[i].getClientRects().length) { span++; }
    }
    td.colSpan = span || row.cells.length;

    var text = document.createElement("div");
    text.className = "wd-note-text";
    text.textContent = note.textContent.trim();

    td.appendChild(text);
    tr.appendChild(td);
    row.parentNode.insertBefore(tr, row.nextSibling);

    // Let an opt-in companion script (progressEdit.js) build an edit UI in
    // here without this generic file knowing anything about reps/weight/
    // save logic.
    if (table.classList.contains("wd-editable")) {
      row.dispatchEvent(new CustomEvent("wd:row-opened", {
        bubbles: true,
        detail: { row: row, noteRow: tr, noteCell: td, entryId: row.dataset.entryId }
      }));
    }
  }

  function closeRow(row) {
    var table = row.closest("table");
    if (table && table.classList.contains("wd-editable")) {
      row.dispatchEvent(new CustomEvent("wd:row-closing", {
        bubbles: true,
        detail: { row: row }
      }));
    }

    row.classList.remove("wd-open");
    var next = row.nextElementSibling;
    if (next && next.classList.contains("wd-note-row")) {
      next.parentNode.removeChild(next);
    }
  }

  function closeOpen(except) {
    var open = document.querySelectorAll(ROW + ".wd-open");
    for (var i = 0; i < open.length; i++) {
      if (open[i] !== except) { closeRow(open[i]); }
    }
  }

  function onClick(e) {
    // Never swallow a real control that happens to sit inside a row.
    if (e.target.closest("a,button,input,select,textarea,label")) { return; }
    // Touching the opened note must not close it - you may be reading or
    // selecting text in there.
    if (e.target.closest("tr.wd-note-row")) { return; }

    var row = e.target.closest(ROW + ".wd-can-open");
    var wasOpen = row && row.classList.contains("wd-open");

    closeOpen(row);                       // other row, or empty page -> collapse
    if (!row) { return; }
    if (wasOpen) { closeRow(row); } else { openRow(row); }
  }

  function start() {
    injectCss();
    markRows();
    document.addEventListener("click", onClick);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { closeOpen(null); }
    });
    // Re-measure once fonts have settled, and whenever a collapse reveals a
    // table we could not measure while it was hidden.
    window.addEventListener("load", markRows);
    document.addEventListener("shown.bs.collapse", markRows);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
