// XiteAI model gateway, at the edge.
//
// WHAT THIS IS FOR. XOS1 must never carry a provider API key: a key on a
// customer's disk is a key anyone can lift, and one lifted key bills the
// company for everyone. So the app proves which machine it is, gets a token
// that lasts minutes, and this Worker makes the provider call on its behalf.
// The key lives in Cloudflare Secrets Store and never leaves the edge.
//
// WHY HERE AND NOT THE TERMINAL. The Terminal is a company console with
// dozens of users; this is in the path of every message from every user.
// Running them in one process means an inference spike takes down payroll.
// It also runs in ~300 cities, so a user in Jakarta is served from Jakarta
// rather than crossing an ocean to one box.
//
// THE TRUST MODEL IS UNCHANGED from the Terminal's version:
//   device signs (Ed25519)  ->  short-lived token  ->  key stays server-side
//
// REVOCATION WITHOUT A ROUND TRIP. Asking the Terminal "is this device still
// allowed?" on every call would put the Terminal back in the hot path and
// undo the point. Instead the Terminal pushes revoked hardware hashes into
// KV; this reads that (cached by the edge) and refuses them. A healthy
// device costs zero extra calls, and a revoked one stops within propagation.

const TOKEN_TTL_S = 15 * 60;
const TOKEN_PREFIX = "xtg1";
const MAX_BODY = 256 * 1024;
const MAX_SKEW_MS = 10 * 60 * 1000;

const PROVIDERS = {
  deepinfra: { secret: "DEEPINFRA_API_KEY", url: "https://api.deepinfra.com/v1/openai/chat/completions" },
  baseten:   { secret: "BASETEN_API_KEY",   url: "https://inference.baseten.co/v1/chat/completions" },
  openai:    { secret: "OPENAI_API_KEY",    url: "https://api.openai.com/v1/chat/completions" },
  cerebras:  { secret: "CEREBRAS_API_KEY",  url: "https://api.cerebras.ai/v1/chat/completions" },
};

// ── small helpers ────────────────────────────────────────────────────────────

const enc = new TextEncoder();
const b64 = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes)));
const unb64 = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
const b64url = (bytes) => b64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

const fail = (status, message, extra = {}) =>
  new Response(JSON.stringify({ error: { message } }), {
    status, headers: { "content-type": "application/json", "cache-control": "no-store", ...extra },
  });

