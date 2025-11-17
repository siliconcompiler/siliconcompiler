from typing import Tuple, Union, Optional

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, \
    PerNode, Scope


class ASICComponentConstraint(NamedSchema):
    """
    Represents a single ASIC component constraint within the design configuration.

    This class defines various constraints that can be applied to an individual
    ASIC component instance, such as its placement, part name (cell name),
    keepout halo, and rotation.
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
                shorthelp="Constraint: component placement",
                example=["api: asic.set('constraint', 'component', 'i0', 'placement', (2.0, 3.0))"],
                schelp="""
                Placement location of a named instance, specified as a (x, y) tuple of
                floats. The location refers to the distance from the substrate origin to
                the anchor point of the placed component, defined by
                the :keypath:`datasheet,package,<name>,anchor` parameter."""))

        schema.insert(
            'partname',
            Parameter(
                'str',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: component part name",
                example=["api: asic.set('constraint', 'component', 'i0', 'partname', 'filler_x1')"],
                schelp="""
                Name of the model, type, or variant of the placed component. In the chip
                design domain, 'partname' is synonymous to 'cellname' or 'cell'. The
                'partname' is required for instances that are not represented within
                the design netlist (ie. physical only cells)."""))

        schema.insert(
            'halo',
            Parameter(
                '(float,float)',
                unit='um',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: component halo",
                switch="-constraint_component_halo 'inst <(float,float)>'",
                example=[
                    "cli: -constraint_component_halo 'i0 (1,1)'",
                    "api: asic.set('constraint', 'component', 'i0', 'halo', (1, 1))"],
                schelp="""
                Placement keepout halo around the named component, specified as a
                (horizontal, vertical) tuple."""))

        rotations = ['R0', 'R90', 'R180', 'R270',
                     'MX', 'MX_R90', 'MX_R180', 'MX_R270',
                     'MY', 'MY_R90', 'MY_R180', 'MY_R270',
                     'MZ', 'MZ_R90', 'MZ_R180', 'MZ_R270',
                     'MZ_MX', 'MZ_MX_R90', 'MZ_MX_R180', 'MZ_MX_R270',
                     'MZ_MY', 'MZ_MY_R90', 'MZ_MY_R180', 'MZ_MY_R270']
        schema.insert(
            'rotation',
            Parameter(
                f'<{",".join(rotations)}>',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                defvalue='R0',
                shorthelp="Constraint: component rotation",
                switch="-constraint_component_rotation 'inst <str>'",
                example=[
                    "cli: -constraint_component_rotation 'i0 R90'",
                    "api: asic.set('constraint', 'component', 'i0', 'rotation', 'R90')"],
                schelp="""
                Placement rotation of the component. Components are always placed
                such that the lower left corner of the cell is at the anchor point
                (0,0) after any orientation. The MZ type rotations are for 3D design and
                typically not supported by 2D layout systems like traditional
                ASIC tools. For graphical illustrations of the rotation types, see
                the SiliconCompiler documentation.

                * ``R0``: North orientation (no rotation)
                * ``R90``: West orientation, rotate 90 deg counter clockwise (ccw)
                * ``R180``: South orientation, rotate 180 deg counter ccw
                * ``R270``: East orientation, rotate 180 deg counter ccw

                * ``MX``, ``MY_R180``: Flip on x-axis
                * ``MX_R90``, ``MY_R270``: Flip on x-axis and rotate 90 deg ccw
                * ``MX_R180``, ``MY``: Flip on x-axis and rotate 180 deg ccw
                * ``MX_R270``, ``MY_R90``: Flip on x-axis and rotate 270 deg ccw

                * ``MZ``: Reverse component metal stack
                * ``MZ_R90``: Reverse metal stack and rotate 90 deg ccw
                * ``MZ_R180``: Reverse metal stack and rotate 180 deg ccw
                * ``MZ_R270``: Reverse  metal stack and rotate 270 deg ccw
                * ``MZ_MX``, ``MZ_MY_R180``: Reverse metal stack and flip on x-axis
                * ``MZ_MX_R90``, ``MZ_MY_R270``: Reverse metal stack, flip on x-axis, and
                    rotate 90 deg ccw
                * ``MZ_MX_R180``, ``MZ_MY``: Reverse metal stack, flip on x-axis, and rotate
                    180 deg ccw
                * ``MZ_MX_R270``, ``MZ_MY_R90``: Reverse metal stack, flip on x-axis and rotate
                    270 deg ccw
                    """))

    def set_placement(self, x: float, y: float,
                      step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the placement constraint for the component.

        Args:
            x (float): The X-coordinate for the component's anchor point in
                       micrometers (um) relative to the substrate origin.
            y (float): The Y-coordinate for the component's anchor point in
                       micrometers (um) relative to the substrate origin.
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
        Retrieves the current placement constraint of the component.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            Tuple[float, float]: A tuple (x, y) representing the component's
                                 anchor point coordinates in micrometers (um).
        """
        return self.get("placement", step=step, index=index)

    def set_partname(self, name: str,
                     step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the part name (cell name) constraint for the component.

        Args:
            name (str): The name of the model, type, or variant of the placed component.
                        This is required for instances not in the design netlist.
            step (str, optional): step name.
            index (str, optional): index name.

        Raises:
            ValueError: If `name` is an empty string or None.
        """
        if not name:
            raise ValueError("a partname is required")
        return self.set("partname", name, step=step, index=index)

    def get_partname(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> str:
        """
        Retrieves the current part name (cell name) constraint of the component.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            str: The part name of the component.
        """
        return self.get("partname", step=step, index=index)

    def set_halo(self, x: float, y: float,
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the placement keepout halo constraint around the component.

        Args:
            x (float): The horizontal extent of the halo in micrometers (um).
                       Must be a non-negative numeric value.
            y (float): The vertical extent of the halo in micrometers (um).
                       Must be a non-negative numeric value.
            step (str, optional): step name.
            index (str, optional): index name.

        Raises:
            TypeError: If `x` or `y` is not an int or float.
            ValueError: If `x` or `y` is a negative value.
        """
        if not isinstance(x, (int, float)):
            raise TypeError("x must be a number")
        if not isinstance(y, (int, float)):
            raise TypeError("y must be a number")
        if x < 0:
            raise ValueError("x must be a positive number")
        if y < 0:
            raise ValueError("y must be a positive number")
        return self.set("halo", (x, y), step=step, index=index)

    def get_halo(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> Tuple[float, float]:
        """
        Retrieves the current placement keepout halo constraint of the component.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            Tuple[float, float]: A tuple (horizontal, vertical) representing the
                                 halo extents in micrometers (um).
        """
        return self.get("halo", step=step, index=index)

    def set_rotation(self, rotation: str,
                     step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the rotation constraint for the component.

        Args:
            rotation (str): The desired rotation of the component. Valid values
                            are defined by the `rotations` list schema help
                            (e.g., 'R0', 'R90', 'MX', 'MZ_R90').
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("rotation", rotation, step=step, index=index)

    def get_rotation(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> str:
        """
        Retrieves the current rotation constraint of the component.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            str: The rotation of the component.
        """
        return self.get("rotation", step=step, index=index)


class ASICComponentConstraints(BaseSchema):
    """
    Manages a collection of ASIC component constraints.

    This class provides methods to add, retrieve, create, and remove
    individual :class:`ASICComponentConstraint` objects, allowing for organized
    management of component-level placement and property constraints.
    """
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.insert("default", ASICComponentConstraint())

    def add_component(self, component: ASICComponentConstraint):
        """
        Adds a component constraint to the design configuration.

        This method incorporates a new or updated component constraint into the system's
        configuration. If a constraint with the same name already exists, it will
        be overwritten (`clobber=True`).

        Args:
            component: The :class:`ASICComponentConstraint` object representing the component
                       constraint to add. This object must have a valid name defined
                       via its `name()` method.

        Raises:
            TypeError: If the provided `component` argument is not an instance of
                       `ASICComponentConstraint`.
            ValueError: If the `component` object's `name()` method returns None,
                        indicating that the component constraint does not have a defined name.
        """
        if not isinstance(component, ASICComponentConstraint):
            raise TypeError("component must be a component constraint object")

        if component.name is None:
            raise ValueError("component constraint must have a name")

        EditableSchema(self).insert(component.name, component, clobber=True)

    def get_component(self, component: Optional[str] = None):
        """
        Retrieves one or all component constraints from the configuration.

        This method provides flexibility to fetch either a specific component constraint
        by its name or a collection of all currently defined constraints.

        Args:
            component (str, optional): The name (string) of the specific component
                                       constraint to retrieve. If this argument is
                                       omitted or set to None, the method will return
                                       a dictionary containing all available component constraints.

        Returns:
            If `component` is provided: The :class:`ASICComponentConstraint` object
                corresponding to the specified component name.
            If `component` is None: A dictionary where keys are component names (str) and
                values are their respective :class:`ASICComponentConstraint` objects.

        Raises:
            LookupError: If a specific `component` name is provided but no component
                         constraint with that name is found in the configuration.
        """
        if component is None:
            components = {}
            for component in self.getkeys():
                components[component] = self.get(component, field="schema")
            return components

        if not self.valid(component):
            raise LookupError(f"{component} is not defined")
        return self.get(component, field="schema")

    def make_component(self, component: str) -> ASICComponentConstraint:
        """
        Creates and adds a new component constraint with the specified name.

        This method initializes a new :class:`ASICComponentConstraint` object with the given
        name and immediately adds it to the design configuration. It ensures that
        a constraint with the same name does not already exist, preventing accidental
        overwrites.

        Args:
            component (str): The name for the new component constraint. This name must be
                             a non-empty string and unique within the current configuration.

        Returns:
            ASICComponentConstraint: The newly created :class:`ASICComponentConstraint` object.

        Raises:
            ValueError: If the provided `component` name is empty or None.
            LookupError: If a component constraint with the specified `component` name
                         already exists in the configuration.
        """
        if not component:
            raise ValueError("component name is required")

        if self.valid(component):
            raise LookupError(f"{component} constraint already exists")

        constraint = ASICComponentConstraint(component)
        self.add_component(constraint)
        return constraint

    def copy_component(self, component: str, name: str, insert: bool = True) \
            -> ASICComponentConstraint:
        """
        Copies an existing component constraint, renames it, and optionally adds it to the design.

        This method retrieves the component constraint identified by ``component``, creates a
        deep copy of it, and renames the copy to ``name``. If ``insert`` is True,
        the new constraint is immediately added to the configuration.

        Args:
            component (str): The name of the existing component constraint to be copied.
            name (str): The name to assign to the new copied constraint.
            insert (bool, optional): Whether to add the newly created constraint
                to the configuration. Defaults to True.

        Returns:
            ASICComponentConstraint: The newly created copy of the component constraint.

        Raises:
            LookupError: If the source component constraint specified by ``component`` does not
                         exist.
        """
        constraint = EditableSchema(self.get_component(component)).copy()
        EditableSchema(constraint).rename(name)
        if insert:
            if self.valid(name):
                raise ValueError(f"{name} already exists")
            self.add_component(constraint)
        return constraint

    def remove_component(self, component: str) -> bool:
        """
        Removes a component constraint from the design configuration.

        This method deletes the specified component constraint from the system's
        configuration.

        Args:
            component (str): The name of the component constraint to remove.
                             This name must be a non-empty string.

        Returns:
            bool: True if the component constraint was successfully removed, False if no
                  component constraint with the given name was found.

        Raises:
            ValueError: If the provided `component` name is empty or None.
        """
        if not component:
            raise ValueError("component name is required")

        if not self.valid(component):
            return False

        EditableSchema(self).remove(component)
        return True
