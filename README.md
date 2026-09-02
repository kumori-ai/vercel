# vercel

Find, and prove, the zero-cost models on Vercel AI Gateway. One Python file, standard library only.

```
python3 gateway.py free      every model the public catalog prices at input=0 and output=0
python3 gateway.py ping      one 8-token prompt to each free chat model: latency, reported cost,
                             and the credit balance before and after
python3 gateway.py credits   balance and total used
```

## Why

I run a pool of free-tier LLMs behind one router ([kumori.ai](https://kumori.ai)), and one of the
things it feeds is [sparebrains](https://github.com/tillo13/sparebrains): idle free compute pointed
at competition math, where a Lean 4 kernel, not a person and not another model, decides what counts.
The pool only takes lanes that cost nothing, so every provider gets the same question: which of your
models are actually priced at zero, and does "zero" survive a real call?

Vercel's gateway publishes its whole catalog with per-model pricing at a public endpoint, so the
question is answerable with one GET. That is what `free` does. `ping` then makes the smallest
possible call to each one and reads the cost the gateway reports, plus the credit balance on either
side, so "free" is a measurement rather than a claim.

## What it found, 2026-09-02

```
$ python3 gateway.py free
5 of 365 models are priced input=0 output=0 at https://ai-gateway.vercel.sh/v1/models

inclusionai/ling-3.0-flash-fin           language  ctx=  256000 no_training=all   tags=free,reasoning,tool-use
inclusionai/ling-3.0-flash-fin-free      language  ctx=  256000 no_training=all   tags=free,reasoning,tool-use
minimax/minimax-m2.7-free                language  ctx=  196608 no_training=none  tags=reasoning,tool-use,implicit-caching,free
minimax/minimax-m3-free                  language  ctx= 1048576 no_training=none  tags=implicit-caching,reasoning,tool-use,vision,free
poolside/laguna-s-2.1-free               language  ctx=  256000 no_training=none  tags=reasoning,tool-use,free
```

```
$ python3 gateway.py ping
credits before: {'balance': '5', 'total_used': '0'}
inclusionai/ling-3.0-flash-fin           HTTP 200  1.0s  in=28 out=8 cost=0 -> '1.  **Analyze the Request:**'
inclusionai/ling-3.0-flash-fin-free      HTTP 200  1.4s  in=28 out=8 cost=0 -> '1.  **Analyze the Request:**'
minimax/minimax-m2.7-free                HTTP 200  1.3s  in=48 out=8 cost=0 -> ''
minimax/minimax-m3-free                  HTTP 200  1.0s  in=170 out=2 cost=0 -> 'pong'
poolside/laguna-s-2.1-free               HTTP 503  0.4s  {"error": {"message": "Service temporarily unavailable. ...
credits after:  {'balance': '5', 'total_used': '0'}
```

Four distinct models, all tagged reasoning and tool-use, one of them with a million-token context
window, and the balance did not move. Laguna answered 503 on this run and passed the pool's own
health probe an hour earlier; upstreams flicker, which is exactly why the pool benches lanes instead
of trusting a catalog.

## So they are in sparebrains now

The four `-free` ids are lanes in the pool as `vercel-minimax-m3-free`, `vercel-minimax-m2-7-free`,
`vercel-laguna-s-2-1-free` and `vercel-ling-3-0-flash-fin-free`. The router's health probe passed all
four on 2026-09-02, and sparebrains' ladder draws from the same list, so from its next run they are
attempting Lean proofs alongside the other free lanes. Every attempt lands in the
[committed ledger](https://github.com/tillo13/sparebrains/tree/main/ledger) with the lane name on it,
and the live view is at [sparebrains.kumori.ai/lanes](https://sparebrains.kumori.ai/lanes). Whether a
zero-cost lane earns its place is decided the same way as every other lane: by the kernel.

## One thing the docs do not say

The zero-priced models refuse to answer without a credit card on file. Before a card was on the
team, every request to every one of the models above returned:

```
HTTP 403  "AI Gateway requires a valid credit card on file to service requests."
```

Nothing on the pricing or getting-started pages mentions this; the dashboard's own quick-start
describes the card step as "verifies your identity and unlocks $5 in free credits". A card does not
move you to the paid tier (only purchasing credits does), auto top-up is off by default, and budgets
can cap a key or a team at any amount, so the exposure is controllable. But a free-models-only user
needs to know the card is a precondition, and today they learn it from the 403.

## Run it

```
export AI_GATEWAY_API_KEY=...     # Vercel dashboard -> AI Gateway -> API Keys
python3 gateway.py free           # no key needed for this one
python3 gateway.py ping
```

`ping` calls only the models the catalog prices at zero, with `max_tokens` 8, and prints the
gateway's own cost figure for each. Set a budget on the key anyway.
