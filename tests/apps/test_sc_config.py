import functools
import json
import logging
import os
import re
import smtplib
import stat
import sys

import pytest

from pathlib import Path
from unittest.mock import patch

from siliconcompiler import Project
from siliconcompiler.apps import sc_config
from siliconcompiler.utils import default_email_credentials_file, default_tokens_file
from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler.utils.settings import SettingsManager


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    '''The test's own settings.json, over its own system.json, read on first use.'''
    @functools.cache
    def manager():
        return SettingsManager(os.path.abspath("settings.json"), logging.getLogger(),
                               system_filepath=os.path.abspath("system.json"))

    monkeypatch.setattr(MPManager, "get_settings", staticmethod(manager))


@pytest.fixture
def email_home(monkeypatch):
    """A home of the test's own: the session's is shared, and email.json and tokens live there."""
    monkeypatch.setattr(Path, "home", lambda: Path(os.getcwd()))


def write_email(**creds):
    os.makedirs(os.path.dirname(default_email_credentials_file()), exist_ok=True)
    with open(default_email_credentials_file(), "w") as f:
        json.dump({"server": "smtp.example.com", "port": 465, "username": "me",
                   "password": "secret", **creds}, f)


def answer(monkeypatch, *answers, password=""):
    answers = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt: password)


def run(monkeypatch, *args):
    monkeypatch.setattr("sys.argv", ["sc-config", *args])
    return sc_config.main()


def written():
    with open("settings.json") as f:
        return json.load(f)


@pytest.mark.parametrize("args,category,key,stored", [
    (["cache", "cleanupdays", "30"], "cache", "cleanupdays", 30),
    (["scheduler-slurm", "sharedpaths", "/a", "/b"], "scheduler-slurm", "sharedpaths",
     ["/a", "/b"]),
    (["schema-options", "scheduler,name", "slurm"], "schema-options", "scheduler,name", "slurm"),
    (["schema-options", "scheduler,msgevent", "end", "fail"], "schema-options",
     "scheduler,msgevent", ["end", "fail"]),
    (["showtask", "gds", "klayout"], "showtask", "gds", "klayout"),
    (["issue", "alllibraries", "true"], "issue", "alllibraries", True),
    (["issue", "libraries", "mylib", "mypdk"], "issue", "libraries", ["mylib", "mypdk"]),
    (["-raw", "mine", "key", '{"a": 1}'], "mine", "key", {"a": 1}),
    (["-raw", "mine", "key", "text"], "mine", "key", "text"),
])
def test_set_writes_a_typed_value(monkeypatch, args, category, key, stored):
    assert run(monkeypatch, "settings", "set", *args) == 0
    assert written() == {category: {key: stored}}


@pytest.mark.parametrize("args,said", [
    (["cache", "cleanupday", "30"], "cache has no setting cleanupday"),
    (["cache", "cleanupdays", "abc"], "cache cleanupdays: \"abc\" unable to convert to int"),
    (["cache", "cleanupdays", "1", "2"], "cache cleanupdays takes one value"),
    (["schema-options", "scheduler,name", "bogus"], "bogus is not a member of"),
    (["schema-options", "flow", "asicflow"], "flow describes one run"),
    (["schema-options", "nosuch", "1"], "nosuch is not an option"),
    (["mine", "key", "1"], "mine is not a settings category"),
    (["showtask", "gds", "gtkwave"], "gtkwave cannot open .gds files"),
])
def test_set_refuses_what_it_cannot_check(monkeypatch, capsys, args, said):
    assert run(monkeypatch, "settings", "set", *args) == 1
    assert said in capsys.readouterr().err
    assert not os.path.exists("settings.json")


def test_get_and_unset_fall_back_to_the_default(monkeypatch, capsys):
    assert run(monkeypatch, "settings", "set", "cache", "cleanupdays", "30") == 0
    assert run(monkeypatch, "settings", "get", "cache", "cleanupdays") == 0
    assert capsys.readouterr().out == "30\n"

    assert run(monkeypatch, "settings", "unset", "cache", "cleanupdays") == 0
    assert run(monkeypatch, "settings", "get", "cache", "cleanupdays") == 0
    assert capsys.readouterr().out == "90\n"
    assert written() == {}

    assert run(monkeypatch, "settings", "get", "showtask", "gds") == 1
    assert "showtask gds is not set" in capsys.readouterr().err


