import pytest

from siliconcompiler.schema import PerNode, Scope

from siliconcompiler.constraints import ASICComponentConstraints, ASICComponentConstraint


# Fixture for ASICComponentConstraint
@pytest.fixture
def component_constraint():
    return ASICComponentConstraint("test_comp")


# Fixture for ASICComponentConstraints
@pytest.fixture
def component_constraints_collection():
    return ASICComponentConstraints()


def test_asic_component_constraint_keys():
    assert ASICComponentConstraint().allkeys() == set([
        ('partname',),
        ('placement',),
        ('rotation',),
        ('halo',)
    ])


@pytest.mark.parametrize("key", ASICComponentConstraint().allkeys())
def test_asic_component_constraint_key_params(key):
    param = ASICComponentConstraint().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.OPTIONAL
    assert param.get(field="scope") == Scope.GLOBAL


def test_asic_component_constraint_init(component_constraint):
    """Test ASICComponentConstraint initialization and name setting."""
    assert component_constraint.name() == "test_comp"
    # Test without name
    no_name_comp = ASICComponentConstraint()
    assert no_name_comp.name() is None


def test_set_get_placement(component_constraint):
    """Test setting and getting component placement."""
    component_constraint.set_placement(10.0, 20.0)
    assert component_constraint.get_placement() == (10.0, 20.0)
    component_constraint.set_placement(5, 15)  # Test integers
    assert component_constraint.get_placement() == (5, 15)

    with pytest.raises(TypeError, match="x must be a number"):
        component_constraint.set_placement("a", 1.0)
    with pytest.raises(TypeError, match="y must be a number"):
        component_constraint.set_placement(1.0, "b")


def test_set_get_partname(component_constraint):
    """Test setting and getting component part name."""
    component_constraint.set_partname("my_cell")
    assert component_constraint.get_partname() == "my_cell"

    with pytest.raises(ValueError, match="a partname is required"):
        component_constraint.set_partname("")
    with pytest.raises(ValueError, match="a partname is required"):
        component_constraint.set_partname(None)


def test_set_get_halo(component_constraint):
    """Test setting and getting component halo."""
    component_constraint.set_halo(1.0, 1.5)
    assert component_constraint.get_halo() == (1.0, 1.5)
    component_constraint.set_halo(0, 0)  # Test zero halo
    assert component_constraint.get_halo() == (0, 0)

    with pytest.raises(TypeError, match="x must be a number"):
        component_constraint.set_halo("a", 1.0)
    with pytest.raises(TypeError, match="y must be a number"):
        component_constraint.set_halo(1.0, "b")
    with pytest.raises(ValueError, match="x must be a positive number"):
        component_constraint.set_halo(-1.0, 1.0)
    with pytest.raises(ValueError, match="y must be a positive number"):
        component_constraint.set_halo(1.0, -1.0)


def test_set_get_rotation(component_constraint):
    """Test setting and getting component rotation."""
    component_constraint.set_rotation("R90")
    assert component_constraint.get_rotation() == "R90"
    component_constraint.set_rotation("MZ_MX_R180")
    assert component_constraint.get_rotation() == "MZ_MX_R180"


def test_asic_component_constraints_keys():
    assert ASICComponentConstraints().allkeys() == set([
        ('default', 'partname'),
        ('default', 'placement'),
        ('default', 'rotation'),
        ('default', 'halo')
    ])


def test_add_component(component_constraints_collection):
    """Test adding new and overwriting existing component constraints."""
    new_comp = ASICComponentConstraint("new_comp")
    component_constraints_collection.add_component(new_comp)
    assert component_constraints_collection.get_component("new_comp") is new_comp

    # Overwrite
    updated_comp = ASICComponentConstraint("new_comp")
    component_constraints_collection.add_component(updated_comp)
    assert component_constraints_collection.get_component("new_comp") is updated_comp

    # Test adding invalid type
    with pytest.raises(TypeError, match="component must be a component constraint object"):
        component_constraints_collection.add_component("not_a_component")

    # Test adding component without a name
    no_name_comp = ASICComponentConstraint()
    with pytest.raises(ValueError, match="component constraint must have a name"):
        component_constraints_collection.add_component(no_name_comp)


def test_get_component(component_constraints_collection):
    """Test retrieving specific and all component constraints."""
    comp1 = component_constraints_collection.make_component("comp1")
    comp2 = component_constraints_collection.make_component("comp2")

    # Get specific
    retrieved_comp1 = component_constraints_collection.get_component("comp1")
    assert retrieved_comp1 is comp1

    # Get all
    all_components = component_constraints_collection.get_component()
    assert isinstance(all_components, dict)
    assert "comp1" in all_components
    assert "comp2" in all_components
    assert all_components["comp1"] is comp1
    assert all_components["comp2"] is comp2

    # Get non-existent
    with pytest.raises(LookupError, match="non_existent_comp is not defined"):
        component_constraints_collection.get_component("non_existent_comp")


def test_make_component(component_constraints_collection):
    """Test creating new component constraints."""
    new_comp = component_constraints_collection.make_component("made_comp")
    assert isinstance(new_comp, ASICComponentConstraint)
    assert new_comp.name() == "made_comp"
    assert component_constraints_collection.get_component("made_comp") is new_comp

    # Test creating existing
    with pytest.raises(LookupError, match="made_comp constraint already exists"):
        component_constraints_collection.make_component("made_comp")

    # Test empty name
    with pytest.raises(ValueError, match="component name is required"):
        component_constraints_collection.make_component("")
    with pytest.raises(ValueError, match="component name is required"):
        component_constraints_collection.make_component(None)


def test_remove_component(component_constraints_collection):
    """Test removing component constraints."""
    component_constraints_collection.make_component("to_remove_comp")
    assert component_constraints_collection.get_component("to_remove_comp") is not None

    # Remove existing
    assert component_constraints_collection.remove_component("to_remove_comp") is True
    with pytest.raises(LookupError, match="to_remove_comp is not defined"):
        component_constraints_collection.get_component("to_remove_comp")

    # Remove non-existent
    assert component_constraints_collection.remove_component("non_existent_comp") is False

    # Test empty name
    with pytest.raises(ValueError, match="component name is required"):
        component_constraints_collection.remove_component("")
    with pytest.raises(ValueError, match="component name is required"):
        component_constraints_collection.remove_component(None)
