import pytest
from siliconcompiler.scheduler import send_messages
from unittest.mock import patch
from siliconcompiler.utils import default_email_credentials_file
import json
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
