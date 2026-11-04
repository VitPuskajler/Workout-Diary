/* --------------------------------------------------------------------------
   bodyChart.js - the body weight chart on /body (body_measurement.html).

   Reads #bodyData (body_measurement() in server.py):
     {weights: [{id, date: "YYYY-MM-DD", weight}],
      measurements: [{id, date, values: {field: number}}],
      fields: [{name, label, unit}]}
   and draws the weight as a line over real time (a gap of a month looks like
   a month). The #bodyPeriod dropdown narrows it to the last N days.

   Tapping a point opens #detailModal: that day's weight and the measurements
   nearest to it (within NEAR_DAYS), each with its change since the
   measurement before. A day that has measurements of its own is drawn as a
   diamond. The newest measurements also sit under the chart, so they show
   even with no weight logged.

   Needs Chart.js (no date adapter: the x axis is plain epoch ms).
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  var wdT = window.wdT || function (text) { return text; };

  var dataTag = document.getElementById("bodyData");
  if (!dataTag) return;
  var data = JSON.parse(dataTag.textContent);

  var DAY = 24 * 60 * 60 * 1000;
  var NEAR_DAYS = 14;

  // "2026-11-04" -> local midnight. new Date("2026-11-04") would be UTC
  // midnight, a day early west of Greenwich.
  function parseDay(text) {
    var p = text.split("-");
    return new Date(+p[0], +p[1] - 1, +p[2]).getTime();
  }

  function formatDay(ms) {
    var d = new Date(ms);
    return d.getDate() + "." + (d.getMonth() + 1) + "." + d.getFullYear();
  }

  function isoToday() {
    var d = new Date();
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  function number(value) {
    return (Math.round(value * 10) / 10).toString();
  }

  var weights = data.weights.map(function (w) {
    return { id: w.id, x: parseDay(w.date), y: w.weight, timeOfDay: w.time_of_day,
             weighedAt: w.weighed_at, fasted: w.fasted, afterBowel: w.after_bowel };
  });

  var TIMES = { morning: wdT("Morning"), noon: wdT("Noon"), evening: wdT("Evening") };

  // "Morning", or the exact time for a custom one - "" when not recorded.
  function timeText(point) {
    if (point.timeOfDay === "custom") return point.weighedAt || "";
    return TIMES[point.timeOfDay] || "";
  }

  function yesNo(value) {
    return value === true ? wdT("Yes") : value === false ? wdT("No") : null;
  }
  var measurements = data.measurements.map(function (m) {
    return { id: m.id, x: parseDay(m.date), values: m.values };
  });
  var measuredDays = {};
  measurements.forEach(function (m) { measuredDays[m.x] = true; });

  // Custom time of day: the exact time, required then.
  var weighedAt = document.getElementById("weighedAt");
  document.querySelectorAll(".js-time-of-day").forEach(function (radio) {
    radio.addEventListener("change", function () {
      var custom = radio.value === "custom" && radio.checked;
      weighedAt.classList.toggle("d-none", !custom);
      weighedAt.required = custom;
      if (custom && !weighedAt.value) {
        // Now, to adjust - most people log right after stepping off the scale.
        var now = new Date();
        weighedAt.value = (now.getHours() < 10 ? "0" : "") + now.getHours() + ":" +
                          (now.getMinutes() < 10 ? "0" : "") + now.getMinutes();
      }
      if (custom) weighedAt.focus();
    });
  });

  // The forms: today's date (the browser's own day), and the latest value of
  // each measurement as its placeholder.
  document.querySelectorAll(".js-today").forEach(function (input) {
    input.value = isoToday();
    input.max = isoToday();
  });
  var latest = measurements.length ? measurements[measurements.length - 1] : null;
  if (latest) {
    document.querySelectorAll(".js-measure").forEach(function (input) {
      var value = latest.values[input.dataset.field];
      if (value !== undefined) input.placeholder = number(value);
    });
  }

  // ---- measurement tables --------------------------------------------------

  function previousOf(m) {
    var index = measurements.indexOf(m);
    return index > 0 ? measurements.slice(0, index) : [];
  }

  // label | value | change since the last measurement that had this field.
  function measurementTable(m) {
    var before = previousOf(m);
    var table = document.createElement("table");
    table.className = "table table-sm wd-measure-table mb-0";
    var body = document.createElement("tbody");
    data.fields.forEach(function (field) {
      var value = m.values[field.name];
      if (value === undefined) return;
      var earlier = null;
      for (var i = before.length - 1; i >= 0; i--) {
        if (before[i].values[field.name] !== undefined) { earlier = before[i].values[field.name]; break; }
      }
      var row = document.createElement("tr");
      var label = document.createElement("td");
      label.textContent = field.label;
      var cell = document.createElement("td");
      cell.textContent = number(value) + " " + field.unit;
      var change = document.createElement("td");
      if (earlier !== null) {
        var diff = Math.round((value - earlier) * 10) / 10;
        change.textContent = (diff > 0 ? "+" : diff < 0 ? "−" : "±") + number(Math.abs(diff));
        change.className = diff === 0 ? "wd-delta-none" : "small";
      }
      row.appendChild(label);
      row.appendChild(cell);
      row.appendChild(change);
      body.appendChild(row);
    });
    table.appendChild(body);
    return table;
  }

  function measurementBlock(m, heading) {
    var box = document.createElement("div");
    var title = document.createElement("h3");
    title.className = "h6";
    title.textContent = heading.replace("{date}", formatDay(m.x));
    box.appendChild(title);
    var before = previousOf(m);
    if (before.length) {
      var note = document.createElement("p");
      note.className = "small text-body-secondary mb-1";
      note.textContent = wdT("Change since {date}").replace("{date}", formatDay(before[before.length - 1].x));
      box.appendChild(note);
    }
    box.appendChild(measurementTable(m));
    return box;
  }

  var latestBox = document.getElementById("latestMeasurements");
  if (latestBox && latest) {
    var card = document.createElement("div");
    card.className = "border rounded p-3";
    card.appendChild(measurementBlock(latest, wdT("Latest measurements") + " · {date}"));
    latestBox.appendChild(card);
  }

  // ---- tapped point --------------------------------------------------------

  var modalEl = document.getElementById("detailModal");
  var detailModal = modalEl && window.bootstrap ? new bootstrap.Modal(modalEl) : null;

  function nearestMeasurement(x) {
    var best = null;
    measurements.forEach(function (m) {
      var gap = Math.abs(m.x - x);
      if (gap <= NEAR_DAYS * DAY && (best === null || gap < Math.abs(best.x - x))) best = m;
    });
    return best;
  }

  function showDetail(point) {
    if (!detailModal) return;
    document.getElementById("detailModalLabel").textContent =
      formatDay(point.x) + " · " + number(point.y) + " kg";
    var body = document.getElementById("detailBody");
    body.textContent = "";
    // How it was weighed - only what was recorded.
    var conditions = [
      [wdT("Time of day"), timeText(point) || null],
      [wdT("Fasted"), yesNo(point.fasted)],
      [wdT("After a bowel movement"), yesNo(point.afterBowel)],
    ].filter(function (pair) { return pair[1]; });
    if (conditions.length) {
      var list = document.createElement("table");
      list.className = "table table-sm mb-3";
      var rows = document.createElement("tbody");
      conditions.forEach(function (pair) {
        var row = document.createElement("tr");
        var key = document.createElement("td");
        key.className = "text-body-secondary";
        key.textContent = pair[0];
        var value = document.createElement("td");
        value.className = "text-end";
        value.textContent = pair[1];
        row.appendChild(key);
        row.appendChild(value);
        rows.appendChild(row);
      });
      list.appendChild(rows);
      body.appendChild(list);
    }
    var m = nearestMeasurement(point.x);
    if (m) {
      body.appendChild(measurementBlock(m, wdT("Measurements from {date}")));
    } else {
      var none = document.createElement("p");
      none.className = "text-body-secondary mb-0";
      none.textContent = wdT("No body measurements around this date.");
      body.appendChild(none);
    }
    var weightForm = document.getElementById("deleteWeightForm");
    weightForm.querySelector("[name=id]").value = point.id;
    var measureForm = document.getElementById("deleteMeasureForm");
    measureForm.querySelector("[name=id]").value = m ? m.id : "";
    measureForm.classList.toggle("d-none", !m);
    detailModal.show();
  }

  // ---- chart ---------------------------------------------------------------

  var canvas = document.getElementById("bodyChart");
  var empty = document.getElementById("bodyChartEmpty");
  var period = document.getElementById("bodyPeriod");
  if (!canvas || typeof Chart === "undefined") return;

  var chart = new Chart(canvas, {
    type: "line",
    data: {
      datasets: [{
        data: [],
        borderColor: "#0d6efd",
        backgroundColor: "rgba(13, 110, 253, .12)",
        fill: true,
        tension: 0.25,
        pointRadius: function (ctx) { return measuredDays[ctx.raw && ctx.raw.x] ? 7 : 4; },
        pointHoverRadius: 9,
        pointHitRadius: 14,
        pointStyle: function (ctx) { return measuredDays[ctx.raw && ctx.raw.x] ? "rectRot" : "circle"; },
        pointBackgroundColor: function (ctx) { return measuredDays[ctx.raw && ctx.raw.x] ? "#198754" : "#0d6efd"; },
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      parsing: false,
      interaction: { mode: "nearest", intersect: false, axis: "x" },
      scales: {
        x: {
          type: "linear",
          ticks: {
            maxTicksLimit: 6,
            callback: function (value) { return formatDay(value); },
          },
        },
        y: {
          ticks: { callback: function (value) { return number(value) + " kg"; } },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: function (items) { return formatDay(items[0].raw.x); },
            label: function (item) {
              var text = number(item.raw.y) + " kg";
              var when = timeText(item.raw);
              if (when) text += " · " + when;
              return measuredDays[item.raw.x] ? text + " · ◆" : text;
            },
          },
        },
      },
      onClick: function (event, elements) {
        if (elements.length) showDetail(chart.data.datasets[0].data[elements[0].index]);
      },
    },
  });

  function draw() {
    var days = period.value === "all" ? null : +period.value;
    var from = days === null ? -Infinity : parseDay(isoToday()) - days * DAY;
    var shown = weights.filter(function (w) { return w.x >= from; });
    chart.data.datasets[0].data = shown;
    // One point alone would sit on an axis zero days wide - give it a week
    // either side.
    var x = chart.options.scales.x;
    if (shown.length === 1) {
      x.min = shown[0].x - 7 * DAY;
      x.max = shown[0].x + 7 * DAY;
    } else {
      delete x.min;
      delete x.max;
    }
    chart.update();
    empty.textContent = weights.length
      ? wdT("No weight in this period.")
      : wdT("No weight logged yet. Log your first one above.");
    empty.classList.toggle("d-none", shown.length > 0);
  }

  period.addEventListener("change", draw);
  draw();
})();
