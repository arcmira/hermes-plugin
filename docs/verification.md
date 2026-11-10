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
