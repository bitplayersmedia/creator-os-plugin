---
name: content-engine
description: Creator OS job skill: research-backed content ideas, hooks and record-ready scripts for an AI influencer character. Use it only when a Creator OS job brief names it.
user-invocable: false
---

# Content engine: research-backed ideas and record-ready scripts

This skill is the craft behind two Creator OS jobs: `bible` (write a persona) and `script` (write one video script). It runs unattended. It never asks a question, never waits for a pick and never stops for a go. The job's brief and its `input` carry every choice; anything missing gets a sensible default that you pick yourself. The result is the JSON the brief describes, written to `result.json`, never a chat reply. If the job cannot be done, write the brief's error shape (`{ "error": { "what", "why", "todo" }, "retry": true|false }`).

The persona is one character: the one in `input.bible` (script job) or the one `input.prompt` describes (bible job). Everything you write is in that character's voice and for that character's niche.

## Which job am I doing?

- **`bible` job:** `input.prompt` describes the creator in a sentence or two. Write the whole persona bible from it (see "The bible job" below). Spend nothing.
- **`script` job:** `input.prompt` is the topic. If it is empty, you choose: research the niche, build a few ideas on the skeletons below, pick the single strongest one yourself and write it. Never output a list of ideas for someone to choose from; the output is one finished script. Spend nothing.

Either way the brief's `result.json` shape is the only output.

## Research the niche first

When the job has a web search tool, run 3 to 5 searches on the character's niche before ideating. Target:

1. Top-performing creators and accounts in the niche right now (AI or virtual ones too).
2. Hooks, formats and video styles currently pulling views on Reels, TikTok and Shorts.
3. The questions, pain points and debates the niche's audience is obsessing over.

Extract patterns, not topics to copy: recurring hook structures, recurring formats (lists, hot takes, storytimes, POVs), recurring emotional triggers (curiosity, outrage, aspiration, relatability, humour) and any seasonal angle worth riding. If there is no search tool, fall back to the evergreen frameworks below, tailored hard to the character, and carry on. Do not ask for one. Never invent ideas from thin air and never write a script blind: know the idea and the character before a word is written.

## Build ideas on proven short-form skeletons

Build every idea on one of these formats and vary across the ideas you weigh:

- **Listicle:** "3 signs...", "5 things I'd never..."
- **Contrarian take:** challenge common advice in the niche.
- **Signs, red flags, green flags:** pattern-recognition content.
- **Things I wish I knew:** hindsight framing, aspirational.
- **Storytime or confession:** a first-person anecdote from the character's backstory.
- **POV or direct address:** speaks straight to one viewer situation.
- **Day in the life or lifestyle flex:** aspirational pictures with light narration.
- **Q and A or myth-bust:** answer the niche's most-asked question, or kill a myth.

Twist a proven pattern from the research through this character's unique angle rather than copying it. A repeatable series format the character could post weekly is worth more than a one-off.

### Hook mechanics

The first spoken line must earn the next three seconds.

- Open with a curiosity gap, a direct callout ("If you're in your 20s and..."), a mild controversy, or a specific number or claim.
- Front-load the most surprising, specific or high-stakes word. No warm-up, no "so", no "today I want to talk about".
- Call out exactly who it is for so the right person feels seen.
- Write the hook in the character's voice (their age, attitude and way of speaking), never a neutral copywriter voice.
- It must also work as on-screen text read in about a second: most viewers scroll muted.
- **Draft and pick:** silently write three different hooks and keep only the strongest. Never ship the first line you think of.

### Hold mechanics

Every idea needs a reason to watch to the end: a countdown list, an open loop resolved in the final line, escalating stakes, a twist or a payoff. Know what the hold is before you write the lines.

### Kill-filter

Before you commit to an idea ask: would a stranger stop scrolling within two seconds? Is the hook specific (a number, a callout, a claim or a curiosity gap)? Can the setting be generated as one simple image? If not, drop the idea and take the next one.

## Producibility: AI video of one consistent character

Every idea must be producible as AI-generated video of one consistent character.

- **One character on screen, doing something while talking.** Every idea needs a physical action that shows the point: slap a page, flick through a file, pour, plant, walk in, hold a prop up to the lens. A character who just sits and talks is not producible content. Others appear only as hands or blurred edges.
- **Describable settings** (desk, cafe table, car seat, kitchen, beach, porch) with one or two props the action uses. The setting description must work as an image-generation prompt. When `input.kit` lists locations and outfits, the setting is one of them.
- **Length:** 10 to 15 seconds of spoken script by default (one video generation). 30 seconds only when the idea needs the room (a list, a story, a product pitch). Never 30 to 60 seconds.
- Large, simple actions are fine. No finger counting or fine finger choreography, no readable text on props, no real product demos, no crowds, no multi-character dialogue.
- Nothing that needs real footage, screen recordings, or the character touching branded products.

### Platform safety (non-negotiable, especially health and money niches)

- No medical claims, cures, or "this fixes X" health advice. Keep health content general, lifestyle-level, and myth or habit framed.
- No guaranteed returns and no specific investment instructions. Keep money content to principles, habits and mindset.
- Nothing likely to get an account flagged, age-restricted or demonetised.
- The persona's own guardrail (`bible.guardrail`) always applies and is repeated in the script's `guardrail` field.

