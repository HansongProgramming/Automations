// ==================  CONFIG  ==================
const SHEET_ID = '1iOUZE7-yFr0AYz1wMXjRt7vVvEX_jskcIvoh3sTh2Zo';
// =============================================

/* -------------- pull ONLY from node “SOP Builder” -------------- */
const upstream = $('SOP Builder').first()?.json;
if (!upstream)
  throw new Error('Node "SOP Builder" is required but produced no data.');

/* ---------- build runtime SOP & DUR --------------- */
const safeObj = o => (o && typeof o === 'object' && !Array.isArray(o) ? o : {});

const SOP = {
  gen: safeObj(upstream.gen),
  svc: safeObj(upstream.svc),
  team: safeObj(upstream.team)
};

/* =====  NEW:  make absolutely sure svc.list is a flat, lower-case array  ==== */
let rawList = SOP.svc.list;
if (typeof rawList === 'object' && !Array.isArray(rawList)) {
  // object whose KEYS are service names  ->  ["haircut","color", …]
  rawList = Object.keys(rawList);
}
if (!Array.isArray(rawList)) rawList = [];          // final safety
SOP.svc.list = rawList.map(s => String(s).trim().toLowerCase()); // normalise
/* ====================================================================== */

const DUR = {};
if (SOP.svc.duration_mins && typeof SOP.svc.duration_mins === 'object') {
  Object.entries(SOP.svc.duration_mins).forEach(([svc, min]) => {
    DUR[svc] = Number(min);
  });
}

// legacy fall-backs
if (!SOP.svc.price)                SOP.svc.price = {};
if (!SOP.team.names)               SOP.team.names = { senior: [], junior: [], tech: [] };
/* ------------------------------------------------------- */

// ---- helper: normalise 12-hour or 24-hour time → "HH:MM" 24-hour ----
function normaliseTime(t) {
  t = t.trim();
  if (/^\d{1,2}:\d{2}$/.test(t)) return t.padStart(5,'0');
  const m = t.match(/^(\d{1,2})\s*(AM|PM)$/i);
  if (!m) throw new Error('Time must be "HH:MM" or "H AM/PM"');
  let h = parseInt(m[1],10);
  const isPm = m[2].toUpperCase() === 'PM';
  if (h === 12) h = isPm ? 12 : 0;
  else if (isPm) h += 12;
  return `${String(h).padStart(2,'0')}:00`;
}

// ---- helper: build ISO string, clamp 10-19h ----
function parseSlot(isoDate, time24) {
  const [h, m] = time24.split(':').map(Number);
  const d = new Date(isoDate + 'T' + time24 + ':00');
  let hour = Math.min(19, Math.max(10, h));
  d.setHours(hour, m, 0, 0);
  return d.toISOString();
}

// ---- main ----
const out = [];
for (const [idx, item] of items.entries()) {
  /* ---------- sanity check ---------- */
  if (!item.json || typeof item.json.output !== 'string') {
    console.warn(`Item #${idx} skipped – missing or non-string "json.output"`);
    continue;
  }
  /* ---------------------------------- */

  const blk = item.json.output.match(/```json\s*([\s\S]*?)```/);
  if (!blk) throw new Error('No JSON fence in item #' + idx);
  const src = JSON.parse(blk[1]);

  const st = (src.status || '').toLowerCase();
  let action = 'new';
  if (/update|reschedule/.test(st)) action = 'updated';
  if (/cancel|delete/.test(st))     action = 'deleted';

  const bd = src.booking_details || src.details || src;
  const bid = bd.bookingId || src.bookingId || 'b_' + Math.random().toString(36).slice(2, 10);
  const service = (bd.service || '').toLowerCase().trim();
  if (!SOP.svc.list.includes(service))
    throw new Error(`Service "${service}" not in official list`);

  const stylist = (bd.stylist || SOP.team.names.senior[0]);

  const price = SOP.svc.price[service] || 500;
  const duration = DUR[service] || 60;

  const startISO = parseSlot(bd.date, normaliseTime(bd.time));

  out.push({
    action,
    bookingID: bid,
    clientName : bd.name,
    clientEmail: bd.email,
    clientPhone: bd.phone,
    service,
    stylist,
    price: String(price),
    durationMin: duration,
    startDateTime: startISO,
    spreadsheetId: SHEET_ID,
    rowNumber: null
  });
}
return out;
