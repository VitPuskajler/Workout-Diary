/* --------------------------------------------------------------------------
   notesEdit.js - room to actually write a note

   The Notes column in the set table is about 97px wide on a phone, roughly
   nine characters. Tapping it grows the cell IN PLACE, covering the Kg /
   Reps / RPE cells of the same row (they're hidden, not lost - their inputs
   still submit normally, display:none has no effect on form submission),
   instead of pushing a whole new row underneath.

   It stays exactly one row tall even while open - a long note scrolls
   inside that one row (mouse wheel, or arrow keys once the caret reaches
   the top/bottom line - both native textarea behaviour, no extra JS) rather
   than growing the row and pushing the rest of the table down.

   The field is the real form input the whole time - no separate proxy
   editor - so nothing needs to be copied anywhere before it saves. Tap
   anywhere else on the page (including the Confirm button) and it collapses
   back, and whatever you typed is already sitting in the field to submit.

   The field is never readOnly - a phone's on-screen keyboard only reliably
   appears when focus() happens natively, as the direct and immediate result
   of the user's own tap on an already-editable field. Toggling readOnly off
   and calling focus() ourselves, even one frame later, is a step removed
   from that and phones silently skip the keyboard. So the tap itself is
   what focuses the field (the browser's own doing, always reliable) - this
   script just reacts to that focus to do the visual expand.

   Opt in per field:
     <textarea rows="1" name="notes" data-note ...></textarea>

   Then one line before </body>:
     <script src="{{ url_for('static', filename='js/notesEdit.js') }}"></script>

   If this script fails to load, the cell inputs stay plain editable inputs and
   the page works exactly as it did before.
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  var SEL = "[data-note]";
  var EDGE = "2px solid rgba(13,110,253,.6)";   // the highlight around the open cell

  var field = null;              // the [data-note] textarea currently open, or null
  var notesTd = null;            // its containing <td>
  var hiddenCells = [];          // the Kg/Reps/RPE <td>s hidden while it's open

  function injectCss() {
    var css = document.createElement("style");
    css.textContent =
      // the cell field is a button in disguise when closed - it opens the
      // editor. one line tall, no resize grip, no scrollbars: it should read
      // as the single line input it replaced.
      SEL + "{cursor:pointer;resize:none;overflow:hidden;white-space:nowrap;" +
        "height:calc(1.5em + .75rem + 2px);min-height:0;" +
        "padding-top:0;padding-bottom:0;line-height:calc(1.5em + .75rem)}" +
      // Open state: same one-row BOX height as closed - width comes from the
      // colSpan below, not height. But a normal line-height for the actual
      // text, not the closed state's (line-height == box height, to centre
      // one line in it) - inheriting that made every wrapped line sit in its
      // own oversized slot, all gap. Normal line-height packs them close, so
      // part of a second line naturally peeks in - the cue that there's more
      // to scroll to, instead of a dead gap before it. Stays text-center
      // (the field's own Bootstrap class, untouched here) both empty - so
      // the "..." placeholder stays centred, not stuck to the left - and
      // while typing.
      SEL + ".wd-note-open{cursor:text;white-space:pre-wrap;overflow-y:auto;" +
        "line-height:1.3}" +
      "td.wd-note-open{border:" + EDGE + ";background:#fff}";
    document.head.appendChild(css);
  }

  function close() {
    if (!field) { return; }

    var closing = field;
    field.classList.remove("wd-note-open");

    if (notesTd) {
      notesTd.colSpan = 1;
      notesTd.classList.remove("wd-note-open");
    }
    hiddenCells.forEach(function (cell) { cell.style.display = ""; });

    field = null;
    notesTd = null;
    hiddenCells = [];

    // Explicit: clicking blank page content doesn't itself move focus away
    // from a focused field (nothing else claims it), so without this the
    // keyboard would stay up and the field would stay focused right through
    // its own collapse.
    closing.blur();
  }

  function open(input) {
    if (field === input) { return; }
    close();

    var row = input.closest("tr");
    var td = input.closest("td");
    if (!row || !td) { return; }

    // Every <td> before the Notes cell in this row - Kg, Reps, RPE - hidden
    // (not removed) so the Notes cell can colSpan across their fixed-layout
    // width. Their inputs keep submitting; display:none doesn't touch that.
    var toHide = [];
    var sib = td.previousElementSibling;
    while (sib) { toHide.unshift(sib); sib = sib.previousElementSibling; }
    toHide.forEach(function (cell) { cell.style.display = "none"; });

    td.colSpan = toHide.length + 1;
    td.classList.add("wd-note-open");
    input.classList.add("wd-note-open");

    field = input;
    notesTd = td;
    hiddenCells = toHide;

    input.setSelectionRange(input.value.length, input.value.length);   // caret at the end
  }

  function isOutside(target) {
    return !(notesTd && notesTd.contains(target));
  }

  function start() {
    injectCss();

    // The field is a real, always-editable textarea - see the file header
    // for why. Focusing it (tap, or Tab) is what opens it.
    document.addEventListener("focusin", function (e) {
      if (e.target.matches && e.target.matches(SEL)) { open(e.target); return; }
      if (isOutside(e.target)) { close(); }
    });

    // Tapping blank page content doesn't move focus by itself (see close()),
    // so closing on an outside click needs its own listener - this is also
    // what makes hitting Confirm collapse the field (it's outside, too; the
    // value is already live in the field, so the submit that follows saves
    // it same as always).
    document.addEventListener("click", function (e) {
      if (isOutside(e.target)) { close(); }
    });

    // Enter must make a newline while typing a note, not reach the page's
    // Enter-triggers-Confirm binding (bound on document, see
    // training_session.html) - a note field only ever has focus while open,
    // so any keydown reaching it here is mid-edit. Escape closes it.
    document.addEventListener("keydown", function (e) {
      if (!e.target.matches || !e.target.matches(SEL)) { return; }
      if (e.key === "Enter") { e.stopPropagation(); }
      else if (e.key === "Escape") { e.stopPropagation(); close(); }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