### Monetisation lens

- If the character sells their own product (supplements, a course, a guide), never write content that undermines it. Prefer ideas that lead naturally toward the problem the product solves, so the product is the obvious answer without the script being an ad.
- If the character relies on brand deals or affiliates, favour topics a sponsor in the niche would happily sit next to.
- Either way the idea must earn the view on its own. Never write an ad.

## Write for the ear, and for a voice generator

- **Clean spoken text only.** No markdown, no symbols, no stage directions inside the spoken lines, no emojis. Write numbers and abbreviations the way they are said ("thirty quid", not "30 pounds sign"). Ordinary punctuation (commas, full stops, the odd ellipsis) controls pacing: that is how you tell the voice where to breathe.
- **Short sentences, contractions, real speech rhythm,** in this character's exact voice (`bible.voice`, their age, attitude, verbal tics). Read it back in your head; if it does not sound like them talking, rewrite it.
- **Every line pushes to the next.** No filler, no wind-up.
- A word in CAPITALS in a spoken line is the stressed word (the brief says so). Use it on the words that carry the point.

### Sound human, not written (check every script against these)

- **No rule of three.** Balanced lists and matched pairs are the classic written-by-AI tell. Break the symmetry: list two things, or four, or start a list and abandon it.
- **No thesis sentences.** Never summarise the insight with an abstraction. Land the idea through the concrete example and trust the viewer.
- **One self-interruption or restart per script:** a "wait, no, the best example...", a trail-off, a mid-sentence correction.
- **Verbal tics go in the boring middles, not the peaks.**
- **One uselessly specific detail.** "A guy she dated for like five minutes in school" beats "a guy from her past".
- **Allow one near-repetition.** People say the thing, then say it again slightly differently.
- **Uneven rhythm.** A few stubby fragments, then one that runs on with "and" in it three times. Never a tidy short-long pulse.

### Structure of every script

1. **Hook.** The first spoken line is the hook: tighten it, keep the surprising word first. It makes a promise.
2. **Deliver.** Pay off that promise. Build with an open loop or a countdown so they stay.
3. **Payoff.** Resolve it with the satisfying line the hook was pointing at.
4. **Hand-back.** The last line lands clean and leaves the character where the hook found them, so the hook plays again when the clip loops.

Never bait and switch: the script delivers exactly what the hook promised.

## Length discipline

Default band: **10 to 15 seconds is about 25 to 40 spoken words**, one generation, leaving room for the action and half a second of stillness at each end. **30 seconds is about 40 to 75 words**, only for an idea that needs it. Nothing between 30 and 60 seconds. Count the words. If it is over, cut: shorter and tighter always beats longer and padded. The one exception is a hook that explicitly promises a runtime ("give me sixty seconds"): honour the promise.

Check the total against `wpm`: words divided by `wpm` times 60 gives the seconds, and it must land in the band (the brief says about 15 to 40 seconds at most).

## Closing line and call to action

No sign-off by default. The persona's catchphrase or `bible.signoff` is spoken only when it is the punchline of that script: never bolted after a line that already landed, never two closers. The call to action (the bio pointer, the product) goes in the post `caption`, not in the mouth, unless the product is the topic. The script ends on its last real line, in the opening pose, ready to loop.

## Output for the script job

Write the brief's `script` object to `result.json` and nothing else. Fill it like this:

- `hook`: the first line viewers hear, at most 300 characters, in the persona's voice. It doubles as the on-screen text, so it must work without sound.
- `setting`: one location from `input.kit`, written so it drops into an image prompt, with the one or two props the action uses.
- `lines`: the spoken script, one to twelve short lines, hook first, clean and copy-pasteable into a voice tool with no editing.
- `guardrail`: the persona's rule that applies to this topic, repeated.
- `wpm`: a whole number from 110 to 170 that matches the persona's speaking pace.
- `caption`: the post caption, with the call to action when one is used.
- `hashtags`: a few relevant tags, each starting with `#`.
- `guidance`: one short paragraph for the video stage: the physical action that shows the point, the length band (**15** or **30**), and the loop pose the clip opens and closes on, with how the last line hands back to the hook.

The beat-by-beat shot table is the `beats` job's work (the `short-form-director` skill), not part of this result. Do not add it here.

## The bible job

The same craft builds the persona, so the scripts that follow it work. Write the whole bible from `input.prompt` in the shape the `bible` brief gives, and when `input.current` and `input.change` are present keep what the change does not touch.

- **Niche:** a short topic label of one to four words in title case, picked after the research above: a niche that has an audience and room for a new voice.
- **Look and anchors:** one character who can be generated again and again, with three concrete visible anchors (a mole, a scar, a hair streak) that every picture repeats word for word.
- **Voice, `signoff` and `gesture`:** a distinct way of speaking and one signature gesture the character makes on the key beat of a video. `signoff` is a catchphrase that earns its place as a punchline now and then, not every time.
- **Locations and outfits:** describable, simple, producible settings and clothes that read at phone size, never a crowd or a brand.
- **Guardrail:** what this persona must never claim (health, income, real-person likeness), and the monetisation fit: never a backstory that would undercut what the persona sells.
- Nothing copied from a real person. Plain, specific language with no filler.

© Bit Players Media LLC. Licensed for use with Creator OS only.
