// Upload, status polling, preview, copy, download, delete. All text goes in via textContent.
"use strict";

const $ = (s) => document.querySelector(s);
const app = $("#app");
const sheet = $("#sheet");
const MAX_BYTES = Number(app.dataset.maxBytes);
const TEMP_MINUTES = app.dataset.tempMinutes;
const ACCEPT = $("#file").accept.split(",");
const POLL_MS = 1000;

let selected = null;   // job id shown in the sheet
let current = null;    // job object shown in the sheet
let previewText = "";
let pollTimer = null;

const mib = (n) => (n / 1024 / 1024).toFixed(1);
const mdName = (name) => name.replace(/\.[^.]+$/, "") + ".md";
const isActive = (job) => job.state === "queued" || job.state === "running";

function when(seconds) {
  const d = new Date(seconds * 1000);
  const today = new Date().toDateString() === d.toDateString();
  return today
    ? d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false })
    : d.toLocaleDateString("ko-KR", { month: "long", day: "numeric" });
}

async function api(path, options) {
  const response = await fetch(path, { credentials: "same-origin", ...options });
  if (response.status === 401) {
    location.href = "/login?expired";
    throw new Error("unauthenticated");
  }
  return response;
}

let toastTimer;
function toast(message) {
  const t = $("#toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 2500);
}

function setState(s) {
  for (const el of sheet.querySelectorAll("[data-s]")) el.hidden = el.dataset.s !== s;
  sheet.classList.remove("fresh");
  if (s === "success") { void sheet.offsetWidth; sheet.classList.add("fresh"); }
}

// ---------- 최근 작업 ----------
function statusOf(job) {
  if (job.state === "queued") return ["대기 중", "wait"];
  if (job.state === "running") return ["변환 중", "wait"];
  if (job.state === "succeeded") return job.result === "available" ? ["완료", "ok"] : ["만료", "gone"];
  if (job.state === "timed_out") return ["시간 초과", "err"];
  if (job.state === "interrupted") return ["중단", "err"];
  return ["실패", "err"];
}

async function refreshList() {
  const jobs = await (await api("/api/jobs")).json();
  const list = $("#jobs");
  list.replaceChildren(...jobs.map((job) => {
    const [label, cls] = statusOf(job);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "job";
    button.dataset.id = job.id;
    button.setAttribute("aria-current", String(job.id === selected));
    const name = document.createElement("span"); name.className = "name"; name.textContent = job.name;
    const at = document.createElement("span"); at.className = "when"; at.textContent = when(job.created_at);
    const st = document.createElement("span"); st.className = "status " + cls; st.textContent = label;
    button.append(name, at, st);
    button.addEventListener("click", () => select(job.id));
    const li = document.createElement("li");
    li.append(button);
    return li;
  }));
  $("#jobs-empty").hidden = jobs.length > 0;
  return jobs;
}

// ---------- 시트 ----------
async function select(id) {
  clearTimeout(pollTimer);
  selected = id;
  for (const b of document.querySelectorAll(".job")) b.setAttribute("aria-current", String(b.dataset.id === id));
  const response = await api(`/api/jobs/${id}`);
  if (response.status === 404) { selected = null; setState("idle"); refreshList(); return; }
  show(await response.json());
}

async function show(job) {
  const wasActive = current && current.id === job.id && isActive(current);
  current = job;
  if (isActive(job)) { showRunning(job); pollTimer = setTimeout(poll, POLL_MS); return; }
  if (wasActive) refreshList();
  if (job.state === "succeeded" && job.result === "available") return showSuccess(job);
  if (job.state === "succeeded") return showExpired(job);
  showFailed(job.name, reasonFor(job), job.upload_kept
    ? "원본 파일은 보관 정책에 따라 서버에 남아 있습니다."
    : "원본 파일은 서버에서 삭제했습니다.", true);
}

async function poll() {
  if (!selected) return;
  const response = await api(`/api/jobs/${selected}`);
  if (response.ok) show(await response.json());
}

function steps(upload, queue, convert) {
  const mark = (id, s) => { $(id).className = s; };
  mark("#step-upload", upload); mark("#step-queue", queue); mark("#step-convert", convert);
}

function showRunning(job) {
  $("#run-title").textContent = job.name;
  $("#step-upload").textContent = `업로드 완료 (${mib(job.size)} MiB)`;
  if (job.state === "queued") steps("done", "now", "");
  else steps("done", "done", "now");
  setState("running");
}

async function showSuccess(job) {
  const response = await api(`/api/jobs/${job.id}/preview`);
  if (!response.ok) { return select(job.id); }  // expired between status and preview
  previewText = await response.text();
  $("#ok-title").textContent = mdName(job.name);
  const meta = [`원본 ${job.name}`, `${when(job.finished_at)} 변환`,
    job.delete_after_download ? "다운로드 후 삭제" : `${when(job.result_expires_at)}까지 보관`];
  $("#ok-meta").replaceChildren(...meta.map((m) => { const s = document.createElement("span"); s.textContent = m; return s; }));
  $("#trunc").hidden = response.headers.get("X-Truncated") !== "1";
  $("#no-keep").hidden = !job.delete_after_download;
  $("#no-keep").textContent = `이 결과는 보관하지 않습니다. 다운로드가 끝나면 서버에서 삭제되고, 받지 않아도 ${TEMP_MINUTES}분 뒤 삭제됩니다.`;
  $("#download").href = `/api/jobs/${job.id}/download`;
  renderCode(previewText);
  setState("success");
}

function renderCode(text) {
  const pre = $("#code");
  pre.replaceChildren(...text.split("\n").map((line) => {
    const l = document.createElement("span");
    l.className = "l" + (/^#{1,6} /.test(line) ? " h" : "");
    const t = document.createElement("span");
    t.className = "txt";
    t.textContent = line || " ";
    l.append(t);
    return l;
  }));
}

function showExpired(job) {
  $("#gone-title").textContent = `${mdName(job.name)}는 더 이상 받을 수 없습니다`;
  $("#gone-text").textContent = (job.delete_after_download
    ? "다운로드가 끝났거나 임시 보관 시간이 지나 서버에서 삭제되었습니다."
    : "보관 기간이 끝나 서버에서 삭제되었습니다.") + " 필요하면 원본을 다시 올리세요.";
  setState("expired");
}

function reasonFor(job) {
  if (job.error === "TIMEOUT") return ["변환이 120초 안에 끝나지 않았습니다", "문서가 너무 크거나 복잡해서 중단했습니다. 문서를 나눠서 다시 올려 주세요."];
  if (job.error === "EMPTY_RESULT") return ["텍스트를 찾지 못했습니다", job.message];
  if (job.error === "INTERRUPTED") return ["변환이 중단되었습니다", job.message];
  return ["변환하지 못했습니다", job.message];
}

function showFailed(name, [title, body], uploadNote, deletable) {
  $("#fail-title").textContent = `${name}를 변환하지 못했습니다`;
  const strong = document.createElement("strong");
  strong.textContent = title;
  $("#reason").replaceChildren(strong, body);
  $("#fail-upload").textContent = uploadNote;
  $("#fail-delete").hidden = !deletable;
  setState("failed");
}

// ---------- 업로드 ----------
const REJECTED = {
  TOO_LARGE: (file) => [`파일이 ${mib(MAX_BYTES)} MiB를 넘습니다`, `올린 파일은 ${mib(file.size)} MiB입니다. 나누거나 압축한 뒤 다시 올려 주세요.`],
  UNSUPPORTED_FORMAT: () => ["지원하지 않는 형식입니다", `${ACCEPT.map((e) => e.slice(1).toUpperCase()).join(", ")} 파일만 올릴 수 있습니다.`],
  QUEUE_FULL: () => ["변환을 기다리는 문서가 많습니다", "앞선 변환이 끝난 뒤 다시 올려 주세요."],
};

function reject(file, reason) {
  const make = REJECTED[reason] || (() => ["업로드하지 못했습니다", "연결 상태를 확인한 뒤 다시 시도해 주세요."]);
  clearTimeout(pollTimer);
  selected = null;
  showFailed(file.name, make(file), "파일은 서버에 저장하지 않았습니다.", false);
}

async function upload(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (!file.name.includes(".") || !ACCEPT.includes(ext)) return reject(file, "UNSUPPORTED_FORMAT");
  if (file.size > MAX_BYTES) return reject(file, "TOO_LARGE");
  clearTimeout(pollTimer);
  selected = null;
  $("#run-title").textContent = file.name;
  $("#step-upload").textContent = `업로드 중 (${mib(file.size)} MiB)`;
  steps("now", "", "");
  setState("running");
  const form = new FormData();
  form.append("file", file);
  let response;
  try {
    response = await api("/api/jobs", { method: "POST", body: form });
  } catch (error) {
    if (error.message !== "unauthenticated") reject(file, "NETWORK");
    return;
  }
  if (response.status !== 202) {
    const body = await response.json().catch(() => ({}));
    return reject(file, body.error);
  }
  const job = await response.json();
  selected = job.id;
  await refreshList();
  show(job);
}

const input = $("#file");
input.addEventListener("change", () => {
  if (input.files[0]) upload(input.files[0]);
  input.value = "";
});
const drop = $("#drop");
for (const e of ["dragenter", "dragover"]) drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add("over"); });
for (const e of ["dragleave", "drop"]) drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.remove("over"); });
drop.addEventListener("drop", (ev) => { if (ev.dataTransfer.files[0]) upload(ev.dataTransfer.files[0]); });

