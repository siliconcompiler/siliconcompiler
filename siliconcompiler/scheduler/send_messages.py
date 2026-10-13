"""
A module for sending email notifications about SiliconCompiler job events.

This module provides functionality to send detailed email updates at various
stages of a compilation flow (e.g., on begin, failure, or a final summary).
It loads SMTP server credentials from a configuration file, constructs
HTML-formatted emails with relevant job data and attachments (logs, images),
and sends them to specified recipients.
"""
import json
import os
import sys
import uuid

import os.path

from siliconcompiler import NodeStatus, sc_open
from siliconcompiler.utils import ConfigCommand, default_email_credentials_file, \
    get_file_template
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.scheduler.listener import RunListener
from siliconcompiler.utils.paths import workdir
from siliconcompiler.utils.settings import replace_file


# Every field the email credentials file may carry, and the type it takes, in
# the order sc-config asks for them.
CREDENTIAL_TYPES = {
    "server": str,       # Address of the SMTP server
    "port": int,         # Port number of the SMTP server
    "ssl": bool,         # Whether to connect over SSL
    "username": str,     # Username on the email server
    "password": str,     # Password on the email server
    "from": str,         # Source address; defaults to the first recipient
    "max_file_size": int  # Maximum number of log lines to attach
}

# Fields a usable credentials file cannot leave out.
REQUIRED_CREDENTIALS = ("username", "password", "server", "port")

# Fields never echoed or printed.
SECRET_CREDENTIALS = ("password",)

# Fields the sender reads unconditionally, so an absent one gets a value here.
CREDENTIAL_DEFAULTS = {
    "ssl": True,
    "max_file_size": 1000
}


def __validate_config(creds):
    """
    Checks an email credentials mapping and fills in the defaults.

    Args:
        creds (dict): Credentials as read from the file.

    Raises:
        ValueError: If a field is missing, unrecognized, or of the wrong type.

    Returns:
        dict: The credentials, with :data:`CREDENTIAL_DEFAULTS` applied to
        whatever the file did not set.
    """
    if not isinstance(creds, dict):
        raise ValueError(f"must be an object, not {type(creds).__name__}")

    unknown = sorted(set(creds) - set(CREDENTIAL_TYPES))
    if unknown:
        raise ValueError(f"unrecognized field(s): {', '.join(unknown)}")

    missing = [field for field in REQUIRED_CREDENTIALS if field not in creds]
    if missing:
        raise ValueError(f"missing field(s): {', '.join(missing)}")

    for field, value in creds.items():
        expected = CREDENTIAL_TYPES[field]
        # bool is a subclass of int, so an int field would otherwise take True.
        if not isinstance(value, expected) or \
                (expected is int and isinstance(value, bool)):
            raise ValueError(f"'{field}' must be {expected.__name__}, "
                             f"not {type(value).__name__}")

    return {**CREDENTIAL_DEFAULTS, **creds}


def read_credentials():
    """
    Reads the email credentials file, and checks it.

    Raises:
        FileNotFoundError: If there is no credentials file.
        ValueError: If it is not JSON, or a field is missing, unrecognized, or
            of the wrong type.

    Returns:
        dict: The credentials, with :data:`CREDENTIAL_DEFAULTS` applied to
        whatever the file did not set.
    """
    with open(default_email_credentials_file()) as f:
        # JSONDecodeError is a ValueError, so malformed JSON is reported the
        # same way as a malformed field.
        return __validate_config(json.load(f))


def write_credentials(creds):
    """
    Checks email credentials and saves them, readable only by the user. The
    file is replaced as one step, so it is never left half written.

    Args:
        creds (dict): The credentials.

    Raises:
        ValueError: If a field is missing, unrecognized, or of the wrong type.

    Returns:
        str: The credentials file.
    """
    __validate_config(creds)
    path = default_email_credentials_file()
    # Created first, so the private mode the file gets is not the directory's.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    replace_file(path, json.dumps(creds, indent=4), 0o600)
    return path


def send_test_message(cred, to):
    """
    Sends one short message, to check email credentials.

    Args:
        cred (dict): The credentials, as :func:`read_credentials` returns them.
        to (str): The address to send it to.

    Raises:
        OSError: If the server cannot be reached, or it refuses the login or
            the message; :class:`smtplib.SMTPException` is an OSError.
    """
    from email.mime.text import MIMEText

    msg = MIMEText("SiliconCompiler can send job emails with these settings.")
    msg['Subject'] = 'SiliconCompiler : test message'
    msg['From'] = cred.get("from", to)
    msg['To'] = to
    _deliver(cred, [to], msg)


def _deliver(cred, to, msg):
    """
    Sends ``msg`` to ``to`` through the SMTP server ``cred`` names, raising
    what :mod:`smtplib` raises.
    """
    import smtplib

    smtp_use = smtplib.SMTP_SSL if cred['ssl'] else smtplib.SMTP
    with smtp_use(cred["server"], cred["port"]) as smtp_server:
        smtp_server.login(cred["username"], cred["password"])
        smtp_server.sendmail(msg['From'], to, msg.as_string())


