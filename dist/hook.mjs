// plugin/src/hook.ts
import { isAbsolute as isAbsolute2, resolve as resolve2 } from "node:path";

// plugin/src/held.ts
import { readFile, rm } from "node:fs/promises";
import { join as join2 } from "node:path";

// machine/config.ts
import { homedir } from "node:os";
import { join } from "node:path";

// src/shared/schema/core.ts
var ok = (value) => ({ ok: true, value });
var fail = (path, message) => ({ ok: false, issues: [{ path, message }] });
var at = (path, key) => path ? `${path}.${key}` : key;
var atIndex = (path, i) => `${path}[${i}]`;
function make(kind, run, optional2) {
  return optional2 ? { kind, optional: optional2, run, parse: (v) => run(v, "") } : { kind, run, parse: (v) => run(v, "") };
}
function string(min, max, pattern) {
  return make("string", (v, p) => {
    if (typeof v !== "string") return fail(p, "must be a string");
    if (v.length < min) return fail(p, min === 1 ? "is required" : `must be at least ${min} characters`);
    if (v.length > max) return fail(p, `must be at most ${max} characters`);
    if (pattern && !pattern.test(v)) return fail(p, "has the wrong format");
    return ok(v);
  });
}
function int(min, max) {
  return make("int", (v, p) => {
    if (typeof v !== "number" || !Number.isInteger(v)) return fail(p, "must be a whole number");
    if (v < min || v > max) return fail(p, `must be between ${min} and ${max}`);
    return ok(v);
  });
}
function number(min = -Infinity, max = Infinity) {
  return make("number", (v, p) => {
    if (typeof v !== "number" || !Number.isFinite(v)) return fail(p, "must be a number");
    if (v < min || v > max) return fail(p, `must be between ${min} and ${max}`);
    return ok(v);
  });
}
function bool() {
  return make("bool", (v, p) => typeof v === "boolean" ? ok(v) : fail(p, "must be true or false"));
}
function literal(value) {
  return make("literal", (v, p) => v === value ? ok(value) : fail(p, `must be ${JSON.stringify(value)}`));
}
function enumeration(values) {
  return make(
    "enum",
    (v, p) => typeof v === "string" && values.includes(v) ? ok(v) : fail(p, `must be one of ${values.join(", ")}`)
  );
}
function unknown() {
  return make("unknown", (v, p) => v === void 0 ? fail(p, "is required") : ok(v));
}
function array(item, min = 0, max = Infinity) {
  return make("array", (v, p) => {
    if (!Array.isArray(v)) return fail(p, "must be a list");
    if (v.length < min || v.length > max) {
      return fail(p, min === max ? `must have exactly ${min} items` : `must have ${min} to ${max} items`);
    }
    const out = [];
    const issues = [];
    v.forEach((x, i) => {
      const r = item.run(x, atIndex(p, i));
      if (r.ok) out.push(r.value);
      else issues.push(...r.issues);
    });
    return issues.length ? { ok: false, issues } : ok(out);
  });
}
function tuple(items) {
  return make("tuple", (v, p) => {
    if (!Array.isArray(v) || v.length !== items.length) return fail(p, `must have exactly ${items.length} items`);
    const out = [];
    const issues = [];
    items.forEach((schema, i) => {
      const r = schema.run(v[i], atIndex(p, i));
      if (r.ok) out.push(r.value);
      else issues.push(...r.issues);
    });
    return issues.length ? { ok: false, issues } : ok(out);
  });
}
function optional(schema) {
  return make("optional", (v, p) => v === void 0 ? ok(void 0) : schema.run(v, p), true);
}
function nullable(schema) {
  return make("nullable", (v, p) => v === null ? ok(null) : schema.run(v, p));
}
function record(value, keys) {
  return make("record", (v, p) => {
    if (typeof v !== "object" || v === null || Array.isArray(v)) return fail(p, "must be an object");
    const out = {};
    const issues = [];
    for (const [k, x] of Object.entries(v)) {
      const here = at(p, k);
      const kr = k === "__proto__" ? fail(here, "is not an allowed key") : keys ? keys.run(k, here) : ok(k);
      if (!kr.ok) {
        issues.push(...kr.issues);
        continue;
      }
      const r = value.run(x, here);
      if (r.ok) Object.defineProperty(out, k, { value: r.value, enumerable: true, writable: true, configurable: true });
      else issues.push(...r.issues);
    }
    return issues.length ? { ok: false, issues } : ok(out);
  });
}

