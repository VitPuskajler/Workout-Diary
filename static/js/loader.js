/* --------------------------------------------------------------------------
   loader.js - "the click registered" overlay

   Shows a full screen veil with a spinning dumbbell the moment a form is
   submitted or a link is followed, and lets it die with the page when the new
   one arrives.
   Server round trips on PythonAnywhere are slow enough that without this
   you cannot tell a real click from a missclick.

   Usage - one line, anywhere before </body>:
     <script src="{{ url_for('static', filename='js/loader.js') }}"></script>

   It builds its own CSS and its own markup, so no template needs to change
   beyond that line. showLoader() / hideLoader() are exposed on window if you
   ever need to drive it by hand.
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  // Resolve the image relative to this script, so it works under any mount point.
  var src = (document.currentScript && document.currentScript.src) || "";
  var IMG = src.replace(/js\/loader\.js.*$/, "title/excercise_title.png");
  if (IMG === src) { IMG = "/static/title/excercise_title.png"; }

  var TIMEOUT = 15000; // hard stop - a dead request must never trap you mid workout
  var overlay = null;
  var timer = null;
  var lastTrigger = null; // whatever earned the .wd-clicked highlight, so hide() can undo it

  function build() {
    var css = document.createElement("style");
    css.textContent =
      "#wd-loader{position:fixed;top:0;left:0;right:0;bottom:0;z-index:2000;" +
        "display:none;align-items:center;justify-content:center;" +
        "background:rgba(255,255,255,.78);-webkit-backdrop-filter:blur(2px);" +
        "backdrop-filter:blur(2px)}" +
      "#wd-loader.wd-on{display:flex}" +
      "#wd-loader img{width:90px;max-width:32vw;height:auto;" +
        "animation:wd-spin 1.2s linear infinite}" +
      "@keyframes wd-spin{from{transform:rotate(0)}to{transform:rotate(360deg)}}" +
      "@media (prefers-reduced-motion:reduce){#wd-loader img{animation-duration:3s}}" +
      // Whatever was actually clicked/pressed, highlighted for as long as the
      // veil is up - so a screen recording shows exactly what triggered the
      // page change, not just a generic spinner. outline (not border) so it
      // never nudges layout or fights a button's own border-radius.
      ".wd-clicked{outline:3px solid #ffc107 !important;outline-offset:1px;" +
        "background-color:#ffc107 !important;color:#000 !important;" +
        "border-color:#ffc107 !important;}";
    document.head.appendChild(css);

    overlay = document.createElement("div");
    overlay.id = "wd-loader";
    overlay.setAttribute("aria-hidden", "true");
    overlay.innerHTML = '<img src="' + IMG + '" alt="Loading">';
    document.body.appendChild(overlay);
  }

  function show(e) {
    if (!overlay) { return; }

    // A form whose response is a file download never replaces the page, so
    // nothing would ever take the veil away and it would sit there until the
    // timeout below. Such a form opts out with data-wd-no-loader.
    var form = e && e.target;
    if (form && form.nodeType === 1 && form.closest &&
        form.closest("[data-wd-no-loader]")) {
      return;
    }

    // e.submitter is the actual button that triggered a real form submit
    // (not the form itself). The onchange="this.form.submit()" selects and
    // plain link clicks carry no such event, but by the time either fires
    // the element the user acted on is still the focused one.
    var trigger = (e && e.submitter) || document.activeElement;
    if (trigger && trigger.nodeType === 1 && trigger !== document.body) {
      trigger.classList.add("wd-clicked");
      lastTrigger = trigger;
    }

    overlay.classList.add("wd-on");
    clearTimeout(timer);
    timer = setTimeout(hide, TIMEOUT);
  }

  function hide() {
    if (!overlay) { return; }
    overlay.classList.remove("wd-on");
    clearTimeout(timer);
    if (lastTrigger) {
      lastTrigger.classList.remove("wd-clicked");
      lastTrigger = null;
    }
  }

  function start() {
    build();

    // Every ordinary submit - Confirm, Repeat, next_day, previous_day.
    // Forms marked data-wd-no-loader are skipped; see show().
    // Capture phase, so we still fire if something downstream stops propagation.
    document.addEventListener("submit", show, true);

    // form.submit() called from JS (the onchange="this.form.submit()" selects)
    // does NOT fire a submit event, so catch it at the source.
    var nativeSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = function () {
      show();
      return nativeSubmit.apply(this, arguments);
    };

    // Links, so the navbar and every other hyperlink give the same feedback a
    // button does. A link only earns the veil if it actually leaves the page,
    // and plenty do not - each of these exists in this app and would otherwise
    // leave the veil up until the timeout above:
    //   href="#"                the current page's own nav item
    //   data-bs-toggle          a collapse or dropdown toggle, profile.html
    //   target="_blank"         the GitHub link in index.html
    //   ctrl/cmd/middle click   the browser opens a new tab instead
    // Bubble phase on purpose, unlike the submit listener: by the time a click
    // reaches the document every handler has run, so defaultPrevented is
    // trustworthy. Missing a click that something else swallowed just means no
    // veil; showing one for a click that never navigates means a stuck veil.
    document.addEventListener("click", function (e) {
      if (e.defaultPrevented) { return; }
      if (e.button !== 0) { return; }
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) { return; }

      var link = e.target && e.target.closest && e.target.closest("a[href]");
      if (!link) { return; }
      if (link.closest("[data-wd-no-loader]")) { return; }
      if (link.hasAttribute("download")) { return; }
      if (link.hasAttribute("data-bs-toggle")) { return; }
      if (link.target && link.target !== "_self") { return; }

      var href = link.getAttribute("href") || "";
      if (!href || href.charAt(0) === "#") { return; }
      if (/^(javascript|mailto|tel|sms):/i.test(href)) { return; }

      show();
    });

    // Coming back via the browser's back button restores the old page from
    // cache - overlay and all. Clear it.
    window.addEventListener("pageshow", function (e) {
      if (e.persisted) { hide(); }
    });

    // Manual escape hatch.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { hide(); }
    });

    // Navbar hamburger menu (#navbarCollapse, same id on every page) -
    // Bootstrap only closes it on a second hit of the toggler button, so
    // tapping anywhere else on the page (the intended, obvious way to
    // dismiss it) did nothing. Close it on any click outside the open menu.
    document.addEventListener("click", function (e) {
      var menu = document.getElementById("navbarCollapse");
      if (!menu || !menu.classList.contains("show")) { return; }
      if (menu.contains(e.target)) { return; }
      if (e.target.closest && e.target.closest('[data-bs-target="#navbarCollapse"]')) { return; }

      if (window.bootstrap && window.bootstrap.Collapse) {
        window.bootstrap.Collapse.getOrCreateInstance(menu).hide();
      } else {
        menu.classList.remove("show");
      }
    });
  }

  window.showLoader = show;
  window.hideLoader = hide;

  if (document.body) {
    start();
  } else {
    document.addEventListener("DOMContentLoaded", start);
  }
})();
