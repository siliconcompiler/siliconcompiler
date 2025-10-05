import pytest

from siliconcompiler.schema import PerNode, Scope

from siliconcompiler.constraints import ASICPinConstraint, ASICPinConstraints


@pytest.fixture
def pin_constraint():
    return ASICPinConstraint("test_pin")


@pytest.fixture
def pin_constraints_collection():
    return ASICPinConstraints()


def test_asic_pin_constraint_keys():
    assert ASICPinConstraint().allkeys() == set([
        ('layer',),
        ('placement',),
        ('side',),
        ('order',),
        ('length',),
        ('shape',),
        ('width',),
    ])


@pytest.mark.parametrize("key", ASICPinConstraint().allkeys())
def test_asic_pin_constraint_key_params(key):
    param = ASICPinConstraint().get(*key, field=None)
    assert param.get(field="pernode") == PerNode.OPTIONAL
    assert param.get(field="scope") == Scope.GLOBAL


def test_asic_pin_constraint_init(pin_constraint):
    """Test ASICPinConstraint initialization and name setting."""
    assert pin_constraint.name == "test_pin"
    # Test without name
    no_name_pin = ASICPinConstraint()
    assert no_name_pin.name is None


def test_set_get_width(pin_constraint):
    """Test setting and getting pin width."""
    pin_constraint.set_width(10.5)
    assert pin_constraint.get_width() == 10.5
    pin_constraint.set_width(5)  # Test integer
    assert pin_constraint.get_width() == 5

    with pytest.raises(TypeError, match="^width must be a number$"):
        pin_constraint.set_width("abc")
    with pytest.raises(ValueError, match="^width must be a positive value$"):
        pin_constraint.set_width(0)
    with pytest.raises(ValueError, match="^width must be a positive value$"):
        pin_constraint.set_width(-1.0)


def test_set_get_width_step_index():
    pin = ASICPinConstraint()
    assert pin.set_width(10)
    assert pin.set_width(20, step="step0", index="1")
    assert pin.get("width") == 10
    assert pin.get("width", step="step0", index="1") == 20
    assert pin.get_width() == 10
    assert pin.get_width(step="step0", index="1") == 20


def test_set_get_length(pin_constraint):
    """Test setting and getting pin length."""
    pin_constraint.set_length(20.0)
    assert pin_constraint.get_length() == 20.0
    pin_constraint.set_length(15)  # Test integer
    assert pin_constraint.get_length() == 15

    with pytest.raises(TypeError, match="^length must be a number$"):
        pin_constraint.set_length([1])
    with pytest.raises(ValueError, match="^length must be a positive value$"):
        pin_constraint.set_length(0.0)
    with pytest.raises(ValueError, match="^length must be a positive value$"):
        pin_constraint.set_length(-5)


def test_set_get_length_step_index():
    pin = ASICPinConstraint()
    assert pin.set_length(10)
    assert pin.set_length(20, step="step0", index="1")
    assert pin.get("length") == 10
    assert pin.get("length", step="step0", index="1") == 20
    assert pin.get_length() == 10
    assert pin.get_length(step="step0", index="1") == 20


def test_set_get_placement(pin_constraint):
    """Test setting and getting pin placement."""
    pin_constraint.set_placement(1.2, 3.4)
    assert pin_constraint.get_placement() == (1.2, 3.4)
    pin_constraint.set_placement(10, 20)  # Test integers
    assert pin_constraint.get_placement() == (10, 20)

    with pytest.raises(TypeError, match="^x must be a number$"):
        pin_constraint.set_placement("a", 1.0)
    with pytest.raises(TypeError, match="^y must be a number$"):
        pin_constraint.set_placement(1.0, "b")


def test_set_get_placement_step_index():
    pin = ASICPinConstraint()
    assert pin.set_placement(0, 10)
    assert pin.set_placement(10, 0, step="step0", index="1")
    assert pin.get("placement") == (0, 10)
    assert pin.get("placement", step="step0", index="1") == (10, 0)
    assert pin.get_placement() == (0, 10)
    assert pin.get_placement(step="step0", index="1") == (10, 0)


def test_set_get_shape(pin_constraint):
    """Test setting and getting pin shape."""
    pin_constraint.set_shape("circle")
    assert pin_constraint.get_shape() == "circle"
    pin_constraint.set_shape("polygon")
    assert pin_constraint.get_shape() == "polygon"


def test_set_get_shape_step_index():
    pin = ASICPinConstraint()
    assert pin.set_shape("rectangle")
    assert pin.set_shape("square", step="step0", index="1")
    assert pin.get("shape") == "rectangle"
    assert pin.get("shape", step="step0", index="1") == "square"
    assert pin.get_shape() == "rectangle"
    assert pin.get_shape(step="step0", index="1") == "square"


def test_set_get_layer(pin_constraint):
    """Test setting and getting pin layer."""
    pin_constraint.set_layer("m5")
    assert pin_constraint.get_layer() == "m5"
    pin_constraint.set_layer("2")  # Test integer as string
    assert pin_constraint.get_layer() == "2"


def test_set_get_layer_step_index():
    pin = ASICPinConstraint()
    assert pin.set_layer("m5")
    assert pin.set_layer("m7", step="step0", index="1")
    assert pin.get("layer") == "m5"
    assert pin.get("layer", step="step0", index="1") == "m7"
    assert pin.get_layer() == "m5"
    assert pin.get_layer(step="step0", index="1") == "m7"


