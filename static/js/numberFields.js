/* --------------------------------------------------------------------------
   numberFields.js - Kg, Reps and RPE on a phone's number pad

   The set fields are text boxes with inputmode, not type="number": a phone
   then opens its number pad (inputmode="decimal", Reps: "numeric" - digits
   only) instead of the full keyboard. A comma typed becomes a dot (a Slovak
   or Czech phone's pad has a comma), anything else is dropped, and the
   ranges type="number" used to check are checked here - the browser stops
   the form's submit with the message, as it did before.

   Opt in per field:
     <input type="text" inputmode="decimal" data-wd-number="decimal"
            data-min="0" data-max="10" data-step="0.5" ...>
   data-wd-number: "decimal" or "whole"; data-max and data-step optional.
   The weight's data-max follows the Kg / Lbs / Other toggle
   (#weightUnitToggle), so it is checked again when that is tapped.
-------------------------------------------------------------------------- */
(function () {
  "use strict";
  var wdT = window.wdT || function (text) { return text; };

  function check(input) {
    var raw = input.value;
    var clean = raw.replace(/,/g, ".").replace(input.dataset.wdNumber === "whole" ? /[^0-9]/g : /[^0-9.]/g, "");
    var dot = clean.indexOf(".");
    if (dot !== -1) clean = clean.slice(0, dot + 1) + clean.slice(dot + 1).replace(/\./g, "");
    if (clean !== raw) input.value = clean;

    var message = "";
    if (clean !== "" && clean !== ".") {
      var number = parseFloat(clean);
      var min = parseFloat(input.dataset.min || "0"), max = parseFloat(input.dataset.max);
      var step = parseFloat(input.dataset.step);
      if (number < min || number > max) {
        message = isNaN(max)
          ? wdT("Enter a number of {min} or more.").replace("{min}", min)
          : wdT("Enter a number from {min} to {max}.").replace("{min}", min).replace("{max}", max);
      } else if (step && Math.abs(number / step - Math.round(number / step)) > 1e-9) {
        message = wdT("Use steps of {step}, e.g. 7.5.").replace("{step}", step);
      }
    }
    input.setCustomValidity(message);
  }

  function start() {
    document.querySelectorAll("input[data-wd-number]").forEach(function (input) {
      input.addEventListener("input", function () { check(input); });
    });
    var unit = document.getElementById("weightUnitToggle");
    if (unit) {
      unit.addEventListener("click", function () {
        // after the toggle's own handler has set the new maximum
        setTimeout(function () {
          var weight = document.getElementById("weightInput");
          if (weight) check(weight);
        });
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
