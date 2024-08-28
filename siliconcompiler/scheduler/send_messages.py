from siliconcompiler.utils import default_email_credentials_file, get_file_template
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json
import os
from siliconcompiler import sc_open
from siliconcompiler.schema import Schema
from siliconcompiler.report import utils as report_utils
import fastjsonschema
from pathlib import Path
from siliconcompiler.flowgraph import get_executed_nodes
import uuid
from siliconcompiler.targets import freepdk45_demo


# Compile validation code for API request bodies.
api_dir = Path(__file__).parent / 'validation'

# 'remote_run': Run a stage of a job using the server's cluster settings.
with open(api_dir / 'email_credentials.json') as schema:
    validate_creds = fastjsonschema.compile(json.loads(schema.read()))


def __load_config(chip):
    path = default_email_credentials_file()
    if not os.path.exists(path):
        chip.logger.warn(f'Email credentials are not available: {path}')
        return {}

    with open(path) as f:
        creds = json.load(f)

    try:
        return validate_creds(creds)
    except fastjsonschema.JsonSchemaException as e:
        chip.logger.error(f'Email credentials failed to validate: {e}')
        return {}


def send(chip, msg_type, step, index):
    chip_step, chip_index = step, index
    if step is None:
        chip_step = Schema.GLOBAL_KEY
    if index is None:
        chip_index = Schema.GLOBAL_KEY
    to = chip.get('option', 'scheduler', 'msgcontact', step=chip_step, index=chip_index)
    event = chip.get('option', 'scheduler', 'msgevent', step=chip_step, index=chip_index)

    if not to or not event:
        # nothing to do
        return

    if 'all' not in event and msg_type not in event:
        # nothing to do
        return

    cred = __load_config(chip)

    if not cred:
        return

    jobname = chip.get("option", "jobname")
    flow = chip.get("option", "flow")

    msg = MIMEMultipart()

    if step and index:
        subject = f'SiliconCompiler : {chip.design} | {jobname} | {step}{index} | {msg_type}'
    else:
        subject = f'SiliconCompiler : {chip.design} | {jobname} | {msg_type}'

    # Setup email header
    msg['Subject'] = subject

    if "from" in cred:
        msg['From'] = cred["from"]
    else:
        msg['From'] = to[0]
    msg['To'] = ", ".join(to)
    msg['X-Entity-Ref-ID'] = uuid.uuid4().hex  # keep emails from getting grouped

    if msg_type == "summary":
        layout_img = report_utils._find_summary_image(chip)
        if layout_img and os.path.isfile(layout_img):
            with open(layout_img, 'rb') as img_file:
                img_attach = MIMEApplication(img_file.read())
                img_attach.add_header('Content-Disposition',
                                      'attachment',
                                      filename=os.path.basename(layout_img))
                msg.attach(img_attach)

        nodes_to_execute = get_executed_nodes(chip, flow)
        nodes, errors, metrics, metrics_unit, metrics_to_show, _ = \
            report_utils._collect_data(chip, flow=flow, flowgraph_nodes=nodes_to_execute)

        text_msg = get_file_template('email/summary.j2').render(
            design=chip.design,
            nodes=nodes,
            errors=errors,
            metrics=metrics,
            metrics_unit=metrics_unit,
            metric_keys=metrics_to_show)
    else:
        # Attach logs
        for log in (f'sc_{step}{index}.log', f'{step}.log'):
            log_file = f'{chip.getworkdir(step=step, index=index)}/{log}'
            if os.path.exists(log_file):
                with sc_open(log_file) as f:
                    log_attach = MIMEApplication(f.read())
                    log_name, _ = os.path.splitext(log)
                    # Make attachment a txt file to avoid issues with tools not loading .log
                    log_attach.add_header('Content-Disposition',
                                          'attachment',
                                          filename=f'{log_name}.txt')
                    msg.attach(log_attach)

        records = {}
        for record in chip.getkeys('record'):
            value = None
            if chip.get('record', record, field='pernode') == 'never':
                value = chip.get('record', record)
            else:
                value = chip.get('record', record, step=step, index=index)

            if value is not None:
                records[record] = value

        nodes, errors, metrics, metrics_unit, metrics_to_show, _ = \
            report_utils._collect_data(chip, flow=flow, flowgraph_nodes=[(step, index)])

        status = chip.get('record', 'status', step=step, index=index)

        text_msg = get_file_template('email/general.j2').render(
            design=chip.design,
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

    if cred['ssl']:
        smtp_use = smtplib.SMTP_SSL
    else:
        smtp_use = smtplib.SMTP

    with smtp_use(cred["server"], cred["port"]) as smtp_server:
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
                smtp_server.sendmail(msg['From'], to, msg.as_string())
            except Exception as e:
                chip.logger.error(f'An error occurred while sending email: {e}')


if __name__ == "__main__":
    from siliconcompiler import Chip
    chip = Chip('test')
    chip.use(freepdk45_demo)
    chip.set('option', 'scheduler', 'msgevent', 'ALL')
    # chip.set('option', 'scheduler', 'msgcontact', 'fillin')
    send(chip, "BEGIN", "import", "0")
