/* CHERT portal — small progressive-enhancement helpers. Local only (no external calls).
   - copy-to-clipboard buttons ([data-copy] inside a .cred, or a literal data-copy value)
   - reveal/hide for masked secret values (.cred[data-value] + [data-reveal])
   - print trigger (#report-print)
   Everything degrades gracefully: values remain readable and forms remain usable without JS. */
(function () {
  "use strict";

  function dots(value) {
    var n = Math.max(4, Math.min(value ? value.length : 8, 32));
    return new Array(n + 1).join("•");
  }

  function onClick(e) {
    var reveal = e.target.closest ? e.target.closest("[data-reveal]") : null;
    if (reveal) {
      var cred = reveal.closest(".cred");
      if (!cred) return;
      var value = cred.getAttribute("data-value") || "";
      var out = cred.querySelector(".cred__value");
      var shown = cred.classList.toggle("is-revealed");
      if (out) out.textContent = shown ? value : dots(value);
      reveal.setAttribute("aria-pressed", shown ? "true" : "false");
      var lbl = shown ? reveal.getAttribute("data-hide-label") : reveal.getAttribute("data-show-label");
      if (lbl) { reveal.setAttribute("aria-label", lbl); reveal.title = lbl; }
      return;
    }

    var copy = e.target.closest ? e.target.closest("[data-copy]") : null;
    if (copy) {
      var container = copy.closest(".cred");
      var text = (container && container.getAttribute("data-value")) || copy.getAttribute("data-copy") || "";
      if (!text || !navigator.clipboard) return;
      navigator.clipboard.writeText(text).then(function () {
        copy.classList.add("is-copied");
        var prev = copy.getAttribute("aria-label");
        copy.setAttribute("aria-label", copy.getAttribute("data-copied-label") || "Copied");
        setTimeout(function () {
          copy.classList.remove("is-copied");
          if (prev) copy.setAttribute("aria-label", prev);
        }, 1400);
      });
      return;
    }

    if (e.target.closest && e.target.closest("#report-print")) window.print();
  }

  // Initialise masked secrets to their dotted display before first paint of JS.
  function initSecrets() {
    var creds = document.querySelectorAll(".cred--secret[data-value]");
    for (var i = 0; i < creds.length; i++) {
      var out = creds[i].querySelector(".cred__value");
      if (out && !creds[i].classList.contains("is-revealed")) out.textContent = dots(creds[i].getAttribute("data-value"));
    }
  }

  if (document.readyState !== "loading") initSecrets();
  else document.addEventListener("DOMContentLoaded", initSecrets);
  document.addEventListener("click", onClick);
})();
