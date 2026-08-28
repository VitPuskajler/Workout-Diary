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

  var current = null;      // the one open, editable row - see buildViewToolbar()
  var pendingTarget = null; // element to re-click once a dirty edit is resolved
  var unsavedModal = null;

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
      return label + " must be a" + (mustBeWhole ? " whole" : "") + " number.";
    }
    if (num < min || (max !== null && num > max)) {
      return max !== null
        ? label + " must be between " + min + " and " + max + "."
        : label + " must be " + min + " or more.";
    }
    return null;
  }

  function validate(reps, weight, rpe, notes) {
    return (
      validateNumber(reps, 0, null, "Reps", true) ||
      validateNumber(weight, 0, 501, "Weight", false) ||
      validateNumber(rpe, 0, 10, "RPE", false) ||
      (notes.length > 150 ? "Notes can be at most 150 characters." : null)
    );
  }

  function refreshDirty(cur) {
    var f = cur.fields;
    cur.dirty =
      f.reps.value !== cur.snapshot.reps ||
      f.weight.value !== cur.snapshot.weight ||
      f.rpe.value !== cur.snapshot.rpe ||
      f.notes.value !== cur.snapshot.notes;
  }

  function buildViewToolbarButtons(cur) {
    cur.toolbar.innerHTML = "";

    var editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-success btn-sm wd-edit-btn";
    editBtn.setAttribute("aria-label", "Edit this set");
    editBtn.textContent = "✎"; // pencil glyph - a plain character, not an
                                     // icon font/SVG, so it never fails to render
    editBtn.addEventListener("click", function () {
      enterEditMode(cur);
    });

    cur.toolbar.appendChild(editBtn);
    cur.editBtn = editBtn;
  }

  function buildEditToolbarButtons(cur) {
    cur.toolbar.innerHTML = "";

    var discardBtn = document.createElement("button");
    discardBtn.type = "button";
    discardBtn.className = "btn btn-link btn-sm p-0 text-secondary wd-discard-link";
    discardBtn.textContent = "Discard";
    discardBtn.addEventListener("click", function () {
      discardEdit(cur);
    });

    var saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "btn btn-success btn-sm wd-edit-btn";
    saveBtn.setAttribute("aria-label", "Save changes");
    saveBtn.textContent = "✓";
    saveBtn.addEventListener("click", function () {
      doSave(cur, function () {});
    });

    cur.toolbar.appendChild(discardBtn);
    cur.toolbar.appendChild(saveBtn);
    cur.saveBtn = saveBtn;
  }

  function enterEditMode(cur) {
    if (cur.editing) return;
    cur.editing = true;

    var repsTd = cur.row.querySelector('[data-field="reps"]');
    var weightTd = cur.row.querySelector('[data-field="weight"]');
    var rpeTd = cur.row.querySelector('[data-field="rpe"]');
    var noteTextEl = cur.noteRow.querySelector(".wd-note-text");

    cur.snapshot = {
      reps: textOf(repsTd),
      weight: textOf(weightTd),
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
    notesInput.placeholder = "No note yet";
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
    setViewSpan(weightTd, cur.snapshot.weight);
    setViewSpan(rpeTd, cur.snapshot.rpe);

    if (cur.fields && cur.fields.noteTextEl) {
      cur.fields.noteTextEl.textContent = cur.snapshot.notes;
    }

    cur.editing = false;
    cur.dirty = false;
    cur.fields = null;
    cur.errorEl = null;

    buildViewToolbarButtons(cur);

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
    exitEditMode(cur, false);
  }

  function applySavedValues(cur, entry) {
    cur.snapshot = {
      reps: String(entry.reps),
      weight: String(entry.weight),
      rpe: String(entry.rpe),
      notes: entry.notes || "",
    };
    var previewDiv = cur.row.querySelector(".wd-notes > div");
    if (previewDiv) previewDiv.textContent = entry.notes || "";
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
          showError(cur, (data && data.error) || "Could not save, try again.");
          done(false);
          return;
        }
        applySavedValues(cur, data.entry);
        exitEditMode(cur, true);
        done(true);
      })
      .catch(function () {
        if (cur.saveBtn) cur.saveBtn.disabled = false;
        showError(cur, "Could not save, try again.");
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

  function start() {
    initUnsavedModal();

    document.addEventListener("wd:row-opened", function (e) {
      if (e.detail && e.detail.entryId) buildViewToolbar(e.detail);
    });

    document.addEventListener("wd:row-closing", function (e) {
      if (current && e.detail && e.detail.row === current.row) {
        if (current.editing) discardEdit(current);
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
