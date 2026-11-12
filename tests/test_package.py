"""Contracts for the shipped package, checked with Hermes's own loader, validators and transport."""

import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

import httpx
from ruamel.yaml import YAML

from agent.secret_scope import reset_multiplex_context, reset_secret_scope, set_multiplex_context, set_secret_scope
from hermes_cli.agent_plugins import load_agent_plugin
from hermes_cli.plugin_validate import validate_plugin_dir
from tools.mcp_tool_config import _interpolate_env_vars, _load_mcp_config, _require_rendered_remote
from tools.mcp_tool_errors import _make_redirect_header_stripper

ROOT = Path(__file__).resolve().parents[1]
HERMES_SOURCE = Path(os.environ["HERMES_SOURCE"])
SERVER = "arcmira"
URL = "https://mcp.arcmira.com/mcp?via=hermes"
USER_AGENT = "arcmira-provider/hermes"
KEY = "ARCMIRA_API_KEY"
PIN_PLACEHOLDER = "REPLACE_WITH_PUSHED_COMMIT_SHA"
DUMMY_SHA = "0123456789abcdef0123456789abcdef01234567"
EXPECTED_SKILLS = {
    "arcmira", "brand-mention-monitoring", "company-watch", "compare-shows", "find-quotes",
    "person-research", "podcast-transcript-search", "sponsor-research", "what-did-they-say",
    "youtube-clip-finder", "youtube-transcript-search",
}
COPY_IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".venv")


def _catalog_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_plugin_catalog", HERMES_SOURCE / "scripts" / "validate_plugin_catalog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _catalog_entry(sha):
    text = (ROOT / "docs" / "catalog-entry.yaml").read_text(encoding="utf-8")
    if sha is not None:
        text = text.replace(PIN_PLACEHOLDER, sha)
    return YAML(typ="safe").load(text)


