"""
Unit tests validating the Schema API reStructuredText (RST) documentation page.
Testing library and framework: pytest
"""

import re
from pathlib import Path
import pytest


def _candidate_roots():
    return [Path('docs'), Path('doc'), Path('documentation'), Path('Docs')]


def _find_schema_api_file():
    """
    Attempt to locate the RST file containing the Schema API docs.
    Strategy:
      1) Look for files named schema_api.rst or schema-api.rst under common docs roots.
      2) Fall back to scanning .rst files under docs roots for the '.. _schema_api:' label.
      3) Final fallback: scan all .rst files in repo for the label (best-effort).
    """
    # 1) Direct filename match under common roots
    for root in _candidate_roots():
        if root.exists():
            for patt in ('schema_api.rst', 'schema-api.rst'):
                for p in root.rglob(patt):
                    if p.is_file():
                        return p

    # 2) Search for anchor label in the first ~2KB of each RST file under common roots
    label = '.. _schema_api:'
    for root in _candidate_roots():
        if root.exists():
            for p in root.rglob('*.rst'):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        head = f.read(2048)
                        if label in head:
                            return p
                except Exception:
                    continue

    # 3) Last-resort search across repo (could be slower, but only runs in CI)
    for p in Path('.').rglob('*.rst'):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                head = f.read(4096)
                if label in head:
                    return p
        except Exception:
            continue

    return None


@pytest.fixture(scope='module')
def docs_path():
    p = _find_schema_api_file()
    if p is None:
        pytest.skip("Schema API documentation RST file not found (label '.. _schema_api:' not located).")
    return p


@pytest.fixture(scope='module')
def docs_content(docs_path):
    return docs_path.read_text(encoding='utf-8')


@pytest.fixture
def docs_lines(docs_content):
    return docs_content.splitlines()


class TestDocumentStructure:
    def test_reference_label_at_top(self, docs_lines):
        non_empty = [ln for ln in docs_lines if ln.strip()]
        assert non_empty, "Document should not be empty"
        assert non_empty[0].strip() == '.. _schema_api:', "Reference label must be the first non-empty line"

    def test_title_and_underline(self, docs_lines):
        # Find 'Schema API' and verify underline uses '-' and is at least title length
        for i, ln in enumerate(docs_lines):
            if ln.strip() == 'Schema API':
                assert i + 1 < len(docs_lines), "Title should have an underline line"
                underline = docs_lines[i + 1].rstrip('\n')
                assert underline.strip() \!= ''
                assert set(underline.strip()) == {'-'}, "Title underline should use '-'"
                assert len(underline.strip()) >= len('Schema API'), "Underline should match or exceed title length"
                break
        else:
            pytest.fail("Could not find 'Schema API' title")

    def test_expected_sections_present(self, docs_content):
        sections = [
            'Useful APIs',
            'Project Classes',
            'User Classes',
            'ASIC Constraint Classes',
            'FPGA Constraint Classes',
            'Core Schema Classes',
            'Supporting Classes',
            'Inheritance',
        ]
        for sec in sections:
            assert sec in docs_content, f"Section '{sec}' should be present"

    def test_no_tabs(self, docs_content):
        assert '\t' not in docs_content, "Tabs found; use spaces in RST"

    def test_minimum_nonempty_lines(self, docs_lines):
        nonempty = sum(1 for ln in docs_lines if ln.strip())
        # Conservative lower bound to avoid flakiness while ensuring substance
        assert nonempty >= 150, f"Expected at least 150 non-empty lines, found {nonempty}"


