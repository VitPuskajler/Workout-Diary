/* --------------------------------------------------------------------------
   notesEdit.js - room to actually write a note

   The Notes column in the set table is about 97px wide on a phone, roughly
   nine characters. Tapping it opens a full width textarea in a row directly
   underneath, so you can see the whole note and put the caret on any line to
   fix a typo. Tap anywhere else and it closes.

   The small cell input stays the real form field - it keeps its name and is
   what gets submitted. The textarea is only an editing surface and writes
   straight back into it, so nothing about the POST changes.

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
  var MAX_HEIGHT = 200;          // px, then the textarea scrolls instead of growing
  var field = null;              // the small input currently being edited
  var editor = null;             // the <tr> holding the textarea

  function injectCss() {
    var css = document.createElement("style");
    css.textContent =
      // the cell field is now a button in disguise - it opens the editor.
      // one line tall, no resize grip, no scrollbars: it should read as the
      // single line input it replaced.
      // line-height is set to the full content box on purpose: one line fills it
      // exactly, so a note containing a newline clips at the boundary instead of
      // showing a sliver of line two.
      SEL + "{cursor:pointer;resize:none;overflow:hidden;white-space:nowrap;" +
        "height:calc(1.5em + .75rem + 2px);min-height:0;" +
        "padding-top:0;padding-bottom:0;line-height:calc(1.5em + .75rem)}" +
      // the editor row
      "tr.wd-note-editor > td{padding:.4rem .5rem;" +
        "box-shadow:inset 3px 0 0 rgba(13,110,253,.6)}" +
      "tr.wd-note-editor textarea{width:100%;text-align:left;resize:none;" +
        "overflow-y:auto;line-height:1.35}";
    document.head.appendChild(css);
  }

  function autoGrow(ta) {
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, MAX_HEIGHT) + "px";
  }

  function close() {
    if (editor && editor.parentNode) { editor.parentNode.removeChild(editor); }
    editor = null;
    field = null;
  }

  function toggle(input) {
    if (field === input) { close(); } else { open(input); }
  }

  function open(input) {
    close();

    var row = input.closest("tr");
    if (!row) { return; }

    var tr = document.createElement("tr");
    tr.className = "wd-note-editor";

    var td = document.createElement("td");
    td.colSpan = row.cells.length;

    var ta = document.createElement("textarea");
    ta.className = "form-control";
    ta.rows = 2;
    ta.value = input.value;
    // the old note lives in the placeholder on these fields - keep showing it
    ta.placeholder = input.placeholder || "";

    // Enter must make a newline here. This page binds Enter on document to the
    // Confirm button, so the event has to be stopped before it gets that far.
    ta.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.stopPropagation(); }
      if (e.key === "Escape") { e.stopPropagation(); close(); input.focus(); }
    });

    ta.addEventListener("input", function () {
      input.value = ta.value;      // the named field is always current
      autoGrow(ta);
    });

    td.appendChild(ta);
    tr.appendChild(td);
    row.parentNode.insertBefore(tr, row.nextSibling);

    field = input;
    editor = tr;

    autoGrow(ta);
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);   // caret at the end
  }

  function isOutside(target) {
    return !(editor && editor.contains(target)) && !target.closest(SEL);
  }

  function start() {
    injectCss();

    // Read-only so tapping the narrow cell does not raise the keyboard for a
    // nine character field. Set from JS, so without JS the field still works.
    var inputs = document.querySelectorAll(SEL);
    for (var i = 0; i < inputs.length; i++) { inputs[i].readOnly = true; }

    // Opening is driven by click, not focus, so that tapping the cell a second
    // time closes the editor again. focusin only ever closes.
    document.addEventListener("click", function (e) {
      if (e.target.matches && e.target.matches(SEL)) { toggle(e.target); }
      else if (isOutside(e.target)) { close(); }
    });

    document.addEventListener("focusin", function (e) {
      if (e.target.matches && e.target.matches(SEL)) { return; }
      if (isOutside(e.target)) { close(); }
    });

    // Keyboard equivalent - Enter or Space on a focused Notes cell.
    document.addEventListener("keydown", function (e) {
      if (!e.target.matches || !e.target.matches(SEL)) { return; }
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        e.stopPropagation();          // must not reach the Confirm binding
        toggle(e.target);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
