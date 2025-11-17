from typing import Union, Tuple, Optional

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, \
    PerNode, Scope


class ASICPinConstraint(NamedSchema):
    """
    Represents a single ASIC pin constraint within the design configuration.

    This class defines various constraints that can be applied to an individual
    ASIC pin, such as its placement, dimensions (width, length), shape,
    metal layer, and its relative position on the chip's side.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)

        schema.insert(
            'placement',
            Parameter(
                '(float,float)',
                unit='um',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pin placement",
                example=["api: asic.set('constraint', 'pin', 'nreset', 'placement', (2.0, 3.0))"],
                help="""
                Placement location of a named pin, specified as a (x,y) tuple of
                floats with respect to the lower left corner of the substrate. The location
                refers to the center of the pin. The 'placement' parameter
                is a goal/intent, not an exact specification. The layout system
                may adjust sizes to meet competing goals such as manufacturing design
                rules and grid placement guidelines."""))

        schema.insert(
            'width',
            Parameter(
                'float',
                unit='um',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pin width",
                example=["api: asic.set('constraint', 'pin', 'nreset', 'width', 1.0)"],
                help="""
                Pin width constraint.  Package pin width is the lateral
                (side-to-side) thickness of a pin on a physical component.
                This parameter represents goal/intent, not an exact
                specification. The layout system may adjust dimensions to meet
                competing goals such as manufacturing design rules and grid placement
                guidelines."""))

        schema.insert(
            'length',
            Parameter(
                'float',
                unit='um',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pin length",
                example=["api: asic.set('constraint', 'pin', 'nreset', 'length', 1.0)"],
                help="""
                Pin length constraint.  Package pin length refers to the
                length of the electrical pins extending out from (or into)
                a component. This parameter represents goal/intent, not an exact
                specification. The layout system may adjust dimensions to meet
                competing goals such as manufacturing design rules and grid placement
                guidelines."""))

        schema.insert(
            'shape',
            Parameter(
                '<circle,rectangle,square,hexagon,octagon,oval,pill,polygon>',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pin shape",
                example=["api: asic.set('constraint', 'pin', 'nreset', 'shape', 'circle')"],
                help="""
                Pin shape constraint specified on a per pin basis. In 3D design systems,
                the pin shape represents the cross section of the pin in the direction
                orthogonal to the signal flow direction. The 'pill' (aka stadium) shape,
                is rectangle with semicircles at a pair of opposite sides. The other
                pin shapes represent common geometric shape definitions."""))

        schema.insert(
            'layer',
            Parameter(
                'str',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pin layer",
                example=["api: asic.set('constraint', 'pin', 'nreset', 'layer', 'm4')"],
                help="""
                Pin metal layer constraint specified on a per pin basis.
                Metal names should either be the PDK specific metal stack name or
                an integer with '1' being the lowest routing layer."""))

        schema.insert(
            'side',
            Parameter(
                'int',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pin side",
                example=["api: asic.set('constraint', 'pin', 'nreset', 'side', 1)"],
                help="""
                Side of block where the named pin should be placed. Sides are
                enumerated as integers with '1' being the lower left side,
                with the side index incremented on right turn in a clock wise
                fashion. In case of conflict between 'lower' and 'left',
                'left' has precedence. The side option and order option are
                orthogonal to the placement option."""))

        schema.insert(
            'order',
            Parameter(
                'int',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pin order",
                example=["api: asic.set('constraint', 'pin', 'nreset', 'order', 1)"],
                help="""
                The relative position of the named pin in a vector of pins
                on the side specified by the 'side' option. Pin order counting
                is done clockwise. If multiple pins on the same side have the
                same order number, the actual order is at the discretion of the
                tool."""))

    def set_width(self, width: float,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the width constraint for the pin.

        Args:
            width (float): The desired width of the pin in micrometers (um).
                           Must be a positive numeric value.
            step (str, optional): step name.
            index (str, optional): index name.

        Raises:
            TypeError: If `width` is not an int or float.
            ValueError: If `width` is not a positive value.
        """
        if not isinstance(width, (int, float)):
            raise TypeError("width must be a number")
        if width <= 0:
            raise ValueError("width must be a positive value")
        return self.set("width", width, step=step, index=index)

    def get_width(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> float:
        """
        Retrieves the current width constraint of the pin.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            float: The width of the pin in micrometers (um).
        """
        return self.get("width", step=step, index=index)

    def set_length(self, length: float,
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the length constraint for the pin.

        Args:
            length (float): The desired length of the pin in micrometers (um).
                            Must be a positive numeric value.
            step (str, optional): step name.
            index (str, optional): index name.

        Raises:
            TypeError: If `length` is not an int or float.
            ValueError: If `length` is not a positive value.
        """
        if not isinstance(length, (int, float)):
            raise TypeError("length must be a number")
        if length <= 0:
            raise ValueError("length must be a positive value")
        return self.set("length", length, step=step, index=index)

    def get_length(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> float:
        """
        Retrieves the current length constraint of the pin.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            float: The length of the pin in micrometers (um).
        """
        return self.get("length", step=step, index=index)

    def set_placement(self, x: float, y: float,
                      step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the placement constraint for the pin.

        Args:
            x (float): The X-coordinate for the pin's center in micrometers (um)
                       relative to the lower-left corner of the substrate.
            y (float): The Y-coordinate for the pin's center in micrometers (um)
                       relative to the lower-left corner of the substrate.
            step (str, optional): step name.
            index (str, optional): index name.

        Raises:
            TypeError: If `x` or `y` is not an int or float.
        """
        if not isinstance(x, (int, float)):
            raise TypeError("x must be a number")
        if not isinstance(y, (int, float)):
            raise TypeError("y must be a number")
        return self.set("placement", (x, y), step=step, index=index)

    def get_placement(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> Tuple[float, float]:
        """
        Retrieves the current placement constraint of the pin.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            Tuple[float, float]: A tuple (x, y) representing the pin's center
                                 coordinates in micrometers (um).
        """
        return self.get("placement", step=step, index=index)

    def set_shape(self, shape: str,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the shape constraint for the pin.

        Args:
            shape (str): The desired shape of the pin. Valid values include
                         'circle', 'rectangle', 'square', 'hexagon', 'octagon',
                         'oval', 'pill', or 'polygon'.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("shape", shape, step=step, index=index)

    def get_shape(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> str:
        """
        Retrieves the current shape constraint of the pin.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            str: The shape of the pin.
        """
        return self.get("shape", step=step, index=index)

    def set_layer(self, layer: str,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the metal layer constraint for the pin.

        Args:
            layer (str): The name of the metal layer for the pin. This can be
                         a PDK-specific metal stack name (e.g., 'm4') or an
                         integer (e.g., '1' for the lowest routing layer).
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("layer", layer, step=step, index=index)

    def get_layer(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> str:
        """
        Retrieves the current metal layer constraint of the pin.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            str: The metal layer of the pin.
        """
        return self.get("layer", step=step, index=index)

    def set_side(self, side: Union[int, str],
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the side constraint for the pin, indicating where it should be placed.

        Args:
            side (Union[int, str]): The side of the block where the pin should be placed.
                                    Can be an integer or a string ('left', 'west', 'top',
                                    'north', 'right', 'east', 'bottom', 'south').
            step (str, optional): step name.
            index (str, optional): index name.

        Raises:
            TypeError: If `side` is not an int or string.
            ValueError: If `side` is an unrecognized string value or a non-positive integer.
        """
        if isinstance(side, str):
            side = side.lower()
            if side in ("left", "west"):
                side = 1
            elif side in ("top", "north"):
                side = 2
            elif side in ("right", "east"):
                side = 3
            elif side in ("bottom", "south"):
                side = 4
            else:
                raise ValueError(f"{side} is a not a recognized side")

        if not isinstance(side, int):
            raise TypeError("side must be an integer")

        if side <= 0:
            raise ValueError("side must be a positive integer")

        return self.set("side", side, step=step, index=index)

    def get_side(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> int:
        """
        Retrieves the current side constraint of the pin.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            int: The integer representation of the side (1 for lower left, etc.).
        """
        return self.get("side", step=step, index=index)

    def set_order(self, order: int,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the relative order constraint for the pin on its assigned side.

        Args:
            order (int): The relative position of the pin in a vector of pins
                         on the specified side. Counting is done clockwise.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("order", order, step=step, index=index)

    def get_order(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> int:
        """
        Retrieves the current order constraint of the pin.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            int: The relative order of the pin on its side.
        """
        return self.get("order", step=step, index=index)


class ASICPinConstraints(BaseSchema):
    """
    Manages a collection of ASIC pin constraints.

    This class provides methods to add, retrieve, create, and remove
    individual :class:`ASICPinConstraint` objects, allowing for organized
    management of pin-level placement and property constraints.
    """

    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.insert("default", ASICPinConstraint())

    def add_pinconstraint(self, pin: ASICPinConstraint):
        """
        Adds a pin constraint to the design configuration.

        This method incorporates a new or updated pin constraint into the system's
        configuration. If a constraint with the same name already exists, it will
        be overwritten (`clobber=True`).

        Args:
            pin: The :class:`ASICPinConstraint` object representing the pin constraint to add.
                 This object must have a valid name defined via its `name()` method.

        Raises:
            TypeError: If the provided `pin` argument is not an instance of
                       :class:`ASICPinConstraint`.
            ValueError: If the `pin` object's `name()` method returns None, indicating
                        that the pin constraint does not have a defined name.
        """
        if not isinstance(pin, ASICPinConstraint):
            raise TypeError("pin must be a pin constraint object")

        if pin.name is None:
            raise ValueError("pin constraint must have a name")

        EditableSchema(self).insert(pin.name, pin, clobber=True)

    def get_pinconstraint(self, pin: Optional[str] = None):
        """
        Retrieves one or all pin constraints from the configuration.

        This method provides flexibility to fetch either a specific pin constraint
        by its name or a collection of all currently defined constraints.

        Args:
            pin (str, optional): The name (string) of the specific pin constraint to retrieve.
                                 If this argument is omitted or set to None, the method will return
                                 a dictionary containing all available pin constraints.

        Returns:
            If `pin` is provided: The :class:`ASICPinConstraint` object corresponding
                to the specified pin constraint name.
            If `pin` is None: A dictionary where keys are pin constraint names (str) and
                values are their respective :class:`ASICPinConstraint` objects.

        Raises:
            LookupError: If a specific `pin` name is provided but no pin constraint with
                         that name is found in the configuration.
        """
        if pin is None:
            pins = {}
            for pin in self.getkeys():
                pins[pin] = self.get(pin, field="schema")
            return pins

        if not self.valid(pin):
            raise LookupError(f"{pin} is not defined")
        return self.get(pin, field="schema")

    def make_pinconstraint(self, pin: str) -> ASICPinConstraint:
        """
        Creates and adds a new pin constraint with the specified name.

        This method initializes a new :class:`ASICPinConstraint` object with the given
        name and immediately adds it to the design configuration. It ensures that
        a constraint with the same name does not already exist, preventing accidental
        overwrites.

        Args:
            pin (str): The name for the new pin constraint. This name must be
                       a non-empty string and unique within the current configuration.

        Returns:
            :class:ASICPinConstraint: The newly created :class:`ASICPinConstraint` object.

        Raises:
            ValueError: If the provided `pin` name is empty or None.
            LookupError: If a pin constraint with the specified `pin` name already exists
                         in the configuration.
        """
        if not pin:
            raise ValueError("pin name is required")

        if self.valid(pin):
            raise LookupError(f"{pin} constraint already exists")

        constraint = ASICPinConstraint(pin)
        self.add_pinconstraint(constraint)
        return constraint

    def copy_pinconstraint(self, pin: str, name: str, insert: bool = True) -> ASICPinConstraint:
        """
        Copies an existing pin constraint, renames it, and optionally adds it to the design.

        This method retrieves the pin constraint identified by ``pin``, creates a
        deep copy of it, and renames the copy to ``name``. If ``insert`` is True,
        the new constraint is immediately added to the configuration.

        Args:
            pin (str): The name of the existing pin constraint to be copied.
            name (str): The name to assign to the new copied constraint.
            insert (bool, optional): Whether to add the newly created constraint
                to the configuration. Defaults to True.

        Returns:
            ASICPinConstraint: The newly created copy of the pin constraint.

        Raises:
            LookupError: If the source pin constraint specified by ``pin`` does not exist.
        """
        constraint = EditableSchema(self.get_pinconstraint(pin)).copy()
        EditableSchema(constraint).rename(name)
        if insert:
            if self.valid(name):
                raise ValueError(f"{name} already exists")
            self.add_pinconstraint(constraint)
        return constraint

    def remove_pinconstraint(self, pin: str) -> bool:
        """
        Removes a pin constraint from the design configuration.

        This method deletes the specified pin constraint from the system's
        configuration.

        Args:
            pin (str): The name of the pin constraint to remove.
                       This name must be a non-empty string.

        Returns:
            bool: True if the pin constraint was successfully removed, False if no
                  pin constraint with the given name was found.

        Raises:
            ValueError: If the provided `pin` name is empty or None.
        """
        if not pin:
            raise ValueError("pin name is required")

        if not self.valid(pin):
            return False

        EditableSchema(self).remove(pin)
        return True
