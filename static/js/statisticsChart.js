/* --------------------------------------------------------------------------
   statisticsChart.js - the interactive progress chart shared by
   period_statistics.html and mesocycle_statistics.html.

   Reads a #chartData <script type="application/json"> tag (shaped like
   exercise_progress_chart_data()'s return value: {exercise_name,
   period_label, dates, weights, reps}) and draws it into a #progressChart
   <canvas>. Requires Chart.js and chartjs-plugin-datalabels to already be
   loaded (see the <script src> tags in whichever page includes this file).

   Used to be a server-rendered matplotlib PNG - a plain image cannot offer
   hover/tap tooltips, which is the whole point, so the server now just
   hands over raw JSON and this draws it client-side instead.
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  var dataTag = document.getElementById("chartData");
  var canvas = document.getElementById("progressChart");
  if (!dataTag || !canvas || typeof Chart === "undefined") return;

  var data = JSON.parse(dataTag.textContent);
  if (!data || !data.dates || !data.dates.length) return;

  Chart.register(ChartDataLabels);

  // Every value is the goal, but a data-label glued to every point on a
  // 30-point, 360px-wide phone chart just draws a smear of overlapping
  // digits - worse than showing nothing. So: measure how much horizontal
  // room each point actually gets and only turn static labels on when they
  // would not collide. Below that density, the point's own tap/hover
  // tooltip (always on, regardless of this) is how you read the value -
  // same information, just one tap away instead of glued to the chart.
  var MIN_PX_PER_LABEL = 28;
  var plotWidth = canvas.parentElement.clientWidth - 56; // rough y-axis gutter
  var pxPerPoint = data.dates.length > 1 ? plotWidth / data.dates.length : plotWidth;
  var showAllLabels = pxPerPoint >= MIN_PX_PER_LABEL;

  new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: data.dates,
      datasets: [{
        label: "Weight (kg)",
        data: data.weights,
        borderColor: "#0d6efd",
        backgroundColor: "#0d6efd",
        pointBackgroundColor: "#0d6efd",
        pointRadius: 4,
        // A generous invisible tap target around each point - a fingertip
        // is much wider than a rendered dot.
        pointHitRadius: 22,
        pointHoverRadius: 7,
        tension: 0.15,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      // "nearest" + no-intersect: tapping/hovering anywhere near a point
      // (not just exactly on the dot) triggers its tooltip - essential on
      // a touchscreen.
      interaction: { mode: "nearest", intersect: false, axis: "x" },
      plugins: {
        title: {
          display: true,
          text: data.exercise_name + (data.period_label ? " - " + data.period_label : ""),
          // A point sitting near the top of the y-axis would otherwise
          // have its rep-count label collide with the title text right
          // above the plot area - this is what actually reserves room
          // between them (a plain layout padding on the chart just pushes
          // the title itself down, it does not widen the title-to-plot gap).
          padding: { top: 6, bottom: 22 },
        },
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              var i = ctx.dataIndex;
              return ctx.parsed.y + " kg × " + data.reps[i] + " reps";
            }
          }
        },
        datalabels: {
          display: showAllLabels,
          align: "top",
          anchor: "end",
          offset: 4,
          clamp: true,
          // Bare rep count, same convention the old matplotlib chart used -
          // "reps" would not fit at this density, and the tooltip already
          // spells the unit out in full.
          formatter: function (value, ctx) {
            return data.reps[ctx.dataIndex];
          },
          font: { size: 10, weight: "bold" },
          color: "#198754",
        }
      },
      scales: {
        y: {
          title: { display: true, text: "Weight (kg)" },
          beginAtZero: false,
        },
        x: {
          ticks: { autoSkip: true, maxRotation: 45, minRotation: 0 },
        }
      }
    }
  });
})();
