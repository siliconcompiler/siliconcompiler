import pytest
from siliconcompiler.scheduler import send_messages
from unittest.mock import patch
from siliconcompiler.utils import default_email_credentials_file
import json
import re
from pathlib import Path
import os
from itertools import combinations_with_replacement


events = (
    "begin",
    "end",
    "timeout",
    "fail",
    "summary"
)


@pytest.fixture
def email_creds(monkeypatch):
    def _mock_home():
        return Path(os.getcwd())

    monkeypatch.setattr(Path, 'home', _mock_home)

    os.makedirs(os.path.dirname(default_email_credentials_file()), exist_ok=True)

    with open(default_email_credentials_file(), 'w') as f:
        json.dump(
            {
                "server": "local",
                "port": 555,
                "username": "test",
                "password": "pass"
            },
            f
        )

    return default_email_credentials_file()


@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    'event', events
)
def test_email_all(asic_gcd, email_creds, event):
    asic_gcd.set('option', 'scheduler', 'msgevent', 'all')
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, event, "import", "0")

        mock_smtp.assert_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_called()
        context.sendmail.assert_called()


@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    'event', events
)
def test_email_none(asic_gcd, email_creds, event):
    asic_gcd.set('option', 'scheduler', 'msgevent', [])
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, event, "import", "0")

        mock_smtp.assert_not_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_not_called()
        context.sendmail.assert_not_called()


@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    'event,check_event', [v for v in combinations_with_replacement(events, 2) if v[0] == v[1]]
)
def test_email_single_match(asic_gcd, email_creds, event, check_event):
    asic_gcd.set('option', 'scheduler', 'msgevent', event)
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, check_event, "import", "0")

        mock_smtp.assert_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_called()
        context.sendmail.assert_called()


@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    'event,check_event', [v for v in combinations_with_replacement(events, 2) if v[0] != v[1]]
)
def test_email_single_not_match(asic_gcd, email_creds, event, check_event):
    asic_gcd.set('option', 'scheduler', 'msgevent', event)
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, check_event, "import", "0")

        mock_smtp.assert_not_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_not_called()
        context.sendmail.assert_not_called()


@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    'event', events
)
def test_email_missing_credentials(asic_gcd, event):
    asic_gcd.set('option', 'scheduler', 'msgevent', [])
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, event, "import", "0")

        mock_smtp.assert_not_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_not_called()
        context.sendmail.assert_not_called()


@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    'event', events
)
def test_email_missing_email(asic_gcd, email_creds, event):
    asic_gcd.set('option', 'scheduler', 'msgevent', [])

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, event, "import", "0")

        mock_smtp.assert_not_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_not_called()
        context.sendmail.assert_not_called()


@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    'event', events
)
def test_email_missing_event(asic_gcd, email_creds, event):
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, event, "import", "0")

        mock_smtp.assert_not_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_not_called()
        context.sendmail.assert_not_called()


@pytest.mark.timeout(30)
def test_email_step_index(asic_gcd, email_creds):
    asic_gcd.set('option', 'scheduler', 'msgevent', 'all', step='syn', index='0')
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, "begin", "import", "0")

        mock_smtp.assert_not_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_not_called()
        context.sendmail.assert_not_called()

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, "begin", "syn", "0")

        mock_smtp.assert_called()

        context = mock_smtp.return_value.__enter__.return_value
        context.login.assert_called()
        context.sendmail.assert_called()


validate = send_messages.__validate_config


def test_validate_applies_defaults():
    # The two fields the sender reads unconditionally are filled in, so a file
    # carrying only the required four is usable.
    assert validate({
        "username": "test",
        "password": "pass",
        "server": "local",
        "port": 555
    }) == {
        "username": "test",
        "password": "pass",
        "server": "local",
        "port": 555,
        "ssl": True,
        "max_file_size": 1000
    }


def test_validate_keeps_values_over_defaults():
    creds = validate({
        "username": "test",
        "password": "pass",
        "server": "local",
        "port": 555,
        "from": "me@testing.xyz",
        "ssl": False,
        "max_file_size": 0
    })

    assert creds["from"] == "me@testing.xyz"
    assert creds["ssl"] is False
    assert creds["max_file_size"] == 0


@pytest.mark.parametrize("missing", ("username", "password", "server", "port"))
def test_validate_missing_required(missing):
    creds = {"username": "test", "password": "pass", "server": "local", "port": 555}
    del creds[missing]

    with pytest.raises(ValueError, match=f"missing field\\(s\\): {missing}"):
        validate(creds)


def test_validate_reports_every_missing_field():
    with pytest.raises(ValueError, match=r"missing field\(s\): username, password, server, port"):
        validate({})


def test_validate_unrecognized_field():
    with pytest.raises(ValueError, match=r"unrecognized field\(s\): smtp, tls"):
        validate({
            "username": "test",
            "password": "pass",
            "server": "local",
            "port": 555,
            "tls": True,
            "smtp": "local"
        })


@pytest.mark.parametrize("field,value,expect", [
    ("username", 5, "'username' must be str, not int"),
    ("port", "555", "'port' must be int, not str"),
    ("ssl", "yes", "'ssl' must be bool, not str"),
    # bool subclasses int, so an integer field must still reject True.
    ("max_file_size", True, "'max_file_size' must be int, not bool"),
])
def test_validate_wrong_type(field, value, expect):
    creds = {"username": "test", "password": "pass", "server": "local", "port": 555}
    creds[field] = value

    with pytest.raises(ValueError, match=re.escape(expect)):
        validate(creds)


def test_validate_not_an_object():
    with pytest.raises(ValueError, match="must be an object, not list"):
        validate([])


def test_load_config_reports_bad_json(asic_gcd, email_creds, caplog):
    # A malformed file is reported rather than ending the run.
    with open(email_creds, 'w') as f:
        f.write("{not json")

    asic_gcd.set('option', 'scheduler', 'msgevent', 'all')
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, "begin", "import", "0")

        mock_smtp.assert_not_called()

    assert "Email credentials failed to validate" in caplog.text


def test_load_config_reports_bad_field(asic_gcd, email_creds, caplog):
    with open(email_creds, 'w') as f:
        json.dump({"username": "test", "password": "pass", "server": "local"}, f)

    asic_gcd.set('option', 'scheduler', 'msgevent', 'all')
    asic_gcd.set('option', 'scheduler', 'msgcontact', 'test@testing.xyz')

    with patch('smtplib.SMTP_SSL', autospec=True) as mock_smtp:
        send_messages.send(asic_gcd, "begin", "import", "0")

        mock_smtp.assert_not_called()

    assert "Email credentials failed to validate: missing field(s): port" in caplog.text