// src/shared/schema/object.ts
var isPlain = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
function object(shape) {
  const keys = Object.keys(shape);
  return make("object", (v, p) => {
    if (!isPlain(v)) return fail(p, "must be an object");
    const out = {};
    const issues = [];
    for (const k of keys) {
      const child = shape[k];
      const x = v[k];
      if (x === void 0 && child.optional) continue;
      const r = child.run(x, at(p, k));
      if (r.ok) out[k] = r.value;
      else issues.push(...r.issues);
    }
    for (const k of Object.keys(v)) {
      if (!Object.hasOwn(shape, k)) issues.push({ path: at(p, k), message: "is not an allowed field" });
    }
    return issues.length ? { ok: false, issues } : ok(out);
  });
}
function union(tag, variants) {
  const names = Object.keys(variants);
  return make("union", (v, p) => {
    if (!isPlain(v)) return fail(p, "must be an object");
    const t = v[tag];
    if (typeof t !== "string" || !Object.hasOwn(variants, t)) {
      return fail(at(p, tag), `must be one of ${names.join(", ")}`);
    }
    return variants[t].run(v, p);
  });
}
var s = {
  string,
  int,
  number,
  bool,
  literal,
  enum: enumeration,
  unknown,
  array,
  tuple,
  optional,
  nullable,
  record,
  object,
  union
};

// src/shared/enums.ts
var PERSONA_STATUS_VALUES = ["setup", "locked"];
var MEDIA_STATUS_VALUES = ["pending", "new", "picked", "approved", "rejected", "kept"];
var VIDEO_STEP_VALUES = ["script", "beats", "generate", "review", "post", "posted"];
var VIDEO_FORMAT_VALUES = ["talking", "narrated"];
var PLATFORM_VALUES = ["tiktok", "instagram", "facebook", "youtube"];
var HISTORY_SUBJECT_VALUES = ["persona", "video", "media", "post"];
var HISTORY_KIND_VALUES = [
  "decided",
  "edited",
  "prompted",
  "generated",
  "posted",
  "failed",
  "idea",
  "imported"
];
var MEASURE_VALUES = ["views", "likes", "comments", "saves", "shares", "follows", "store_visits", "sales"];

// src/shared/bible.ts
var BIBLE_LIMITS = {
  name: [1, 60],
  age: [0, 150],
  niche: [1, 80],
  usp: [0, 400],
  ethnicity: [0, 200],
  look: [1, 300],
  backstory: [1, 2e3],
  reasonOnline: [0, 400],
  signoff: [0, 200],
  gesture: [0, 200],
  guardrail: [1, 400],
  anchor: [1, 200],
  outfitName: [1, 60],
  outfitDescription: [0, 400],
  outfitRule: [0, 300],
  specialRule: [0, 300],
  locationName: [1, 60],
  locationNotes: [0, 300],
  voice: [0, 300],
  displayName: [1, 60],
  username: [1, 30],
  bioLine: [1, 150],
  bioTikTok: [0, 80]
};
var L = BIBLE_LIMITS;
var SLUG_RE = /^[a-z0-9_]{1,40}$/;
var outfit = s.object({
  name: s.string(...L.outfitName),
  description: s.string(...L.outfitDescription)
});
var location = s.object({
  slug: s.string(1, 40, SLUG_RE),
  name: s.string(...L.locationName),
  notes: s.string(...L.locationNotes)
});
var BIBLE_SHAPE = {
  name: s.string(...L.name),
  age: s.int(...L.age),
  niche: s.string(...L.niche),
  usp: s.string(...L.usp),
  ethnicity: s.string(...L.ethnicity),
  look: s.string(...L.look),
  backstory: s.string(...L.backstory),
  reasonOnline: s.string(...L.reasonOnline),
  signoff: s.string(...L.signoff),
  gesture: s.string(...L.gesture),
  guardrail: s.string(...L.guardrail),
  anchors: s.tuple([s.string(...L.anchor), s.string(...L.anchor), s.string(...L.anchor)]),
  outfits: s.tuple([
    s.object({ name: s.literal("Base"), description: s.string(1, L.outfitDescription[1]) }),
    outfit,
    outfit,
    outfit
  ]),
  outfitRule: s.string(...L.outfitRule),
  specialRule: s.string(...L.specialRule),
  locations: s.tuple([location, location, location, location]),
  voice: s.object({
    accent: s.string(...L.voice),
    age: s.string(...L.voice),
    delivery: s.string(...L.voice),
    texture: s.string(...L.voice),
    seedLine: s.string(...L.voice),
    rule: s.string(...L.voice)
  }),
  bio: s.object({
    displayName: s.string(...L.displayName),
    username: s.string(...L.username),
    lines: s.array(s.string(...L.bioLine), 1, 5),
    tiktok: s.string(...L.bioTikTok)
  })
};
var BibleSchema = s.object(BIBLE_SHAPE);
var BIBLE_KEYS = Object.keys(BIBLE_SHAPE);

