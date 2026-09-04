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

    field.readOnly = true;
    field.classList.remove("wd-note-open");

    if (notesTd) {
      notesTd.colSpan = 1;
      notesTd.classList.remove("wd-note-open");
    }
    hiddenCells.forEach(function (cell) { cell.style.display = ""; });

    field = null;
    notesTd = null;
    hiddenCells = [];
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

    input.readOnly = false;
    input.classList.add("wd-note-open");

    field = input;
    notesTd = td;
    hiddenCells = toHide;

    // Phones: focus() called in the same tick as removing readOnly is a
    // known no-op for the on-screen keyboard on some mobile browsers - the
    // readOnly removal hasn't been registered yet when focus is requested.
    // One frame later it has, and the keyboard opens as expected. Still
    // inside the same user gesture as far as iOS/Android are concerned, so
    // this isn't blocked as an unrequested focus.
    requestAnimationFrame(function () {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);   // caret at the end
    });
  }

  function isOutside(target) {
    return !(notesTd && notesTd.contains(target));
  }

  function start() {
    injectCss();

    // Read-only so tapping the narrow closed cell does not raise the
    // keyboard for a nine character field. Set from JS, so without JS the
    // field still works as a plain always-editable input.
    var inputs = document.querySelectorAll(SEL);
    for (var i = 0; i < inputs.length; i++) { inputs[i].readOnly = true; }

    document.addEventListener("click", function (e) {
      if (e.target.matches && e.target.matches(SEL)) {
        // A tap on the already-open field is just placing the cursor, same
        // as any other text field - only tapping a still-closed one opens it.
        if (field !== e.target) { open(e.target); }
        return;
      }
      if (isOutside(e.target)) { close(); }
    });

    document.addEventListener("focusin", function (e) {
      if (e.target.matches && e.target.matches(SEL)) { return; }
      if (isOutside(e.target)) { close(); }
    });

    // Keyboard: Enter/Space opens a still-closed field, same as a tap. Once
    // open, Enter must make a newline instead of reaching the page's
    // Enter-triggers-Confirm binding (bound on document, see
    // training_session.html), and Escape closes it.
    document.addEventListener("keydown", function (e) {
      if (!e.target.matches || !e.target.matches(SEL)) { return; }

      if (field === e.target) {
        if (e.key === "Enter") { e.stopPropagation(); }
        else if (e.key === "Escape") { e.stopPropagation(); close(); e.target.blur(); }
        return;
      }

      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        e.stopPropagation();
        open(e.target);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
