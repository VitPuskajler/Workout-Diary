/* --------------------------------------------------------------------------
   progressEdit.js - inline editing for one logged set on /progress

   Companion to rowExpand.js. That file stays generic (it just opens/closes a
   note panel); this file owns everything domain-specific: turning Reps /
   Weight / RPE / Notes for a single entry into editable fields, saving them
   over AJAX, and guarding against losing an in-progress edit.

   Wiring, all opt-in per table via the "wd-editable" class (see rowExpand.js):
     - "wd:row-opened"   -> build the small green pencil button in the panel
     - "wd:row-closing"  -> snap the row back to view mode if it was mid-edit

   Only one row can be open at a time (rowExpand.js already enforces that),
   so a single module-level "current" record is enough state.

   Unsaved-changes guard: a capturing document click listener (added only
   while the current edit is dirty) blocks whatever the click would have
   done - opening another row, following a nav link, anything - and asks
   first. Confirming "Discard" replays the original click once the row is
   back to a clean state. A native beforeunload prompt is the fallback for
   the one thing a click listener cannot see: the mesocycle/day dropdown,
   which navigates on "change" rather than "click".
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  // The page's language - partials/_js_translations.html. English without it.
  var wdT = window.wdT || function (text) { return text; };

  var current = null;      // the one open, editable row - see buildViewToolbar()
  var pendingTarget = null; // element to re-click once a dirty edit is resolved
  var unsavedModal = null;
  var fixUnitModal = null;
  var fixUnitTargetUnit = null; // unit selected in the fix-unit popup, before submit
  var deleteModal = null;

  var UNIT_LABELS = { kg: "Kg", lbs: "Lbs", other: wdT("Other") };
  var KG_PER_LB = 0.45359237;

  // ---- the odd unit out ---------------------------------------------------
  // A set logged in another unit than the rest of its exercise is most
  // likely the Kg/Lbs toggle forgotten during the workout - one set of the
  // day, or every set of one day. Compared against the unit most of the
  // table was logged in, and against the unit most of that day's sets were
  // logged in. A tie means no clear "usual" unit, so it marks nothing.
  function majority(counts) {
    var best = null, bestN = 0, tie = false;
    for (var unit in counts) {
      if (!Object.prototype.hasOwnProperty.call(counts, unit)) continue;
      if (counts[unit] > bestN) { best = unit; bestN = counts[unit]; tie = false; }
      else if (counts[unit] === bestN) { tie = true; }
    }
    return tie ? null : best;
  }

  function markOddUnits(table) {
    var rows = table.querySelectorAll("tbody > tr[data-entry-id]");
    var all = {}, byDay = {}, weighed = [];
    for (var i = 0; i < rows.length; i++) {
      var td = rows[i].querySelector('[data-field="weight"]');
      if (!td) continue;
      td.classList.remove("wd-unit-odd");
      td.removeAttribute("title");
      if (!td.dataset.weight) continue;          // "-": nothing to compare
      var unit = rows[i].dataset.unit || "kg";
      var day = rows[i].dataset.date || "";
      all[unit] = (all[unit] || 0) + 1;
      byDay[day] = byDay[day] || {};
      byDay[day][unit] = (byDay[day][unit] || 0) + 1;
      weighed.push({ td: td, unit: unit, day: day });
    }
    var usual = majority(all);
    weighed.forEach(function (w) {
      var dayUsual = majority(byDay[w.day]) || usual;
      if ((usual && w.unit !== usual) || (dayUsual && w.unit !== dayUsual)) {
        w.td.classList.add("wd-unit-odd");
        w.td.title = wdT("Another unit than the other sets of this exercise - forgot the Kg/Lbs switch?");
      }
    });
  }

  function markAllOddUnits() {
    var tables = document.querySelectorAll("table.wd-editable");
    for (var i = 0; i < tables.length; i++) markOddUnits(tables[i]);
  }

  function roundTo(num, places) {
    var f = Math.pow(10, places);
    return Math.round(num * f) / f;
  }

  function textOf(td) {
    var span = td.querySelector(".wd-view-value");
    return (span ? span.textContent : td.textContent).trim();
  }

  function setViewSpan(td, text) {
    td.innerHTML = "";
    var span = document.createElement("span");
    span.className = "wd-view-value";
    span.textContent = text;
    td.appendChild(span);
  }

  // The Weight cell as the page draws it (progress.html): the number as it
  // was logged plus its unit ("kg" / "lbs" - "other" has none), or "-" for
  // no weight. The bare number lives in data-weight, for editing.
  function renderWeight(td, value, unit) {
    var num = Number(value) || 0;
    td.innerHTML = "";
    td.dataset.weight = num ? String(num) : "";
    var span = document.createElement("span");
    span.className = "wd-view-value";
    span.textContent = num ? String(num) : "-";
    td.appendChild(span);
    unit = unit || "kg";
    if (num && (unit === "kg" || unit === "lbs")) {
      var unitEl = document.createElement("span");
      unitEl.className = "wd-unit wd-unit-" + unit;
      unitEl.textContent = unit;
      td.appendChild(unitEl);
    }
  }

  function makeNumberInput(value, attrs) {
    var input = document.createElement("input");
    input.type = "number";
    input.className = "form-control form-control-sm wd-field-input";
    for (var key in attrs) {
      if (Object.prototype.hasOwnProperty.call(attrs, key)) {
        input.setAttribute(key, attrs[key]);
      }
    }
    input.value = value;
    return input;
  }

  function showError(cur, message) {
    if (!cur.errorEl) return;
    cur.errorEl.textContent = message;
    cur.errorEl.classList.remove("d-none");
  }

  function hideError(cur) {
    if (!cur.errorEl) return;
    cur.errorEl.classList.add("d-none");
  }

  // Mirrors the server-side rules in WorkoutManagement.update_progress_entry
  // so an obviously-invalid save never leaves this device.
  function validateNumber(raw, min, max, label, mustBeWhole) {
    if (raw === "") return null;
    var num = Number(raw);
    if (!isFinite(num) || (mustBeWhole && Math.floor(num) !== num)) {
      return (mustBeWhole ? wdT("{label} must be a whole number.") : wdT("{label} must be a number."))
        .replace("{label}", label);
    }
    if (num < min || (max !== null && num > max)) {
      return (max !== null
        ? wdT("{label} must be between {min} and {max}.").replace("{max}", max)
        : wdT("{label} must be {min} or more."))
        .replace("{label}", label).replace("{min}", min);
    }
    return null;
  }

  function validate(reps, weight, rpe, notes) {
    return (
      validateNumber(reps, 0, null, wdT("Repetitions"), true) ||
      validateNumber(weight, 0, 501, wdT("Weight"), false) ||
      validateNumber(rpe, 0, 10, "RPE", false) ||
      (notes.length > 150 ? wdT("Notes can be at most 150 characters.") : null)
    );
  }

  function refreshDirty(cur) {
    var f = cur.fields;
    cur.dirty =
      f.reps.value !== cur.snapshot.reps ||
      f.weight.value !== cur.snapshot.weight ||
      f.rpe.value !== cur.snapshot.rpe ||
      f.notes.value !== cur.snapshot.notes ||
      cur.unitUndo.length > 0;
  }

  function buildViewToolbarButtons(cur) {
    cur.toolbar.innerHTML = "";

    var editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-success btn-sm wd-edit-btn";
    editBtn.setAttribute("aria-label", wdT("Edit this set"));
    editBtn.title = wdT("Edit your entry");
    editBtn.textContent = "✎"; // pencil glyph - a plain character, not an
                                     // icon font/SVG, so it never fails to render
    editBtn.addEventListener("click", function () {
      enterEditMode(cur);
    });

    // A "repeat last set" mistake is the realistic case this is for - one
    // extra logged set with nothing worth editing, just removing. Outline
    // style (not solid btn-danger) so it doesn't compete with the pencil for
    // attention; the confirm popup is the actual safety net.
    var deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn btn-outline-danger btn-sm wd-edit-btn";
    deleteBtn.setAttribute("aria-label", wdT("Delete this set"));
    deleteBtn.title = wdT("Delete this set");
    // Minus-in-a-circle rather than a plain X - keeps it visually distinct
    // from the X used to discard an in-progress edit (see buildEditToolbarButtons).
    deleteBtn.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">' +
      '<use href="#dash-circle"></use></svg>';
    deleteBtn.addEventListener("click", function () {
      openDeleteConfirm();
    });

    cur.toolbar.appendChild(editBtn);
    cur.toolbar.appendChild(deleteBtn);
    cur.editBtn = editBtn;
    cur.deleteBtn = deleteBtn;
  }

  // Label for the fix-unit button: the bowed-arrow icon plus this entry's
  // CURRENT unit.
  function fixUnitBtnHtml(unit) {
    return (
      '<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" class="me-1" aria-hidden="true">' +
      '<use href="#arrow-repeat"></use></svg>' + UNIT_LABELS[unit]
    );
  }

  function buildEditToolbarButtons(cur) {
    cur.toolbar.innerHTML = "";

    var fixUnitBtn = document.createElement("button");
    fixUnitBtn.type = "button";
    fixUnitBtn.className = "btn btn-outline-secondary btn-sm wd-fixunit-btn";
    fixUnitBtn.setAttribute("aria-label", wdT("Fix this set's unit"));
    fixUnitBtn.title = wdT("Wrong unit? Fix it here");
    fixUnitBtn.innerHTML = fixUnitBtnHtml(cur.currentUnit);
    fixUnitBtn.addEventListener("click", function () {
      openFixUnitModal();
    });

    var discardBtn = document.createElement("button");
    discardBtn.type = "button";
    discardBtn.className = "btn btn-outline-danger btn-sm wd-edit-btn";
    discardBtn.setAttribute("aria-label", wdT("Discard changes"));
    discardBtn.title = wdT("Discard");
    discardBtn.textContent = "✕";
    discardBtn.addEventListener("click", function () {
      discardEdit(cur);
    });

    var saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "btn btn-success btn-sm wd-edit-btn";
    saveBtn.setAttribute("aria-label", wdT("Save changes"));
    saveBtn.title = wdT("Confirm changes");
    saveBtn.textContent = "✓";
    saveBtn.addEventListener("click", function () {
      doSave(cur, function () {});
    });

    cur.toolbar.appendChild(fixUnitBtn);
    cur.toolbar.appendChild(discardBtn);
    cur.toolbar.appendChild(saveBtn);
    cur.fixUnitBtn = fixUnitBtn;
    cur.saveBtn = saveBtn;
  }

  function enterEditMode(cur) {
    if (cur.editing) return;
    cur.editing = true;
    cur.currentUnit = cur.row.dataset.unit || "kg";
    // Unit fixes made during this edit, with the unit each set had before -
    // ✕ Discard puts them back, ✓ Save keeps them. See submitFixUnit().
    cur.unitUndo = [];

    var repsTd = cur.row.querySelector('[data-field="reps"]');
    var weightTd = cur.row.querySelector('[data-field="weight"]');
    var rpeTd = cur.row.querySelector('[data-field="rpe"]');
    var noteTextEl = cur.noteRow.querySelector(".wd-note-text");

    cur.snapshot = {
      reps: textOf(repsTd),
      weight: weightTd.dataset.weight || "",
      rpe: textOf(rpeTd),
      notes: noteTextEl ? noteTextEl.textContent : "",
    };

    var repsInput = makeNumberInput(cur.snapshot.reps, { min: "0", step: "1" });
    var weightInput = makeNumberInput(cur.snapshot.weight, { min: "0", max: "501", step: "any" });
    var rpeInput = makeNumberInput(cur.snapshot.rpe, { min: "0", max: "10", step: "0.5" });

    var notesInput = document.createElement("textarea");
    notesInput.className = "form-control form-control-sm wd-note-edit";
    notesInput.rows = 2;
    notesInput.maxLength = 150;
    notesInput.placeholder = wdT("No note yet");
    notesInput.value = cur.snapshot.notes;

    repsTd.innerHTML = "";
    repsTd.appendChild(repsInput);
    weightTd.innerHTML = "";
    weightTd.appendChild(weightInput);
    rpeTd.innerHTML = "";
    rpeTd.appendChild(rpeInput);

    var errorEl = document.createElement("div");
    errorEl.className = "text-danger wd-edit-error d-none mt-1";

    if (noteTextEl) {
      noteTextEl.innerHTML = "";
      noteTextEl.appendChild(notesInput);
      noteTextEl.appendChild(errorEl);
    }

    cur.fields = { reps: repsInput, weight: weightInput, rpe: rpeInput, notes: notesInput, noteTextEl: noteTextEl };
    cur.errorEl = errorEl;

    [repsInput, weightInput, rpeInput, notesInput].forEach(function (el) {
      el.addEventListener("input", function () { refreshDirty(cur); });
    });

    buildEditToolbarButtons(cur);
  }

  function exitEditMode(cur, saved) {
    var repsTd = cur.row.querySelector('[data-field="reps"]');
    var weightTd = cur.row.querySelector('[data-field="weight"]');
    var rpeTd = cur.row.querySelector('[data-field="rpe"]');

    setViewSpan(repsTd, cur.snapshot.reps);
    renderWeight(weightTd, cur.snapshot.weight, cur.row.dataset.unit);
    setViewSpan(rpeTd, cur.snapshot.rpe);

    if (cur.fields && cur.fields.noteTextEl) {
      cur.fields.noteTextEl.textContent = cur.snapshot.notes;
    }

    cur.editing = false;
    cur.dirty = false;
    cur.fields = null;
    cur.errorEl = null;

    buildViewToolbarButtons(cur);
    markAllOddUnits();

    if (saved && cur.editBtn) {
      var original = cur.editBtn.textContent;
      cur.editBtn.textContent = "✓";
      setTimeout(function () {
        if (cur.editBtn) cur.editBtn.textContent = original;
      }, 900);
    }
  }

  function discardEdit(cur) {
    if (!cur.editing) return;
    var undo = cur.unitUndo || [];
    cur.unitUndo = [];
    exitEditMode(cur, false);
    if (undo.length) undoUnitFixes(undo);
  }

  // A unit fix is saved the moment it is picked (it can change several sets
  // at once), so "Discard" sends each set's old unit back, one by one.
  function undoUnitFixes(undo) {
    undo.forEach(function (item) {
      fetch("/progress/fix_unit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // The exact old number back, not a conversion of a conversion.
        body: JSON.stringify({ entry_id: item.entryId, unit: item.unit, scope: "entry",
                               restore_weight: item.weight === "" ? null : item.weight }),
      })
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data || !data.ok) return;
          for (var i = 0; i < data.updated.length; i++) {
            applyUnitFixToRow(data.updated[i].entry_id, data.updated[i].unit, data.updated[i].weight);
          }
          markAllOddUnits();
        })
        .catch(function () { /* the rows keep showing what the server has */ });
    });
  }

  function applySavedValues(cur, entry) {
    cur.snapshot = {
      reps: String(entry.reps),
      weight: entry.weight ? String(entry.weight) : "",
      rpe: String(entry.rpe),
      notes: entry.notes || "",
    };
    var previewDiv = cur.row.querySelector(".wd-notes > div");
    if (previewDiv) previewDiv.textContent = entry.notes || "";

    // Keeps the phone-only chevron's has-note darkening (see progress.html)
    // correct after an inline edit, without a full page reload.
    cur.row.classList.toggle("wd-has-note", !!(entry.notes || "").trim());
  }

  function doSave(cur, done) {
    hideError(cur);

    var reps = cur.fields.reps.value.trim();
    var weight = cur.fields.weight.value.trim();
    var rpe = cur.fields.rpe.value.trim();
    var notes = cur.fields.notes.value;

    var error = validate(reps, weight, rpe, notes);
    if (error) {
      showError(cur, error);
      done(false);
      return;
    }

    cur.saveBtn.disabled = true;

    fetch("/progress/update_entry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entry_id: cur.entryId,
        reps: reps === "" ? null : reps,
        weight: weight === "" ? null : weight,
        rpe: rpe === "" ? null : rpe,
        notes: notes,
      }),
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (cur.saveBtn) cur.saveBtn.disabled = false;
        if (!data || !data.ok) {
          showError(cur, (data && data.error) || wdT("Could not save, try again."));
          done(false);
          return;
        }
        applySavedValues(cur, data.entry);
        cur.unitUndo = [];
        exitEditMode(cur, true);
        done(true);
      })
      .catch(function () {
        if (cur.saveBtn) cur.saveBtn.disabled = false;
        showError(cur, wdT("Could not save, try again."));
        done(false);
      });
  }

  function buildViewToolbar(detail) {
    var toolbar = document.createElement("div");
    toolbar.className = "wd-edit-toolbar";
    detail.noteCell.appendChild(toolbar);

    current = {
      row: detail.row,
      noteRow: detail.noteRow,
      noteCell: detail.noteCell,
      entryId: detail.entryId,
      toolbar: toolbar,
      editing: false,
      dirty: false,
      fields: null,
      snapshot: null,
      errorEl: null,
      unitUndo: [],
    };

    buildViewToolbarButtons(current);
  }

  // ---- unsaved-changes guard --------------------------------------------

  function replayPending() {
    var target = pendingTarget;
    pendingTarget = null;
    if (target && document.body.contains(target)) {
      target.click();
    }
  }

  function showUnsavedModal() {
    if (!unsavedModal) { replayPending(); return; }
    unsavedModal.show();
  }

  function initUnsavedModal() {
    var modalEl = document.getElementById("progress_unsaved");
    if (!modalEl || typeof bootstrap === "undefined") return;
    unsavedModal = new bootstrap.Modal(modalEl);

    var saveBtn = document.getElementById("progress_unsaved_save");
    if (saveBtn) {
      saveBtn.addEventListener("click", function () {
        if (!current) { unsavedModal.hide(); return; }
        doSave(current, function (ok) {
          unsavedModal.hide();
          if (ok) replayPending();
        });
      });
    }

    var discardBtn = document.getElementById("progress_unsaved_discard");
    if (discardBtn) {
      discardBtn.addEventListener("click", function () {
        if (current) discardEdit(current);
        unsavedModal.hide();
        replayPending();
      });
    }
  }

  // ---- "fix unit" popup ---------------------------------------------------

  // Push one freshly-repaired unit/weight into its row on the page. A
  // session-wide fix returns several entries, so this runs once per entry.
  function applyUnitFixToRow(entryId, unit, weight) {
    var rows = document.querySelectorAll('tr[data-entry-id="' + entryId + '"]');
    for (var i = 0; i < rows.length; i++) {
      rows[i].dataset.unit = unit;

      if (current && current.row === rows[i] && current.editing) {
        // The row you fixed from is still open - update its live input and
        // snapshot together so this does not register as an unsaved edit.
        // A conversion changes the number too - into the input as well,
        // unless something else was typed there already.
        var newWeight = weight ? String(weight) : "";
        if (newWeight !== current.snapshot.weight) {
          if (current.fields && current.fields.weight &&
              current.fields.weight.value === current.snapshot.weight) {
            current.fields.weight.value = newWeight;
          }
          current.snapshot.weight = newWeight;
        }
        rows[i].querySelector('[data-field="weight"]').dataset.weight = newWeight;
        current.currentUnit = unit;
        if (current.fixUnitBtn) {
          current.fixUnitBtn.innerHTML = fixUnitBtnHtml(unit);
        }
        continue;
      }

      var weightTd = rows[i].querySelector('[data-field="weight"]');
      if (weightTd) renderWeight(weightTd, weight, unit);
    }
  }

  function setFixUnitTarget(unit, targetBtns, sessionBtn, entryBtn) {
    fixUnitTargetUnit = unit;
    for (var i = 0; i < targetBtns.length; i++) {
      var btn = targetBtns[i];
      var isTarget = btn.dataset.targetUnit === unit;
      var isCurrent = current && btn.dataset.targetUnit === current.currentUnit;
      btn.classList.toggle("btn-secondary", isTarget);
      btn.classList.toggle("btn-outline-secondary", !isTarget);
      btn.disabled = !!isCurrent; // converting a unit to itself is a no-op
    }
    var label = UNIT_LABELS[unit];
    sessionBtn.textContent = wdT("This exercise today →") + " " + label;
    entryBtn.textContent = wdT("This set →") + " " + label;
    showFixUnitPreview(unit);
  }

  // ---- the two repairs: relabel or convert --------------------------------
  // "Only the unit is wrong": 50 kg -> 50 lbs, the number as typed.
  // "Convert the weight":     36.29 kg -> 80 lbs, recalculated (kg <-> lbs).
  // The server rounds the same way (_converted_weight).
  var fixMode = "label";       // the repair picked in the popup
  var fixModeTouched = false;  // picked by hand - no more guessing for it

  function convertWeight(weight, from, to) {
    if (from === to || from === "other" || to === "other") return weight;
    return to === "lbs" ? roundTo(weight / KG_PER_LB, 1) : roundTo(weight * KG_PER_LB, 2);
  }

  // On a half-kilo / half-pound step, the way plates add up.
  function isRound(num) {
    return Math.abs(num * 2 - Math.round(num * 2)) < 0.05;
  }

  function currentWeight() {
    var weight = Number(current.row.querySelector('[data-field="weight"]').dataset.weight) || 0;
    if (current.fields && current.fields.weight && current.fields.weight.value.trim() !== "") {
      weight = Number(current.fields.weight.value) || weight;
    }
    return weight;
  }

  function setFixMode(mode) {
    fixMode = mode;
    var radio = document.getElementById(mode === "convert" ? "progress_fix_mode_convert" : "progress_fix_mode_label");
    if (radio) radio.checked = true;
    showFixUnitNote();
  }

  function showFixUnitPreview(unit) {
    var modes = document.getElementById("progress_fix_unit_modes");
    if (!modes || !current) return;
    var from = current.currentUnit, weight = currentWeight();
    var canConvert = !!weight && from !== "other" && unit !== "other";
    var converted = convertWeight(weight, from, unit);
    function shown(u) { return u === "other" ? UNIT_LABELS.other.toLowerCase() : u; }

    document.getElementById("progress_fix_mode_label_result").textContent =
      weight ? weight + " " + shown(from) + " → " + weight + " " + shown(unit) : "";
    document.getElementById("progress_fix_mode_convert_result").textContent =
      canConvert ? weight + " " + shown(from) + " → " + converted + " " + shown(unit) : "";
    document.getElementById("progress_fix_mode_convert").disabled = !canConvert;
    document.querySelector('label[for="progress_fix_mode_convert"]').classList.toggle("d-none", !canConvert);

    // The likelier repair, until one is picked by hand: a number that only
    // comes out round once converted (36.29 kg = 80 lbs) was converted
    // before; a round number as it is was typed off the machine.
    var mode = fixModeTouched ? fixMode : (canConvert && !isRound(weight) && isRound(converted) ? "convert" : "label");
    setFixMode(canConvert ? mode : "label");
  }

  function showFixUnitNote() {
    var note = document.getElementById("progress_fix_unit_note");
    if (!note || !current || !fixUnitTargetUnit) return;
    var weight = currentWeight(), unit = fixUnitTargetUnit;
    var result = fixMode === "convert" ? convertWeight(weight, current.currentUnit, unit) : weight;
    note.textContent = weight && unit === "lbs"
      ? wdT("Statistics count it as {kg} kg.").replace("{kg}", roundTo(result * KG_PER_LB, 1))
      : "";
  }

  function openFixUnitModal() {
    if (!fixUnitModal || !current) return;

    var currentEl = document.getElementById("progress_fix_unit_current");
    var errorEl = document.getElementById("progress_fix_unit_error");
    var targetBtns = document.querySelectorAll("#progress_fix_unit_targets [data-target-unit]");
    var sessionBtn = document.getElementById("progress_fix_unit_session");
    var entryBtn = document.getElementById("progress_fix_unit_entry");

    currentEl.textContent = UNIT_LABELS[current.currentUnit];
    errorEl.classList.add("d-none");

    // Default guess: the realistic mistake is the toggle sitting one click
    // off, i.e. Kg meant to be Lbs or vice versa. "Other" has no natural
    // opposite, so it defaults to Kg, the most common intended unit.
    var defaultTarget = current.currentUnit === "kg" ? "lbs" : "kg";
    // Better still: the unit the rest of this exercise was logged in.
    var counts = {};
    var tableRows = current.row.closest("table").querySelectorAll("tbody > tr[data-entry-id]");
    for (var r = 0; r < tableRows.length; r++) {
      var td = tableRows[r].querySelector('[data-field="weight"]');
      if (!td || !td.dataset.weight || tableRows[r] === current.row) continue;
      var u = tableRows[r].dataset.unit || "kg";
      counts[u] = (counts[u] || 0) + 1;
    }
    var usual = majority(counts);
    if (usual && usual !== current.currentUnit) defaultTarget = usual;
    fixModeTouched = false;
    setFixUnitTarget(defaultTarget, targetBtns, sessionBtn, entryBtn);

    fixUnitModal.show();
  }

  function submitFixUnit(scope) {
    if (!current || !fixUnitTargetUnit) return;
    var errorEl = document.getElementById("progress_fix_unit_error");
    errorEl.classList.add("d-none");

    fetch("/progress/fix_unit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entry_id: current.entryId,
        unit: fixUnitTargetUnit,
        scope: scope,
        convert: fixMode === "convert",
      }),
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (!data || !data.ok) {
          errorEl.textContent = (data && data.error) || wdT("Could not save, try again.");
          errorEl.classList.remove("d-none");
          return;
        }
        var cur = current;
        for (var i = 0; i < data.updated.length; i++) {
          var u = data.updated[i];
          if (cur && cur.unitUndo) {
            var seen = cur.unitUndo.some(function (item) { return item.entryId === u.entry_id; });
            var row = document.querySelector('tr[data-entry-id="' + u.entry_id + '"]');
            if (!seen && row) {
              var wTd = row.querySelector('[data-field="weight"]');
              cur.unitUndo.push({ entryId: u.entry_id, unit: row.dataset.unit || "kg",
                                  weight: wTd ? wTd.dataset.weight || "" : "" });
            }
          }
          applyUnitFixToRow(u.entry_id, u.unit, u.weight);
        }
        // Back to their own unit everywhere: nothing left to undo for those.
        if (cur && cur.unitUndo) {
          cur.unitUndo = cur.unitUndo.filter(function (item) {
            var row = document.querySelector('tr[data-entry-id="' + item.entryId + '"]');
            if (!row) return false;
            var wTd = row.querySelector('[data-field="weight"]');
            var nowWeight = row === cur.row ? cur.snapshot.weight : (wTd ? wTd.dataset.weight || "" : "");
            return (row.dataset.unit || "kg") !== item.unit || String(nowWeight) !== String(item.weight);
          });
          refreshDirty(cur);
        }
        markAllOddUnits();
        fixUnitModal.hide();
      })
      .catch(function () {
        errorEl.textContent = wdT("Could not save, try again.");
        errorEl.classList.remove("d-none");
      });
  }

  function initFixUnitModal() {
    var modalEl = document.getElementById("progress_fix_unit");
    if (!modalEl || typeof bootstrap === "undefined") return;
    fixUnitModal = new bootstrap.Modal(modalEl);

    var targetBtns = modalEl.querySelectorAll("#progress_fix_unit_targets [data-target-unit]");
    var sessionBtn = document.getElementById("progress_fix_unit_session");
    var entryBtn = document.getElementById("progress_fix_unit_entry");
    var cancelBtn = document.getElementById("progress_fix_unit_cancel");

    targetBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        setFixUnitTarget(btn.dataset.targetUnit, targetBtns, sessionBtn, entryBtn);
      });
    });

    ["label", "convert"].forEach(function (mode) {
      var radio = document.getElementById("progress_fix_mode_" + mode);
      if (radio) radio.addEventListener("change", function () {
        if (radio.checked) { fixModeTouched = true; setFixMode(mode); }
      });
    });

    sessionBtn.addEventListener("click", function () { submitFixUnit("session"); });
    entryBtn.addEventListener("click", function () { submitFixUnit("entry"); });
    cancelBtn.addEventListener("click", function () { fixUnitModal.hide(); });
  }

  // ---- "delete set" confirm popup -----------------------------------------

  function openDeleteConfirm() {
    if (!deleteModal || !current) return;
    var errorEl = document.getElementById("progress_delete_confirm_error");
    errorEl.classList.add("d-none");
    deleteModal.show();
  }

  function submitDelete() {
    if (!current) return;
    var errorEl = document.getElementById("progress_delete_confirm_error");
    errorEl.classList.add("d-none");

    var entryId = current.entryId;
    var row = current.row;
    // Wide-note mode (phones) opens a separate row for the note - in-place
    // mode (see rowExpand.js) reuses the row itself, so there is nothing
    // extra to remove there.
    var noteRow = current.noteRow !== row ? current.noteRow : null;
    var deleteBtn = document.getElementById("progress_delete_confirm_delete");
    if (deleteBtn) deleteBtn.disabled = true;

    fetch("/progress/delete_entry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entry_id: entryId }),
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (deleteBtn) deleteBtn.disabled = false;
        if (!data || !data.ok) {
          errorEl.textContent = (data && data.error) || wdT("Could not delete, try again.");
          errorEl.classList.remove("d-none");
          return;
        }
        deleteModal.hide();
        if (noteRow && noteRow.parentNode) { noteRow.parentNode.removeChild(noteRow); }
        var table = row ? row.closest("table") : null;
        if (row && row.parentNode) { row.parentNode.removeChild(row); }
        if (table) markOddUnits(table);
        if (current && current.row === row) { current = null; }
      })
      .catch(function () {
        if (deleteBtn) deleteBtn.disabled = false;
        errorEl.textContent = wdT("Could not delete, try again.");
        errorEl.classList.remove("d-none");
      });
  }

  function initDeleteConfirmModal() {
    var modalEl = document.getElementById("progress_delete_confirm");
    if (!modalEl || typeof bootstrap === "undefined") return;
    deleteModal = new bootstrap.Modal(modalEl);

    var cancelBtn = document.getElementById("progress_delete_confirm_cancel");
    var deleteBtn = document.getElementById("progress_delete_confirm_delete");
    if (cancelBtn) cancelBtn.addEventListener("click", function () { deleteModal.hide(); });
    if (deleteBtn) deleteBtn.addEventListener("click", submitDelete);
  }

  function start() {
    markAllOddUnits();
    initUnsavedModal();
    initFixUnitModal();
    initDeleteConfirmModal();

    document.addEventListener("wd:row-opened", function (e) {
      if (e.detail && e.detail.entryId) buildViewToolbar(e.detail);
    });

    document.addEventListener("wd:row-closing", function (e) {
      if (current && e.detail && e.detail.row === current.row) {
        if (current.editing) discardEdit(current);
        // In wide-note mode the whole note row (toolbar included) gets torn
        // down by rowExpand.js right after this fires. In in-place mode the
        // Notes cell is the row's own permanent cell, not a disposable one -
        // nothing else ever removes the toolbar we appended into it, so a
        // repeated open/close would otherwise stack up one per open.
        if (current.toolbar && current.toolbar.parentNode) {
          current.toolbar.parentNode.removeChild(current.toolbar);
        }
        current = null;
      }
    });

    // Capture phase, so this runs before rowExpand.js's own bubble-phase
    // click handling - it can veto the click entirely by stopping it here.
    // Anything typed into our own fields, or clicked on our own buttons
    // (or any other button/input/select/textarea on the page), is exempt -
    // only clicks that would abandon the edit get intercepted.
    document.addEventListener("click", function (e) {
      if (!current || !current.dirty) return;
      if (e.defaultPrevented || e.button !== 0) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (e.target.closest("button,input,select,textarea,label")) return;

      e.preventDefault();
      e.stopPropagation();
      pendingTarget = e.target;
      showUnsavedModal();
    }, true);

    // Escape is rowExpand.js's own close shortcut (bubble-phase keydown) -
    // intercept it the same way as a click when there is something to lose.
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape" || !current || !current.dirty) return;
      e.preventDefault();
      e.stopPropagation();
      pendingTarget = current.row;
      showUnsavedModal();
    }, true);

    // Last resort for anything a click/keydown listener cannot see - chiefly
    // the mesocycle/day <select onchange="this.form.submit()">, which
    // navigates on "change", not "click". Generic browser wording; it
    // cannot be styled to match the modal above.
    window.addEventListener("beforeunload", function (e) {
      if (!current || !current.dirty) return;
      e.preventDefault();
      e.returnValue = "";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