// src/shared/kit.ts
var ZOOM_VALUES = ["soft", "hard"];
var CAPTION_PRESET_VALUES = ["persona", "bold", "clean"];
var SOUL_TYPE_VALUES = ["soul_2", "soul_cinematic", "reference"];
var SOUL_STATUS_VALUES = ["training", "ready", "approved", "rejected"];
var MediaIdSchema = s.string(1, 60);
var CaptionStyleSchema = s.object({
  font: s.string(1, 80),
  size: s.int(8, 300),
  primary: s.string(1, 40),
  outline: s.string(1, 40),
  highlight: s.string(1, 40),
  box: s.string(0, 40),
  positionY: s.number(0, 1e4),
  hookSeconds: s.number(0, 30),
  uppercase: s.bool(),
  maxWords: s.int(1, 20)
});
var FinishChoicesSchema = s.object({
  zoom: s.enum(ZOOM_VALUES),
  broll: s.bool(),
  captions: s.object({ preset: s.enum(CAPTION_PRESET_VALUES), style: s.optional(CaptionStyleSchema) })
});
var KitSchema = s.object({
  portrait: s.optional(MediaIdSchema),
  sheet: s.optional(MediaIdSchema),
  profile: s.optional(MediaIdSchema),
  soul: s.optional(
    s.object({
      ref: s.string(1, 200),
      type: s.enum(SOUL_TYPE_VALUES),
      status: s.enum(SOUL_STATUS_VALUES),
      tests: s.array(MediaIdSchema, 0, 12)
    })
  ),
  voice: s.optional(s.object({ sample: MediaIdSchema, cloneRef: s.optional(s.string(1, 200)) })),
  locations: s.record(MediaIdSchema, s.string(1, 40, SLUG_RE)),
  post: FinishChoicesSchema,
  shotPreset: s.optional(s.object({ talking: s.optional(s.string(0, 4e3)), narrated: s.optional(s.string(0, 4e3)) }))
});

// src/shared/job-io/spend.ts
var SpendSchema = s.optional(
  s.object({ higgsfield: s.optional(s.number(0, 1e5)), flow: s.optional(s.number(0, 1e5)) })
);