// ---------- 결과 도구 ----------
// The Clipboard API exists only on HTTPS/localhost; plain-http LAN access falls back to execCommand.
async function copyText(text) {
  if (window.isSecureContext && navigator.clipboard) {
    try { await navigator.clipboard.writeText(text); return true; } catch { /* fall through */ }
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.cssText = "position:fixed;top:0;left:0;width:1px;height:1px;opacity:0";
  document.body.append(area);
  area.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch { ok = false; }
  area.remove();
  return ok;
}

$("#copy").addEventListener("click", async () => {
  const partial = !$("#trunc").hidden;
  if (await copyText(previewText)) {
    toast(partial ? "미리보기 부분(64 KiB)만 복사했습니다" : "Markdown을 복사했습니다");
  } else {
    const range = document.createRange();
    range.selectNodeContents($("#code"));
    getSelection().removeAllRanges();
    getSelection().addRange(range);
    toast("복사하지 못했습니다. 선택된 원문을 직접 복사하세요");
  }
});

$("#download").addEventListener("click", () => {
  toast("다운로드를 시작했습니다");
  // A keep-N result is deleted after the transfer; refresh the list so it shows as expired.
  if (current && current.delete_after_download) setTimeout(refreshList, 2000);
});

function confirmDelete() {
  $("#confirm-text").textContent = `${mdName(current.name)} 작업이 서버에서 바로 삭제됩니다. 삭제한 결과는 되돌릴 수 없습니다.`;
  $("#confirm").showModal();
}
$("#delete").addEventListener("click", confirmDelete);
$("#fail-delete").addEventListener("click", confirmDelete);
$("#confirm").addEventListener("close", async () => {
  if ($("#confirm").returnValue !== "delete" || !current) return;
  const response = await api(`/api/jobs/${current.id}`, { method: "DELETE" });
  if (response.status === 409) return toast("변환이 끝난 뒤에 삭제할 수 있습니다");
  if (!response.ok && response.status !== 404) return toast("삭제하지 못했습니다. 잠시 뒤 다시 시도하세요");
  toast("삭제했습니다");
  selected = null;
  current = null;
  setState("idle");
  refreshList();
});

// ---------- 시작 ----------
refreshList().then((jobs) => {
  const active = jobs.find(isActive);
  if (active) select(active.id);
});