class TestSphinxDirectives:
    def test_currentmodule_directive(self, docs_content):
        assert '.. currentmodule:: siliconcompiler.schema' in docs_content

    def test_autosummary_blocks(self, docs_content):
        autosummary_blocks = re.findall(r'^\.\. autosummary::\s*\n((?:    .*\n)*)',
                                        docs_content, re.MULTILINE)
        assert len(autosummary_blocks) >= 2, "Expect at least two autosummary blocks"
        # nosignatures in autosummary blocks
        assert re.search(r'\.\. autosummary::\s*\n\s*:nosignatures:', docs_content), \
            "Expected ':nosignatures:' option in autosummary blocks"

    def test_autoclass_directives_present_and_options(self, docs_content):
        autoclass_count = docs_content.count('.. autoclass::')
        assert autoclass_count >= 25, f"Too few autoclass directives: {autoclass_count}"
        members_count = docs_content.count(':members:')
        # Ensure a majority include :members:
        assert members_count >= max(10, int(autoclass_count * 0.5)), \
            "Most autoclass directives should include :members:"
        show_inheritance_count = docs_content.count(':show-inheritance:')
        assert show_inheritance_count >= 5, "Expect multiple classes to show inheritance"
        inherited_members_count = docs_content.count(':inherited-members:')
        assert inherited_members_count >= 5, "Expect multiple classes with inherited members"

    def test_custom_scclassinherit_present(self, docs_content):
        assert '.. scclassinherit::' in docs_content
        # Verify the classes list includes the slash form used by this directive
        assert 'siliconcompiler/ASIC' in docs_content
        assert 'siliconcompiler/FPGA' in docs_content


class TestBaseSchemaAPI:
    BASE_SCHEMA_METHODS = [
        'set', 'add', 'get', 'getkeys', 'getdict',
        'valid', 'unset', 'remove', 'write_manifest',
        'read_manifest', 'from_manifest'
    ]

    def test_base_schema_section_and_methods(self, docs_content):
        assert '**Base schema:**' in docs_content
        # Confirm autosummary entries for BaseSchema methods
        for m in self.BASE_SCHEMA_METHODS:
            assert f'BaseSchema.{m}' in docs_content, f"Missing BaseSchema.{m}"

    def test_base_schema_private_members_are_listed_explicitly(self, docs_content):
        # Focus on the diff-sensitive detail: explicit private members list
        assert ':private-members: +_from_dict,_parent' in docs_content, \
            "BaseSchema should explicitly include private members _from_dict and _parent"


class TestEditableSchemaAPI:
    def test_editable_schema_methods_and_section(self, docs_content):
        assert '**Editing schema:**' in docs_content
        for m in ('insert', 'remove', 'search'):
            assert f'EditableSchema.{m}' in docs_content, f"Missing EditableSchema.{m}"


class TestProjectAndUserClasses:
    def test_project_classes_documented(self, docs_content):
        # Exact modules as present in doc snippet
        assert '.. autoclass:: siliconcompiler.project.Project' in docs_content
        for cls in ('ASIC', 'FPGA', 'Lint', 'Sim'):
            assert f'.. autoclass:: siliconcompiler.{cls}' in docs_content
        # Options on project classes
        for cls in ('ASIC', 'FPGA', 'Lint', 'Sim'):
            pattern = rf'\.\. autoclass:: siliconcompiler\.{cls}.*?:show-inheritance:'
            assert re.search(pattern, docs_content, re.DOTALL), f"{cls} should show inheritance"

    def test_user_classes_documented(self, docs_content):
        for cls in ('Design', 'PDK', 'Flowgraph', 'Checklist', 'Task', 'FPGADevice', 'StdCellLibrary'):
            assert f'.. autoclass:: siliconcompiler.{cls}' in docs_content
            pat = rf'\.\. autoclass:: siliconcompiler\.{cls}.*?(?::show-inheritance:|:inherited-members:)'
            assert re.search(pat, docs_content, re.DOTALL), f"{cls} should include inheritance-related options"