def __load_config(project):
    """
    Loads and validates email credentials from the default configuration file.

    Args:
        project (Project): The project object, used for logging.

    Returns:
        dict: A dictionary containing the validated email credentials. Returns
        an empty dictionary if the file is not found or is invalid.
    """
    try:
        return read_credentials()
    except FileNotFoundError:
        project.logger.warning('Email credentials are not available: '
                               f'{default_email_credentials_file()}')
    except ValueError as e:
        # Reported rather than ending the run.
        project.logger.error(f'Email credentials failed to validate: {e}')
    return {}


def send(project, msg_type, step, index):
    """
    Constructs and sends an email notification for a specific job event.

    This function checks if a notification is required for the given event type
    based on the project's configuration. If so, it assembles an email with a
    subject, HTML body, and relevant attachments (logs or images) and sends
    it via the configured SMTP server.

    Args:
        project (Project): The project object containing all run data and configuration.
        msg_type (str): The type of event triggering the message (e.g., 'begin',
            'fail', 'summary').
        step (str): The step name associated with the event. Can be None for
            global events.
        index (str): The index associated with the event. Can be None for
            global events.
    """
    to = project.option.scheduler.get_msgcontact(step=step, index=index)
    event = project.option.scheduler.get_msgevent(step=step, index=index)

    if not to or not event:
        # nothing to do
        return

    if 'all' not in event and msg_type not in event:
        # nothing to do
        return

    # Imported here rather than at module scope: smtplib pulls in ssl and the
    # report package pulls in Pillow, and every run reaches this module through
    # EmailListener, almost none of which send mail.
    import smtplib

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    from siliconcompiler.report import utils as report_utils

    cred = __load_config(project)

    if not cred:
        return

    jobname = project.option.get_jobname()

    msg = MIMEMultipart()

    if step and index:
        subject = f'SiliconCompiler : {project.name} | {jobname} | {step} | {index} | {msg_type}'
    else:
        subject = f'SiliconCompiler : {project.name} | {jobname} | {msg_type}'

    # Setup email header
    msg['Subject'] = subject

    if "from" in cred:
        msg['From'] = cred["from"]
    else:
        msg['From'] = list(to)[0]
    msg['To'] = ", ".join(to)
    msg['X-Entity-Ref-ID'] = uuid.uuid4().hex  # keep emails from getting grouped

    # max_file_size caps the log lines a message carries; zero turns the
    # attachments off, and the body is rendered and sent either way.
    attach_files = cred["max_file_size"] > 0

    if msg_type == "summary":
        # Handle summary message: attach layout image and metrics summary
        if attach_files:
            layout_img = report_utils._find_summary_image(project)
            if layout_img and os.path.isfile(layout_img):
                with open(layout_img, 'rb') as img_file:
                    img_attach = MIMEApplication(img_file.read())
                    img_attach.add_header('Content-Disposition',
                                          'attachment',
                                          filename=os.path.basename(layout_img))
                    msg.attach(img_attach)

        runtime = RuntimeFlowgraph.from_project(project)

        nodes, errors, metrics, metrics_unit, metrics_to_show, _ = \
            report_utils._collect_data(project, flowgraph_nodes=runtime.get_nodes())

        text_msg = get_file_template('email/summary.j2').render(
            design=project.name,
            nodes=nodes,
            errors=errors,
            metrics=metrics,
            metrics_unit=metrics_unit,
            metric_keys=metrics_to_show)
    else:
        # Handle general node message: attach log files and node-specific data
        # Attach logs
        if attach_files:
            for log in (f'sc_{step}_{index}.log', f'{step}.log'):
                log_file = f'{workdir(project, step=step, index=index)}/{log}'
                if os.path.exists(log_file):
                    with sc_open(log_file) as f:
                        file_content = f.read().splitlines()
                        # Limit to max_file_size
                        file_content = file_content[-cred["max_file_size"]:]
                        log_attach = MIMEApplication("\n".join(file_content))
                        log_name, _ = os.path.splitext(log)
                        # Make attachment a txt file to avoid issues with tools not loading .log
                        log_attach.add_header('Content-Disposition',
                                              'attachment',
                                              filename=f'{log_name}.txt')
                        msg.attach(log_attach)

        # Collect records for the specific node
        records = {}
        for record in project.getkeys('record'):
            value = None
            if project.get('record', record, field='pernode').is_never():
                value = project.get('record', record)
            else:
                value = project.get('record', record, step=step, index=index)

            if value is not None:
                records[record] = value

        # Collect metrics for the specific node
        nodes, errors, metrics, metrics_unit, metrics_to_show, _ = \
            report_utils._collect_data(project, flowgraph_nodes=[(step, index)])

        status = project.get('record', 'status', step=step, index=index)

        # Render the general email template
        text_msg = get_file_template('email/general.j2').render(
            design=project.name,
            job=jobname,
            step=step,
            index=index,
            status=status,
            records=records,
            nodes=nodes,
            errors=errors,
            metrics=metrics,
            metrics_unit=metrics_unit,
            metric_keys=metrics_to_show)

    body = MIMEText(text_msg, 'html')
    msg.attach(body)

    try:
        _deliver(cred, to, msg)
    except smtplib.SMTPAuthenticationError as e:
        project.logger.error(f'Unable to authenticate to email server: {e}')
    except Exception as e:
        project.logger.error(f'An error occurred while sending email: {e}')