def test_add_and_remove_change_a_list(monkeypatch, capsys):
    """add keeps the system default and skips entries already held; remove refuses a missing one."""
    with open("system.json", "w") as f:
        json.dump({"scheduler-slurm": {"sharedpaths": ["/nfs"]}}, f)

    args = ["scheduler-slurm", "sharedpaths"]
    assert run(monkeypatch, "settings", "add", *args, "/a", "/nfs") == 0
    assert run(monkeypatch, "settings", "add", *args, "/b") == 0
    assert run(monkeypatch, "settings", "remove", *args, "/nfs") == 0
    assert written() == {"scheduler-slurm": {"sharedpaths": ["/a", "/b"]}}

    assert run(monkeypatch, "settings", "remove", *args, "/a", "/x") == 1
    assert "scheduler-slurm sharedpaths does not hold /x" in capsys.readouterr().err
    assert run(monkeypatch, "settings", "add", "cache", "cleanupdays", "5") == 1
    assert "cache cleanupdays is not a list; set changes it" in capsys.readouterr().err
    assert written() == {"scheduler-slurm": {"sharedpaths": ["/a", "/b"]}}


def test_get_prints_a_stored_null(monkeypatch, capsys):
    """A null written with -raw reads back as null, not as an unset key."""
    assert run(monkeypatch, "settings", "set", "-raw", "mine", "key", "null") == 0
    assert run(monkeypatch, "settings", "get", "-raw", "mine", "key") == 0
    assert capsys.readouterr().out == "null\n"


def test_list_marks_defaults_and_unknown_keys(monkeypatch, capsys):
    with open("settings.json", "w") as f:
        json.dump({"cache": {"cleanupdays": 30}, "mycache": {"cleanupdays": 1}}, f)

    assert run(monkeypatch, "settings", "list") == 0
    lines = [line.split() for line in capsys.readouterr().out.splitlines()]
    assert ["cache", "cleanupdays", "30"] in lines
    assert ["cache", "cleanupinterval", "7", "(default)"] in lines
    assert ["mycache", "cleanupdays", "1", "(unknown)"] in lines


def test_a_setting_the_system_file_fixes_is_refused(monkeypatch, capsys):
    with open("system.json", "w") as f:
        json.dump({"record": {"region": {"value": "us-east-1", "system_priority": True}}}, f)

    for args in (["set", "record", "region", "eu"], ["unset", "record", "region"]):
        assert run(monkeypatch, "settings", *args) == 1
        assert "record region is fixed by the system settings file" in capsys.readouterr().err
    assert not os.path.exists("settings.json")

    assert run(monkeypatch, "settings", "list") == 0
    assert "us-east-1  (fixed by the system)" in capsys.readouterr().out


def test_a_malformed_settings_file_is_left_alone(monkeypatch, capsys):
    with open("settings.json", "w") as f:
        f.write("{bad")

    assert run(monkeypatch, "settings", "set", "cache", "cleanupdays", "30") == 1
    assert "is malformed" in capsys.readouterr().err
    with open("settings.json") as f:
        assert f.read() == "{bad"


def test_a_saved_option_is_every_projects_default(monkeypatch):
    assert run(monkeypatch, "settings", "set", "schema-options", "scheduler,name", "slurm") == 0
    assert Project().option.scheduler.get_name() == "slurm"


def test_email_set_asks_for_each_field(monkeypatch, capsys, email_home):
    """set asks again for a bad or missing value, and saves the unechoed password privately."""
    answer(monkeypatch, "", "smtp.example.com", "abc", "465", "", "me", "", "",
           password="secret")
    assert run(monkeypatch, "email", "set") == 0

    err = capsys.readouterr().err
    assert "server is required" in err
    assert '"abc" unable to convert to int' in err
    with open(default_email_credentials_file()) as f:
        assert json.load(f) == {"server": "smtp.example.com", "port": 465, "ssl": True,
                                "username": "me", "password": "secret", "max_file_size": 1000}
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(default_email_credentials_file()).st_mode) == 0o600


def test_email_set_keeps_what_is_there(monkeypatch, email_home):
    """Enter keeps every current value, the password included."""
    write_email(ssl=False)
    answer(monkeypatch, *[""] * 6)
    assert run(monkeypatch, "email", "set") == 0

    with open(default_email_credentials_file()) as f:
        assert json.load(f) == {"server": "smtp.example.com", "port": 465, "ssl": False,
                                "username": "me", "password": "secret", "max_file_size": 1000}


def test_email_show_hides_the_password(monkeypatch, capsys, email_home):
    """show masks the password, and says how to write settings where there are none."""
    assert run(monkeypatch, "email", "show") == 1
    assert "there are no email settings" in capsys.readouterr().err

    write_email()
    assert run(monkeypatch, "email", "show") == 0
    out = capsys.readouterr().out
    assert "password       ********" in out
    assert "secret" not in out


def test_email_test_sends_one_message(monkeypatch, capsys, email_home):
    """test logs in and sends to the address given, and reports what the server refused."""
    write_email()
    with patch("smtplib.SMTP_SSL", autospec=True) as smtp:
        server = smtp.return_value.__enter__.return_value
        assert run(monkeypatch, "email", "test", "you@example.com") == 0
        server.login.assert_called_once_with("me", "secret")
        assert server.sendmail.call_args.args[:2] == ("you@example.com", ["you@example.com"])

        server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"refused")
        assert run(monkeypatch, "email", "test", "you@example.com") == 1
    assert "sending through smtp.example.com:465 failed" in capsys.readouterr().err


