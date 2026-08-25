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

  function injectCss() {
    var css = document.createElement("style");
    css.textContent =
      // --- density: shorter rows than Bootstrap's default .5rem padding
      TABLE + " > thead > tr > th," +
      TABLE + " > tbody > tr > td{padding:.3rem .4rem;vertical-align:middle}" +

      // --- the note itself: one line, ellipsis, no effect on column width
      TABLE + " .wd-notes > div{display:-webkit-box;-webkit-box-orient:vertical;" +
        "-webkit-line-clamp:1;line-clamp:1;overflow:hidden;word-break:break-word;" +
        // notes can now contain real newlines - honour them when opened
        "white-space:pre-line}" +
      TABLE + " > tbody > tr.wd-open .wd-notes > div{-webkit-line-clamp:unset;" +
        "line-clamp:unset;overflow:visible}" +

      // --- only rows that actually hold a hidden note look and behave tappable.
      //     outline rather than background-color, so it stays visible on top of
      //     Bootstrap's striping and its table-info / table-success tints, which
      //     paint themselves with an inset box-shadow over the background.
      TABLE + " > tbody > tr.wd-can-open{cursor:pointer}" +
      "@media (hover:hover){" + TABLE + " > tbody > tr.wd-can-open:not(.wd-open):hover{" +
        "outline:1px solid rgba(13,110,253,.3);outline-offset:-1px}}" +
      TABLE + " > tbody > tr.wd-open{outline:2px solid rgba(13,110,253,.55);" +
        "outline-offset:-2px}";
    document.head.appendChild(css);
  }

  // Is this note hiding anything worth a tap?
  function isExpandable(div, row) {
    var text = div.textContent.trim();
    for (var i = 0; i < PLACEHOLDERS.length; i++) {
      if (text === PLACEHOLDERS[i]) { return false; }
    }
    // An open row measures as "fits" by definition - leave it alone.
    if (row.classList.contains("wd-open")) { return true; }
    // offsetParent is null inside a closed Bootstrap collapse, where nothing can
    // be measured. Assume expandable there and re-check once it is shown.
    if (div.offsetParent === null) { return true; }
    return div.scrollHeight - div.clientHeight > 1;
  }

  function markRows() {
    var rows = document.querySelectorAll(ROW);
    for (var i = 0; i < rows.length; i++) {
      var note = rows[i].querySelector(".wd-notes > div");
      rows[i].classList.toggle("wd-can-open", !!note && isExpandable(note, rows[i]));
    }
  }

  function closeOpen(except) {
    var open = document.querySelectorAll(ROW + ".wd-open");
    for (var i = 0; i < open.length; i++) {
      if (open[i] !== except) { open[i].classList.remove("wd-open"); }
    }
  }

  function onClick(e) {
    // Never swallow a real control that happens to sit inside a row.
    if (e.target.closest("a,button,input,select,textarea,label")) { return; }

    var row = e.target.closest(ROW + ".wd-can-open");
    closeOpen(row);                       // other row, or empty page -> collapse
    if (row) { row.classList.toggle("wd-open"); }
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
