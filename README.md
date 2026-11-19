# Creator OS plugin

This is the Claude Code plugin for Creator OS, a dashboard for running AI influencer personas. The plugin lets the
Claude Code session you already have open do the slow work (writing, pictures, voices, video) that your Creator OS
workspace queues, instead of a separate program on your computer.

It follows **Option A**: your open session does the jobs itself, one at a time, ideally each in a subagent. The plugin
never starts another Claude process, never creates a Claude session of its own and never touches your Claude sign-in.

## Before you start

You need four things:

- **Claude Code**, signed in, on macOS, Linux or Windows. On Windows use WSL2 (Windows Subsystem for Linux) and do
  everything below inside it.
- **Node 22.18 or newer.** Check with `node --version`; get it from nodejs.org. Without it the plugin's server cannot
  start and Claude shows no Creator OS tools.
- **A Creator OS account** where you are the owner or an admin. Only they see Settings, Connect Claude, which gives the
  code that links your computer.
- **A Higgsfield account with credits**, for pictures and video (see "What the jobs need" below). Writing jobs spend
  nothing.

## Install

Pick one of the two forms. They do the same thing.

**Inside Claude Code** (type these as messages):

```
/plugin marketplace add bitplayersmedia/creator-os-plugin
/plugin install creator-os@creator-os
```

**From a terminal:**

```
claude plugin marketplace add bitplayersmedia/creator-os-plugin
claude plugin install creator-os@creator-os
```

Then **restart Claude Code** (close it and open it again). A running session does not pick up a new plugin's tools.
After the restart, typing `/creator-os` should offer `/creator-os:setup` and `/creator-os:work`.

**Turn on auto-update (off by default).** Open `/plugin`, choose Marketplaces, pick `creator-os` and enable auto-update.
Until you do, you get a new version only when you update it yourself.

**Disconnect.** Ask Claude to run the plugin's `disconnect` tool (the setup skill also offers it), or revoke the computer
in Creator OS under Settings. Either one ends the link. `disconnect` deletes the token on this computer at once; after a
Settings revoke, the plugin deletes it the next time it calls the site.

**What it can and cannot touch.** It reads and writes the job folder on this computer
(`~/creator-os-jobs/<job id>` unless you chose another) and calls your Creator OS site. It asks before writing a file
outside the job folder. It never starts another Claude and never touches your Claude sign-in.

## Your first video

About fifteen minutes, plus the waiting for pictures and video. Keep Creator OS open in a browser next to Claude Code.

1. **Get a code.** In Creator OS open Settings, then Connect Claude, and press "Get a code". You see a code like
   `AB3D-EF7H` and the word WAITING. The code is good for 10 minutes and works once.
2. **Link this computer.** In Claude Code type `/creator-os:setup`. When Claude asks, give it the code. Claude answers
   `Linked to <your studio>.` Settings now says LINKED. If you use a Creator OS site other than the plugin's default one,
   give Claude its address when it asks (for example `https://example.com`).
3. **Check your tools.** Setup then looks at your picture and video tool (Higgsfield) with one real call each, and asks
   how many credits Creator OS may use each time you run `/creator-os:work`. Say a number above 0 to allow spending;
   0 (the default) means it never spends, and every picture and video job will be skipped. Setup tells Creator OS what
   is ready, so the website stops asking you to run setup again.
4. **Make a persona on the website.** Start a new persona in Creator OS and fill in the first steps. This queues the
   writing job for the persona. Nothing happens until Claude works the queue.
5. **Let Claude work.** In Claude Code type `/creator-os:work`. Claude takes the oldest waiting job, does it, uploads the
   result, then takes the next, until none are left. Before it uses a paid service it tells you what it will use and
   waits for your yes. No yes, no spend.
6. **Review on the website.** Look at the persona's bible and portraits in Creator OS and approve or reject them. A
   reject queues the work again.
7. **Make a video.** On the website start a video for the persona, then step through script, beats and generate. Each
   step queues jobs.
8. **Let Claude work again.** Type `/creator-os:work` again. The video is done in several passes (script, beats, the
   pictures and clips, then the finish). Say yes to each paid step.