// src/shared/job-io/persona.ts
var text = s.string(0, 2e3);
var slug = s.string(1, 40, SLUG_RE);
var baseOutfit = s.object({ name: s.literal("Base"), description: s.string(1, BIBLE_LIMITS.outfitDescription[1]) });
var { look, anchors, ethnicity, outfits, voice } = BIBLE_SHAPE;
var PERSONA_INPUT = {
  bible: s.object({ prompt: text, current: s.optional(BibleSchema), change: s.optional(text) }),
  // The first outfit (the base one in the character sheet) is all the portraits need: outfits is a list of one.
  portraits: s.object({
    bible: s.object({ look, anchors, ethnicity, outfits: s.tuple([baseOutfit]) }),
    round: s.int(1, 1e3),
    prompt: s.optional(text),
    count: s.literal(6)
  }),
  soul_id: s.object({
    bible: s.object({ look, anchors, ethnicity, outfits }),
    portrait: MediaIdSchema,
    note: s.optional(text)
  }),
  locations: s.object({
    locations: s.array(s.object({ slug, name: s.string(1, 60), notes: s.string(0, 300) }), 1, 4),
    only: s.optional(slug),
    prompt: s.optional(text)
  }),
  voices: s.object({ voice, signoff: s.string(0, 200), count: s.literal(3) })
};
var PERSONA_RESULT = {
  bible: s.object({ bible: BibleSchema }),
  portraits: s.object({ media: s.array(MediaIdSchema, 6, 6), spend: SpendSchema }),
  soul_id: s.object({
    ref: s.string(1, 200),
    type: s.enum(SOUL_TYPE_VALUES),
    sheet: MediaIdSchema,
    tests: s.array(MediaIdSchema, 3, 3),
    profile: MediaIdSchema,
    spend: SpendSchema
  }),
  locations: s.object({ media: s.array(s.object({ slug, id: MediaIdSchema }), 1, 4), spend: SpendSchema }),
  voices: s.object({
    media: s.array(s.object({ id: MediaIdSchema, wpm: s.int(1, 400), check: s.string(0, 400) }), 3, 3),
    spend: SpendSchema
  })
};

// src/shared/beats.ts
var CheckSchema = s.object({ name: s.string(1, 100), ok: s.bool(), note: s.string(0, 400) });
var BeatRowSchema = s.object({
  start: s.number(0, 120),
  end: s.number(0, 120),
  shot: s.string(1, 60),
  action: s.string(1, 300),
  line: s.string(0, 300),
  face: s.string(0, 120)
});
var BEAT_ROWS_MAX = 8;
var BeatSheetSchema = s.object({
  rows: s.array(BeatRowSchema, 1, BEAT_ROWS_MAX),
  sound: s.string(0, 200),
  loopPose: s.string(0, 200),
  agentChecks: s.array(CheckSchema, 0, 20)
});

// src/shared/caption.ts
var CAPTION_MAX_CHARS = 2200;
var CAPTION_MAX_TAGS = 30;

// src/shared/script.ts
var WPM_MIN = 110;
var WPM_MAX = 170;
var SCRIPT_SHAPE = {
  hook: s.string(1, 300),
  setting: s.string(0, 400),
  lines: s.array(s.string(1, 300), 1, 12),
  guardrail: s.string(1, 400),
  wpm: s.int(WPM_MIN, WPM_MAX),
  caption: s.string(0, CAPTION_MAX_CHARS),
  hashtags: s.array(s.string(1, 100), 0, CAPTION_MAX_TAGS),
  guidance: s.string(0, 1e3),
  tiktokTrack: s.optional(s.string(0, 200)),
  youtubeTrack: s.optional(s.string(0, 200))
};
var VideoScriptSchema = s.object(SCRIPT_SHAPE);
var SCRIPT_KEYS = Object.keys(SCRIPT_SHAPE);

