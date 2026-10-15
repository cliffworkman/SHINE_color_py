"use strict";
const $ = (id) => document.getElementById(id),
  NS = "http://www.w3.org/2000/svg";
let report,
  review,
  token,
  live = false,
  current = null,
  visible = [],
  scale = 1,
  cx = 0.5,
  cy = 0.5,
  fit = true,
  loading = 0;
let saving = Promise.resolve(),
  pending = 0,
  saveFailure = false;
const palette = { pre: "#a1b7cb", post: "#ebba73", target: "#91b69b" };
function notice(text, error = false) {
  $("notice").textContent = text;
  $("notice").classList.toggle("error", error);
}
function el(tag, text) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  return e;
}
function svgEl(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  parent.append(e);
  return e;
}
function text(svg, x, y, s) {
  const t = svgEl("text", { x, y }, svg);
  t.textContent = s;
  return t;
}
const fmt = (v) => (v == null ? "Unavailable" : Number(v).toFixed(3));
function decision(id) {
  return (
    review.decisions[id] || {
      status: "Unreviewed",
      note: "",
      reviewer: "",
      revision: 0,
    }
  );
}
function channel() {
  return $("channel").value;
}
function updateCounts() {
  const counts = { Unreviewed: 0, Accept: 0, Flag: 0, Reject: 0 };
  report.stimuli.forEach((s) => counts[decision(s.stimulus_id).status]++);
  $("counts").textContent = Object.entries(counts)
    .map(([k, v]) => `${k} ${v}`)
    .join(" · ");
}
function score(s) {
  const c = s.channels[channel()];
  return {
    name: 0,
    rmse: s.rgb_rmse,
    mean: Math.abs(c.delta_mean),
    sd: Math.abs(c.delta_sample_sd),
    hist: c.histogram_total_variation,
    gamut: s.gamut_clip_fraction ?? -1,
  }[$("sort").value];
}
function rebuild() {
  const f = $("filter").value;
  visible = report.stimuli.filter(
    (s) => f === "All" || decision(s.stimulus_id).status === f,
  );
  visible.sort(
    (a, b) => score(b) - score(a) || a.input_path.localeCompare(b.input_path),
  );
  $("scene").replaceChildren(
    ...visible.map((s) => new Option(s.input_path, s.stimulus_id)),
  );
  if (visible.length) {
    const next =
      visible.find((s) => s.stimulus_id === current?.stimulus_id) || visible[0];
    select(next);
  } else {
    current = null;
    $("beforeImage").removeAttribute("src");
    $("afterImage").removeAttribute("src");
    $("metrics").replaceChildren();
    $("histogram").replaceChildren();
    $("status").disabled = $("note").disabled = $("reviewer").disabled = true;
    notice("No images match this filter.");
  }
  updateCounts();
  summary();
}
function loadImage(image, url) {
  return new Promise((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(Error("Image unavailable or changed."));
    image.src = url;
  });
}
async function select(s) {
  const seq = ++loading;
  current = s;
  $("scene").value = s.stimulus_id;
  cx = cy = 0.5;
  fit = true;
  const d = decision(s.stimulus_id);
  $("status").value = d.status;
  $("note").value = d.note;
  $("reviewer").value = d.reviewer;
  $("status").disabled = $("note").disabled = $("reviewer").disabled = !live;
  $("dimensions").textContent = `${s.width} × ${s.height}`;
  $("outputName").textContent = s.output_path;
  $("pairIdentity").textContent =
    `Pair ${s.pair_id.slice(0, 16)} · RGB change percentile ${s.rgb_rmse_percentile.toFixed(1)}`;
  $("thumbnail").src = s.thumbnail;
  $("saveStatus").textContent = live
    ? "Saved on disk · revision " + d.revision
    : "Read-only exported snapshot";
  metrics();
  $("beforeImage").hidden = $("afterImage").hidden = true;
  try {
    if (report.portable_images === false)
      throw Error("Metadata-only snapshot: images were not included.");
    await Promise.all([
      loadImage($("beforeImage"), s.before_image),
      loadImage($("afterImage"), s.after_image),
    ]);
    if (seq !== loading) return;
    $("beforeImage").hidden = $("afterImage").hidden = false;
    layout();
    notice(
      `${s.input_path} · ${report.pipeline.colorspace}, mode ${report.pipeline.mode} · Saved-output measurements; no normalization is run here.`,
    );
  } catch (e) {
    if (seq === loading) notice(e.message, true);
  }
}
function fitScale() {
  return (
    Math.min(
      ...["beforeViewport", "afterViewport"].map((id) =>
        Math.min(
          $(id).clientWidth / current.width,
          $(id).clientHeight / current.height,
        ),
      ),
    ) * 0.98
  );
}
function layout() {
  if (!current) return;
  if (fit) scale = fitScale();
  for (const [v, i] of [
    ["beforeViewport", "beforeImage"],
    ["afterViewport", "afterImage"],
  ]) {
    const view = $(v),
      img = $(i);
    img.style.width = current.width * scale + "px";
    img.style.height = current.height * scale + "px";
    img.style.left = view.clientWidth / 2 - cx * current.width * scale + "px";
    img.style.top = view.clientHeight / 2 - cy * current.height * scale + "px";
  }
  $("zoomLabel").textContent = (scale * 100).toFixed(0) + "%";
}
function zoom(factor) {
  if (!current) return;
  fit = false;
  scale = Math.min(12, Math.max(fitScale() * 0.2, scale * factor));
  layout();
}
for (const id of ["beforeViewport", "afterViewport"]) {
  const v = $(id);
  let drag = null;
  v.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      zoom(e.deltaY < 0 ? 1.15 : 1 / 1.15);
    },
    { passive: false },
  );
  v.addEventListener("pointerdown", (e) => {
    if (!current) return;
    drag = { x: e.clientX, y: e.clientY, cx, cy };
    v.setPointerCapture(e.pointerId);
  });
  v.addEventListener("pointermove", (e) => {
    if (!drag || !current) return;
    fit = false;
    cx = drag.cx - (e.clientX - drag.x) / (current.width * scale);
    cy = drag.cy - (e.clientY - drag.y) / (current.height * scale);
    layout();
  });
  v.addEventListener("pointerup", () => (drag = null));
  v.addEventListener("pointercancel", () => (drag = null));
}
function lines(svg, series) {
  svg.replaceChildren();
  const width = 600,
    height = 170,
    left = 40,
    base = 143,
    top = 16;
  const arrays = series.map(([name, a]) => [
    name,
    a.map((x) => x / (a.reduce((s, v) => s + v, 0) || 1)),
  ]);
  const max = Math.max(0.001, ...arrays.flatMap((x) => x[1]));
  svgEl(
    "path",
    { d: `M${left},${top}V${base}H580`, fill: "none", stroke: "#50616a" },
    svg,
  );
  for (const [name, a] of arrays) {
    const points = a
      .map(
        (v, i) =>
          `${left + (i * 540) / Math.max(1, a.length - 1)},${base - (v / max) * (base - top)}`,
      )
      .join(" ");
    svgEl(
      "polyline",
      { points, fill: "none", stroke: palette[name], "stroke-width": 1.8 },
      svg,
    );
  }
  text(svg, 40, 163, "0");
  text(svg, 550, 163, "255");
  text(svg, 42, 13, "Probability (each distribution normalized)");
}
function metrics() {
  if (!current) return;
  const c = current.channels[channel()];
  $("metricTitle").textContent = `${channel()} · working 0–255 · sample SD`;
  $("metrics").replaceChildren();
  const rows = [
    ["Measure", "Original", "Saved output"],
    ["Mean", fmt(c.pre.mean), fmt(c.post_saved.mean)],
    ["Sample SD", fmt(c.pre.sample_sd), fmt(c.post_saved.sample_sd)],
    ["Mean shift", "", fmt(c.delta_mean)],
    ["Sample SD shift", "", fmt(c.delta_sample_sd)],
    ["RGB RMSE", "", fmt(current.rgb_rmse)],
    ["Channel RMSE", "", fmt(c.rmse)],
    ["Histogram TV", "", fmt(c.histogram_total_variation)],
    [
      "Histogram TV from target",
      "",
      fmt(c.post_target_histogram_total_variation),
    ],
    ["Derived target mean", "", fmt(c.target_mean)],
    ["Derived target sample SD", "", fmt(c.target_sample_sd)],
    ["Mean minus target", "", fmt(c.post_target_delta_mean)],
    ["SD minus target", "", fmt(c.post_target_delta_sample_sd)],
    ["Mean minus recorded intermediate", "", fmt(c.post_minus_recorded_mean)],
    [
      "SD minus recorded intermediate",
      "",
      fmt(c.post_minus_recorded_sample_sd),
    ],
    [
      "Recorded RGB gamut clipping",
      "",
      current.gamut_clip_fraction == null
        ? "Unavailable"
        : (100 * current.gamut_clip_fraction).toFixed(2) + "%",
    ],
  ];
  rows.forEach((r, i) => {
    const tr = el("tr");
    r.forEach((x) => tr.append(el(i === 0 ? "th" : "td", x)));
    $("metrics").append(tr);
  });
  const series = [
    ["pre", c.pre.histogram],
    ["post", c.post_saved.histogram],
  ];
  if (c.target_histogram) series.push(["target", c.target_histogram]);
  lines($("histogram"), series);
  $("provenance").textContent =
    `Target: ${c.target_provenance}. Gamut: ${current.gamut_clip_provenance}.`;
}
function scatter(id, key) {
  const svg = $(id);
  svg.replaceChildren();
  const values = report.stimuli.map((s) => s.channels[channel()]);
  const max = Math.max(
    1,
    ...values.flatMap((c) => [c.pre[key], c.post_saved[key]]),
  );
  svgEl(
    "path",
    { d: "M45,20V260H420 M45,260L420,20", fill: "none", stroke: "#50616a" },
    svg,
  );
  values.forEach((c, i) => {
    const circle = svgEl(
      "circle",
      {
        cx: 45 + (c.pre[key] / max) * 375,
        cy: 260 - (c.post_saved[key] / max) * 240,
        r: 3,
        fill: palette.post,
        opacity: 0.7,
      },
      svg,
    );
    const title = svgEl("title", {}, circle);
    title.textContent = `${report.stimuli[i].input_path}: ${fmt(c.pre[key])} → ${fmt(c.post_saved[key])}`;
  });
  text(svg, 45, 282, "Original →");
  text(svg, 48, 14, "Saved output ↑");
  text(svg, 350, 282, "Max " + max.toFixed(1));
}
function summary() {
  if (!report) return;
  const name = channel(),
    group = report.summary[name];
  $("groupInfo").textContent =
    `${report.stimuli.length} images · ${report.pipeline.colorspace} mode ${report.pipeline.mode} · equal image weight. ${name}: mean of image means ${fmt(group.pre.mean_of_image_means)} → ${fmt(group.post_saved.mean_of_image_means)}; mean sample SD ${fmt(group.pre.mean_of_image_sample_sds)} → ${fmt(group.post_saved.mean_of_image_sample_sds)}. Ranking describes transformation magnitude, not acceptability.`;
  scatter("meanScatter", "mean");
  scatter("sdScatter", "sample_sd");
  for (const [key, id] of [
    ["mean", "meanDistribution"],
    ["sample_sd", "sdDistribution"],
  ]) {
    const series = ["pre", "post_saved"].map((side, j) => {
      const h = Array(256).fill(0);
      report.stimuli.forEach(
        (s) => h[Math.min(255, Math.round(s.channels[name][side][key]))]++,
      );
      return [j ? "post" : "pre", h];
    });
    lines($(id), series);
  }
  lines($("groupHistogram"), [
    ["pre", group.pre.average_probability_histogram],
    ["post", group.post_saved.average_probability_histogram],
  ]);
  $("flagged").replaceChildren();
  report.stimuli
    .filter((s) => ["Flag", "Reject"].includes(decision(s.stimulus_id).status))
    .forEach((s) => {
      const li = el("li"),
        b = el("button", s.input_path),
        d = decision(s.stimulus_id);
      b.onclick = async () => {
        if (!(await flush())) return;
        $("filter").value = "All";
        current = s;
        rebuild();
        showPage(false);
      };
      li.append(b, el("span", `${d.status}: ${d.note}`));
      $("flagged").append(li);
    });
}
function queueSave() {
  if (!live || !current) return;
  const s = current;
  const draft = {
    stimulus_id: s.stimulus_id,
    pair_id: s.pair_id,
    project_id: report.project_id,
    status: $("status").value,
    note: $("note").value,
    reviewer: $("reviewer").value,
  };
  pending++;
  $("saveStatus").textContent = "Saving to disk…";
  saving = saving.then(async () => {
    try {
      if (saveFailure)
        throw Error("A prior save failed; reload or retry before continuing.");
      const response = await fetch("api/decision", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Review-Token": token,
        },
        body: JSON.stringify({
          ...draft,
          revision: decision(s.stimulus_id).revision,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw Error(result.error || "Save failed");
      review.decisions[s.stimulus_id] = result;
      updateCounts();
      summary();
      if (current?.stimulus_id === s.stimulus_id) {
        $("saveStatus").textContent =
          "Saved on disk · revision " + result.revision;
        $("saveStatus").classList.remove("error");
      }
    } catch (e) {
      saveFailure = true;
      $("saveStatus").textContent = e.message;
      $("saveStatus").classList.add("error");
      $("retry").hidden = false;
    } finally {
      pending--;
    }
  });
}
async function flush() {
  if (noteTimer) {
    clearTimeout(noteTimer);
    noteTimer = null;
    queueSave();
  }
  await saving;
  return !saveFailure;
}
async function move(step) {
  if (!(await flush()) || !visible.length) return;
  const i = visible.findIndex((s) => s.stimulus_id === current?.stimulus_id);
  select(visible[(i + step + visible.length) % visible.length]);
}
function showPage(summaryPage) {
  $("pairPage").hidden = summaryPage;
  $("summaryPage").hidden = !summaryPage;
  $("pairTab").setAttribute("aria-pressed", !summaryPage);
  $("summaryTab").setAttribute("aria-pressed", summaryPage);
  if (summaryPage) summary();
  else layout();
}
$("prev").onclick = () => move(-1);
$("next").onclick = () => move(1);
$("scene").onchange = async () => {
  if (await flush())
    select(visible.find((s) => s.stimulus_id === $("scene").value));
  else $("scene").value = current.stimulus_id;
};
for (const id of ["filter", "sort", "channel"])
  $(id).onchange = async () => {
    if (await flush()) rebuild();
  };
function saveNow() {
  clearTimeout(noteTimer);
  noteTimer = null;
  queueSave();
}
$("status").onchange = saveNow;
$("note").onchange = saveNow;
$("reviewer").onchange = saveNow;
let noteTimer;
function schedule() {
  clearTimeout(noteTimer);
  noteTimer = setTimeout(() => {
    noteTimer = null;
    queueSave();
  }, 300);
}
$("note").oninput = schedule;
$("reviewer").oninput = schedule;
$("retry").onclick = () => {
  saveFailure = false;
  $("retry").hidden = true;
  queueSave();
};
$("fit").onclick = () => {
  cx = cy = 0.5;
  fit = true;
  layout();
};
$("native").onclick = () => {
  fit = false;
  scale = 1;
  layout();
};
$("plus").onclick = () => zoom(1.4);
$("minus").onclick = () => zoom(1 / 1.4);
$("pairTab").onclick = () => showPage(false);
$("summaryTab").onclick = () => showPage(true);
$("aboutButton").onclick = () => $("about").showModal();
$("closeAbout").onclick = () => $("about").close();
window.addEventListener("resize", layout);
document.addEventListener("keydown", (e) => {
  if (
    e.target.closest("input,textarea,select") ||
    e.ctrlKey ||
    e.metaKey ||
    e.altKey ||
    $("about").open
  )
    return;
  if (e.key === "ArrowLeft") {
    e.preventDefault();
    move(-1);
  }
  if (e.key === "ArrowRight") {
    e.preventDefault();
    move(1);
  }
});
window.addEventListener("beforeunload", (e) => {
  if (pending || noteTimer || saveFailure) {
    e.preventDefault();
    e.returnValue = "Unsaved review changes";
  }
});
async function download(kind) {
  if (!(await flush())) return;
  if (live) {
    const r = await fetch("api/export." + kind);
    if (!r.ok) {
      notice("Export failed", true);
      return;
    }
    const blob = await r.blob();
    saveBlob(blob, "shine_review." + kind);
  } else if (kind === "json") {
    saveBlob(
      new Blob([JSON.stringify({ report, review }, null, 2)], {
        type: "application/json",
      }),
      "shine_review.json",
    );
  } else {
    location.href = "metrics.csv";
  }
}
function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob),
    a = el("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("csvExport").onclick = (e) => {
  e.preventDefault();
  download("csv");
};
$("jsonExport").onclick = (e) => {
  e.preventDefault();
  download("json");
};
async function start() {
  try {
    let session;
    try {
      const response = await fetch("api/session");
      if (!response.ok) throw Error();
      session = await response.json();
      live = true;
    } catch {
      const response = await fetch("report.json");
      if (!response.ok)
        throw Error(
          "Open this project with the local review server, or serve the exported snapshot locally.",
        );
      const data = await response.json();
      session = {
        report: data,
        review: data.embedded_review || { decisions: {} },
      };
    }
    report = session.report;
    review = session.review;
    token = session.token;
    const keys = Object.keys(report.stimuli[0].channels);
    $("channel").replaceChildren(...keys.map((k) => new Option(k, k)));
    $("runInfo").textContent = "Run " + report.manifest_sha256.slice(0, 12);
    rebuild();
  } catch (e) {
    notice(e.message, true);
  }
}
window.reviewSnapshot = () => ({
  stimulus: current?.stimulus_id,
  cx,
  cy,
  scale,
  live,
  pending,
  saveFailure,
});
start();