def test_set_get_side(pin_constraint):
    """Test setting and getting pin side with integers and strings."""
    pin_constraint.set_side(1)
    assert pin_constraint.get_side() == 1
    pin_constraint.set_side("top")
    assert pin_constraint.get_side() == 2
    pin_constraint.set_side("EAST")  # Test case insensitivity
    assert pin_constraint.get_side() == 3
    pin_constraint.set_side("south")
    assert pin_constraint.get_side() == 4
    pin_constraint.set_side("west")
    assert pin_constraint.get_side() == 1

    with pytest.raises(TypeError, match="^side must be an integer$"):
        pin_constraint.set_side(3.5)
    with pytest.raises(ValueError, match="^side must be a positive integer$"):
        pin_constraint.set_side(0)
    with pytest.raises(ValueError, match="^side must be a positive integer$"):
        pin_constraint.set_side(-1)
    with pytest.raises(ValueError, match="^invalid is a not a recognized side$"):
        pin_constraint.set_side("invalid")


def test_set_get_side_step_index():
    pin = ASICPinConstraint()
    assert pin.set_side(1)
    assert pin.set_side(2, step="step0", index="1")
    assert pin.get("side") == 1
    assert pin.get("side", step="step0", index="1") == 2
    assert pin.get_side() == 1
    assert pin.get_side(step="step0", index="1") == 2


def test_set_get_order(pin_constraint):
    """Test setting and getting pin order."""
    pin_constraint.set_order(5)
    assert pin_constraint.get_order() == 5
    pin_constraint.set_order(0)  # Order can be 0 or negative based on context, no validation here
    assert pin_constraint.get_order() == 0
    pin_constraint.set_order(-2)
    assert pin_constraint.get_order() == -2


def test_set_get_order_step_index():
    pin = ASICPinConstraint()
    assert pin.set_order(1)
    assert pin.set_order(2, step="step0", index="1")
    assert pin.get("order") == 1
    assert pin.get("order", step="step0", index="1") == 2
    assert pin.get_order() == 1
    assert pin.get_order(step="step0", index="1") == 2


def test_asic_pin_constraints_keys():
    assert ASICPinConstraints().allkeys() == set([
        ('default', 'layer'),
        ('default', 'placement'),
        ('default', 'side'),
        ('default', 'order'),
        ('default', 'length'),
        ('default', 'shape'),
        ('default', 'width'),
    ])


def test_add_pinconstraint(pin_constraints_collection):
    """Test adding new and overwriting existing pin constraints."""
    new_pin = ASICPinConstraint("new_pin")
    pin_constraints_collection.add_pinconstraint(new_pin)
    assert pin_constraints_collection.get_pinconstraint("new_pin") is new_pin

    # Overwrite
    updated_pin = ASICPinConstraint("new_pin")
    pin_constraints_collection.add_pinconstraint(updated_pin)
    assert pin_constraints_collection.get_pinconstraint("new_pin") is updated_pin

    # Test adding invalid type
    with pytest.raises(TypeError, match="^pin must be a pin constraint object$"):
        pin_constraints_collection.add_pinconstraint("not_a_pin")

    # Test adding pin without a name
    no_name_pin = ASICPinConstraint()
    with pytest.raises(ValueError, match="^pin constraint must have a name$"):
        pin_constraints_collection.add_pinconstraint(no_name_pin)


def test_get_pinconstraint(pin_constraints_collection):
    """Test retrieving specific and all pin constraints."""
    pin1 = pin_constraints_collection.make_pinconstraint("pin1")
    pin2 = pin_constraints_collection.make_pinconstraint("pin2")

    # Get specific
    retrieved_pin1 = pin_constraints_collection.get_pinconstraint("pin1")
    assert retrieved_pin1 is pin1

    # Get all
    all_pins = pin_constraints_collection.get_pinconstraint()
    assert isinstance(all_pins, dict)
    assert "pin1" in all_pins
    assert "pin2" in all_pins
    assert all_pins["pin1"] is pin1
    assert all_pins["pin2"] is pin2

    # Get non-existent
    with pytest.raises(LookupError, match="^non_existent_pin is not defined$"):
        pin_constraints_collection.get_pinconstraint("non_existent_pin")


def test_make_pinconstraint(pin_constraints_collection):
    """Test creating new pin constraints."""
    new_pin = pin_constraints_collection.make_pinconstraint("made_pin")
    assert isinstance(new_pin, ASICPinConstraint)
    assert new_pin.name == "made_pin"
    assert pin_constraints_collection.get_pinconstraint("made_pin") is new_pin

    # Test creating existing
    with pytest.raises(LookupError, match="^made_pin constraint already exists$"):
        pin_constraints_collection.make_pinconstraint("made_pin")

    # Test empty name
    with pytest.raises(ValueError, match="^pin name is required$"):
        pin_constraints_collection.make_pinconstraint("")
    with pytest.raises(ValueError, match="^pin name is required$"):
        pin_constraints_collection.make_pinconstraint(None)


def test_remove_pinconstraint(pin_constraints_collection):
    """Test removing pin constraints."""
    pin_constraints_collection.make_pinconstraint("to_remove_pin")
    assert pin_constraints_collection.get_pinconstraint("to_remove_pin") is not None

    # Remove existing
    assert pin_constraints_collection.remove_pinconstraint("to_remove_pin") is True
    with pytest.raises(LookupError, match="^to_remove_pin is not defined$"):
        pin_constraints_collection.get_pinconstraint("to_remove_pin")

    # Remove non-existent
    assert pin_constraints_collection.remove_pinconstraint("non_existent_pin") is False

    # Test empty name
    with pytest.raises(ValueError, match="^pin name is required$"):
        pin_constraints_collection.remove_pinconstraint("")
    with pytest.raises(ValueError, match="^pin name is required$"):
        pin_constraints_collection.remove_pinconstraint(None)
