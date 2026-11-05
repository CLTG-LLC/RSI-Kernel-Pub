"""Block real HTTP for every decision test."""

import urllib.request

import pytest


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("live networking is forbidden in decision tests")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", no_network)
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setenv("EXPERIENTIAL_API_KEY", "synthetic-test-key")