// src/shared/job-io/video.ts
var CAPTION_MATCH_MIN = 0.6;
var format = s.enum(VIDEO_FORMAT_VALUES);
var { look: look2, anchors: anchors2, ethnicity: ethnicity2 } = BIBLE_SHAPE;
var VIDEO_INPUT = {
  // prompt is always the topic (empty: the agent picks one); `note`, when present, is the owner's rejection comment on `current`.
  script: s.object({
    bible: BibleSchema,
    kit: s.object({ locations: s.array(s.string(1, 60), 0, 4), outfits: s.array(s.string(1, 60), 0, 4) }),
    format,
    prompt: s.string(0, 2e3),
    current: s.optional(VideoScriptSchema),
    note: s.optional(s.string(0, 2e3))
  }),
  beats: s.object({
    bible: s.object({ anchors: anchors2, look: look2 }),
    script: VideoScriptSchema,
    format,
    prompt: s.optional(s.string(0, 2e3))
  }),
  // kit.locations is the Kit's own map: slug -> media id.
  generate: s.object({
    bible: s.object({ anchors: anchors2, ethnicity: ethnicity2, look: look2 }),
    kit: s.object({
      soulRef: s.string(1, 200),
      soulType: s.optional(s.enum(SOUL_TYPE_VALUES)),
      profile: s.optional(MediaIdSchema),
      voiceRef: s.optional(s.string(1, 200)),
      portrait: MediaIdSchema,
      sheet: MediaIdSchema,
      locations: s.record(MediaIdSchema, s.string(1, 40, SLUG_RE)),
      shotPreset: s.optional(s.object({ talking: s.optional(s.string(0, 4e3)), narrated: s.optional(s.string(0, 4e3)) }))
    }),
    format,
    script: VideoScriptSchema,
    beats: BeatSheetSchema,
    attempt: s.int(1, 1e3),
    note: s.optional(s.string(0, 2e3)),
    previousTake: s.optional(MediaIdSchema)
  }),
  finish: s.object({
    take: MediaIdSchema,
    format,
    script: VideoScriptSchema,
    beats: BeatSheetSchema,
    choices: FinishChoicesSchema,
    captionStyle: CaptionStyleSchema,
    hook: s.string(1, 300)
  })
};
var VIDEO_RESULT = {
  script: s.object({ script: VideoScriptSchema }),
  beats: s.object({ beats: BeatSheetSchema }),
  generate: s.object({
    take: MediaIdSchema,
    meta: s.object({ durationS: s.number(0, 36e3), model: s.string(1, 100) }),
    spend: SpendSchema
  }),
  finish: s.object({
    clip: MediaIdSchema,
    preview: MediaIdSchema,
    thumb: MediaIdSchema,
    qc: s.object({
      seamSsim: s.optional(s.number(0, 1)),
      captionMatch: s.number(CAPTION_MATCH_MIN, 1),
      loop: s.bool()
    }),
    spend: SpendSchema
  })
};

// src/shared/jobs.ts
var JOB_INPUT = { ...PERSONA_INPUT, ...VIDEO_INPUT };
var JOB_RESULT = { ...PERSONA_RESULT, ...VIDEO_RESULT };

// src/shared/platforms.ts
var SLOT_NAMES = {
  tiktok: "TikTok",
  instagram: "Instagram",
  facebook: "Facebook",
  youtube: "YouTube",
  store: "Store"
};
var URL_MAX_CHARS = 2048;
var URL_HOSTS = {
  tiktok: ["tiktok.com", "www.tiktok.com", "vm.tiktok.com"],
  youtube: ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"],
  instagram: ["instagram.com", "www.instagram.com", "instagr.am"],
  facebook: ["facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch", "fb.com", "www.fb.com"]
};
var YT_ID = /^[A-Za-z0-9_-]{11}$/;
var TIKTOK_VIDEO = /\/video\/(\d{6,25})(?:\/|$)/;
var FB_DIGITS = /^\d{1,25}$/;
var FB_REEL = /^\/reel\/(\d{1,25})\/?$/;
var FB_VIDEOS = /^\/[^/]+\/videos\/(?:[^/]+\/)?(\d{1,25})\/?$/;
var FB_WATCH = /^\/(?:watch|video\.php)\/?$/;
function facebookId(u) {
  if (u.hostname.toLowerCase() === "fb.watch") return null;
  const v = FB_WATCH.test(u.pathname) ? u.searchParams.get("v") : null;
  if (v !== null) return FB_DIGITS.test(v) ? v : null;
  return (FB_REEL.exec(u.pathname) ?? FB_VIDEOS.exec(u.pathname))?.[1] ?? null;
}
function videoId(platform, u) {
  if (platform === "tiktok") return TIKTOK_VIDEO.exec(u.pathname)?.[1] ?? null;
  if (platform === "facebook") return facebookId(u);
  if (platform === "instagram") return null;
  const host = u.hostname.toLowerCase();
  const path = /^\/(?:shorts|embed|live|v)\/([^/]+)/.exec(u.pathname)?.[1];
  const part = host === "youtu.be" ? u.pathname.split("/")[1] : u.searchParams.get("v") ?? path;
  return typeof part === "string" && YT_ID.test(part) ? part : null;
}
var IMPORT_HOSTS = URL_HOSTS;
function check(platform, raw) {
  const text3 = raw.trim();
  const name = SLOT_NAMES[platform];
  const aName = `${platform === "instagram" ? "an" : "a"} ${name}`;
  if (text3.length === 0 || text3.length > URL_MAX_CHARS) return { ok: false, message: `Paste the ${name} link.` };
  let u;
  try {
    u = new URL(text3);
  } catch {
    return { ok: false, message: `That is not a link. Paste the ${name} link.` };
  }
  if (u.protocol !== "https:") return { ok: false, message: "The link must start with https://" };
  if (u.username || u.password || u.port) return { ok: false, message: `That is not ${aName} link.` };
  const host = u.hostname.toLowerCase();
  if (!IMPORT_HOSTS[platform].includes(host)) return { ok: false, message: `That is not ${aName} link.` };
  return { ok: true, url: text3, host, externalId: videoId(platform, u) };
}
function parseImportUrl(platform, raw) {
  return check(platform, raw);
}