class SummaryEmailListener(RunListener):
    """
    Sends the ``summary`` email, if ``[option,scheduler,msgevent]`` asks for it,
    once a run's flow is over. A run that fails in setup sends none.

    This is the mail the client side of a remote run sends; the server's run
    sends the rest.
    """

    def flow_finished(self, project, error):
        send(project, "summary", None, None)


class EmailListener(SummaryEmailListener):
    """
    Sends a run's email notifications, as ``[option,scheduler,msgevent]``
    selects them: ``begin`` as a node is launched, ``end``, ``skipped`` or
    ``fail`` as it finishes, and ``summary`` once the flow is over.
    """

    def node_started(self, project, step, index):
        send(project, "begin", step, index)

    def node_finished(self, project, step, index):
        status = project.get('record', 'status', step=step, index=index)
        if status == NodeStatus.SKIPPED:
            msg_type = "skipped"
        elif NodeStatus.is_error(status):
            msg_type = "fail"
        else:
            msg_type = "end"
        send(project, msg_type, step, index)


if __name__ == "__main__":
    # Example usage for testing the send function
    from siliconcompiler import Project
    from siliconcompiler.targets import freepdk45_demo
    project = Project('test')
    project.use(freepdk45_demo)
    project.option.scheduler.add_msgevent('all')
    # To test, uncomment the following line and fill in a valid email address
    # project.option.scheduler.add_msgcontact('your.email@example.com')
    send(project, "BEGIN", "import", "0")


def _add_parser(commands):
    """
    Add the ``email`` command: it sets, shows and tests the email credentials.
    """
    parser = commands.add_parser(
        "email",
        help="the SMTP server job emails are sent through",
        description="Set the SMTP server job emails are sent through. The settings are "
                    "kept in ~/.sc/email.json, readable only by you.")
    actions = parser.add_subparsers(dest="action", metavar="<action>", required=True)
    actions.add_parser(
        "set",
        help="ask for each setting; Enter keeps the value shown, and the password is "
             "never echoed").set_defaults(func=_cli_set)
    actions.add_parser(
        "show", help="print the settings, the password hidden").set_defaults(func=_cli_show)
    action = actions.add_parser("test", help="send one message, to check the settings")
    action.add_argument("address", help="where to send it")
    action.set_defaults(func=_cli_test)


def _shown(field, value):
    if field in SECRET_CREDENTIALS:
        return "********"
    return value if isinstance(value, str) else json.dumps(value)


def _cli_ask(field, kind, current):
    """One field, asked for until it is valid; Enter keeps ``current``."""
    import getpass
    from siliconcompiler.schema.parametertype import NodeType

    shown = "" if current is None else f" [{_shown(field, current)}]"
    while True:
        if field in SECRET_CREDENTIALS:
            answer = getpass.getpass(f"{field}{shown}: ")
        else:
            answer = input(f"{field}{shown}: ").strip()
        if not answer:
            if current is not None or field not in REQUIRED_CREDENTIALS:
                return current
            print(f"Error: {field} is required", file=sys.stderr)
            continue
        try:
            return NodeType.normalize(answer, NodeType.parse(kind.__name__))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)


def _cli_credentials():
    path = default_email_credentials_file()
    try:
        return read_credentials()
    except FileNotFoundError:
        raise ValueError(f"there are no email settings in {path}; "
                         "sc-config email set writes them") from None
    except ValueError as e:
        raise ValueError(f"{path}: {e}") from e


def _cli_set(args):
    try:
        current = read_credentials()
    except FileNotFoundError:
        current = {}
    except ValueError as e:
        print(f"Replacing {default_email_credentials_file()}: {e}", file=sys.stderr)
        current = {}

    creds = {}
    try:
        for field, kind in CREDENTIAL_TYPES.items():
            value = _cli_ask(field, kind, current.get(field, CREDENTIAL_DEFAULTS.get(field)))
            if value is not None:
                creds[field] = value
    except EOFError:
        raise ValueError("the input ended before every setting was given; "
                         "nothing was saved") from None

    print(f"Saved {write_credentials(creds)}")
    return 0


def _cli_show(args):
    creds = _cli_credentials()
    width = max(len(field) for field in creds)
    for field in CREDENTIAL_TYPES:
        if field in creds:
            print(f"{field:<{width}}  {_shown(field, creds[field])}")
    return 0


def _cli_test(args):
    creds = _cli_credentials()
    try:
        send_test_message(creds, args.address)
    except OSError as e:
        raise ValueError(f"sending through {creds['server']}:{creds['port']} "
                         f"failed: {e}") from e
    print(f"Sent a test message to {args.address}")
    return 0


EMAIL_COMMAND = ConfigCommand(
    examples="""\
To set the server job emails are sent through, and check it:
    sc-config email set
    sc-config email test you@example.com""",
    add_parser=_add_parser)
