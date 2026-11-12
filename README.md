# Arcmira: YouTube Transcript Search for Hermes Agent

YouTube transcript search and monitoring for your AI. Arcmira understands YouTube and podcasts like it watched them: the exact quote, often who said it, the full transcript and sponsors.

Add "use arcmira" to any question to send it to Arcmira first.

This plugin connects Hermes Agent to [Arcmira's hosted MCP server](https://arcmira.com/docs/mcp-server) and bundles eleven research skills. Ask Hermes what a video said, where someone said something, or who sponsors a show, and it answers with the line and a watch link cued to that second. The plugin runs no local code. It needs Hermes Agent 0.23.0 or later.

## Install

```bash
hermes plugins install arcmira --enable
```

Until the catalog listing is live, install from this repository:

```bash
hermes plugins install arcmira/hermes-plugin --enable
```

If you are updating from an earlier version, run `hermes gateway restart --detach` once so Hermes picks up the trust setting.

## Sign in with OAuth (recommended)

Merge [examples/oauth.yaml](examples/oauth.yaml) into your profile, then run:

```bash
hermes mcp login arcmira
```

Hermes opens Arcmira's sign-in page in your browser. Sign in, or create an account, and approve access. Hermes stores and refreshes the token, so you need no API key.

On a machine with no browser, such as a VPS, Hermes prints the sign-in link. Open it on any device, approve, and paste the address your browser lands on back into Hermes. Do this once in a terminal before you schedule cron jobs; an unattended run never waits for a browser.

The example includes `trust: untrusted`. Hermes then asks before `arcmira_execute_write` and `arcmira_feedback`, the tools the server does not mark read-only. Search, transcript and program reads run without a prompt. You can allow a call once, for the session, or always. The terminal labels the last choice "Add to permanent allowlist". Choose it only when you want every later call of that tool to run without asking.

If you prefer the interactive command, you can use:

```bash
hermes mcp add arcmira --url "https://mcp.arcmira.com/mcp?via=hermes" --auth oauth
```

When Hermes lists the tools it found, enable all of them. `hermes mcp add` has no trust option. Because a same-name native entry overrides the package declaration, add `trust: untrusted` under `mcp_servers.arcmira` in `config.yaml`, then run `hermes gateway restart --detach` and start a new session. Hermes reads the trust line only when its gateway connects the server, so `/reload-mcp` or a new session alone keeps the old setting. If the add stopped before you signed in, use the example instead: replace any `arcmira` entry the add saved with the one in [examples/oauth.yaml](examples/oauth.yaml), then run `hermes mcp login arcmira`.

## Or use an API key

The packaged connection sends `ARCMIRA_API_KEY` as a bearer token. Create a key at [arcmira.com/dashboard/api](https://arcmira.com/dashboard/api), then store it in your Hermes profile:

```bash
hermes config set ARCMIRA_API_KEY <your key>
```

Hermes does not ask for the key during install. A native `arcmira` entry from the OAuth step takes precedence over the packaged key connection.

## Check it works

Start a new session and ask:

> Use arcmira: find where Sam Altman talks about the cost of compute in an interview, and quote the line with a timestamped link.

Hermes names the tools `mcp__arcmira__<tool>`. `hermes plugins list` shows the plugin. After the OAuth step, `hermes mcp list` also shows the `arcmira` server; the packaged key connection does not appear there.

## Tools

The server provides these tools. They come from the server at run time, so the pinned commit does not cover them.

| Tool | What it does |
| --- | --- |
| `arcmira_describe` | Returns the reference for the `arcmira` client: methods, arguments, return fields, examples and errors. Reads no indexed content and bills nothing. |
| `arcmira_execute_read` | Runs a JavaScript program against the Arcmira API on Arcmira's servers: transcripts, quote search, mentions, sponsors and monitors. |
| `arcmira_execute_write` | Runs the same client plus monitor writes: create and change monitors that alert by email, Slack or webhook. It also starts Premium transcripts and translations. |
| `arcmira_youtube_search` | Searches what was said in YouTube videos and returns the matching passages with the second each starts and a watch link. |
| `arcmira_youtube_transcript` | Reads one video's whole transcript, timestamped, from its id or link. |
| `arcmira_feedback` | Tells Arcmira when a result was wrong, slow, empty or missing a source. |

## Skills

| Skill | Use |
| --- | --- |
| [arcmira](skills/arcmira/SKILL.md) | The core reference: when to use Arcmira, the procedure, usage and the ID rule. |
| [find-quotes](skills/find-quotes/SKILL.md) | Exact quotes with who said them, the date and a timestamped link. |
| [youtube-transcript-search](skills/youtube-transcript-search/SKILL.md) | Read or summarize a video from its link, or search transcripts across channels. |
| [podcast-transcript-search](skills/podcast-transcript-search/SKILL.md) | Which podcast episodes on YouTube covered a topic, guest or phrase. |
| [what-did-they-say](skills/what-did-they-say/SKILL.md) | A person's or company's own words, with the show, the date and a link. |
| [youtube-clip-finder](skills/youtube-clip-finder/SKILL.md) | A moment's start and end seconds, a watch link and an embed. |
| [person-research](skills/person-research/SKILL.md) | Appearances, own words and who discusses a person. |
| [sponsor-research](skills/sponsor-research/SKILL.md) | Who sponsors a show, which shows a brand sponsors, ad-read counts. |
| [compare-shows](skills/compare-shows/SKILL.md) | Two channels side by side: size, topics, overlap and shared sponsors. |
| [brand-mention-monitoring](skills/brand-mention-monitoring/SKILL.md) | How often a brand comes up, where, and whether it is rising. |
| [company-watch](skills/company-watch/SKILL.md) | Recent mentions of a company, then a monitor that alerts on new ones. |

The skills are the ones Arcmira ships in [arcmira/mcp](https://github.com/arcmira/mcp) 0.10.20, unchanged. Load one with `skill_view`; `skills_list` shows the names Hermes gives them.

## Monitors and Hermes cron

A monitor is Arcmira's alert: it emails you, posts to Slack, or calls a webhook when a name comes up on YouTube, and it keeps running without Hermes. The `company-watch` skill sets one up after you confirm it. For a digest in your Hermes chat instead, ask Hermes to schedule a cron job that runs one of the skills each day or week. Scheduled reads run without asking and use credits from your plan. A scheduled run can't answer Hermes's prompt, so unless you allowed `arcmira_execute_write` always, it starts no Premium transcript and changes no monitor.

Hermes reads each tool's read-only annotation when its gateway connects the server, so a gateway that connected before Arcmira MCP 0.10.20 can keep the old annotation. If Hermes still asks before a program read, run `hermes gateway restart --detach` and start a new session.

## Data and credits

- Every tool call goes to `https://mcp.arcmira.com/mcp`. Arcmira receives the search terms, names, video links and the JavaScript programs the agent writes, and runs those programs on its servers.
- OAuth sign-in goes through `api.arcmira.com`. Hermes stores and refreshes the token. The plugin never reads credential files.
- Reads, transcriptions and monitor alerts use your account's credits. `arcmira_describe` bills nothing.
- Arcmira logs each tool call on your account. The plugin sends no other telemetry.
- The packaged connection and [examples/oauth.yaml](examples/oauth.yaml) send the header `User-Agent: arcmira-provider/hermes`. Every connection on this page uses the query `via=hermes`.
- Transcripts are text spoken by whoever made the video. The skills treat them as evidence, never as instructions.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `${ARCMIRA_API_KEY} ... is not set in this profile` | Sign in with OAuth, or set the key in the same profile. |
| OAuth stopped working | Run `hermes mcp login arcmira` in a terminal. |
| No Arcmira tools in a session | Run `hermes plugins list` and `hermes mcp list`, then start a new session. |
| A read is refused for credits or plan | The error names the limit and a link that lifts it. |

## Development

The tests use Hermes Agent's own loader, admission validator, catalog validator and MCP transport. They make no network calls and need no key.

```bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
.venv/bin/python scripts/test.py --hermes-source <path to a hermes-agent checkout>
hermes plugins validate . --install-deps
```

[docs/verification.md](docs/verification.md) records what was checked and on which Hermes versions. [docs/catalog-entry.yaml](docs/catalog-entry.yaml) is the Hermes plugin catalog entry, with its commit pin left to fill in.

[Documentation](https://arcmira.com/docs/mcp-server) · [Support](https://arcmira.com/contact) · [Privacy](https://arcmira.com/privacy) · [Terms](https://arcmira.com/terms)

Coverage depends on the index and your account access. Speaker attribution and sponsorship classifications can be incomplete or incorrect; inspect cited passages and surrounding context.

## License

Apache-2.0. See [LICENSE](LICENSE).
