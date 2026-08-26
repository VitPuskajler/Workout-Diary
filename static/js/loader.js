/* --------------------------------------------------------------------------
   loader.js - "the click registered" overlay

   Shows a full screen veil with a spinning dumbbell the moment a form is
   submitted, and lets it die with the page when the new one arrives.
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
      "@media (prefers-reduced-motion:reduce){#wd-loader img{animation-duration:3s}}";
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

    overlay.classList.add("wd-on");
    clearTimeout(timer);
    timer = setTimeout(hide, TIMEOUT);
  }

  function hide() {
    if (!overlay) { return; }
    overlay.classList.remove("wd-on");
    clearTimeout(timer);
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

    // Coming back via the browser's back button restores the old page from
    // cache - overlay and all. Clear it.
    window.addEventListener("pageshow", function (e) {
      if (e.persisted) { hide(); }
    });

    // Manual escape hatch.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { hide(); }
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
