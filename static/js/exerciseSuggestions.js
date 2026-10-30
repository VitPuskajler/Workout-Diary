/* --------------------------------------------------------------------------
   exerciseSuggestions.js - the exercise-name dropdown, a page at a time

   Typing asks /exercise_suggestions for the first page only: 7 names on a
   phone, 10 on a computer. The list is a little shorter than a page, so the
   half-cut last row shows there is more, and scrolling it (finger or wheel)
   fetches the next page when its end comes near. Typing on waits 150 ms
   before asking, so "squat" typed quickly is one request, not five.

   With icons, each suggestion shows its stick-figure drawing, and the one
   under the mouse plays its rep (icons/exercises/anim). A phone has no
   hover, so there only the top suggestion - the best match - moves; a whole
   list moving would be too busy to read. Nothing moves for "reduce motion".

   Usage:
     wireExerciseSuggestions(input, list, {
       url: "{{ url_for('exercise_suggestions') }}",
       icons: {                            // optional
         base: "{{ url_for('static', filename='icons/exercises/') }}",
         slugs: {{ exercise_icon_slugs|tojson }},
         choices: {{ exercise_icon_choices()|tojson }},
         animated: {{ exercise_icon_animated_slugs|tojson }},
       },
       onPick: function (name) {},         // optional, after input.value = name
     });
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  var DEBOUNCE = 150;
  var PHONE = window.matchMedia("(max-width: 576px)");
  var MOTION_OK = window.matchMedia("(prefers-reduced-motion: no-preference)");
  var NO_HOVER = window.matchMedia("(hover: none)");

  // The drawing for an exercise - same rule as exercise_icon() in server.py:
  // the one picked on /admin/exercises, else the one named after it.
  function iconSlug(icons, name) {
    var slug = icons.choices[name] || (name.toLowerCase().match(/[a-z0-9]+/g) || []).join("-");
    return icons.slugs.has(slug) ? slug : null;
  }

  var styled = false;

  function addStyle() {
    if (styled) return;
    styled = true;
    var css = document.createElement("style");
    css.textContent = ".dropdown-item .wd-exercise-icon{width:28px;height:28px;" +
      "flex:0 0 28px;margin-right:.35rem}";
    document.head.appendChild(css);
  }

  function addIcon(icons, li, name, first) {
    li.classList.add("d-flex", "align-items-center");
    var slug = iconSlug(icons, name);
    if (!slug) return;
    var img = document.createElement("img");
    var still = icons.base + slug + ".svg";
    img.src = still;
    img.alt = "";
    img.className = "wd-exercise-icon";
    li.prepend(img);

    if (!icons.animated.has(slug) || !MOTION_OK.matches) return;
    var moving = icons.base + "anim/" + slug + ".svg";
    if (NO_HOVER.matches) {
      if (first) img.src = moving;
      return;
    }
    li.addEventListener("mouseenter", function () { img.src = moving; });
    li.addEventListener("mouseleave", function () { img.src = still; });
  }

  function wire(input, list, options) {
    options = options || {};
    if (options.icons) addStyle();
    var icons = options.icons && {
      base: options.icons.base,
      slugs: new Set(options.icons.slugs),
      choices: options.icons.choices,
      animated: new Set(options.icons.animated)
    };
    var query = "";
    var offset = 0;
    var hasMore = false;
    var loading = false;
    var generation = 0;      // bumped by every keystroke: older answers are dropped
    var timer = null;
    var spinner = null;

    list.style.overflowY = "auto";
    // Reaching the end of the list must not start scrolling the page under it.
    list.style.overscrollBehavior = "contain";

    function pageSize() {
      return PHONE.matches ? 7 : 10;
    }

    function hide() {
      list.style.display = "none";
    }

    function item(name, first) {
      var li = document.createElement("li");
      li.classList.add("dropdown-item");
      li.textContent = name;
      if (icons) addIcon(icons, li, name, first);
      li.onclick = function () {
        input.value = name;
        hide();
        if (options.onPick) options.onPick(name);
      };
      return li;
    }

    function showSpinner(on) {
      if (on && !spinner) {
        spinner = document.createElement("li");
        spinner.className = "dropdown-item-text text-muted small text-center";
        spinner.textContent = "Loading…";
        list.appendChild(spinner);
      } else if (!on && spinner) {
        spinner.remove();
        spinner = null;
      }
    }

    function load(first) {
      var asked = query;
      var mine = generation;
      loading = true;
      if (!first) showSpinner(true);

      var xhr = new XMLHttpRequest();
      xhr.open("GET", options.url + "?query=" + encodeURIComponent(asked) +
        "&offset=" + offset + "&limit=" + pageSize(), true);
      xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) return;
        // Typed on since, or the field was put back (create_workout reverts
        // a collapsed row) - this answer is for a list nobody wants now.
        if (mine !== generation || input.value.trim() !== asked) return;
        loading = false;
        showSpinner(false);
        if (xhr.status !== 200) return;

        var data = JSON.parse(xhr.responseText);
        if (first) {
          list.innerHTML = "";
          list.scrollTop = 0;
        }
        data.items.forEach(function (name, i) { list.appendChild(item(name, first && i === 0)); });
        offset += data.items.length;
        hasMore = data.has_more;

        if (!list.children.length) {
          hide();
          return;
        }
        list.style.display = "block";
        if (first) {
          // Half a row short of a page, measured on the real rows - with an
          // icon they are taller than without.
          var row = list.firstElementChild.offsetHeight;
          list.style.maxHeight = hasMore ? row * (pageSize() - 0.5) + "px" : "";
        }
      };
      xhr.send();
    }

    input.addEventListener("input", function () {
      clearTimeout(timer);
      generation += 1;
      loading = false;
      showSpinner(false);
      query = input.value.trim();
      if (!query) {
        hide();
        return;
      }
      timer = setTimeout(function () {
        offset = 0;
        hasMore = false;
        load(true);
      }, DEBOUNCE);
    });

    list.addEventListener("scroll", function () {
      if (!hasMore || loading) return;
      // Two rows before the end, so the next page is usually there by the
      // time the finger gets to it.
      var row = list.firstElementChild ? list.firstElementChild.offsetHeight : 30;
      if (list.scrollTop + list.clientHeight >= list.scrollHeight - 2 * row) load(false);
    });
  }

  window.wireExerciseSuggestions = wire;
})();