class TestConstraintClasses:
    def test_asic_constraints_documented(self, docs_content):
        assert '.. autoclass:: siliconcompiler.asic.ASICConstraint' in docs_content
        for cls in ('ASICTimingConstraintSchema', 'ASICTimingScenarioSchema', 'ASICAreaConstraint',
                    'ASICPinConstraints', 'ASICPinConstraint', 'ASICComponentConstraints', 'ASICComponentConstraint'):
            assert f'.. autoclass:: siliconcompiler.constraints.{cls}' in docs_content

    def test_fpga_constraints_documented(self, docs_content):
        assert '.. autoclass:: siliconcompiler.fpga.FPGAConstraint' in docs_content
        for cls in ('FPGATimingConstraintSchema', 'FPGATimingScenarioSchema',
                    'FPGAComponentConstraints', 'FPGAPinConstraints'):
            assert f'.. autoclass:: siliconcompiler.constraints.{cls}' in docs_content


class TestCoreSchemaClasses:
    def test_core_schema_classes(self, docs_content):
        for cls in ('BaseSchema', 'EditableSchema', 'SafeSchema', 'Journal', 'NamedSchema', 'Parameter'):
            assert f'.. autoclass:: {cls}' in docs_content
        # Parameter values
        for cls in ('NodeListValue', 'NodeSetValue', 'NodeValue', 'PathNodeValue', 'DirectoryNodeValue', 'FileNodeValue'):
            assert f'.. autoclass:: siliconcompiler.schema.parametervalue.{cls}' in docs_content
        # Parameter types
        for cls in ('NodeType', 'NodeEnumType'):
            assert f'.. autoclass:: siliconcompiler.schema.parametertype.{cls}' in docs_content
        # Scope and PerNode
        assert '.. autoclass:: siliconcompiler.schema.parameter.Scope' in docs_content
        assert '.. autoclass:: siliconcompiler.schema.parameter.PerNode' in docs_content
        # DocsSchema
        assert '.. autoclass:: siliconcompiler.schema.DocsSchema' in docs_content
        # Inheritance visibility for Node*Value concrete classes
        for cls in ('PathNodeValue', 'DirectoryNodeValue', 'FileNodeValue'):
            pat = rf'\.\. autoclass:: .*{cls}.*?:show-inheritance:'
            assert re.search(pat, docs_content, re.DOTALL), f"{cls} should show inheritance"


class TestSupportingClasses:
    def test_supporting_classes_documented(self, docs_content):
        expectations = {
            'siliconcompiler.schema_support.dependencyschema.DependencySchema',
            'siliconcompiler.schema_support.option.OptionSchema',
            'siliconcompiler.schema_support.option.SchedulerSchema',
            'siliconcompiler.schema_support.cmdlineschema.CommandLineSchema',
            'siliconcompiler.schema_support.pathschema.PathSchemaBase',
            'siliconcompiler.schema_support.pathschema.PathSchema',
            'siliconcompiler.schema_support.filesetschema.FileSetSchema',
            'siliconcompiler.flowgraph.FlowgraphNodeSchema',
            'siliconcompiler.flowgraph.RuntimeFlowgraph',
            'siliconcompiler.tool.TaskError',
            'siliconcompiler.tool.TaskTimeout',
            'siliconcompiler.tool.TaskExecutableNotFound',
            'siliconcompiler.schema_support.packageschema.PackageSchema',
            'siliconcompiler.library.LibrarySchema',
            'siliconcompiler.library.ToolLibrarySchema',
            'siliconcompiler.schema_support.record.RecordSchema',
            'siliconcompiler.schema_support.metric.MetricSchema',
            'siliconcompiler.Schematic',
        }
        for path in expectations:
            assert f'.. autoclass:: {path}' in docs_content, f"Missing autoclass for {path}"


