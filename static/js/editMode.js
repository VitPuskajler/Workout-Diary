/* --------------------------------------------------------------------------
   editMode.js - "Edit" toggle with swipe-to-delete rows

   Outside Edit mode a list is read-only to the thumb: nothing can be dragged
   or deleted by accident while scrolling. Edit mode shows whatever is tagged
   .wd-edit-only (drag handles) and lets a row be swiped left, which slides out
   its red .wd-swipe-del button. That button is the confirmation - the swipe
   alone deletes nothing. What the button does is up to the page.

   Markup:
     <div data-wd-editable="some-key">            scope; the key remembers the
       <button type="button" data-wd-edit-toggle>   mode across a reload
       <tr data-wd-swipe>
         ... <td class="wd-swipe-cell"> <button class="wd-swipe-del">Delete</button>

   .wd-swipe-cell must be the row's last visible cell - the button grows out
   of its right edge, over the cells to its left.
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  var OPEN_WIDTH = 88;     // px of the Delete button once the swipe is let go
  var OPEN_AT = 45;        // px of swipe that counts as "open it"

  var css =
    "[data-wd-editable]:not(.wd-edit-on) .wd-edit-only { display: none !important; }" +
    // On the cells: touch-action does not apply to a table row itself.
    ".wd-edit-on tr[data-wd-swipe] > td { touch-action: pan-y; }" +
    ".wd-swipe-cell { position: relative; }" +
    ".wd-swipe-del { position: absolute; top: 0; right: 0; bottom: 0; width: 0; overflow: hidden;" +
    "  padding: 0; border: 0; background: #dc3545; color: #fff; font-weight: 600; white-space: nowrap;" +
    "  z-index: 2; transition: width .15s ease; }" +
    "tr.wd-swiping .wd-swipe-del { transition: none; }" +
    "tr.wd-swiped .wd-swipe-del { width: " + OPEN_WIDTH + "px; }";
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  function setMode(scope, on) {
    scope.classList.toggle("wd-edit-on", on);
    scope.querySelectorAll("[data-wd-edit-toggle]").forEach(function (btn) {
      btn.textContent = on ? "Done" : "Edit";
      btn.classList.toggle("btn-primary", on);
      btn.classList.toggle("btn-outline-secondary", !on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (!on) closeAll();
    try {
      var key = "wd_edit_" + scope.dataset.wdEditable;
      on ? sessionStorage.setItem(key, "1") : sessionStorage.removeItem(key);
    } catch (e) { }
  }

  function closeAll(except) {
    document.querySelectorAll("tr.wd-swiped").forEach(function (row) {
      if (row !== except) row.classList.remove("wd-swiped");
    });
  }

  document.querySelectorAll("[data-wd-editable]").forEach(function (scope) {
    var remembered = false;
    try { remembered = sessionStorage.getItem("wd_edit_" + scope.dataset.wdEditable) === "1"; } catch (e) { }
    setMode(scope, remembered);
  });

  document.addEventListener("click", function (e) {
    var toggle = e.target.closest("[data-wd-edit-toggle]");
    if (!toggle) return;
    var scope = toggle.closest("[data-wd-editable]");
    if (scope) setMode(scope, !scope.classList.contains("wd-edit-on"));
  });

  // ---- the swipe
  var drag = null;   // {row, x, y, horizontal}

  document.addEventListener("pointerdown", function (e) {
    var row = e.target.closest("tr[data-wd-swipe]");
    // A tap anywhere but an open Delete button puts it away again.
    if (!e.target.closest(".wd-swipe-del")) closeAll(row);
    if (!row) return;
    if (!row.closest(".wd-edit-on")) return;
    // The drag handle belongs to Sortable. A finger may start on an input -
    // the /create_workout rows are little else - but a mouse there is
    // selecting text.
    if (e.target.closest(".wd-drag-handle")) return;
    if (e.pointerType === "mouse" && e.target.closest("input, textarea, select")) return;
    drag = { row: row, x: e.clientX, y: e.clientY, horizontal: null };
  });

  document.addEventListener("pointermove", function (e) {
    if (!drag) return;
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (drag.horizontal === null) {
      if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
      drag.horizontal = Math.abs(dx) > Math.abs(dy);
      if (!drag.horizontal) { drag = null; return; }      // a scroll, leave it be
      drag.open = drag.row.classList.contains("wd-swiped");
      drag.row.classList.add("wd-swiping");
    }
    var width = Math.max(0, Math.min(OPEN_WIDTH + 30, (drag.open ? OPEN_WIDTH : 0) - dx));
    var button = drag.row.querySelector(".wd-swipe-del");
    if (button) button.style.width = width + "px";
  });

  function endDrag(e) {
    if (!drag) return;
    var row = drag.row;
    if (drag.horizontal) {
      var button = row.querySelector(".wd-swipe-del");
      var width = button ? parseFloat(button.style.width) || 0 : 0;
      if (button) button.style.width = "";
      row.classList.remove("wd-swiping");
      row.classList.toggle("wd-swiped", e.type === "pointerup" && width >= OPEN_AT);
      swallowClick = true;
      setTimeout(function () { swallowClick = false; }, 400);
    }
    drag = null;
  }
  document.addEventListener("pointerup", endDrag);
  document.addEventListener("pointercancel", endDrag);

  // The row may hold a button of its own (on /intuitive_training the exercise
  // name opens that exercise). The click that ends a swipe must not press it.
  var swallowClick = false;
  document.addEventListener("click", function (e) {
    if (!swallowClick) return;
    swallowClick = false;
    e.preventDefault();
    e.stopPropagation();
  }, true);

  // A tap on the row's trash icon (.wd-swipe-open), where there is one, slides
  // the button out too - for anyone who does not think to swipe.
  document.addEventListener("click", function (e) {
    var opener = e.target.closest(".wd-swipe-open");
    if (!opener) return;
    var row = opener.closest("tr[data-wd-swipe]");
    if (!row) return;
    closeAll(row);
    row.classList.toggle("wd-swiped");
  });
})();
