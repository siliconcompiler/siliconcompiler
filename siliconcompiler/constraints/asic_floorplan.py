from typing import Union, List, Tuple

from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, PerNode, Scope


class ASICAreaConstraint(BaseSchema):
    def __init__(self):
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
                example=["api: chip.set('constraint', 'diearea', (0, 0))"],
                schelp="""
                List of (x, y) points that define the outline physical layout
                physical design. Simple rectangle areas can be defined with two points,
                one for the lower left corner and one for the upper right corner."""))

        schema.insert(
            'corearea',
            Parameter(
                '[(float,float)]',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                unit='um',
                shorthelp="Constraint: layout core area",
                switch="-constraint_corearea <(float,float)>",
                example=["api: chip.set('constraint', 'corearea', (0, 0))"],
                schelp="""
                List of (x, y) points that define the outline of the core area for the
                physical design. Simple rectangle areas can be defined with two points,
                one for the lower left corner and one for the upper right corner."""))

        schema.insert(
            'coremargin',
            Parameter(
                'float',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                unit='um',
                shorthelp="Constraint: layout core margin",
                switch="-constraint_coremargin <float>",
                example=["api: chip.set('constraint', 'coremargin', 1)"],
                schelp="""
                Halo/margin between the outline and core area for fully
                automated layout sizing and floorplanning."""))

        schema.insert(
            'density', Parameter(
                'float',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: layout density",
                switch="-constraint_density <float>",
                example=["api: chip.set('constraint', 'density', 30)"],
                schelp="""
                Target density based on the total design cells area reported
                after synthesis/elaboration. This number is used when no outline
                or floorplan is supplied. Any number between 1 and 100 is legal,
                but values above 50 may fail due to area/congestion issues during
                automated place and route."""))

        schema.insert(
            'aspectratio', Parameter(
                'float',
                pernode=PerNode.OPTIONAL,
                defvalue=1.0,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: layout aspect ratio",
                switch="-constraint_aspectratio <float>",
                example=["api: chip.set('constraint', 'aspectratio', 2.0)"],
                schelp="""
                Height to width ratio of the block for automated floorplanning.
                Values below 0.1 and above 10 should be avoided as they will likely fail
                to converge during placement and routing. The ideal aspect ratio for
                most designs is 1. This value is only used when no diearea or floorplan
                is supplied."""))

    def set_density(self,
                    density: float,
                    aspectratio: float = None,
                    coremargin: float = None,
                    step: str = None, index: Union[str, int] = None):
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

    def get_density(self, step: str = None, index: Union[str, int] = None) -> float:
        return self.get("density", step=step, index=index)

    def set_aspectratio(self,
                        aspectratio: float,
                        step: str = None, index: Union[str, int] = None):
        if not isinstance(aspectratio, (int, float)):
            raise TypeError("aspectratio must be a number")

        if aspectratio <= 0.0:
            raise ValueError("aspectratio cannot be zero or negative")

        return self.set("aspectratio", aspectratio, step=step, index=index)

    def get_aspectratio(self,
                        step: str = None, index: Union[str, int] = None) -> float:
        return self.get("aspectratio", step=step, index=index)

    def set_coremargin(self,
                       coremargin: float,
                       step: str = None, index: Union[str, int] = None):
        if not isinstance(coremargin, (int, float)):
            raise TypeError("coremargin must be a number")

        if coremargin < 0.0:
            raise ValueError("coremargin cannot be negative")

        return self.set("coremargin", coremargin, step=step, index=index)

    def get_coremargin(self,
                       step: str = None, index: Union[str, int] = None) -> float:
        return self.get("coremargin", step=step, index=index)

    def set_diearea_rectangle(self,
                              height: float,
                              width: float,
                              coremargin: Union[float, Tuple[float, float]] = None,
                              step: str = None, index: Union[str, int] = None):
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
                               step: str = None, index: Union[str, int] = None):
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
            raise TypeError("coremargin must be a number to a tuple of two numbers")
        else:
            if len(coremargin) != 2:
                raise ValueError("coremargin must be a number to a tuple of two numbers")

        xmargin, ymargin = coremargin

        if xmargin < 0:
            raise ValueError("x margin canont be negative")

        if ymargin < 0:
            raise ValueError("y margin canont be negative")

        if 2 * xmargin >= diewidth:
            raise ValueError("x margin is greather than the die width")

        if 2 * ymargin >= dieheight:
            raise ValueError("y margin is greather than the die height")

        return self.set_corearea([
            (xmargin, ymargin),
            (diewidth - xmargin, dieheight - ymargin)], step=step, index=index)

    def set_diearea(self,
                    points: List[Tuple[float, float]],
                    step: str = None, index: Union[str, int] = None):
        return self.set("diearea", points, step=step, index=index)

    def get_diearea(self,
                    step: str = None, index: Union[str, int] = None) -> List[Tuple[float, float]]:
        return self.get("diearea", step=step, index=index)

    def set_corearea(self,
                     points: List[Tuple[float, float]],
                     step: str = None, index: Union[str, int] = None):
        return self.set("corearea", points, step=step, index=index)

    def get_corearea(self,
                     step: str = None, index: Union[str, int] = None) -> List[Tuple[float, float]]:
        return self.get("corearea", step=step, index=index)