9. **Review the video** on the website. That is your first video.

Keep Claude Code open while it works; if you close it, see "Troubleshooting" below.

## What it does

What it does today:

- `/creator-os:setup` links this computer to your studio. You type the code from Settings, Connect Claude, and the plugin
  saves a token in a private file on this computer (never shown, never in a chat). It then checks your picture and video
  tool and tells Creator OS what is ready.
- `/creator-os:work` does the queued jobs. It takes the oldest waiting job (`next_job`), which becomes a folder with a
  `JOB.md` brief, hands it to a subagent, uploads the files in `outputs/` and sends the result (`complete`), then takes the next. `/creator-os:work watch` keeps
  looking when the queue is empty, with `sleep` between looks (a minute, then two, five and ten); press Esc to stop.
- The MCP server (built on the official MCP SDK) has eleven tools: `pair`, `save_setup`, `check_tools`, `status` and `disconnect` for the
  link, and `next_job`, `progress`, `upload`, `complete`, `fail` and `stop` for the work.
- While a job is held the plugin renews its 15-minute lease every 5 minutes. If your session ends mid-job the job goes
  back in the queue when the lease runs out, and the next `next_job` picks up a job that is still yours.
- A small hook asks you before the session writes a file outside the held job's folder. It adds a question and never
  blocks; shell commands are not covered.

Full-quality files stay in the job folder on this computer (`~/creator-os-jobs/<job id>` unless you chose another folder);
only the review copy of each result file is uploaded. Google Drive comes later. A paid picture or video service is called
only after you say yes in the session.

The server is quiet: starting it and listing its tools call nothing over the network, and nothing runs in the background
while no job is held. The site is called only when you ask (`pair`, `disconnect`, `status` with `waiting`, and
`save_setup` and `check_tools` when they record your setup) or while you
work (`next_job`, `upload`, `complete`, `fail`, `stop`, and one renewal every 5 minutes while a job is held). The link lasts
until you run `disconnect`, an owner revokes it in Settings, or it sits idle for 30 days.

**For developers:** the server needs Node 22.18 or newer. Build it with `npm run plugin` (it writes `dist/server.mjs`,
`dist/hook.mjs` and `dist/briefs/`), then try it with `claude --plugin-dir plugin`.

## What the jobs need

The video jobs lean on a few things that live outside the plugin:

- **A Higgsfield account with credits**, connected through Higgsfield's hosted MCP at `https://mcp.higgsfield.ai/mcp`
  with your own account. For example `claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp`,
  then sign in with `/mcp`. Higgsfield's own skills are not bundled in this plugin.
- **For the finish job:** `ffmpeg` built with libass, `python3`, and the `openai-whisper` command line tool, all on
  your `PATH`.

## Troubleshooting

Find what you see in the left column. Messages in quotes are the exact words the plugin or the website shows.

