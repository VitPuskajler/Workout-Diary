/* --------------------------------------------------------------------------
   notesEdit.js - room to actually write a note

   The Notes column in the set table is about 97px wide on a phone, roughly
   nine characters. Tapping it lays the field over the Kg / Reps / RPE cells
   of the same row, instead of pushing a whole new row underneath.

   Over them, not instead of them: those cells stay where they are, visible
   to the browser, only covered. The iPhone keyboard's up/down arrows step
   through the fields the browser can see - with the cells hidden, "up" from
   a note skipped this row's RPE and landed in the set above it. Covered,
   "up" goes to RPE, and moving there closes the note.

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

  function injectCss() {
    var css = document.createElement("style");
    css.textContent =
      // the cell field is a button in disguise when closed - it opens the
      // editor. one line tall, no resize grip, no scrollbars: it should read
      // as the single line input it replaced.
      SEL + "{cursor:pointer;resize:none;overflow:hidden;white-space:nowrap;" +
        "height:calc(1.5em + .75rem + 2px);min-height:0;" +
        "padding-top:0;padding-bottom:0;line-height:calc(1.5em + .75rem)}" +
      // Open state: same one-row BOX height as closed - width comes from
      // open() below, not height. But a normal line-height for the actual
      // text, not the closed state's (line-height == box height, to centre
      // one line in it) - inheriting that made every wrapped line sit in its
      // own oversized slot, all gap. Normal line-height packs them close, so
      // part of a second line naturally peeks in - the cue that there's more
      // to scroll to, instead of a dead gap before it.
      //
      // Alignment: writing starts from the left, like any normal text field
      // (overriding the field's own Bootstrap text-center class, which is
      // !important - so this has to be too). The one exception is the
      // generic "..." hint on a genuinely blank note (the brand new set's
      // empty row) - that stays centred, matching the closed state's look.
      //
      // An EXISTING set's note is a different case even though its field is
      // also technically empty: the old note text lives in placeholder=,
      // not value= (same pattern as the Kg/Reps/RPE fields - leave it alone
      // and the old value is kept, type something and it's replaced). That
      // placeholder is real content, not a blank-slate hint, so it must
      // stay left-aligned like typed text does - a plain :placeholder-shown
      // match cannot tell "..." apart from that and centred it too, which is
      // exactly what put the caret on an empty field slap in the middle of
      // a previous note. The literal [placeholder="..."] match is what
      // actually narrows this to the blank-slate case alone.
      SEL + ".wd-note-open{cursor:text;white-space:pre-wrap;overflow-y:auto;" +
        "line-height:1.3;text-align:left!important}" +
      SEL + ".wd-note-open[placeholder=\"...\"]:placeholder-shown{text-align:center!important}" +
      SEL + ".wd-note-open{position:absolute;z-index:3;background:#fff;border:" + EDGE + "}" +
      "td.wd-note-open{position:relative}";
    document.head.appendChild(css);
  }

  function close() {
    if (!field) { return; }

    var closing = field;
    field.classList.remove("wd-note-open");

    ["top", "left", "width"].forEach(function (side) { closing.style[side] = ""; });
    if (notesTd) { notesTd.classList.remove("wd-note-open"); }

    field = null;
    notesTd = null;

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

    // From the row's first cell (Kg) to the Notes cell's right edge, inside
    // the same padding the closed field has - measured before it moves.
    var first = row.cells[0].getBoundingClientRect();
    var box = input.getBoundingClientRect();
    var cell = td.getBoundingClientRect();
    var pad = box.left - cell.left;

    td.classList.add("wd-note-open");
    input.classList.add("wd-note-open");
    input.style.top = (box.top - cell.top) + "px";
    input.style.left = (first.left - cell.left + pad) + "px";
    input.style.width = (box.right - first.left - pad) + "px";

    field = input;
    notesTd = td;

    // The closed field is one clipped, unwrapped line showing maybe the
    // first ten characters - a tap on it lands the caret wherever that
    // narrow strip happens to map to (usually mid-word, in whatever the
    // first couple of words are), which has nothing to do with where the
    // user actually wants to write. End of the note is the predictable,
    // useful spot - ready to keep writing, like re-opening any note.
    //
    // Deferred a frame: set immediately, it would still be positioned
    // against the OLD narrow single-line layout, an instant before the
    // lay-over above widens it - the browser doesn't recompute
    // where that caret renders just because the layout changed under it.
    // One frame later, the wider layout has settled and it renders correctly.
    var pos = input.value.length;
    requestAnimationFrame(function () {
      if (field === input) { input.setSelectionRange(pos, pos); }
    });
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

    // The open field is placed in pixels over its row - turning the phone
    // changes the row, so it closes rather than sit in the wrong place.
    window.addEventListener("orientationchange", close);

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