class TestInheritanceSection:
    def test_inheritance_section_and_diagrams(self, docs_content):
        assert 'Inheritance' in docs_content
        # Project classes diagram
        assert re.search(r'\.\. scclassinherit::\s*\n\s*:classes:\s*siliconcompiler/ASIC,'
                         r'siliconcompiler/FPGA,siliconcompiler/Lint,siliconcompiler/Sim',
                         docs_content)
        # User classes diagram
        assert re.search(r'\.\. scclassinherit::\s*\n\s*:classes:.*siliconcompiler/Design,'
                         r'siliconcompiler/PDK,.*siliconcompiler/FPGADevice,.*siliconcompiler/StdCellLibrary,'
                         r'.*siliconcompiler/Flowgraph,.*siliconcompiler/Checklist,.*siliconcompiler/Task',
                         docs_content, re.DOTALL)


class TestCrossReferencesAndQuality:
    def test_glossary_reference_present(self, docs_content):
        assert ':ref:`glossary <glossary>`' in docs_content

    def test_currentmodule_before_first_autosummary(self, docs_content):
        i_mod = docs_content.find('.. currentmodule::')
        i_auto = docs_content.find('.. autosummary::')
        assert i_mod \!= -1 and i_auto \!= -1 and i_mod < i_auto, \
            "currentmodule should appear before autosummary blocks"

    def test_autoclass_paths_look_valid(self, docs_content):
        targets = re.findall(r'\.\. autoclass:: ([\w.]+)', docs_content)
        assert targets, "No autoclass targets found"
        for t in targets:
            assert re.match(r'^[A-Za-z_][\w.]*$', t), f"Invalid autoclass path: {t}"
            assert '..' not in t, f"Malformed autoclass path with consecutive dots: {t}"

    def test_reasonable_directive_count(self, docs_content):
        # Not too strict to avoid brittleness but ensures structural richness
        directive_starts = docs_content.count('.. ')
        assert directive_starts >= 30, f"Too few directives found: {directive_starts}"


class TestSectionSpacingAndUnderlines:
    def test_section_underlines_length(self, docs_lines):
        section_chars = {'=', '-', '~', '^', '"', '#'}
        # Validate underline of each expected section heading if found
        for idx, ln in enumerate(docs_lines[:-1]):
            if ln.strip() in {
                'Useful APIs', 'Project Classes', 'User Classes',
                'ASIC Constraint Classes', 'FPGA Constraint Classes',
                'Core Schema Classes', 'Supporting Classes', 'Inheritance'
            }:
                underline = docs_lines[idx + 1]
                if underline.strip():
                    assert set(underline.strip()).issubset(section_chars)
                    assert len(underline.strip()) >= len(ln.strip()), \
                        f"Underline too short for section '{ln.strip()}'"

    def test_spacing_between_sections(self, docs_lines):
        # Ensure at least a couple of lines between major sections (not overly strict)
        headings = []
        for i, ln in enumerate(docs_lines):
            if ln.strip() in {
                'Useful APIs', 'Project Classes', 'User Classes',
                'ASIC Constraint Classes', 'FPGA Constraint Classes',
                'Core Schema Classes', 'Supporting Classes', 'Inheritance'
            }:
                headings.append(i)
        for a, b in zip(headings, headings[1:]):
            gap = b - a
            assert gap >= 2, f"Expected some spacing between sections, got gap={gap}"


class TestIntroAndCoverage:
    def test_intro_mentions_purpose(self, docs_content):
        head = docs_content.split('Useful APIs')[0] if 'Useful APIs' in docs_content else docs_content[:400]
        head_low = head.lower()
        assert ('describes all public methods' in head_low) or ('python api' in head_low), \
            "Intro should describe the purpose of the page"
        assert ('user guide' in head) or ('User Guide' in head), "Intro should reference the User Guide"

    def test_overall_coverage_signal(self, docs_content):
        autoclass_count = docs_content.count('.. autoclass::')
        autosummary_refs = docs_content.count('BaseSchema.') + docs_content.count('EditableSchema.')
        total_items = autoclass_count + autosummary_refs
        assert total_items >= 40, f"Expected broad coverage (>=40 items), found {total_items}"


if __name__ == '__main__':
    pytest.main([__file__, '-q'])