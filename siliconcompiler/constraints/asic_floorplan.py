from typing import Union, List, Tuple, Optional

from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, PerNode, Scope


class ASICAreaConstraint(BaseSchema):
    """
    Manages various area-related constraints for an ASIC design.

    This class provides a structured way to define and retrieve constraints
    related to the die area, core area, core margin, target density, and
    aspect ratio of the physical layout. These constraints are essential for
    automated floorplanning and physical design tasks.
    """

    def __init__(self):
        """Initializes the ASICAreaConstraint schema."""
        super().__init__()

        schema = EditableSchema(self)

        schema.insert(
            'diearea',
            Parameter(
                '[(float,float)]',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                unit='um',
                shorthelp="Constraint: die area outline",
                switch="-constraint_diearea <(float,float)>",
                example=["api: asic.set('constraint', 'diearea', (0, 0))"],
                schelp="""
                List of (x, y) points that define the outline of the physical
                design's die area. Simple rectangular areas can be defined with
                two points: one for the lower-left corner and one for the
                upper-right corner."""))

        schema.insert(
            'corearea',
            Parameter(
                '[(float,float)]',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                unit='um',
                shorthelp="Constraint: layout core area",
                switch="-constraint_corearea <(float,float)>",
                example=["api: asic.set('constraint', 'corearea', (0, 0))"],
                schelp="""
                List of (x, y) points that define the outline of the core area for the
                physical design. The core area is where standard cells are placed.
                Simple rectangular areas can be defined with two points: one for
                the lower-left corner and one for the upper-right corner."""))

        schema.insert(
            'coremargin',
            Parameter(
                'float',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                unit='um',
                shorthelp="Constraint: layout core margin",
                switch="-constraint_coremargin <float>",
                example=["api: asic.set('constraint', 'coremargin', 1)"],
                schelp="""
                Specifies the halo or margin between the die area outline and the
                core area. This is used for fully automated layout sizing and
                floorplanning to ensure adequate space for I/O pads and power rings."""))

        schema.insert(
            'density', Parameter(
                'float',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: layout density",
                switch="-constraint_density <float>",
                example=["api: asic.set('constraint', 'density', 30)"],
                schelp="""
                Target density for automated floorplanning, calculated based on the
                total area of standard cells after synthesis. This number is used
                when no explicit die or core area is supplied. Any number between
                1 and 100 is legal, but values above 50 may fail due to area or
                congestion issues during automated place and route."""))

        schema.insert(
            'aspectratio', Parameter(
                'float',
                pernode=PerNode.OPTIONAL,
                defvalue=1.0,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: layout aspect ratio",
                switch="-constraint_aspectratio <float>",
                example=["api: asic.set('constraint', 'aspectratio', 2.0)"],
                schelp="""
                Height-to-width ratio of the core area for automated floorplanning.
                Values below 0.1 and above 10 should be avoided as they will likely
                fail to converge during placement and routing. The ideal aspect
                ratio for most designs is 1.0. This value is only used when no
                diearea or corearea is supplied."""))

    def set_density(self,
                    density: float,
                    aspectratio: Optional[float] = None,
                    coremargin: Optional[float] = None,
                    step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the target layout density.

        This method validates the `density` input to ensure it's a number
        between 0 (exclusive) and 100 (inclusive). Optionally, it can also
        set the aspect ratio and core margin if provided.

        Args:
            density (float): The target density value (0 < density <= 100).
            aspectratio (float, optional): The aspect ratio to set. If provided,
                                           `set_aspectratio` will be called.
                                           Defaults to None.
            coremargin (float, optional): The core margin to set. If provided,
                                          `set_coremargin` will be called.
                                          Defaults to None.
            step (str, optional): The step in a workflow to associate this
                                  setting with. Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               associate this setting with.
                                               Defaults to None.

        Raises:
            TypeError: If `density` is not a number.
            ValueError: If `density` is not within the valid range (0, 100].

        Returns:
            list: A list of return values from the internal `set` calls.
        """
        if not isinstance(density, (int, float)):
            raise TypeError("density must be a number")

        if density <= 0.0 or density > 100.0:
            raise ValueError("density must be between (0, 100]")

        params = [
            self.set("density", density, step=step, index=index)
        ]
        if aspectratio is not None:
            params.append(self.set_aspectratio(aspectratio, step=step, index=index))
        if coremargin is not None:
            params.append(self.set_coremargin(coremargin, step=step, index=index))
        return params

    def get_density(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> float:
        """
        Retrieves the current target layout density.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            float: The current density value.
        """
        return self.get("density", step=step, index=index)

    def set_aspectratio(self,
                        aspectratio: float,
                        step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the layout aspect ratio.

        This method validates the `aspectratio` input to ensure it's a positive number.

        Args:
            aspectratio (float): The aspect ratio value (height / width).
                                 Must be a number greater than 0.0.
            step (str, optional): The step in a workflow to associate this
                                  setting with. Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               associate this setting with.
                                               Defaults to None.

        Raises:
            TypeError: If `aspectratio` is not a number.
            ValueError: If `aspectratio` is zero or negative.

        Returns:
            The return value from the internal `set` method call.
        """
        if not isinstance(aspectratio, (int, float)):
            raise TypeError("aspectratio must be a number")

        if aspectratio <= 0.0:
            raise ValueError("aspectratio cannot be zero or negative")

        return self.set("aspectratio", aspectratio, step=step, index=index)

    def get_aspectratio(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> float:
        """
        Retrieves the current layout aspect ratio.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            float: The current aspect ratio value.
        """
        return self.get("aspectratio", step=step, index=index)

    def set_coremargin(self,
                       coremargin: float,
                       step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the core margin.

        This method validates the `coremargin` input to ensure it's a non-negative number.

        Args:
            coremargin (float): The core margin value in schema units (e.g., um).
                                Must be a number greater than or equal to 0.0.
            step (str, optional): The step in a workflow to associate this
                                  setting with. Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               associate this setting with.
                                               Defaults to None.

        Raises:
            TypeError: If `coremargin` is not a number.
            ValueError: If `coremargin` is negative.

        Returns:
            The return value from the internal `set` method call.
        """
        if not isinstance(coremargin, (int, float)):
            raise TypeError("coremargin must be a number")

        if coremargin < 0.0:
            raise ValueError("coremargin cannot be negative")

        return self.set("coremargin", coremargin, step=step, index=index)

    def get_coremargin(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> float:
        """
        Retrieves the current core margin.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            float: The current core margin value.
        """
        return self.get("coremargin", step=step, index=index)

    def set_diearea_rectangle(self,
                              height: float,
                              width: float,
                              coremargin: Optional[Union[float, Tuple[float, float]]] = None,
                              step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the die area as a rectangle with its bottom-left corner at (0,0).

        Optionally, it can also set the core area as a rectangle based on
        the provided core margin.

        Args:
            height (float): The height of the rectangular die area. Must be > 0.
            width (float): The width of the rectangular die area. Must be > 0.
            coremargin (Union[float, Tuple[float, float]], optional):
                        The margin for the core area. Can be a single float
                        (uniform margin) or a tuple of two floats (x, y margins).
                        If provided, `set_corearea_rectangle` will be called.
                        Defaults to None.
            step (str, optional): The step in a workflow to associate this
                                  setting with. Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               associate this setting with.
                                               Defaults to None.

        Raises:
            TypeError: If `height` or `width` are not numbers.
            ValueError: If `height` or `width` are zero or negative.

        Returns:
            list: A list of return values from the internal `set` calls.
        """
        if not isinstance(height, (int, float)):
            raise TypeError("height must be a number")
        if not isinstance(width, (int, float)):
            raise TypeError("width must be a number")

        if height <= 0.0:
            raise ValueError("height must be greater than zero")

        if width <= 0.0:
            raise ValueError("width must be greater than zero")

        params = [
            self.set_diearea([(0, 0), (width, height)], step=step, index=index)
        ]
        if coremargin is not None:
            params.append(self.set_corearea_rectangle(
                height, width, coremargin, step=step, index=index))
        return params

    def set_corearea_rectangle(self,
                               dieheight: float,
                               diewidth: float,
                               coremargin: Union[float, Tuple[float, float]],
                               step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the core area as a rectangle within a die area, based on margins.

        The core area is calculated by subtracting the margins from the die
        dimensions. Margins can be uniform (single float) or specified
        separately for x and y.

        Args:
            dieheight (float): The height of the die area. Must be > 0.
            diewidth (float): The width of the die area. Must be > 0.
            coremargin (Union[float, Tuple[float, float]]): The margin(s) to apply.
                        - If a float, it's applied uniformly to all four sides.
                        - If a tuple of two floats, it's (x_margin, y_margin).
            step (str, optional): The step in a workflow to associate this
                                  setting with. Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               associate this setting with.
                                               Defaults to None.

        Raises:
            TypeError: If `dieheight`/`diewidth` are not numbers, or if
                       `coremargin` is not a number or a tuple of two numbers.
            ValueError: If dimensions are invalid or margins are too large.

        Returns:
            The return value from the internal `set_corearea` method call.
        """
        if not isinstance(dieheight, (int, float)):
            raise TypeError("height must be a number")
        if not isinstance(diewidth, (int, float)):
            raise TypeError("width must be a number")

        if dieheight <= 0.0:
            raise ValueError("height must be greater than zero")

        if diewidth <= 0.0:
            raise ValueError("width must be greater than zero")

        if isinstance(coremargin, (int, float)):
            coremargin = (coremargin, coremargin)
        elif not isinstance(coremargin, (list, tuple)):
            raise TypeError("coremargin must be a number or a tuple of two numbers")
        else:
            if len(coremargin) != 2:
                raise ValueError("coremargin must be a number or a tuple of two numbers")

        xmargin, ymargin = coremargin

        if xmargin < 0:
            raise ValueError("x margin cannot be negative")

        if ymargin < 0:
            raise ValueError("y margin cannot be negative")

        if 2 * xmargin >= diewidth:
            raise ValueError("x margin is greater than or equal to the die width")

        if 2 * ymargin >= dieheight:
            raise ValueError("y margin is greater than or equal to the die height")

        return self.set_corearea([
            (xmargin, ymargin),
            (diewidth - xmargin, dieheight - ymargin)], step=step, index=index)

    def set_diearea(self,
                    points: List[Tuple[float, float]],
                    step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the die area using a list of points defining its boundary.

        Args:
            points (List[Tuple[float, float]]): A list of (x, y) tuples representing
                                                the coordinates that define the die area.
            step (str, optional): The step in a workflow to associate this
                                  setting with. Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               associate this setting with.
                                               Defaults to None.

        Returns:
            The return value from the internal `set` method call.
        """
        return self.set("diearea", points, step=step, index=index)

    def get_diearea(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> List[Tuple[float, float]]:
        """
        Retrieves the current die area definition.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            List[Tuple[float, float]]: A list of (x, y) tuples representing
                                       the coordinates that define the die area.
        """
        return self.get("diearea", step=step, index=index)

    def set_corearea(self,
                     points: List[Tuple[float, float]],
                     step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the core area using a list of points defining its boundary.

        Args:
            points (List[Tuple[float, float]]): A list of (x, y) tuples representing
                                                the coordinates that define the core area.
            step (str, optional): The step in a workflow to associate this
                                  setting with. Defaults to None.
            index (Union[str, int], optional): An index or identifier within a step.
                                               Defaults to None.

        Returns:
            The return value from the internal `set` method call.
        """
        return self.set("corearea", points, step=step, index=index)

    def get_corearea(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> List[Tuple[float, float]]:
        """
        Retrieves the current core area definition.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            List[Tuple[float, float]]: A list of (x, y) tuples representing
                                       the coordinates that define the core area.
        """
        return self.get("corearea", step=step, index=index)

    def calc_diearea(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> float:
        '''Calculates the area of a rectilinear die.

        Uses the shoelace formula to calculate the design area from the (x,y)
        point tuples in the 'diearea' parameter. If 'diearea' contains only
        two points, they are treated as the lower-left and upper-right corners
        of a rectangle.
        (Ref: https://en.wikipedia.org/wiki/Shoelace_formula)

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (str, optional): The index within a step to retrieve from.
                                   Defaults to None.

        Returns:
            float: The calculated design area in square schema units.

        Examples:
            >>> # In the context of a 'pdk' object
            >>> area = asic.get('constraint').calc_diearea()
        '''
        vertices = self.get('diearea', step=step, index=index)

        if not vertices:
            return 0.0

        if len(vertices) == 2:
            width = vertices[1][0] - vertices[0][0]
            height = vertices[1][1] - vertices[0][1]
            area = width * height
        else:
            area = 0.0
            for i in range(len(vertices)):
                j = (i + 1) % len(vertices)
                area += vertices[i][0] * vertices[j][1]
                area -= vertices[j][0] * vertices[i][1]
            area = abs(area) / 2.0

        return area
