# XiteAI model gateway (Cloudflare Worker)

Runs the model calls at the edge so XOS1 never carries an API key, and so an
inference spike can't take the company console down with it.

Same trust model as the Terminal's built-in gateway — device signs with
Ed25519, gets a token good for 15 minutes, key stays server-side — just in a
place that scales to millions and answers from the nearest city.

## Deploy

```
cd worker
npm install -g wrangler        # once
npx wrangler login             # once

# The key that signs device tokens. Any long random string; nothing else uses it.
python -c "import secrets;print(secrets.token_urlsafe(32))"
npx wrangler secret put TOKEN_SIGNING_KEY

npx wrangler deploy
```

Wrangler prints a URL like `https://xiteai-gateway.<you>.workers.dev`.

## Point XOS1 at it

One line in `core/ai/gateway.py`:

```python
BASE = "https://xiteai-gateway.<you>.workers.dev/api/v1/ai"
```

Nothing else in the app changes — the client already fetches a token, renews
it, and hands it to the `openai` SDK.

## Checks before trusting it

```
# should be 401: no signature
curl -X POST https://xiteai-gateway.<you>.workers.dev/api/v1/ai/token -d '{}'

# should be 401: no token
curl -X POST https://xiteai-gateway.<you>.workers.dev/api/v1/ai/deepinfra/chat/completions \
     -d '{"messages":[{"role":"user","content":"hi"}]}'
```

Then run XOS1 with the provider keys removed from its `.env` and confirm a
reply still arrives. If it does, no key is on that machine any more.

## Revoking a machine

```
npx wrangler kv key put --binding=REVOKED <hardware_hash> 1
```

Takes effect within KV propagation. The Terminal knows each install's
hardware hash on its Installs page.

## What is deliberately not here

- **No device registry.** The Worker trusts any correctly signed device that
  isn't on the revoked list. Checking "is this a known install?" would mean
  calling the Terminal on every request, which puts the Terminal back in the
  hot path and undoes the reason this exists. The signature already proves the
  device holds a private key that never left its machine.
- **No logging of prompts or replies.** Nothing from a conversation is stored
  or printed here. Add Cloudflare AI Gateway in front if you want analytics
  and caching — it goes between this Worker and the provider.