def _enabled_manager(home, extra_config=""):
    from hermes_cli.plugins import PluginManager

    shutil.copytree(ROOT, home / "plugins" / SERVER, ignore=COPY_IGNORE)
    (home / "config.yaml").write_text("plugins:\n  enabled: [arcmira]\n" + extra_config, encoding="utf-8")
    bundled = home / "empty-bundled"
    bundled.mkdir()
    return PluginManager(scope_key=str(home)), {"HERMES_HOME": str(home), "HERMES_BUNDLED_PLUGINS": str(bundled)}


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="arcmira-package-")
        self.addCleanup(self.temp.cleanup)
        self.package = load_agent_plugin(ROOT, Path(self.temp.name) / "data")

    def test_hermes_admission_passes_with_no_warnings_or_skipped_parts(self):
        report = validate_plugin_dir(ROOT)
        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.warnings, [])
        self.assertEqual(self.package.diagnostics, ())
        self.assertEqual(set(self.package.mcp_servers), {SERVER})
        self.assertEqual({skill.name for skill in self.package.skills}, EXPECTED_SKILLS)

    def test_hosted_server_is_untrusted_in_manifest_and_oauth_example(self):
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["extensions"]["com.nousresearch.hermes"]["servers"][SERVER]["trust"],
            "untrusted",
        )
        oauth = YAML(typ="safe").load((ROOT / "examples" / "oauth.yaml").read_text(encoding="utf-8"))
        self.assertEqual(oauth["mcp_servers"][SERVER]["trust"], "untrusted")
        self.assertEqual(self.package.mcp_servers[SERVER]["trust"], "untrusted")

    def test_installed_package_exposes_every_skill_and_the_server_only_when_enabled(self):
        from tools.skills_tool import skill_view

        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                home = Path(self.temp.name) / f"home-{enabled}"
                manager, env = _enabled_manager(home)
                if not enabled:
                    (home / "config.yaml").write_text("plugins:\n  enabled: []\n", encoding="utf-8")
                with patch.dict(os.environ, env):
                    try:
                        manager.discover_and_load()
                        self.assertEqual(set(manager.get_portable_mcp_servers()), {SERVER} if enabled else set())
                        listed = manager.list_plugin_skill_metadata()
                        self.assertEqual(len(listed), len(EXPECTED_SKILLS) if enabled else 0)
                        if not enabled:
                            continue
                        row = next(p for p in manager.list_plugins() if p["name"] == SERVER)
                        self.assertIsNone(row["error"])
                        with patch("hermes_cli.plugins.get_plugin_manager", return_value=manager):
                            loaded = set()
                            for skill in listed:
                                skill_md = manager.find_plugin_skill(skill["name"])
                                viewed = json.loads(skill_view(skill["name"]))
                                self.assertTrue(viewed["success"], viewed)
                                loaded.add(skill_md.parent.name)
                                body = skill_md.read_text(encoding="utf-8")
                                for target in re.findall(r"\]\((references/[^)]+)\)", body):
                                    self.assertTrue((skill_md.parent / target).is_file(), f"{skill['name']}: {target}")
                                for path in sorted((skill_md.parent / "references").glob("*.md")):
                                    resource = json.loads(skill_view(skill["name"], file_path=f"references/{path.name}"))
                                    self.assertTrue(resource["success"], resource)
                                    self.assertIn(path.read_text(encoding="utf-8").strip(), resource["content"])
                            self.assertEqual(loaded, EXPECTED_SKILLS)
                    finally:
                        manager.unload()

    def test_packaged_connection_is_the_api_key_path(self):
        server = self.package.mcp_servers[SERVER]
        self.assertEqual(server["url"], URL)
        self.assertEqual(server["headers"], {"Authorization": f"Bearer ${{{KEY}}}", "User-Agent": USER_AGENT})
        self.assertTrue(server["strict_redirect_headers"])
        self.assertNotIn("command", server)

    def test_api_key_path_uses_only_the_active_profile_key(self):
        with patch.dict(os.environ, {KEY: "foreign-profile-value"}):
            for key in ("profile-a-value", "profile-b-value"):
                with self.subTest(profile=key):
                    token = set_secret_scope({KEY: key})
                    try:
                        server = _require_rendered_remote(SERVER, _interpolate_env_vars(self.package.mcp_servers[SERVER]))
                        self.assertEqual(server["headers"]["Authorization"], f"Bearer {key}")
                        self.assertEqual(server["headers"]["User-Agent"], USER_AGENT)
                    finally:
                        reset_secret_scope(token)

    def test_api_key_path_without_a_key_fails_before_any_request(self):
        with patch.dict(os.environ, {KEY: "foreign-profile-value"}):
            multiplex = set_multiplex_context(True)
            token = set_secret_scope({})
            try:
                server = _interpolate_env_vars(self.package.mcp_servers[SERVER])
                with self.assertRaisesRegex(ValueError, KEY):
                    _require_rendered_remote(SERVER, server)
            finally:
                reset_secret_scope(token)
                reset_multiplex_context(multiplex)

    def test_oauth_path_replaces_the_key_connection_and_needs_no_key(self):
        home = Path(self.temp.name) / "oauth-home"
        manager, env = _enabled_manager(home, (ROOT / "examples" / "oauth.yaml").read_text(encoding="utf-8"))
        with patch.dict(os.environ, {**env, KEY: "foreign-profile-value"}):
            multiplex = set_multiplex_context(True)
            token = set_secret_scope({})
            try:
                manager.discover_and_load()
                with patch("hermes_cli.plugins.get_plugin_manager", return_value=manager):
                    servers = _load_mcp_config()
                self.assertEqual(set(servers), {SERVER})
                server = _require_rendered_remote(SERVER, servers[SERVER])
                self.assertEqual(server["auth"], "oauth")
                self.assertEqual(servers[SERVER]["trust"], "untrusted")
                self.assertEqual(server["url"], URL)
                self.assertEqual(server["headers"], {"User-Agent": USER_AGENT})
                self.assertEqual(len(manager.list_plugin_skill_metadata()), len(EXPECTED_SKILLS))
            finally:
                manager.unload()
                reset_secret_scope(token)
                reset_multiplex_context(multiplex)


