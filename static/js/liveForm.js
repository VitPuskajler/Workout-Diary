/* --------------------------------------------------------------------------
   liveForm.js - log a set without reloading the page

   A POST form marked data-wd-live="#region" is sent in the background
   (fetch) instead of as a page load. The server does exactly what it always
   did - saves the set and redirects to the page (Post/Redirect/Get) - and
   fetch follows that redirect, so the answer is the whole page as a reload
   would have shown it. Only #region is taken from it and swapped in; the
   rest of the page (the stopwatch bar above all, its clock and its buttons)
   stays as it was: no flash, no jump to the top, no keyboard closing and
   opening again.

   After the swap:
     - the stopwatch gets the new #wd-sw-state (window.wdStopwatch.update),
       as if the page had loaded with it;
     - a "wd-swapped" event on document, for the scripts that set up the
       elements inside the region (rowExpand.js, the page's own).

   Falls back to the plain form submit wherever it cannot do this (no fetch,
   the answer is some other page - the login, say - or no #region in it).
   A request that fails on the way (no signal in the gym) is NOT sent again
   by itself - it may have reached the server, and a second send would log
   the set twice. The typed numbers stay in the fields and a note says so.

   Load it AFTER partials/_stopwatch.html: that one adds its hidden fields
   (sw_start, set_started...) on the same submit event, and listeners on one
   element run in the order they were added.
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  if (!window.fetch || !window.DOMParser || !window.URLSearchParams) return;

  var wdT = window.wdT || function (text) { return text; };
  var busy = false;

  // The button that sent the form. e.submitter is missing on older Safari,
  // so remember the last submit button pressed as well.
  var lastButton = null;
  document.addEventListener("click", function (e) {
    var button = e.target.closest && e.target.closest("button[type=submit], input[type=submit]");
    if (button && button.form && button.form.hasAttribute("data-wd-live")) lastButton = button;
  }, true);

  function hideLoader() {
    if (window.hideLoader) window.hideLoader();
  }

  function warn(region, text) {
    var old = document.getElementById("wd-live-error");
    if (old) old.remove();
    var note = document.createElement("div");
    note.id = "wd-live-error";
    note.className = "alert alert-warning alert-dismissible fade show mx-auto my-2 py-2";
    note.style.maxWidth = "540px";
    note.setAttribute("role", "alert");
    note.textContent = text;
    var close = document.createElement("button");
    close.type = "button";
    close.className = "btn-close py-2";
    close.setAttribute("data-bs-dismiss", "alert");
    close.setAttribute("aria-label", wdT("Close"));
    note.appendChild(close);
    region.insertBefore(note, region.firstChild);
  }

  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form || !form.matches || !form.matches("form[data-wd-live]") || e.defaultPrevented) return;
    if (String(form.method).toLowerCase() !== "post") return;
    var selector = form.getAttribute("data-wd-live");
    var region = document.querySelector(selector);
    if (!region || !region.contains(form)) return;

    e.preventDefault();
    if (busy) return;                     // a second tap while the first is on its way
    busy = true;

    var data = new FormData(form);
    var button = e.submitter || lastButton;
    if (button && button.name) data.append(button.name, button.value || "");
    lastButton = null;

    // The phone's keyboard closes as it would on a reload.
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();

    fetch(form.action, {
      method: "POST",
      body: new URLSearchParams(data),
      credentials: "same-origin",
      headers: { "X-Requested-With": "fetch" },
    })
      .then(function (response) {
        // Redirected somewhere else (logged out, no workout plan): go there.
        if (!response.ok || new URL(response.url).pathname !== new URL(form.action, location.href).pathname) {
          location.href = response.url;
          return null;
        }
        return response.text();
      })
      .then(function (html) {
        if (html === null) return;
        var doc = new DOMParser().parseFromString(html, "text/html");
        var fresh = doc.querySelector(selector);
        // No region, or one that swallowed the stopwatch (an unclosed tag in
        // the template makes the browser end it later than it looks): a
        // plain reload - the set is saved already, so it is a safe GET.
        if (!fresh || fresh.querySelector("#wd-sw") || region.querySelector("#wd-sw")) {
          location.reload();
          return;
        }
        region.replaceWith(document.importNode(fresh, true));

        var state = doc.getElementById("wd-sw-state");
        if (state && window.wdStopwatch) {
          try { window.wdStopwatch.update(JSON.parse(state.textContent)); } catch (err) { }
        }
        document.dispatchEvent(new CustomEvent("wd-swapped"));
      })
      .catch(function () {
        warn(region, wdT("No connection. Reload the page to see whether the set was saved."));
      })
      .then(function () {
        busy = false;
        hideLoader();
      });
  });
})();
