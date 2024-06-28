from siliconcompiler.utils import default_email_credentials_file, get_file_template
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json
import os
from siliconcompiler import sc_open
from siliconcompiler.report import utils as report_utils


def __load_config(chip):
    path = default_email_credentials_file()
    if not os.path.exists(path):
        chip.logger.warn(f'Email credentials are not available: {path}')
        return {}

    with open(path) as f:
        return json.load(f)


def send(chip, msg_type, step, index):
    to = chip.get('option', 'scheduler', 'msgcontact', step=step, index=index)
    event = chip.get('option', 'scheduler', 'msgevent', step=step, index=index)

    if not to or not event:
        # nothing to do
        return

    if event != "ALL" and event != msg_type:
        # nothing to do
        return

    if event == "NONE":
        # nothing to do
        return

    cred = __load_config(chip)

    if not cred:
        return

    jobname = chip.get("option", "jobname")
    flow = chip.get("option", "flow")

    msg = MIMEMultipart()

    # Setup email header
    msg['Subject'] = \
        f'SiliconCompiler : {chip.design} | {jobname} | {step}{index} | {msg_type}'
    msg['From'] = cred["from"]
    msg['To'] = ", ".join(to)

    missing_logs = []
    # Attach logs
    for log in (f'sc_{step}{index}.log', f'{step}.log'):
        log_file = f'{chip._getworkdir(step=step, index=index)}/{log}'
        if os.path.exists(log_file):
            with sc_open(log_file) as f:
                log_attach = MIMEApplication(f.read())
                log_attach.add_header('Content-Disposition', 'attachment', filename=log)
                msg.attach(log_attach)
        else:
            missing_logs.append(log)

    records = {}
    for record in chip.getkeys('record'):
        value = None
        if chip.get('record', record, field='pernode') == 'never':
            value = chip.get('record', record)
        else:
            value = chip.get('record', record, step=step, index=index)

        if value is not None:
            records[record] = value

    _, errors, report_metrics, metrics_unit, metrics_to_show, _ = \
        report_utils._collect_data(chip, flow=flow, flowgraph_nodes=[(step, index)])

    metrics = {}
    for metric, value in report_metrics[step, index].items():
        if metric in metrics_to_show:
            metrics[metric] = f'{value} {metrics_unit[metric]}'

    status = chip.get('flowgraph', flow, step, index, 'status')

    text_msg = get_file_template('email/body.j2').render(
        design=chip.design,
        job=jobname,
        step=step,
        index=index,
        status=status,
        missing_logs=", ".join(missing_logs),
        records=records,
        metrics=metrics)

    body = MIMEText(text_msg)
    msg.attach(body)

    with smtplib.SMTP_SSL(cred["server"], cred["port"]) as smtp_server:
        do_send = False
        try:
            smtp_server.login(cred["username"], cred["password"])
            do_send = True
        except smtplib.SMTPAuthenticationError as e:
            chip.logger.error(f'Unable to authenticate to email server: {e}')
        except Exception as e:
            chip.logger.error(f'An error occurred during login to email server: {e}')

        if do_send:
            try:
                smtp_server.sendmail(cred["from"], to, msg.as_string())
            except Exception as e:
                chip.logger.error(f'An error occurred while sending email: {e}')


if __name__ == "__main__":
    from siliconcompiler import Chip
    chip = Chip('test')
    chip.load_target("freepdk45_demo")
    chip.set('option', 'scheduler', 'msgevent', 'ALL')
    # chip.set('option', 'scheduler', 'msgcontact', 'fillin')
    send(chip, "BEGIN", "import", "0")