class CatalogEntryTests(unittest.TestCase):
    def test_entry_passes_the_hermes_catalog_validator_once_pinned(self):
        errors, warnings = _catalog_validator().validate_entry(_catalog_entry(DUMMY_SHA))
        self.assertEqual((errors, warnings), ([], []))

    def test_unpinned_entry_cannot_pass_the_validator(self):
        errors, _ = _catalog_validator().validate_entry(_catalog_entry(None))
        self.assertTrue(any("sha" in error for error in errors), errors)

    def test_entry_declares_what_the_package_does(self):
        entry = _catalog_entry(DUMMY_SHA)
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        mcp_text = (ROOT / "mcp.json").read_text(encoding="utf-8")
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual(entry["version"], manifest["version"])
        self.assertEqual(entry["repo"], manifest["repository"])
        caps = entry["capabilities"]
        self.assertEqual((caps["provides_tools"], caps["provides_hooks"], caps["provides_middleware"]), ([], [], []))
        self.assertEqual(sorted(caps["requires_env"]), sorted(set(re.findall(r"\$\{([A-Z0-9_]+)\}", mcp_text))))
        for field in ("docs_url", "image"):
            self.assertIn(DUMMY_SHA, entry[field])
        image = entry["image"].split(DUMMY_SHA + "/", 1)[1]
        self.assertTrue((ROOT / image).is_file(), image)

    def test_entry_disclosure_is_read_by_hermes(self):
        from hermes_cli.plugin_catalog_presence import _DISCLOSURE

        description = " ".join(_catalog_entry(DUMMY_SHA)["description"].split())
        match = _DISCLOSURE.search(description)
        self.assertIsNotNone(match)
        self.assertIn("mcp.arcmira.com", match.group(1))


class TransportTests(unittest.IsolatedAsyncioTestCase):
    def _rendered(self):
        with tempfile.TemporaryDirectory() as data:
            package = load_agent_plugin(ROOT, Path(data))
        token = set_secret_scope({KEY: "fixture-key"})
        try:
            return _require_rendered_remote(SERVER, _interpolate_env_vars(package.mcp_servers[SERVER]))
        finally:
            reset_secret_scope(token)

    async def test_every_rpc_request_sends_the_key_and_the_provider_user_agent(self):
        server = self._rendered()
        received = []

        def capture(request):
            received.append(request)
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}})

        factory = _make_redirect_header_stripper(
            httpx, httpx.URL(server["url"]), strict=server["strict_redirect_headers"],
            configured_header_names={key.lower() for key in server["headers"]},
        )
        async with factory(headers=server["headers"], transport=httpx.MockTransport(capture)) as client:
            for method in ("initialize", "tools/list", "tools/call"):
                await client.post(server["url"], json={"jsonrpc": "2.0", "id": 1, "method": method})
        self.assertEqual(len(received), 3)
        for request in received:
            self.assertEqual(str(request.url), URL)
            self.assertTrue(request.headers["User-Agent"].startswith(USER_AGENT))
            self.assertEqual(request.headers["Authorization"], "Bearer fixture-key")

    async def test_redirect_to_another_origin_drops_the_key(self):
        server = self._rendered()
        received = []

        def redirect(request):
            received.append(request)
            if request.url.host == "mcp.arcmira.com":
                return httpx.Response(307, headers={"Location": "https://other.example/mcp"})
            return httpx.Response(200)

        factory = _make_redirect_header_stripper(
            httpx, httpx.URL(server["url"]), strict=server["strict_redirect_headers"],
            configured_header_names={key.lower() for key in server["headers"]},
        )
        async with factory(headers=server["headers"], follow_redirects=True,
                           transport=httpx.MockTransport(redirect)) as client:
            await client.post(server["url"], json={"method": "tools/list"})
        self.assertEqual(len(received), 2)
        self.assertNotIn("Authorization", received[-1].headers)