@pytest.mark.parametrize("given,token", [([], "asked"), (["given"], "given")])
def test_tokens_set_list_and_unset(monkeypatch, capsys, email_home, given, token):
    """set stores the token given, or else the unechoed answer, privately; list hides
    it and marks an export that overrides it, and unset removes it."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    answer(monkeypatch, password=" asked ")
    assert run(monkeypatch, "tokens", "set", "GITHUB_TOKEN", *given) == 0
    with open(default_tokens_file()) as f:
        assert json.load(f) == {"tokens": {"GITHUB_TOKEN": token}}
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(default_tokens_file()).st_mode) == 0o600
        assert stat.S_IMODE(os.stat(os.path.dirname(default_tokens_file())).st_mode) == 0o700

    monkeypatch.setenv("GITHUB_TOKEN", "exported")
    assert run(monkeypatch, "tokens", "list") == 0
    out = capsys.readouterr().out
    assert "GITHUB_TOKEN  ********  (overridden by the environment)" in out
    assert token not in out

    assert run(monkeypatch, "tokens", "unset", "GITHUB_TOKEN") == 0
    assert run(monkeypatch, "tokens", "unset", "GITHUB_TOKEN") == 1
    assert "GITHUB_TOKEN is not stored" in capsys.readouterr().err
    assert run(monkeypatch, "tokens", "list") == 0
    assert capsys.readouterr().out == "No tokens are stored\n"


@pytest.mark.parametrize("name,token,said", [
    ("github_token", "secret", "github_token is not a token variable"),
    ("GITHUB", "secret", "GITHUB is not a token variable"),
    ("GITHUB_TOKEN", " ", "no token was given; nothing was saved"),
])
def test_tokens_set_refuses_a_bad_name_or_no_token(monkeypatch, capsys, email_home,
                                                   name, token, said):
    """set stores nothing under a name no data source reads, or for an empty answer."""
    answer(monkeypatch, password=token)
    assert run(monkeypatch, "tokens", "set", name) == 1
    assert said in capsys.readouterr().err
    assert not os.path.exists(default_tokens_file())


def test_cache_show_reports_size_and_sweeps(monkeypatch, capsys):
    """show gives the size and last sweep, and the sweep settings: off, or defaults if invalid."""
    os.makedirs("cache")
    with open(os.path.join("cache", "data"), "w") as f:
        f.write("x" * 2048)

    assert run(monkeypatch, "cache", "show", "-cachedir", "cache") == 0
    out = capsys.readouterr().out
    assert "size             2.0KB" in out
    assert "last sweep       never" in out
    assert "automatic sweep  every 7 days, of what has gone unused for 90 days" in out

    assert run(monkeypatch, "settings", "set", "cache", "cleanupdays", "0") == 0
    assert run(monkeypatch, "cache", "show", "-cachedir", "nocache") == 0
    out = capsys.readouterr().out
    assert "nothing is cached yet" in out
    assert "automatic sweep  off" in out

    assert run(monkeypatch, "settings", "set", "-raw", "cache", "cleanupdays", "null") == 0
    assert run(monkeypatch, "cache", "show", "-cachedir", "nocache") == 0
    assert "every 7 days, of what has gone unused for 90 days" in capsys.readouterr().out


def test_paths_marks_what_is_missing(monkeypatch, capsys, email_home):
    """paths lists the default locations, marking the ones not created yet."""
    os.makedirs(".sc")
    with open(os.path.join(".sc", "settings.json"), "w") as f:
        f.write("{}")

    assert run(monkeypatch, "paths") == 0
    lines = {line.split()[0]: line for line in capsys.readouterr().out.splitlines()}
    assert lines["settings"].endswith(os.path.join(".sc", "settings.json"))
    assert lines["email"].endswith("(missing)")
    assert lines["tokens"].endswith("(missing)")
    assert lines["managers"].endswith("(missing)")
    assert lines["tool"].endswith("(missing)")


@pytest.mark.parametrize("args,helps", [
    (["-h"], ["sc-config"]),
    (["settings", "-h"], ["sc-config settings"]),
    (["settings", "-helpall"], ["sc-config settings", *(
        f"sc-config settings {action}"
        for action in ("list", "get", "set", "add", "remove", "unset"))]),
])
def test_helpall_prints_every_help_below(monkeypatch, capsys, args, helps):
    """-h prints one level, and -helpall that level and every command below it."""
    with pytest.raises(SystemExit) as exit:
        run(monkeypatch, *args)
    assert exit.value.code == 0
    out = capsys.readouterr().out
    assert re.findall(r"^usage: (.+?) \[-h\]", out, re.MULTILINE) == helps