// src/shared/records.ts
var str = (max) => s.string(0, max);
var MediaMetaSchema = s.object({
  width: s.optional(s.int(1, 2e4)),
  height: s.optional(s.int(1, 2e4)),
  durationS: s.optional(s.number(0, 36e3)),
  wpm: s.optional(s.int(1, 400)),
  check: s.optional(str(400)),
  qc: s.optional(s.object({ seamSsim: s.optional(s.number(0, 1)), captionMatch: s.number(0, 1), loop: s.bool() })),
  quality: s.optional(s.enum(["master", "review_copy"]))
});
var JobErrorSchema = s.object({ what: str(300), why: str(600), todo: str(600) });
var ConnectionLinesSchema = s.record(
  s.object({ done: s.bool(), skipped: s.optional(s.literal(true)), value: s.optional(str(2e3)), at: s.string(1, 40) }),
  s.string(1, 40)
);
var ConnectionFieldsSchema = s.object({
  igUserId: s.optional(str(100)),
  pageId: s.optional(str(100)),
  openId: s.optional(str(200)),
  channelId: s.optional(str(100)),
  channelUrl: s.optional(str(500)),
  storeUrl: s.optional(str(500)),
  gaProperty: s.optional(str(100)),
  scopes: s.optional(s.array(s.string(1, 200), 0, 50))
});
var TestSchema = s.object({
  ok: s.bool(),
  note: str(600),
  checks: s.array(s.object({ name: s.string(1, 100), ok: s.bool(), detail: str(600) }), 0, 30)
});
var SourceStateSchema = s.object({
  status: s.enum(["ok", "scope_missing", "not_approved", "not_connected", "error", "simulated", "unavailable"]),
  note: str(600),
  at: s.string(1, 40)
});
var ConnectionStatsSchema = s.record(SourceStateSchema, s.enum(MEASURE_VALUES));
var PostWorkSchema = s.object({
  step: s.string(1, 60),
  containerId: s.optional(str(200)),
  mediaId: s.optional(str(200)),
  fbVideoId: s.optional(str(200)),
  publishId: s.optional(str(300)),
  uploaded: s.optional(s.bool()),
  inboxAt: s.optional(s.string(1, 40)),
  tries: s.int(0, 100),
  startedAt: s.string(1, 40),
  /** The outbound call a runner is making now (src/posting/claim.ts): set by a compare-and-set before it, cleared by the save after. */
  claim: s.optional(s.object({ step: s.string(1, 40), at: s.string(1, 40) }))
});
var HistoryDataSchemas = {
  decided: s.object({ decision: s.enum(["pick", "approve", "reject", "reopen"]), note: str(2e3), what: s.optional(s.enum(["script", "video"])) }),
  edited: s.object({ key: s.string(1, 80), was: s.unknown() }),
  prompted: s.object({ prompt: str(2e3) }),
  generated: s.object({ jobId: s.string(1, 60), previous: s.optional(s.unknown()) }),
  posted: s.object({ platform: s.enum(PLATFORM_VALUES), url: str(2e3) }),
  failed: JobErrorSchema,
  idea: s.object({ hook: str(300), format: str(60), setting: str(400), why: str(600) }),
  imported: s.object({ source: str(300) })
};
var rowOf = (kind) => s.object({
  id: s.string(1, 60),
  subjectKind: s.enum(HISTORY_SUBJECT_VALUES),
  subjectId: s.string(1, 60),
  kind: s.literal(kind),
  data: HistoryDataSchemas[kind],
  by: s.string(1, 100),
  at: s.string(1, 40)
});
var HistoryRowSchema = s.union("kind", {
  decided: rowOf("decided"),
  edited: rowOf("edited"),
  prompted: rowOf("prompted"),
  generated: rowOf("generated"),
  posted: rowOf("posted"),
  failed: rowOf("failed"),
  idea: rowOf("idea"),
  imported: rowOf("imported")
});