// Constant-time compare: a token check must not leak where it stopped matching.
function sameString(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// ── tokens: stateless, HMAC over their own claims ────────────────────────────

async function tokenKey(env) {
  // Derived from the signing secret so this key can only ever sign tokens.
  const material = await crypto.subtle.digest("SHA-256", enc.encode("gateway-token|" + env.TOKEN_SIGNING_KEY));
  return crypto.subtle.importKey("raw", material, { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

async function issueToken(env, hardwareHash) {
  const claims = { h: hardwareHash, e: Math.floor(Date.now() / 1000) + TOKEN_TTL_S };
  const body = b64url(enc.encode(JSON.stringify(claims)));
  const sig = b64url(await crypto.subtle.sign("HMAC", await tokenKey(env), enc.encode(body)));
  return `${TOKEN_PREFIX}.${body}.${sig}`;
}

async function readToken(env, token) {
  const parts = (token || "").split(".");
  if (parts.length !== 3 || parts[0] !== TOKEN_PREFIX) throw new Error("not a token");
  const expected = b64url(await crypto.subtle.sign("HMAC", await tokenKey(env), enc.encode(parts[1])));
  if (!sameString(parts[2], expected)) throw new Error("token doesn't check out");
  const claims = JSON.parse(new TextDecoder().decode(unb64(parts[1])));
  if (Number(claims.e) < Date.now() / 1000) throw new Error("token expired");
  return claims.h;
}

// ── device identity: the same signed envelope check-in uses ──────────────────

async function verifyEnvelope(body) {
  const payloadBytes = unb64(body.payload);
  const sigBytes = unb64(body.signature);
  const pkBytes = unb64(body.public_key);
  if (pkBytes.length !== 32 || sigBytes.length !== 64) throw new Error("bad key or signature length");

  const key = await crypto.subtle.importKey("raw", pkBytes, { name: "Ed25519" }, false, ["verify"]);
  const ok = await crypto.subtle.verify({ name: "Ed25519" }, key, sigBytes, payloadBytes);
  if (!ok) throw new Error("signature does not match payload");

  const payload = JSON.parse(new TextDecoder().decode(payloadBytes));
  if (payload.v !== 1) throw new Error("unsupported payload version");
  if (!/^[0-9a-f]{64}$/.test(String(payload.hardware_hash || ""))) throw new Error("bad hardware_hash");
  const sentAt = Date.parse(payload.sent_at);
  if (!sentAt || Math.abs(Date.now() - sentAt) > MAX_SKEW_MS) throw new Error("sent_at is too far from server time");
  return payload;
}

async function isRevoked(env, hardwareHash) {
  if (!env.REVOKED) return false;                    // no list bound: nothing is revoked
  return (await env.REVOKED.get(hardwareHash)) !== null;
}

// ── rate limit: per device, per minute ───────────────────────────────────────
// Uses the rate limiting binding when one is configured. Without it the
// Terminal's own per-device limit and the provider's remain the backstop.

async function overLimit(env, hardwareHash) {
  if (!env.RATE) return false;
  const { success } = await env.RATE.limit({ key: hardwareHash });
  return !success;
}

// ── routes ───────────────────────────────────────────────────────────────────

async function handleToken(request, env) {
  const raw = await request.text();
  if (raw.length > 8 * 1024) return fail(413, "Too large.");
  let payload;
  try {
    payload = await verifyEnvelope(JSON.parse(raw));
  } catch (e) {
    return fail(401, e.message);
  }
  if (await isRevoked(env, payload.hardware_hash)) return fail(403, "This machine is no longer allowed.");
  if (await overLimit(env, payload.hardware_hash)) return fail(429, "Slow down.", { "retry-after": "60" });
  return json({ token: await issueToken(env, payload.hardware_hash), expires_in: TOKEN_TTL_S });
}

async function handleChat(request, env, provider) {
  const p = PROVIDERS[provider];
  if (!p) return fail(404, "No provider by that name.");

  const auth = request.headers.get("authorization") || "";
  if (!auth.toLowerCase().startsWith("bearer ")) return fail(401, "Missing token.");
  let hardwareHash;
  try {
    hardwareHash = await readToken(env, auth.slice(7).trim());
  } catch (e) {
    return fail(401, e.message);
  }
  if (await isRevoked(env, hardwareHash)) return fail(403, "This machine is no longer allowed.");
  if (await overLimit(env, hardwareHash)) return fail(429, "Slow down.", { "retry-after": "60" });

  const raw = await request.text();
  if (raw.length > MAX_BODY) return fail(413, "Too large.");
  let ask;
  try {
    ask = JSON.parse(raw);
  } catch {
    return fail(400, "Body must be JSON.");
  }
  if (!ask || !ask.messages) return fail(400, "messages is required.");

  // Secrets Store bindings expose .get(); a plain Worker secret is a string.
  const binding = env[p.secret];
  const key = typeof binding === "string" ? binding : await binding?.get();
  if (!key) return fail(503, "That key isn't set on the gateway.");

  const upstream = await fetch(p.url, {
    method: "POST",
    headers: { authorization: `Bearer ${key}`, "content-type": "application/json",
               "user-agent": "xiteai-gateway" },
    body: JSON.stringify(ask),
  });

  // Streamed straight back, untouched: time-to-first-token stays the
  // provider's. The key is never in anything returned or logged.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") || "application/json",
      "cache-control": "no-store",
    },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method !== "POST") return fail(405, "POST only.");

    if (url.pathname === "/api/v1/ai/token") return handleToken(request, env);

    const chat = url.pathname.match(/^\/api\/v1\/ai\/([a-z0-9_-]+)\/chat\/completions$/);
    if (chat) return handleChat(request, env, chat[1]);

    return fail(404, "Nothing here.");
  },
};
