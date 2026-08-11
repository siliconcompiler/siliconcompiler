import math

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
                'float<0..>',
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
                'float<0.0..100.0>',
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
                'float<0.0..>',
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

    @staticmethod
    def _calc_boundingbox(points: List[Tuple[float, float]]) \
            -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Computes the bounding box of a list of (x, y) points.

        Args:
            points (List[Tuple[float, float]]): The points to bound. An empty
                                                list yields a zero-size box at
                                                the origin.

        Returns:
            Tuple[Tuple[float, float], Tuple[float, float]]: The lower-left and
            upper-right coordinates of the bounding box.
        """
        if not points:
            return ((0.0, 0.0), (0.0, 0.0))

        min_x = min(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_x = max(point[0] for point in points)
        max_y = max(point[1] for point in points)

        return ((min_x, min_y), (max_x, max_y))

    @staticmethod
    def _calc_size(boundingbox: Tuple[Tuple[float, float], Tuple[float, float]]) \
            -> Tuple[float, float]:
        """
        Computes the (width, height) of a bounding box.

        Args:
            boundingbox (Tuple[Tuple[float, float], Tuple[float, float]]): The
                lower-left and upper-right coordinates of the bounding box.

        Returns:
            Tuple[float, float]: The width and height of the bounding box.
        """
        (min_x, min_y), (max_x, max_y) = boundingbox
        return (max_x - min_x, max_y - min_y)

    def get_dieboundingbox(self, step: Optional[str] = None,
                           index: Optional[Union[str, int]] = None) \
            -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Retrieves the bounding box of the die area.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            Tuple[Tuple[float, float], Tuple[float, float]]: A tuple containing the
            lower-left and upper-right coordinates of the die area's bounding box.
        """
        return self._calc_boundingbox(self.get_diearea(step=step, index=index))

    def get_diesize(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> \
            Tuple[float, float]:
        """
        Retrieves the size (width and height) of the die area.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            Tuple[float, float]: A tuple containing the width and height of the die area.
        """
        return self._calc_size(self.get_dieboundingbox(step=step, index=index))

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

    def get_coreboundingbox(self, step: Optional[str] = None,
                            index: Optional[Union[str, int]] = None) \
            -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Retrieves the bounding box of the core area.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            Tuple[Tuple[float, float], Tuple[float, float]]: A tuple containing the
            lower-left and upper-right coordinates of the core area's bounding box.
        """
        return self._calc_boundingbox(self.get_corearea(step=step, index=index))

    def get_coresize(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> \
            Tuple[float, float]:
        """
        Retrieves the size (width and height) of the core area.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Returns:
            Tuple[float, float]: A tuple containing the width and height of the core area.
        """
        return self._calc_size(self.get_coreboundingbox(step=step, index=index))

    @staticmethod
    def _calc_polygon_vertices(points: List[Tuple[float, float]]) \
            -> List[Tuple[float, float]]:
        """
        Reduces an outline to the vertices that give it its shape.

        Repeated points have no edge direction, and a point in the middle of a
        straight edge does not turn the outline, so neither survives.

        Args:
            points (List[Tuple[float, float]]): The outline points, without a
                                                repeated closing point.

        Returns:
            List[Tuple[float, float]]: The corners of the outline, in the order
                                       they were given.
        """
        unique = []
        for point in points:
            point = tuple(point)
            if not unique or point != unique[-1]:
                unique.append(point)
        if len(unique) > 1 and unique[0] == unique[-1]:
            unique.pop()

        if len(unique) < 3:
            return unique

        corners = []
        for index, (x, y) in enumerate(unique):
            x0, y0 = unique[index - 1]
            x1, y1 = unique[(index + 1) % len(unique)]

            # cross product of the incoming and outgoing edges
            if (x - x0) * (y1 - y) != (y - y0) * (x1 - x):
                corners.append((x, y))

        return corners

    @staticmethod
    def _calc_signed_area(points: List[Tuple[float, float]]) -> float:
        """
        Computes the signed area of a closed polygon with the shoelace formula.

        Args:
            points (List[Tuple[float, float]]): The polygon vertices, without a
                                                repeated closing vertex.

        Returns:
            float: The signed area. Positive for a counter-clockwise outline and
                   negative for a clockwise one.
        """
        area = 0.0
        for index, (x0, y0) in enumerate(points):
            x1, y1 = points[(index + 1) % len(points)]
            area += x0 * y1 - x1 * y0
        return area / 2.0

    @classmethod
    def _calc_offset_polygon(cls, points: List[Tuple[float, float]], offset: float) \
            -> List[Tuple[float, float]]:
        """
        Offsets a closed polygon by sliding every edge along its inward normal.

        Each vertex of the result is the intersection of its two offset edges, so
        a rectilinear outline stays rectilinear and concave corners are offset
        into the shape rather than away from it. Mitering a concave corner keeps
        the result inside the outline it was offset from, which is what matters
        for a core area, but it does trim slightly more than the offset distance
        right at that corner.

        Args:
            points (List[Tuple[float, float]]): The polygon vertices, optionally
                                                repeating the first vertex to
                                                close the outline.
            offset (float): The distance to move each edge. A positive offset
                            shrinks the polygon and a negative one grows it.

        Raises:
            ValueError: If the outline is not a polygon, or if the offset
                        collapses or inverts it.

        Returns:
            List[Tuple[float, float]]: The offset polygon, closed the same way
                                       the input was.
        """
        closed = len(points) > 1 and tuple(points[0]) == tuple(points[-1])
        vertices = cls._calc_polygon_vertices(points[:-1] if closed else points)

        if len(vertices) < 3:
            raise ValueError("outline must have at least three vertices")

        area = cls._calc_signed_area(vertices)
        if area == 0.0:
            raise ValueError("outline does not enclose an area")

        # A counter-clockwise outline keeps its interior to the left of each edge.
        winding = 1.0 if area > 0.0 else -1.0

        # Slide every edge along its inward normal, keeping it as a point plus a
        # unit direction so the offset vertices can be solved for below.
        edges = []
        for index, (x0, y0) in enumerate(vertices):
            x1, y1 = vertices[(index + 1) % len(vertices)]
            dx, dy = x1 - x0, y1 - y0
            length = math.hypot(dx, dy)
            dx, dy = dx / length, dy / length
            edges.append((x0 - offset * winding * dy, y0 + offset * winding * dx, dx, dy))

        # Every vertex becomes the intersection of the two edges that meet there.
        offset_vertices = []
        for index, (qx, qy, vx, vy) in enumerate(edges):
            px, py, ux, uy = edges[index - 1]

            # sin() of the angle the outline turns through at this vertex
            turn = ux * vy - uy * vx
            if abs(turn) < 1e-9:
                raise ValueError("outline doubles back on itself")

            distance = ((qx - px) * vy - (qy - py) * vx) / turn
            offset_vertices.append((px + distance * ux, py + distance * uy))

        # A big enough offset folds the outline over itself, which shows up as an edge
        # that now runs backwards. Checking the direction of every edge catches that
        # even when the folded outline keeps its winding and encloses a smaller area.
        for index, (_, _, dx, dy) in enumerate(edges):
            x0, y0 = offset_vertices[index]
            x1, y1 = offset_vertices[(index + 1) % len(offset_vertices)]
            if (x1 - x0) * dx + (y1 - y0) * dy <= 0.0:
                raise ValueError("offset is too large for the outline")

        if closed:
            offset_vertices.append(offset_vertices[0])

        return offset_vertices

    def calc_floorplan_areas(self, step: Optional[str] = None,
                             index: Optional[Union[str, int]] = None) \
            -> Optional[Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]]:
        """
        Resolves the die and core areas used to initialize a floorplan.

        Floorplanning tools need both a die and a core outline, but only one of
        them has to be specified since the other can be derived from the core
        margin:

        * die area and core area: both are used as specified.
        * die area only: the core area is the die area inset by the core margin.
        * core area only: the die area is the core area outset by the core
          margin. The core keeps the coordinates it was given so that component
          placements remain valid, which means the core area has to sit at least
          one core margin away from the origin.

        Rectilinear outlines are offset edge by edge, so a polygonal die yields a
        polygonal core that follows it rather than its bounding box.

        A core margin of zero is assumed when the margin has not been set.

        Args:
            step (str, optional): The step in a workflow to retrieve from.
                                  Defaults to None.
            index (Union[str, int], optional): The index within a step to
                                               retrieve from. Defaults to None.

        Raises:
            ValueError: If the core margin does not leave a core area with a
                        positive width and height, or if it places the die area
                        at a negative coordinate.

        Returns:
            Optional[Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]]:
            The die and core areas, or None if neither area has been specified,
            in which case the floorplan must be sized from the density and
            aspect ratio.
        """
        diearea = self.get_diearea(step=step, index=index)
        corearea = self.get_corearea(step=step, index=index)

        if diearea and corearea:
            return diearea, corearea

        if not diearea and not corearea:
            return None

        coremargin = self.get_coremargin(step=step, index=index)
        if coremargin is None:
            coremargin = 0.0

        if diearea:
            if len(diearea) == 2:
                # Two points are the lower left and upper right of a rectangle.
                (die_x0, die_y0), (die_x1, die_y1) = self._calc_boundingbox(diearea)

                if 2 * coremargin >= (die_x1 - die_x0):
                    raise ValueError("core margin is greater than or equal to the die width")
                if 2 * coremargin >= (die_y1 - die_y0):
                    raise ValueError("core margin is greater than or equal to the die height")

                corearea = [
                    (die_x0 + coremargin, die_y0 + coremargin),
                    (die_x1 - coremargin, die_y1 - coremargin)]
            else:
                try:
                    corearea = self._calc_offset_polygon(diearea, coremargin)
                except ValueError as e:
                    raise ValueError(f"core margin does not fit in the die area: {e}") from e
        else:
            if len(corearea) == 2:
                (core_x0, core_y0), (core_x1, core_y1) = self._calc_boundingbox(corearea)

                diearea = [
                    (core_x0 - coremargin, core_y0 - coremargin),
                    (core_x1 + coremargin, core_y1 + coremargin)]
            else:
                try:
                    diearea = self._calc_offset_polygon(corearea, -coremargin)
                except ValueError as e:
                    raise ValueError(f"core margin cannot be applied to the core area: {e}") from e

            # OpenROAD rejects a die area with negative coordinates.
            (die_x0, die_y0), _ = self._calc_boundingbox(diearea)
            if die_x0 < 0.0:
                raise ValueError("core margin places the die area at a negative x coordinate")
            if die_y0 < 0.0:
                raise ValueError("core margin places the die area at a negative y coordinate")

        return diearea, corearea

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
