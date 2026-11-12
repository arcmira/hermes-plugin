# Verification record

Checked 2026-11-08 on macOS with Python 3.14, against three Hermes Agent builds:

- Stable 0.22.2: `d923a5eb487a17c0a68801bba9ef0f56c81040a8`.
- Stable 0.23.0: `2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`.
- Development `main`: `110afdd60e3098b86950963b06a792e261bd36a4`.

The package bundles the eleven skills of [arcmira/mcp](https://github.com/arcmira/mcp) 0.10.14 (`plugins/arcmira/skills`, commit `303e83e0049194e3df765a1399cb7152dccc187c`), unchanged.

## Package checks

`python scripts/test.py --hermes-source <checkout>` runs 12 checks and passes on all three builds. It also passes with only the hash-pinned `requirements-dev.txt` installed, against the same sparse checkout CI uses. The checks use Hermes's real admission validator, portable loader, plugin manager, `skill_view`, catalog validator and MCP transport:

- Admission passes with no warnings, and the package loads one MCP server and all eleven skills with no diagnostics.
- Installed and enabled, every skill loads through `skill_view`, every `references/` file it links exists and loads with the same content, and the server and skills disappear when the plugin is disabled.
- The packaged connection is the API-key path: `https://mcp.arcmira.com/mcp?via=hermes`, `Authorization: Bearer ${ARCMIRA_API_KEY}`, `User-Agent: arcmira-provider/hermes`, strict redirect headers.
- The key comes only from the active profile, and a missing key fails before any request, naming `ARCMIRA_API_KEY`.
- The OAuth example replaces the key connection, carries no `Authorization` header and needs no key.
- Every MCP request sends the key and the provider User-Agent, and a cross-origin redirect drops the key.
- The catalog entry in `docs/catalog-entry.yaml` passes Hermes's catalog validator once pinned, fails it while the pin placeholder remains, declares the same name, version, repository and environment variables as the package, and has a disclosure Hermes's catalog reader finds.

`hermes plugins validate . --install-deps` passes on all three builds: portable manifest parses, security scan `safe`, no warnings.

## Live checks

On Hermes 0.23.0, `hermes plugins install` cloned a local commit of this package into a fresh profile, enabled it and listed it at version 0.10.14. Hermes's MCP layer then connected with an API key taken from the process environment, registered six tools (`arcmira_describe`, `arcmira_execute_read`, `arcmira_execute_write`, `arcmira_feedback`, `arcmira_youtube_search`, `arcmira_youtube_transcript`) and made one `arcmira_youtube_search` call for "Hermes Agent", which returned two passages with titles, channels, seconds and watch links.

`hermes mcp add arcmira --url "https://mcp.arcmira.com/mcp?via=hermes" --auth oauth` was started in a terminal with no browser. Hermes read the server's protected-resource metadata, registered itself with Arcmira's authorization server, and printed and opened an authorization link at `api.arcmira.com` with `resource=https://mcp.arcmira.com/mcp`, PKCE `S256` and the server's scopes. It offered to accept the pasted redirect address and stopped at its 60-second connect timeout when no sign-in arrived. Without a terminal, the same command refused to start the flow and told the user to run `hermes mcp login arcmira` interactively first.

## Package shape

The package is `plugin.json` only. With a `plugin.yaml` beside it, Hermes 0.22.2 and 0.23.0 treat the directory as a native plugin, refuse to load it ("No `__init__.py`") and expose no MCP server and no skills, while `hermes plugins validate` still passes. The catalog entry's `requires_hermes` is therefore the package's only version floor, as the catalog rules describe for portable packages.

## Not checked

- A completed browser OAuth sign-in, token refresh and a tool call over OAuth.
- A full Hermes chat turn where the model picks the skills and tools.
- Windows and Linux runs, which CI covers after publication.
- Installing by catalog name, which needs the merged entry.

# 2026-11-12: trust setting and Hermes 0.23.0 floor

This revision marks the hosted server `trust: untrusted` and raises the floor to Hermes 0.23.0. The package bundles the eleven skills of [arcmira/mcp](https://github.com/arcmira/mcp) 0.10.16 (`plugins/arcmira/skills`, commit `7cab56fb51958e33f352fbeeb6e770e3d55bb736`), unchanged. They are the same files as in arcmira/mcp 0.10.19.

## Package checks

`python scripts/test.py --hermes-source <checkout>` runs 13 checks, one more than on 2026-11-08. The new check confirms that the hosted server is `untrusted` in `plugin.json` and `examples/oauth.yaml`, and that Hermes's own loader keeps that setting. Two existing checks now also confirm that Hermes keeps it, on the API-key setup with no `config.yaml` entry and through the config merge with the OAuth example. The checks pass on Hermes 0.23.0 (`2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`) and 0.23.1 (`3b421578588243f920886e6fe79a6faa87ea026e`). CI runs them on Linux, macOS and Windows.

## Live checks on Hermes 0.23.1

These ran in a fresh profile on macOS, with Hermes 0.23.1 and this package installed at a commit with `hermes plugins install --ref`.

- Right after the install, `hermes mcp login arcmira` answered "Server 'arcmira' not found in config." The login command reads only `config.yaml`.
- After `examples/oauth.yaml` was merged into `config.yaml`, the same command started Arcmira's OAuth sign-in. It printed an authorization link at `api.arcmira.com` with `resource=https://mcp.arcmira.com/mcp` and PKCE `S256`. No sign-in was completed.
- The remaining checks used the same entry with the API-key header in place of OAuth, and with `trust: untrusted` kept. Hermes logged that the package's server conflicts with the `config.yaml` entry and skipped the package's server. It registered the six Arcmira tools. `arcmira_describe`, `arcmira_youtube_search` and `arcmira_youtube_transcript` were the read-only ones.
- A call to `arcmira_execute_write` through Hermes's tool handler showed the trust prompt. When the prompt was answered Deny, Hermes returned "The command was NOT run." With no `trust` line, as `hermes mcp add` writes the entry, the server was `full` and Hermes's gate let the call through without a prompt.
- A cron job ran the `arcmira` skill with one `arcmira_execute_read` call. Hermes blocked the read, logging "no user can answer in this session". In an interactive `hermes chat`, `arcmira_execute_read` was then allowed always ("Add to permanent allowlist" in the terminal). The profile's `config.yaml` then listed `mcp:arcmira/arcmira_execute_read` under `command_allowlist`. After that, the same cron job's read ran and returned the plan. With that entry removed from `command_allowlist`, the next cron run's read was blocked again.

## When the trust setting applies

Hermes 0.23.1 records a server's trust setting when its gateway connects the server. These checks ran on macOS with the API-key entry above. Each read was one `arcmira_execute_read` call, and each prompt was answered Deny.

- A chat started the gateway, with no service installed and no `trust` line. After the line was added, `hermes gateway restart` stopped that gateway and ran the new one in the same terminal until Ctrl+C. `hermes gateway restart --detach` started the new one in the background and returned. In both cases the next chat asked before the read.
- In an open chat, after the line was added, `/reload-mcp` printed "MCP servers reconciled (no server changes)", and the next read in that chat ran without asking.
- With the gateway installed as a launchd service, `hermes gateway restart` and `hermes gateway restart --detach` each returned, and launchd ran the new gateway with its cron scheduler. The next chat asked before the read. After `hermes gateway stop`, the gateway and the cron scheduler stayed down until the next chat started the service again.
- With this package installed at `34231f97eaacb5461a3f9e23c22d851330df98f6`, before its trust setting, and a gateway connected, the package was moved to this revision with `hermes plugins install --force --ref`. Hermes printed "Gateway reloaded plugins — deferred: MCP servers (next session)", and the next chat ran the read without asking.
- With a gateway running, `hermes mcp add arcmira --url "https://mcp.arcmira.com/mcp?via=hermes" --auth header` added the server, and a new chat ran the read with no restart.

## Hermes 0.22.2

On 0.22.2 the trust prompt approves one call or denies it and remembers no answer. Every read asks again, and a scheduled run's reads are always blocked. Session and Always are remembered from 0.23.0 onward, so 0.23.0 is the floor.

## Not checked

- A completed browser OAuth sign-in and a tool call over OAuth.
- The prompt in Telegram, Discord and other gateway surfaces.
- Live runs on Windows and Linux. CI runs the package checks there.
