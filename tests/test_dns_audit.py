"""Dangling-CNAME detection.

Until 2026-08-13 `www.mr-race.com` pointed at an Azure CDN endpoint
deleted with an earlier project. Cloud endpoint names are claimable, so
whoever registered the missing name would have served content on that
subdomain - by which time it was also an Entra redirect URI.

These stub DNS entirely. A test that needs the network tells you about
the network, and would go red on a plane.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import dns_audit  # noqa: E402


@pytest.fixture
def zone(monkeypatch):
    """Build a fake zone: {fqdn: cname_target} plus a set of names that
    resolve. Anything not in `resolving` has no address."""
    def _build(cnames, resolving):
        def fake_dig(name, rtype):
            if rtype == "CNAME":
                t = cnames.get(name)
                return [t + "."] if t else []
            return ["203.0.113.1"] if name in resolving else []
        monkeypatch.setattr(dns_audit, "dig", fake_dig)
    return _build


class TestDetection:
    def test_flags_a_cname_whose_target_has_no_address(self, zone):
        """The real 2026-08-13 case."""
        zone({"www.mr-race.com": "azureresumeach.azureedge.net"},
             resolving=set())

        rows = dns_audit.audit()

        assert [r["name"] for r in rows if not r["resolves"]] == \
            ["www.mr-race.com"]

    def test_does_not_flag_a_live_target(self, zone):
        zone({"www.mr-race.com": "live.azurestaticapps.net"},
             resolving={"live.azurestaticapps.net"})

        rows = dns_audit.audit()

        assert all(r["resolves"] for r in rows)

    def test_separates_live_from_dangling_in_one_zone(self, zone):
        """The realistic shape: most records fine, one rotten."""
        zone({"www.mr-race.com": "live.azurestaticapps.net",
              "mcp.mr-race.com": "live.azurecontainerapps.io",
              "resume.mr-race.com": "gone.azureedge.net"},
             resolving={"live.azurestaticapps.net",
                        "live.azurecontainerapps.io"})

        rows = dns_audit.audit()
        dangling = [r["name"] for r in rows if not r["resolves"]]

        assert dangling == ["resume.mr-race.com"]
        assert len(rows) == 3

    def test_a_name_with_no_cname_is_not_reported(self, zone):
        """An A record can't dangle - there is no indirection to break."""
        zone({}, resolving={"mr-race.com"})

        assert dns_audit.audit() == []


class TestExitCode:
    """The exit code is the part a script consumes, so it is pinned."""

    def test_clean_zone_exits_zero(self, zone, monkeypatch, capsys):
        zone({"www.mr-race.com": "live.net"}, resolving={"live.net"})
        monkeypatch.setattr(sys, "argv", ["dns_audit.py"])

        assert dns_audit.main() == 0

    def test_dangling_zone_exits_one(self, zone, monkeypatch, capsys):
        zone({"www.mr-race.com": "gone.net"}, resolving=set())
        monkeypatch.setattr(sys, "argv", ["dns_audit.py"])

        assert dns_audit.main() == 1

    def test_output_does_not_bury_the_finding(self, zone, monkeypatch,
                                              capsys):
        zone({"www.mr-race.com": "gone.net"}, resolving=set())
        monkeypatch.setattr(sys, "argv", ["dns_audit.py"])

        dns_audit.main()
        out = capsys.readouterr().out

        assert "DANGLING" in out
        assert "gone.net" in out
        # It must also warn against pasting the target somewhere public,
        # since naming it is what an attacker needs.
        assert "SECURITY.md" in out
