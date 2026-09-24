// CHERT: Arabic is translation-only — the login stays LTR (Keycloak flags `ar` as RTL and emits
// <html dir="rtl">). The theme CSS already forces LTR rendering; this mirrors that onto the DOM
// attribute so the document is unambiguously dir="ltr" for any consumer that reads it. Local
// resource only (no external script); pairs with the CSS override in css/chert.css.
document.documentElement.setAttribute("dir", "ltr");
