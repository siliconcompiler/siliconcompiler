import os
import base64
import webbrowser
import subprocess
from siliconcompiler import utils

from siliconcompiler.report.utils import _collect_data, _find_summary_image
from siliconcompiler.tools._common import get_tool_task


def _generate_html_report(chip, flow, flowgraph_nodes, results_html):
    '''
    Generates an HTML based on the run
    '''

    # only report tool based steps functions
    for (step, index) in flowgraph_nodes.copy():
        tool, task = get_tool_task(chip, step, '0', flow=flow)
        if tool == 'builtin':
            index = flowgraph_nodes.index((step, index))
            del flowgraph_nodes[index]

    schema = chip.schema.copy()
    schema.prune()
    pruned_cfg = schema.cfg
    if 'history' in pruned_cfg:
        del pruned_cfg['history']
    if 'library' in pruned_cfg:
        del pruned_cfg['library']

    layout_img = _find_summary_image(chip)

    img_data = None
    # Base64-encode layout for inclusion in HTML report
    if layout_img and os.path.isfile(layout_img):
        with open(layout_img, 'rb') as img_file:
            img_data = base64.b64encode(img_file.read()).decode('utf-8')

    nodes, errors, metrics, metrics_unit, metrics_to_show, reports = \
        _collect_data(chip, flow, flowgraph_nodes)

    # Hardcode the encoding, since there's a Unicode character in a
    # Bootstrap CSS file inlined in this template. Without this setting,
    # this write may raise an encoding error on machines where the
    # default encoding is not UTF-8.
    with open(results_html, 'w', encoding='utf-8') as wf:
        wf.write(utils.get_file_template('report/sc_report.j2').render(
            design=chip.design,
            nodes=nodes,
            errors=errors,
            metrics=metrics,
            metrics_unit=metrics_unit,
            reports=reports,
            manifest=chip.schema.cfg,
            pruned_cfg=pruned_cfg,
            metric_keys=metrics_to_show,
            img_data=img_data,
        ))

    chip.logger.info(f'Generated HTML report at {results_html}')


def _open_html_report(chip, results_html):
    try:
        webbrowser.get(results_html)
    except webbrowser.Error:
        # Python 'webbrowser' module includes a limited number of popular defaults.
        # Depending on the platform, the user may have defined their own with
        # $BROWSER.
        env_browser = os.getenv('BROWSER')
        if env_browser:
            subprocess.Popen([env_browser, os.path.relpath(results_html)])
        else:
            chip.logger.warning(f'Unable to open results page in web browser: {results_html}')
