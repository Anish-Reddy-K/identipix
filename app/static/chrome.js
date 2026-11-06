/* Shared site footer (one place for links, so the three pages stay in sync). */
(function () {
  var REPO = "https://github.com/Anish-Reddy-K/identipix";
  var EMAIL = "contact@identipix.com";
  var COPY = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="8" width="13" height="13" rx="2"/><path d="M4 16V5a2 2 0 0 1 2-2h11"/></svg>';
  var CHECK = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';
  var HEART = '<svg class="heart" viewBox="0 0 24 24" width="15" height="15" role="img" aria-label="love"><defs><linearGradient id="heartGrad" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#E91E63"/><stop offset="1" stop-color="#8E24AA"/></linearGradient></defs><path fill="url(#heartGrad)" d="M12 21.2 10.6 20C5.4 15.3 2 12.2 2 8.4 2 5.3 4.4 3 7.4 3c1.7 0 3.4.8 4.6 2.1C13.2 3.8 14.9 3 16.6 3 19.6 3 22 5.3 22 8.4c0 3.8-3.4 6.9-8.6 11.6L12 21.2Z"/></svg>';
  var ICONS = {"instagram": "M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077", "linkedin": "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z", "github": "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"};
  function icon(name) {
    return '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="currentColor"><path d="' + ICONS[name] + '"/></svg>';
  }
  function social(name, label, href) {
    return '<a class="social" href="' + href + '" target="_blank" rel="noopener" aria-label="' + label + '">' + icon(name) + "</a>";
  }
  var promo = document.getElementById("promo");   // slim strip across the top of the guest page
  if (promo) {
    promo.innerHTML =
      '<a class="promo" href="' + REPO + '" target="_blank" rel="noopener">' +
        '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>' +
        '<span class="promo-long">Free &amp; open source. Your selfie is never stored.</span>' +
        '<span class="promo-cta"><span class="promo-long">Star Identipix on GitHub</span><span class="promo-short">Open source. Star us on GitHub</span> &rarr;</span>' +
      "</a>";
  }
  var bar = document.querySelector(".topbar");   // open-source link, top right next to the logo
  if (bar) {
    bar.insertAdjacentHTML("beforeend",
      '<a class="gh" href="' + REPO + '" target="_blank" rel="noopener" aria-label="Identipix is open source: view on GitHub">' +
      icon("github") + "<span>GitHub</span></a>");
  }
  var el = document.getElementById("site-footer");
  if (!el) return;
  el.innerHTML =
    '<div class="footer-inner">' +
      '<div class="footer-top">' +
        '<div class="footer-brand">' +
          '<img src="/static/brand/logo.png" alt="Identipix">' +
          '<p class="footer-tagline">Photos that <span class="grad">find you</span>.</p>' +
        "</div>" +
        '<div class="footer-contact">' +
          '<div class="socials">' +
            social("instagram", "Instagram", "https://www.instagram.com/identipix/") +
            social("linkedin", "LinkedIn", "https://www.linkedin.com/company/identipix/") +
            social("github", "GitHub", REPO) +
          "</div>" +
          '<div class="email-row">' +
            '<a href="mailto:' + EMAIL + '">' + EMAIL + "</a>" +
            '<button type="button" class="copy" aria-label="Copy email address">' + COPY + "</button>" +
          "</div>" +
        "</div>" +
      "</div>" +
      '<div class="footer-bottom">' +
        '<nav class="footer-links" aria-label="Footer">' +
          '<a href="' + REPO + '/blob/main/legal/PRIVACY.md" target="_blank" rel="noopener">Privacy Policy</a>' +
          '<a href="' + REPO + '/blob/main/legal/TERMS.md" target="_blank" rel="noopener">Terms of Service</a>' +
          '<span class="footer-copy">&copy; ' + new Date().getFullYear() + " Identipix</span>" +
        "</nav>" +
        '<p class="footer-place">Made with ' + HEART + ' in Waterloo, Canada</p>' +
      "</div>" +
    "</div>";
  var btn = el.querySelector(".copy");
  btn.addEventListener("click", function () {
    function done() {
      btn.innerHTML = CHECK; btn.setAttribute("aria-label", "Email copied");
      setTimeout(function () { btn.innerHTML = COPY; btn.setAttribute("aria-label", "Copy email address"); }, 1600);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(EMAIL).then(done, function () {});
    } else {  // plain http fallback
      var t = document.createElement("textarea"); t.value = EMAIL; t.style.position = "fixed"; t.style.opacity = "0";
      document.body.appendChild(t); t.select();
      try { document.execCommand("copy"); done(); } catch (e) {}
      document.body.removeChild(t);
    }
  });
})();
