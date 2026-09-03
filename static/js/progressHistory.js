/* --------------------------------------------------------------------------
   progressHistory.js - "Show all" / "Hide" toggle for a /progress table

   Each exercise table on /progress starts collapsed to its last two logged
   sessions (older rows tagged "wd-hist-older" and hidden by CSS - see
   progress.html). This just flips a class on the table to reveal them and
   swaps the toggle's own label - it never touches the data itself, so
   "Copy all" (built server-side from the full history) is unaffected either
   way.

   The toggle is a <span>, not a <button> - on purpose, so a click on it
   still runs through progressEdit.js's unsaved-changes guard like any other
   navigation, instead of being exempted the way the edit toolbar's own
   buttons are.
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  function toggle(el) {
    if (!el.classList.contains("wd-history-has-more")) return;

    var targetId = el.dataset.target;
    var table = targetId && document.getElementById(targetId);
    if (!table) return;

    var expanded = table.classList.toggle("wd-history-expanded");
    el.textContent = expanded ? "Hide ▴" : "Show all ▾";
    el.setAttribute("aria-expanded", expanded ? "true" : "false");
  }

  document.addEventListener("click", function (e) {
    var el = e.target.closest(".wd-history-toggle");
    if (el) toggle(el);
  });

  // Space/Enter, to match native button behaviour - the toggle is a <span>
  // (see file header for why), so it needs this spelled out explicitly.
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" && e.key !== " ") return;
    var el = e.target.closest(".wd-history-toggle");
    if (!el) return;
    e.preventDefault();
    toggle(el);
  });
})();
