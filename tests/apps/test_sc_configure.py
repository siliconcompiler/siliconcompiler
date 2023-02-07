import json
import os
import pytest
import sys

from siliconcompiler.apps import sc_configure

@pytest.mark.eda
@pytest.mark.quick
def test_sc_configure_cmdarg(monkeypatch):
    os.environ['HOME'] = os.getcwd()
    server_name = 'https://example.com'
    monkeypatch.setattr('sys.argv', ['sc-configure', server_name])

    sc_configure.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open('./.sc/credentials', 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == server_name
    assert not 'username' in generated_creds
    assert not 'password' in generated_creds

@pytest.mark.eda
@pytest.mark.quick
def test_sc_configure_interactive(monkeypatch):
    os.environ['HOME'] = os.getcwd()
    server_name = 'https://example.com'
    username = 'ci_test_user'
    password = 'ci_test_password'
    monkeypatch.setattr('sys.argv', ['sc-configure'])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
         wf.write(f'{server_name}\n{username}\n{password}\n')
    with open('cfg_stdin.txt', 'r') as rf:
         sys.stdin = rf

         sc_configure.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open('./.sc/credentials', 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == server_name
    assert generated_creds['username'] == username
    assert generated_creds['password'] == password

@pytest.mark.eda
@pytest.mark.quick
def test_sc_configure_override_y(monkeypatch):
    os.makedirs('.sc')
    with open('.sc/credentials', 'w') as cf:
        cf.write('{"address": "old_example_address"}')
    os.environ['HOME'] = os.getcwd()
    server_name = 'https://example.com'
    username = 'ci_test_user'
    password = 'ci_test_password'
    monkeypatch.setattr('sys.argv', ['sc-configure'])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
         wf.write(f'y\n{server_name}\n{username}\n{password}\n')
    with open('cfg_stdin.txt', 'r') as rf:
         sys.stdin = rf

         sc_configure.main()

    # Check that generated credentials match the expected values.
    generated_creds = {}
    with open('./.sc/credentials', 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] == server_name
    assert generated_creds['username'] == username
    assert generated_creds['password'] == password

@pytest.mark.eda
@pytest.mark.quick
def test_sc_configure_override_n(monkeypatch):
    os.makedirs('.sc')
    with open('.sc/credentials', 'w') as cf:
        cf.write('{"address": "old_example_address"}')
    os.environ['HOME'] = os.getcwd()
    server_name = 'https://example.com'
    username = 'ci_test_user'
    password = 'ci_test_password'
    monkeypatch.setattr('sys.argv', ['sc-configure'])

    # Use sys.stdin to simulate user input.
    with open('cfg_stdin.txt', 'w') as wf:
         wf.write(f'n\n{server_name}\n{username}\n{password}\n')
    with open('cfg_stdin.txt', 'r') as rf:
         sys.stdin = rf

         sc_configure.main()

    # Check that the existing credentials were not overridden.
    generated_creds = {}
    with open('./.sc/credentials', 'r') as cf:
        generated_creds = json.loads(cf.read())

    assert generated_creds['address'] != server_name
    assert not 'username' in generated_creds
    assert not 'password' in generated_creds
