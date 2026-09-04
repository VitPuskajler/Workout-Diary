/* --------------------------------------------------------------------------
   flipCards.js - tap-to-flip for .flip-card on touch devices.

   The cards flip on :hover in CSS for a real mouse (see style.css), but a
   touch screen has no "mouse leave" to flip back - a tap satisfies :hover
   and then it just stays flipped. This adds the other half: tap a card to
   flip it, tap it again (or tap anywhere else on the page) to flip it back.
-------------------------------------------------------------------------- */
(function () {
  "use strict";

  var cards = document.querySelectorAll(".flip-card");
  if (!cards.length) { return; }

  cards.forEach(function (card) {
    card.addEventListener("click", function (e) {
      // Without this, the document listener below would immediately undo
      // the flip this same click just applied.
      e.stopPropagation();

      var wasFlipped = card.classList.contains("is-flipped");
      cards.forEach(function (c) { c.classList.remove("is-flipped"); });
      if (!wasFlipped) {
        card.classList.add("is-flipped");
      }
    });
  });

  // Tapping the plain page flips whatever card is currently flipped back.
  document.addEventListener("click", function () {
    cards.forEach(function (c) { c.classList.remove("is-flipped"); });
  });
})();
