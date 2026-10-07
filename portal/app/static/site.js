/* CHERT IoT — marketing site motion & interactivity (templates/index.html).
   Local only: no network calls. Content comes from the #sx-data JSON the server renders from
   app/site_content.py. Everything is progressive — without JS the page is a complete document.
   prefers-reduced-motion: no canvas animation, packets or autoplay; state changes stay instant. */
(function () {
  "use strict";

  var root = document.documentElement;
  root.classList.remove("no-js");
  root.classList.add("js");

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var dataEl = document.getElementById("sx-data");
  var DATA = dataEl ? JSON.parse(dataEl.textContent) : { nodes: {}, edges: [], journeys: {}, stageTitles: {} };

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function token(name) { return getComputedStyle(root).getPropertyValue(name).trim(); }
  function rgba(hex, a) {
    var h = (hex || "").replace("#", "");
    if (h.length === 3) h = h.split("").map(function (c) { return c + c; }).join("");
    var n = parseInt(h, 16) || 0;
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function onVisible(el, cb, threshold) {
    if (!el) return;
    if (!("IntersectionObserver" in window)) { cb(true); return; }
    new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { cb(e.isIntersecting); });
    }, { threshold: threshold || 0 }).observe(el);
  }
  function scrollTo(el, block) {
    if (el) el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: block || "start" });
  }

  /* ------------------------------------------------------------ nav --- */
  var nav = $("[data-sx-nav]");
  function navState() { if (nav) nav.classList.toggle("is-solid", window.scrollY > 40); }
  window.addEventListener("scroll", navState, { passive: true });
  navState();

  /* --------------------------------------------------------- reveals --- */
  var reveals = $$(".sx-reveal");
  if ("IntersectionObserver" in window && !reduce) {
    var rio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-in"); rio.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    reveals.forEach(function (el) { rio.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  }

  /* -------------------------------------------------- stat count-up --- */
  var counted = false;
  onVisible($(".sx-stats"), function (vis) {
    if (!vis || counted || reduce) return;
    counted = true;
    $$("[data-sx-count]").forEach(function (el) {
      var target = parseInt(el.getAttribute("data-sx-count"), 10) || 0, t0 = performance.now();
      (function step(now) {
        var t = Math.min(1, (now - t0) / 1300);
        el.textContent = Math.round(target * (1 - Math.pow(1 - t, 3)));
        if (t < 1) requestAnimationFrame(step);
      })(t0);
    });
  }, 0.4);

  /* ------------------------------------------- hero: device network --- */
  (function heroField() {
    var canvas = $("[data-sx-field]");
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext("2d");
    var orange = token("--chert-orange"), tan = token("--chert-tan"), text = token("--chert-dark-text");
    var W = 0, H = 0, dpr = 1, nodes = [], packets = [], running = false, visible = true, last = 0, spawn = 0;
    var mouse = { x: -9999, y: -9999 };
    var LINK = 130;

    function resize() {
      var r = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = r.width; H = r.height;
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var count = Math.max(28, Math.min(90, Math.round((W * H) / 15000)));
      nodes = [];
      for (var i = 0; i < count; i++) {
        nodes.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - 0.5) * 0.22,
                     vy: (Math.random() - 0.5) * 0.22, r: 1 + Math.random() * 1.6, hub: Math.random() < 0.12 });
      }
      packets = [];
      draw(0);
    }

    function neighbours(a) {
      var out = [];
      for (var i = 0; i < nodes.length; i++) {
        var b = nodes[i];
        if (b === a) continue;
        var dx = a.x - b.x, dy = a.y - b.y;
        if (dx * dx + dy * dy < LINK * LINK) out.push(b);
      }
      return out;
    }

    function draw(dt) {
      ctx.clearRect(0, 0, W, H);
      var i, j, a, b, dx, dy, d2;
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        if (dt) {
          a.x += a.vx * dt * 0.06; a.y += a.vy * dt * 0.06;
          if (a.x < -20) a.x = W + 20; else if (a.x > W + 20) a.x = -20;
          if (a.y < -20) a.y = H + 20; else if (a.y > H + 20) a.y = -20;
        }
      }
      ctx.lineWidth = 1;
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        for (j = i + 1; j < nodes.length; j++) {
          b = nodes[j]; dx = a.x - b.x; dy = a.y - b.y; d2 = dx * dx + dy * dy;
          if (d2 < LINK * LINK) {
            ctx.strokeStyle = rgba(tan, 0.16 * (1 - Math.sqrt(d2) / LINK));
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
        dx = a.x - mouse.x; dy = a.y - mouse.y; d2 = dx * dx + dy * dy;
        if (d2 < 170 * 170) {
          ctx.strokeStyle = rgba(orange, 0.35 * (1 - Math.sqrt(d2) / 170));
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
        }
      }
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        ctx.fillStyle = a.hub ? rgba(orange, 0.9) : rgba(text, 0.45);
        ctx.beginPath(); ctx.arc(a.x, a.y, a.hub ? a.r + 1.2 : a.r, 0, Math.PI * 2); ctx.fill();
        if (a.hub) {
          ctx.strokeStyle = rgba(orange, 0.25);
          ctx.beginPath(); ctx.arc(a.x, a.y, a.r + 6, 0, Math.PI * 2); ctx.stroke();
        }
      }
      for (i = packets.length - 1; i >= 0; i--) {
        var p = packets[i];
        p.t += dt / p.dur;
        if (p.t >= 1) { packets.splice(i, 1); continue; }
        var x = p.a.x + (p.b.x - p.a.x) * p.t, y = p.a.y + (p.b.y - p.a.y) * p.t;
        var g = ctx.createRadialGradient(x, y, 0, x, y, 9);
        g.addColorStop(0, rgba(orange, 0.95)); g.addColorStop(1, rgba(orange, 0));
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2); ctx.fill();
      }
    }

    function frame(now) {
      if (!running) return;
      var dt = last ? Math.min(now - last, 50) : 16;
      last = now; spawn += dt;
      if (spawn > 260 && packets.length < 16) {
        spawn = 0;
        var a = nodes[(Math.random() * nodes.length) | 0], ns = neighbours(a);
        if (ns.length) packets.push({ a: a, b: ns[(Math.random() * ns.length) | 0], t: 0, dur: 900 + Math.random() * 900 });
      }
      draw(dt);
      requestAnimationFrame(frame);
    }
    function start() { if (running || reduce || !visible || document.hidden) return; running = true; last = 0; requestAnimationFrame(frame); }
    function stop() { running = false; }

    resize();
    var rt;
    window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(resize, 150); });
    var hero = canvas.parentElement;
    hero.addEventListener("pointermove", function (e) {
      var r = canvas.getBoundingClientRect(); mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top;
    });
    hero.addEventListener("pointerleave", function () { mouse.x = mouse.y = -9999; });
    onVisible(hero, function (vis) { visible = vis; if (vis) start(); else stop(); });
    document.addEventListener("visibilitychange", function () { if (document.hidden) stop(); else start(); });
    start();
  })();

  /* ----------------------------------------- hero: sample telemetry --- */
  (function telemetry() {
    var card = $("[data-sx-tele]");
    if (!card) return;
    var valEl = $("[data-sx-tele-value]", card), line = $("[data-sx-tele-line]", card);
    var v = 23.4, series = [];
    for (var i = 0; i < 28; i++) { v += (Math.random() - 0.5) * 0.5; v = Math.max(21, Math.min(27, v)); series.push(v); }
    function render() {
      var min = 20.5, max = 27.5, n = series.length, d = "";
      series.forEach(function (s, k) {
        d += (k ? " L" : "M") + (k * 200 / (n - 1)).toFixed(1) + " " + (44 - ((s - min) / (max - min)) * 40).toFixed(1);
      });
      line.setAttribute("d", d);
      valEl.textContent = series[n - 1].toFixed(1);
    }
    render();
    if (reduce) return;
    setInterval(function () {
      if (document.hidden) return;
      v += (Math.random() - 0.5) * 0.6; v = Math.max(21, Math.min(27, v));
      series.push(v); series.shift(); render();
    }, 1600);
  })();

  /* ----------------------------------------------- lifecycle wheel --- */
  var lifecycle = (function () {
    var wrap = $("[data-sx-life]");
    if (!wrap) return { set: function () {} };
    var stops = $$(".sx-stop", wrap), panels = $$(".sx-stage", wrap), total = stops.length;
    var progress = $("[data-sx-progress]", wrap), center = $(".sx-wheel__center", wrap);
    var cN = $("[data-sx-center-n]", wrap), cT = $("[data-sx-center-t]", wrap);
    var playBtn = $("[data-sx-life-play]", wrap), bar = $("[data-sx-life-bar]", wrap);
    var current = 1, timer = null, playing = false, inView = false, autoStarted = false, DWELL = 5200;

    function set(n, focus) {
      n = ((n - 1 + total) % total) + 1;
      current = n;
      stops.forEach(function (b, i) {
        var k = i + 1, on = k === n;
        b.classList.toggle("is-active", on);
        b.classList.toggle("is-done", k < n);
        b.setAttribute("aria-selected", on ? "true" : "false");
        b.tabIndex = on ? 0 : -1;
        if (on && focus) b.focus();
      });
      panels.forEach(function (p) { p.classList.toggle("is-active", +p.getAttribute("data-stage") === n); });
      if (progress) progress.style.strokeDashoffset = String(100 - ((n - 1) / total) * 100);
      cN.textContent = pad(n);
      cT.textContent = stops[n - 1].querySelector(".sx-stop__label").textContent;
      center.classList.remove("is-swap"); void center.offsetWidth; center.classList.add("is-swap");
      if (playing) runBar();
    }
    function runBar() {
      if (!bar) return;
      bar.style.transition = "none"; bar.style.width = "0%"; void bar.offsetWidth;
      bar.style.transition = "width " + DWELL + "ms linear"; bar.style.width = "100%";
    }
    function play(on) {
      playing = on;
      clearInterval(timer);
      playBtn.setAttribute("aria-pressed", on ? "true" : "false");
      playBtn.setAttribute("aria-label", playBtn.getAttribute(on ? "data-label-pause" : "data-label-play"));
      if (on) { runBar(); timer = setInterval(function () { if (inView && !document.hidden) set(current + 1); }, DWELL); }
      else if (bar) { bar.style.transition = "none"; bar.style.width = "0%"; }
    }
    function user(n, focus) { play(false); set(n, focus); }

    stops.forEach(function (b) {
      b.addEventListener("click", function () { user(+b.getAttribute("data-stage")); });
    });
    $(".sx-wheel__stops", wrap).addEventListener("keydown", function (e) {
      var map = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
      if (map[e.key]) { e.preventDefault(); user(current + map[e.key], true); }
      else if (e.key === "Home") { e.preventDefault(); user(1, true); }
      else if (e.key === "End") { e.preventDefault(); user(total, true); }
    });
    $("[data-sx-life-prev]", wrap).addEventListener("click", function () { user(current - 1); });
    $("[data-sx-life-next]", wrap).addEventListener("click", function () { user(current + 1); });
    playBtn.addEventListener("click", function () { play(!playing); });
    onVisible(wrap, function (vis) {
      inView = vis;
      if (vis && !autoStarted && !reduce) { autoStarted = true; play(true); }
    }, 0.35);
    set(1);
    return { set: user };
  })();

  /* -------------------------------------------- architecture console --- */
  var arch = (function () {
    var box = $("[data-sx-arch]");
    if (!box) return { select: function () {}, play: function () {} };
    var diagram = $("[data-sx-diagram]", box), svg = $("[data-sx-svg]", box);
    var insp = $("[data-sx-inspector]", box), idle = $("[data-sx-idle]", box), body = $("[data-sx-body]", box);
    var f = {
      layer: $("[data-sx-layer]", box), name: $("[data-sx-name]", box), role: $("[data-sx-role]", box),
      text: $("[data-sx-text]", box), step: $("[data-sx-step]", box), stages: $("[data-sx-stages]", box), jnav: $("[data-sx-jnav]", box)
    };
    var SVGNS = "http://www.w3.org/2000/svg";
    var nodeEls = {};
    $$("[data-node]", diagram).forEach(function (b) { nodeEls[b.getAttribute("data-node")] = b; });
    var wires = {}, packets = [], rafOn = false, inView = false, showWires = true;
    var selected = null, journey = null, step = -1, jTimer = null, ambientT = 0, autoPlayed = false, userTouched = false;

    function rel(el) {
      var d = diagram.getBoundingClientRect(), r = el.getBoundingClientRect();
      return { l: r.left - d.left, t: r.top - d.top, r: r.right - d.left, b: r.bottom - d.top,
               cx: r.left - d.left + r.width / 2, cy: r.top - d.top + r.height / 2 };
    }
    function geometry(src, dst) {
      var a = rel(nodeEls[src]), b = rel(nodeEls[dst]), sx, sy, ex, ey, k;
      var gapX = Math.max(b.l - a.r, a.l - b.r), gapY = Math.max(b.t - a.b, a.t - b.b);
      if (gapY >= gapX) {
        var down = b.cy > a.cy;
        sx = a.cx; sy = down ? a.b : a.t; ex = b.cx; ey = down ? b.t : b.b; k = (ey - sy) / 2;
        return "M" + sx + " " + sy + " C" + sx + " " + (sy + k) + " " + ex + " " + (ey - k) + " " + ex + " " + ey;
      }
      var right = b.cx > a.cx;
      sx = right ? a.r : a.l; sy = a.cy; ex = right ? b.l : b.r; ey = b.cy; k = (ex - sx) / 2;
      return "M" + sx + " " + sy + " C" + (sx + k) + " " + sy + " " + (ex - k) + " " + ey + " " + ex + " " + ey;
    }
    function drawWires() {
      var w = diagram.clientWidth, h = diagram.clientHeight;
      svg.setAttribute("viewBox", "0 0 " + w + " " + h);
      svg.setAttribute("width", w); svg.setAttribute("height", h);
      while (svg.firstChild) svg.removeChild(svg.firstChild);
      wires = {}; packets = [];
      DATA.edges.forEach(function (e) {
        if (!nodeEls[e[0]] || !nodeEls[e[1]]) return;
        var p = document.createElementNS(SVGNS, "path");
        p.setAttribute("class", "sx-wire");
        p.setAttribute("d", geometry(e[0], e[1]));
        svg.appendChild(p);
        wires[e[0] + ">" + e[1]] = p;
      });
      paint();
    }
    // A wire for a journey hop: the drawn edge (forwards or backwards), else a temporary path.
    function hop(a, b) {
      if (wires[a + ">" + b]) return { path: wires[a + ">" + b], reverse: false };
      if (wires[b + ">" + a]) return { path: wires[b + ">" + a], reverse: true };
      var p = document.createElementNS(SVGNS, "path");
      p.setAttribute("class", "sx-wire is-temp");
      p.setAttribute("d", geometry(a, b));
      svg.appendChild(p);
      return { path: p, reverse: false, temp: true };
    }

    /* packets share one rAF loop */
    function launch(path, reverse, dur, ambient, done) {
      var c = document.createElementNS(SVGNS, "circle");
      c.setAttribute("r", ambient ? 2.6 : 5);
      c.setAttribute("class", ambient ? "sx-packet sx-packet--ambient" : "sx-packet");
      svg.appendChild(c);
      packets.push({ el: c, path: path, len: path.getTotalLength(), reverse: reverse, t0: performance.now(), dur: dur, done: done });
      if (!rafOn) { rafOn = true; requestAnimationFrame(tick); }
    }
    function tick(now) {
      if (inView && showWires && !journey && !reduce && now - ambientT > 650) {
        ambientT = now;
        var keys = Object.keys(wires);
        if (keys.length && packets.length < 6) launch(wires[keys[(Math.random() * keys.length) | 0]], false, 1700, true);
      }
      for (var i = packets.length - 1; i >= 0; i--) {
        var p = packets[i], t = Math.min(1, (now - p.t0) / p.dur);
        if (!p.el.isConnected) { packets.splice(i, 1); continue; }
        var pt = p.path.getPointAtLength(p.len * (p.reverse ? 1 - ease(t) : ease(t)));
        p.el.setAttribute("cx", pt.x); p.el.setAttribute("cy", pt.y);
        if (t >= 1) { p.el.remove(); packets.splice(i, 1); if (p.done) p.done(); }
      }
      if (packets.length || (inView && showWires && !journey && !reduce)) requestAnimationFrame(tick);
      else rafOn = false;
    }
    function kick() { if (!rafOn && inView && !reduce) { rafOn = true; requestAnimationFrame(tick); } }

    /* inspector */
    function fill(id, text, stepLabel) {
      var n = DATA.nodes[id];
      if (!n) return;
      idle.hidden = true; body.hidden = false;
      f.layer.textContent = n.layer;
      f.name.textContent = n.name;
      f.role.textContent = "· " + n.role;
      f.text.textContent = text || n.detail;
      f.step.hidden = !stepLabel; f.step.textContent = stepLabel || "";
      f.jnav.hidden = !journey;
      while (f.stages.firstChild) f.stages.removeChild(f.stages.firstChild);
      if (n.stages.length) {
        var lbl = document.createElement("span");
        lbl.textContent = insp.getAttribute("data-label-stages");
        f.stages.appendChild(lbl);
        n.stages.forEach(function (s) {
          var b = document.createElement("button");
          b.type = "button"; b.className = "sx-stagechip"; b.setAttribute("data-goto-stage", s);
          b.textContent = pad(s) + " · " + DATA.stageTitles[s];
          f.stages.appendChild(b);
        });
      }
      body.classList.remove("is-swap"); void body.offsetWidth; body.classList.add("is-swap");
    }
    function clearInspector() { idle.hidden = false; body.hidden = true; }

    /* visual state */
    function paint() {
      var lit = journey ? DATA.journeys[journey][step].node : null;
      var visited = {}, hot = {};
      if (journey) {
        DATA.journeys[journey].slice(0, step + 1).forEach(function (s) { visited[s.node] = true; });
      }
      Object.keys(nodeEls).forEach(function (id) {
        var el = nodeEls[id], related = false;
        if (selected && !journey) {
          related = DATA.edges.some(function (e) { return (e[0] === selected && e[1] === id) || (e[1] === selected && e[0] === id); });
        }
        el.classList.toggle("is-selected", !journey && id === selected);
        el.classList.toggle("is-related", related);
        el.classList.toggle("is-lit", id === lit);
        el.classList.toggle("is-visited", !!visited[id] && id !== lit);
        el.setAttribute("aria-pressed", !journey && id === selected ? "true" : "false");
      });
      if (selected && !journey) {
        DATA.edges.forEach(function (e) { if (e[0] === selected || e[1] === selected) hot[e[0] + ">" + e[1]] = true; });
      }
      if (journey) {
        var steps = DATA.journeys[journey];
        for (var i = 1; i <= step; i++) {
          var a = steps[i - 1].node, b = steps[i].node;
          hot[a + ">" + b] = true; hot[b + ">" + a] = true;
        }
      }
      Object.keys(wires).forEach(function (k) { wires[k].classList.toggle("is-hot", !!hot[k]); });
      $$(".is-temp", svg).forEach(function (p) { p.classList.add("is-hot"); });
      diagram.classList.toggle("is-focus", !!(selected || journey));
    }

    function select(id) {
      stopJourney();
      selected = selected === id ? null : id;
      paint();
      if (selected) fill(selected); else clearInspector();
    }

    /* journeys */
    function setJourneyButtons() {
      $$("[data-journey]", box).forEach(function (b) {
        b.setAttribute("aria-pressed", b.getAttribute("data-journey") === journey ? "true" : "false");
      });
    }
    function stopJourney() {
      clearTimeout(jTimer);
      journey = null; step = -1;
      $$(".is-temp", svg).forEach(function (p) { p.remove(); });
      setJourneyButtons();
    }
    function showStep(i, auto) {
      var steps = DATA.journeys[journey];
      if (!steps) return;
      clearTimeout(jTimer);
      var prev = step;
      step = Math.max(0, Math.min(steps.length - 1, i));
      var s = steps[step];
      var label = insp.getAttribute("data-label-step") + " " + (step + 1) + " / " + steps.length;
      var jid = journey, at = step;
      function arrive() {
        if (journey !== jid || step !== at) return; // stopped or moved on while the packet flew
        paint();
        fill(s.node, s.text, label);
        if (auto && step < steps.length - 1) {
          jTimer = setTimeout(function () { showStep(step + 1, true); }, reduce ? 3200 : 2600);
        } else if (auto) {
          jTimer = setTimeout(function () { journey = null; setJourneyButtons(); f.jnav.hidden = true; kick(); }, 4000);
        }
      }
      if (prev >= 0 && step === prev + 1 && !reduce) {
        var h = hop(steps[prev].node, s.node);
        paint();
        launch(h.path, h.reverse, 900, false, arrive);
      } else {
        arrive();
      }
    }
    function play(id) {
      if (!DATA.journeys[id]) return;
      stopJourney();
      selected = null;
      journey = id;
      setJourneyButtons();
      showStep(0, true);
    }

    /* events */
    diagram.addEventListener("click", function (e) {
      var b = e.target.closest("[data-node]");
      userTouched = true;
      if (b) select(b.getAttribute("data-node"));
      else if (selected || journey) { stopJourney(); selected = null; paint(); clearInspector(); }
    });
    $$("[data-journey]", box).forEach(function (b) {
      b.addEventListener("click", function () {
        userTouched = true;
        var id = b.getAttribute("data-journey");
        if (journey === id) { stopJourney(); paint(); clearInspector(); } else play(id);
      });
    });
    $("[data-sx-jprev]", box).addEventListener("click", function () { if (journey) showStep(step - 1, false); });
    $("[data-sx-jnext]", box).addEventListener("click", function () { if (journey) showStep(step + 1, false); });
    f.stages.addEventListener("click", function (e) {
      var b = e.target.closest("[data-goto-stage]");
      if (!b) return;
      lifecycle.set(+b.getAttribute("data-goto-stage"));
      scrollTo($("#lifecycle"));
    });
    $("[data-sx-wires]", box).addEventListener("change", function (e) {
      showWires = e.target.checked;
      diagram.classList.toggle("no-wires", !showWires);
      kick();
    });

    var rd;
    function redraw() { cancelAnimationFrame(rd); rd = requestAnimationFrame(function () { drawWires(); }); }
    if ("ResizeObserver" in window) new ResizeObserver(redraw).observe(diagram);
    else window.addEventListener("resize", redraw);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(redraw);
    drawWires();

    onVisible(diagram, function (vis) { inView = vis; kick(); }, 0);
    // Auto-play the first journey once the console is on screen. Observe the (small) toolbar, not
    // the diagram: on phones the stacked diagram is taller than the viewport.
    onVisible($(".sx-console__bar", box), function (vis) {
      if (vis && !autoPlayed && !userTouched && !reduce) { autoPlayed = true; setTimeout(function () { if (!userTouched) play("reading"); }, 700); }
    }, 1);

    return {
      select: function (id) { userTouched = true; selected = null; select(id); },
      play: function (id) { userTouched = true; play(id); }
    };
  })();

  /* --------------------------------------- cross-section navigation --- */
  document.addEventListener("click", function (e) {
    var chip = e.target.closest("[data-node-link]");
    if (chip) {
      e.preventDefault();
      var id = chip.getAttribute("data-node-link");
      arch.select(id);
      var el = document.querySelector('[data-node="' + id + '"]');
      scrollTo(el || $("#architecture"), "center");
      return;
    }
    var auto = e.target.closest("[data-sx-autoplay]");
    if (auto) {
      e.preventDefault();
      scrollTo($("#architecture"));
      arch.play(auto.getAttribute("data-sx-autoplay"));
    }
  });
})();