| What you see | Why, and what to do |
|---|---|
| Claude has no `/creator-os:setup` or `/creator-os:work`, or Creator OS tools are missing, or `/mcp` says the creator-os server failed | Restart Claude Code after installing. Then check `node --version`: it must be 22.18 or newer. An older Node prints "creator-os: needs Node 22.18 or newer, found <your version>" and the server stops. Install a newer Node from nodejs.org, then restart Claude Code. On WSL2, run `node --version` inside WSL2, not in Windows |
| "That code is not valid. Ask for a new one." | The code was typed wrong, is older than 10 minutes, was already used, or belongs to another Creator OS site. Wrong and expired codes get the same answer on purpose. In Settings, Connect Claude, press "Get a code" again, run `/creator-os:setup` and type the new code. If you use a site other than the plugin's default, give Claude its address when it asks, or set `CREATOR_OS_SITE` before starting Claude Code |
| "That site address is not a web address. Use the full address, for example https://example.com." | Type the whole address, starting with `https://` |
| "Too many wrong codes. Wait a few minutes and ask for a new one." | Ten wrong tries from one connection lock pairing for about 10 minutes. Wait, get a new code and type it carefully |
| "Could not reach <site>. Check the connection and try again." | This computer cannot reach the site. Check your internet and the address, then run `/creator-os:setup` again |
| The website keeps saying "Run /creator-os:setup again in Claude before anything can be made. Missing: <what is missing>." (an image tool, a video tool or a storage choice) | Creator OS has not been told your tools are ready. Either a tool check failed (Higgsfield is not connected in this session, or its sign-in ran out) or setup ran while offline. Connect Higgsfield (`/mcp`), run `/creator-os:setup` again and let it finish the tool check. The plugin tells you if the site could not be reached: "The site could not be reached, so Creator OS still shows setup as missing. Run /creator-os:setup again when you are online." |
| Setup ended with "Not linked yet: run pair first." | The link step did not finish. Run `/creator-os:setup` again and give it a fresh code |
| "Skipped: the spend cap is 0 (no spending). Run /creator-os:setup to allow credits." | The spend cap is 0, so Creator OS never spends. Run `/creator-os:setup` again and give a number of credits above 0. The job stays queued and nothing is lost |
| "Skipped: the <images or video> tool is missing or its last check failed. Run /creator-os:setup again." | Same as the setup row above: connect the tool, run setup again |
| "Skipped: the spend cap is reached (<used> of <cap> credits used, this job needs <cost>)." | This run used up its cap. Run `/creator-os:work` again for a new run, or raise the cap in `/creator-os:setup` |
| "This link was revoked or idle for 30 days. Run /creator-os:setup again." | An owner revoked this computer in Settings, or it sat unused for 30 days. Get a new code and run `/creator-os:setup` |
| "Creator OS needs a newer plugin. Update it, then run /creator-os:work again." | Update the plugin (`/plugin`, Marketplaces, `creator-os`, update), restart Claude Code, run `/creator-os:work` again |
| "Could not reach <site>. The job is still yours for a while; try again." | A short network problem while working. Run `/creator-os:work` again; you keep the job |
| The answer ends "daily job limit is reached. Try again tomorrow." | Your studio hit its limit for the day. Nothing is broken; try tomorrow |
| Claude Code closed or crashed in the middle of a job | Nothing is lost. The job goes back in the queue by itself after up to 15 minutes, once its lease runs out. Open Claude Code and run `/creator-os:work` again; it picks up the same job. If the job is still yours it carries on; otherwise it is claimed again as a new try |
| "Creator OS has taken this job back (cancelled, done elsewhere or its lease ran out). Stop work on it; call next_job for the next one." | You cancelled the job on the website, or it sat too long. Let Claude go on to the next job |
| The finish job fails or stops, saying `ffmpeg`, `python3` or `whisper` is missing | The finish step burns captions into the video and needs three programs on your PATH: `ffmpeg` built with libass, `python3`, and the `whisper` command (`pip install openai-whisper`; the first run downloads a model of about 460 MB). On macOS with Homebrew: `brew install ffmpeg-full`. Install them, then press Retry on the job in Creator OS and run `/creator-os:work` |
| Pictures or videos do not start | Higgsfield is not connected in this session, or has no credits. Add it with `claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp`, sign in with `/mcp`, and run `/creator-os:setup` again |
| You want to see the full-quality files, or to use Google Drive | Full-quality files stay on this computer in `~/creator-os-jobs/<job id>` (or the folder you chose in setup). Only a review copy goes to Creator OS. Google Drive comes later |

**Linux and WSL2.** The plugin keeps its link in Claude Code's plugin data folder (`~/.config/creator-os` when Claude Code gives none) and job
files in `~/creator-os-jobs`, inside your Linux (or WSL2) home folder. Run Claude Code, Node and the finish tools inside the same Linux or WSL2 shell; a Claude
Code in Windows and a Node in WSL2 do not see each other. Install `ffmpeg` and `python3` with your package manager
(for example `sudo apt install ffmpeg python3`), and check that your ffmpeg has libass (`ffmpeg -filters | grep ass`).

**Still stuck?** Run `/creator-os:setup` again. It is safe to repeat: a new code replaces the old link.

## Licence

See [LICENSE](LICENSE). The plugin is proprietary to Bit Players Media LLC, except `skills/video-prompting`, which is
CC BY 4.0 and keeps its own LICENSE and NOTICE.