// src/shared/setup.ts
var SETUP_TOOL_VALUES = ["ready", "missing"];
var SETUP_STORAGE_VALUES = ["drive", "local", "missing"];

// src/shared/time.ts
var isIso = (v) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/.test(v) && !Number.isNaN(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v.slice(0, 10);
var toIso = (v) => isIso(v) ? new Date(v).toISOString() : null;

// src/shared/machine.ts
var MAX_FILE_BYTES = 95 * 1024 * 1024;
var lease = s.string(1, 100);
var SetupSchema = s.object({ images: s.enum(SETUP_TOOL_VALUES), video: s.enum(SETUP_TOOL_VALUES), storage: s.enum(SETUP_STORAGE_VALUES) });
var JobClaimBodySchema = s.object({ version: s.string(1, 40) });
var HeartbeatBodySchema = s.object({
  version: s.string(1, 40),
  running: s.array(s.object({ id: s.string(1, 60), lease, phase: s.optional(s.string(1, 60)), pct: s.optional(s.number(0, 1)) }), 0, 4),
  setup: s.optional(SetupSchema)
});
var CompleteBodySchema = s.object({ lease, result: s.unknown() });
var FailBodySchema = s.object({ lease, error: JobErrorSchema, retry: s.bool() });
var PairBodySchema = s.object({ code: s.string(1, 20), name: s.string(1, 60), setup: s.optional(SetupSchema) });
var sourceRef = s.string(1, 300);
var medias = s.array(s.object({ mediaId: s.string(1, 60), status: s.enum(MEDIA_STATUS_VALUES) }), 0, 200);
var ImportPersonaBodySchema = s.object({
  sourceRef,
  prompt: s.string(0, 2e3),
  bible: s.unknown(),
  kit: s.unknown(),
  status: s.enum(PERSONA_STATUS_VALUES),
  filed: s.object({ who: s.optional(s.bool()), look: s.optional(s.bool()), locations: s.optional(s.bool()), voice: s.optional(s.bool()) }),
  media: medias
});
var isoAt = make("string", (v, p) => {
  const iso = toIso(v);
  return iso === null ? fail(p, "must be a UTC time such as 2026-10-16T12:00:00.000Z") : ok(iso);
});
var postShape = s.object({
  sourceRef,
  platform: s.enum(PLATFORM_VALUES),
  url: s.string(1, 2048),
  postedAt: isoAt,
  aiLabel: s.bool(),
  musicTrack: s.string(0, 200),
  postedBy: s.string(0, 100)
});
var importPost = make("object", (v, p) => {
  const r = postShape.run(v, p);
  if (!r.ok) return r;
  const link = parseImportUrl(r.value.platform, r.value.url);
  return link.ok ? ok({ ...r.value, url: link.url }) : fail(at(p, "url"), link.message);
});
var ImportVideoBodySchema = s.object({
  sourceRef,
  personaRef: sourceRef,
  number: s.optional(s.int(1, 1e5)),
  step: s.enum(VIDEO_STEP_VALUES),
  format: s.enum(["talking", "narrated"]),
  script: s.unknown(),
  beats: s.unknown(),
  choices: s.unknown(),
  attempt: s.int(0, 1e3),
  redoNote: s.optional(s.string(0, 2e3)),
  media: s.array(s.object({ mediaId: s.string(1, 60), status: s.enum(MEDIA_STATUS_VALUES), round: s.int(1, 1e3) }), 0, 200),
  history: s.array(s.object({
    sourceRef,
    kind: s.enum(HISTORY_KIND_VALUES),
    data: s.unknown(),
    by: s.string(1, 100),
    at: isoAt
  }), 0, 500),
  posts: s.array(importPost, 0, 50)
});

// machine/config.ts
var defaultDir = () => join(homedir(), ".config", "creator-os");
var BaseSchema = s.object({
  site: s.string(1, 300),
  token: s.string(1, 300),
  machineId: s.string(1, 100),
  workspace: s.object({ id: s.string(1, 100), name: s.string(1, 200) }),
  agentCommand: s.optional(s.string(1, 2e3)),
  statsAgentCommand: s.optional(s.string(1, 2e3)),
  skillsDir: s.optional(s.string(1, 1e3)),
  spendCap: s.optional(s.int(0, 1e5))
});
var LastSchema = s.object({ id: s.string(1, 100), type: s.string(1, 40), at: s.string(1, 40), outcome: s.string(1, 40) });
var LastJobsSchema = s.object({ text: s.optional(LastSchema), media: s.optional(LastSchema) });
var queue = Promise.resolve();

// plugin/src/held.ts
var FILE = "held.json";
var text2 = (v) => typeof v === "string" && v !== "";
function uploadedOf(v) {
  if (typeof v !== "object" || v === null || Array.isArray(v)) return null;
  const out = {};
  for (const [k, id] of Object.entries(v)) {
    if (typeof id !== "string") return null;
    out[k] = id;
  }
  return out;
}
async function readHeld(dir) {
  try {
    const raw = JSON.parse(await readFile(join2(dir, FILE), "utf8"));
    if (typeof raw !== "object" || raw === null) return null;
    const uploaded = uploadedOf(raw.uploaded);
    const { id, type, lease: lease2, folder, leaseUntil, attempt } = raw;
    if (!text2(id) || !text2(type) || !text2(lease2) || !text2(folder) || !text2(leaseUntil)) return null;
    if (typeof attempt !== "number" || !Number.isInteger(attempt) || attempt < 1 || uploaded === null) return null;
    return { id, type, lease: lease2, folder, leaseUntil, attempt, uploaded };
  } catch {
    return null;
  }
}
var chain = Promise.resolve();

// plugin/src/node-version.ts
var MIN_NODE = "22.18.0";
var parts = (version) => version.replace(/^v/, "").split(".").slice(0, 3).map((p) => Number.parseInt(p, 10) || 0);
var nodeTooOld = (version) => {
  const have = parts(version);
  const need = parts(MIN_NODE);
  for (let i = 0; i < 3; i++) {
    const a = have[i] ?? 0;
    const b = need[i] ?? 0;
    if (a !== b) return a < b;
  }
  return false;
};

// plugin/src/paths.ts
import { realpath, stat } from "node:fs/promises";
import { dirname, isAbsolute, join as join3, resolve, sep } from "node:path";
var within = (root, path) => path === root || path.startsWith(root + sep);
async function insideFolder(folder, path) {
  let root;
  try {
    root = await realpath(folder);
  } catch {
    return false;
  }
  let at2 = resolve(path);
  const rest = [];
  for (; ; ) {
    try {
      return within(root, join3(await realpath(at2), ...rest));
    } catch {
      const up = dirname(at2);
      if (up === at2) return false;
      rest.unshift(at2.slice(up.length).replace(/^[\\/]+/, ""));
      at2 = up;
    }
  }
}

// plugin/src/store.ts
var dataDirOf = (env = process.env) => env.CLAUDE_PLUGIN_DATA || defaultDir();

// plugin/src/hook.ts
async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}
function targetOf(input) {
  const given = input.tool_input?.file_path ?? input.tool_input?.notebook_path;
  if (typeof given !== "string" || given === "") return null;
  const base = typeof input.cwd === "string" && input.cwd !== "" ? input.cwd : process.cwd();
  return isAbsolute2(given) ? given : resolve2(base, given);
}
async function decide(input, dir, now) {
  const path = targetOf(input);
  const held = path === null ? null : await readHeld(dir);
  if (path === null || held === null || !(Date.parse(held.leaseUntil) > now)) return null;
  if (await insideFolder(held.folder, path)) return null;
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: `A Creator OS job is running; this writes outside its job folder ${held.folder}.`
    }
  });
}
async function main() {
  if (nodeTooOld(process.versions.node)) return;
  const answer = await decide(JSON.parse(await readStdin()), dataDirOf(), Date.now());
  if (answer !== null) process.stdout.write(`${answer}
`);
}
try {
  await main();
} catch {
}
process.exit(0);
