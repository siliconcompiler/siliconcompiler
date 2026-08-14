import re
import warnings

from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

from siliconcompiler import TaskSkip
from siliconcompiler.schema import EditableSchema
from siliconcompiler.tools.klayout import KLayoutStreamTask


class KLayoutOperation:
    """
    Base class for a single KLayout layout operation.

    An operation is a handle onto a group of task parameters. Constructing one
    records the requested values, ``OperationsTask.add_klayout_operation``
    binds it to a task and appends it to that node's sequence, and the setters
    and getters below read and write the underlying parameters. The names of
    those parameters are an implementation detail and are never exposed.

    Args:
        name (str, optional): Identifier for this operation. If not provided one
            is allocated from the operation type.
        values: Initial field values, flushed to the schema when the operation is
            added to a task.
    """

    # Separator between an operation identifier and one of its field names.
    SEPARATOR: str = "."

    # An identifier must be usable as the leading part of a schema key. SEPARATOR
    # is deliberately excluded so a user supplied identifier can never collide
    # with a generated field key.
    NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

    def __init__(self, name: Optional[str] = None, **values):
        # 'name' identifies the operation, so it can never also be one of its fields
        assert "name" not in self.params, f"{type(self).__name__} cannot own a 'name' field"

        if name is not None and not self.NAME_REGEX.match(name):
            raise ValueError(f"'{name}' is not a valid operation name, "
                             f"must match {self.NAME_REGEX.pattern}")

        self._task: Optional["OperationsTask"] = None
        self._id: Optional[str] = name
        self._pending: Dict[str, Any] = {key: value for key, value in values.items()
                                         if value is not None}

    ###############################################################
    # Definition, overridden by each operation
    ###############################################################
    @property
    def optype(self) -> str:
        """
        Operation type, as recorded in the task's list of operations.
        """
        raise NotImplementedError("operations must implement optype")

    @property
    def params(self) -> Dict[str, Tuple]:
        """
        Parameters owned by this operation.

        Maps a field name onto ``(schema type, help)``, or onto
        ``(schema type, help, kwargs)`` where the extra dictionary is passed
        through to :class:`.Parameter`.
        """
        return {

        }

    ###############################################################
    # Storage, private to this class
    ###############################################################
    def _key(self, field: str) -> str:
        """
        Returns the name of the task parameter backing ``field``.

        Args:
            field (str): Name of the field.
        """
        return f"{self._id}{self.SEPARATOR}{field}"

    def _bind(self, task: "OperationsTask", opid: str) -> "KLayoutOperation":
        """
        Attaches this operation to a task, creating any parameters it needs and
        flushing the values recorded before it was attached.

        Args:
            task (``OperationsTask``): Task to attach to.
            opid (str): Identifier to store this operation under.

        Returns:
            This operation.
        """
        self._task = task
        self._id = opid

        for field, spec in self.params.items():
            key = self._key(field)
            if task.valid("var", key):
                continue
            ptype, phelp = spec[0], spec[1]
            kwargs = spec[2] if len(spec) > 2 else {}
            task.add_parameter(key, ptype, f"{self.optype} '{opid}': {phelp}", **kwargs)

        pending, self._pending = self._pending, {}
        for field, value in pending.items():
            self._set(field, value)

        return self

    def _set(self, field: str, value,
             step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets one field, recording it until the operation is attached to a task.

        Args:
            field (str): Name of the field.
            value: Value to store.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        if self._task is None:
            self._pending[field] = value
            return None
        return self._task.set("var", self._key(field), value, step=step, index=index)

    def _add(self, field: str, value,
             step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Appends to one field, recording it until the operation is attached to a task.

        Args:
            field (str): Name of the field.
            value: Value to append.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        if self._task is None:
            held = self._pending.get(field, None)
            if held is None:
                held = []
            elif isinstance(held, (list, set, tuple)):
                held = list(held)
            else:
                # a scalar is one element, not something to iterate over
                held = [held]

            # mirror the schema: a list is many values, anything else -- including
            # a tuple, which may be one compound value -- is a single one
            if isinstance(value, list):
                held.extend(value)
            else:
                held.append(value)
            self._pending[field] = held
            return None
        return self._task.add("var", self._key(field), value, step=step, index=index)

    def _get(self, field: str,
             step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Returns one field, reading back values recorded before the operation was
        attached to a task.

        Args:
            field (str): Name of the field.
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        if self._task is None:
            return self._pending.get(field, None)
        return self._task.get("var", self._key(field), step=step, index=index)

    def _has_value(self, field: Optional[str] = None,
                   step: Optional[str] = None,
                   index: Optional[Union[str, int]] = None) -> bool:
        """
        Returns whether a field carries a value.

        Args:
            field (str, optional): Field to check. If not provided, every field
                is checked.
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        fields = [field] if field else list(self.params)
        for check in fields:
            value = self._get(check, step=step, index=index)
            if value is None:
                continue
            if isinstance(value, (list, set, tuple)) and not value:
                continue
            return True
        return False

    def _require(self, field: str,
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Declares one field as required by the task driver.

        Args:
            field (str): Name of the field.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._task.add_required_key("var", self._key(field), step=step, index=index)

    ###############################################################
    # Public surface
    ###############################################################
    @property
    def name(self) -> Optional[str]:
        """
        Identifier for this operation.
        """
        return self._id

    def setup(self, task: "OperationsTask") -> None:
        """
        Declares the task requirements for this operation.

        The default implementation requires every field that carries a value.

        Args:
            task (``OperationsTask``): Task this operation belongs to.
        """
        for field in self.params:
            if self._has_value(field=field):
                self._require(field)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._id})"


class Merge(KLayoutOperation):
    """
    Merges another stream into the top cell of the current layout.

    Exactly one of ``file`` or ``input`` must be provided.

    Args:
        file (str or list of str, optional): stream file to merge.
        input (str, optional): name of a stream provided by an input node.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "merge"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "file": ("[file]", "stream files to merge into the layout"),
            "input": ("str", "stream file provided by an input node")
        }

    def __init__(self, file: Optional[Union[str, List[str]]] = None,
                 input: Optional[str] = None,
                 name: Optional[str] = None):
        super().__init__(name, file=file, input=input)

    def set_file(self, file: Union[str, List[str]],
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the stream files to merge.

        Args:
            file (str or list of str): Path(s) to the stream file(s).
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("file", file, step=step, index=index)

    def add_file(self, file: Union[str, List[str]],
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Adds a stream file to merge.

        Args:
            file (str or list of str): Path(s) to the stream file(s).
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._add("file", file, step=step, index=index)

    def get_file(self, step: Optional[str] = None,
                 index: Optional[Union[str, int]] = None) -> List[str]:
        """
        Returns the stream files to merge.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("file", step=step, index=index)

    def set_input(self, file: str,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the stream provided by an input node.

        Args:
            file (str): Name of the file arriving from an input node.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("input", file, step=step, index=index)

    def get_input(self, step: Optional[str] = None,
                  index: Optional[Union[str, int]] = None) -> str:
        """
        Returns the stream provided by an input node.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("input", step=step, index=index)

    def setup(self, task):
        has_file = self._has_value(field="file")
        has_input = self._has_value(field="input")

        if has_file and has_input:
            raise ValueError(f"{self.optype} '{self.name}' cannot set both file and input")
        if not has_file and not has_input:
            raise ValueError(f"{self.optype} '{self.name}' requires a file or an input")

        if has_file:
            self._require("file")
        else:
            self._require("input")
            task.add_input_file(self._get("input"))


class Add(Merge):
    """
    Adds another stream to the current layout as a new cell instance.

    Exactly one of ``file`` or ``input`` must be provided.

    Args:
        file (str or list of str, optional): stream file to add.
        input (str, optional): name of a stream provided by an input node.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "add"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "file": ("[file]", "stream files to add to the layout"),
            "input": ("str", "stream file provided by an input node")
        }


class Rotate(KLayoutOperation):
    """
    Rotates the layout about its lower left corner.

    Args:
        angle (int, optional): rotation in degrees, one of 0, 90, 180 or 270.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "rotate"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "angle": ("int<0,90,180,270>", "rotation angle in degrees", {"defvalue": 90})
        }

    def __init__(self, angle: Optional[int] = None, name: Optional[str] = None):
        super().__init__(name, angle=angle)

    def set_angle(self, angle: int,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the rotation angle.

        Args:
            angle (int): Rotation in degrees, one of 0, 90, 180 or 270.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("angle", angle, step=step, index=index)

    def get_angle(self, step: Optional[str] = None,
                  index: Optional[Union[str, int]] = None) -> int:
        """
        Returns the rotation angle in degrees.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("angle", step=step, index=index)

    def setup(self, task):
        self._require("angle")


class Flatten(KLayoutOperation):
    """
    Flattens the hierarchy of the top cell.

    Args:
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "flatten"


class Outline(KLayoutOperation):
    """
    Adds a box covering the top cell bounding box on the given layer.

    Args:
        layer (int, optional): stream layer number.
        purpose (int, optional): stream purpose (datatype) number.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "outline"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "layer": ("(int,int)", "layer/purpose pair to draw the outline on")
        }

    def __init__(self, layer: Optional[int] = None, purpose: int = 0,
                 name: Optional[str] = None):
        super().__init__(name, layer=None if layer is None else (layer, purpose))

    def set_layer(self, layer: int, purpose: int = 0,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the layer to draw the outline on.

        Args:
            layer (int): Stream layer number.
            purpose (int, optional): Stream purpose (datatype) number.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("layer", (layer, purpose), step=step, index=index)

    def get_layer(self, step: Optional[str] = None,
                  index: Optional[Union[str, int]] = None) -> Tuple[int, int]:
        """
        Returns the (layer, purpose) pair the outline is drawn on.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("layer", step=step, index=index)

    def setup(self, task):
        if not self._has_value(field="layer"):
            raise ValueError(f"{self.optype} '{self.name}' requires a layer")
        self._require("layer")


class RenameTop(KLayoutOperation):
    """
    Renames the top cell.

    Args:
        cellname (str, optional): new name for the top cell.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "rename"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "cellname": ("str", "new name for the top cell")
        }

    def __init__(self, cellname: Optional[str] = None, name: Optional[str] = None):
        super().__init__(name, cellname=cellname)

    def set_cellname(self, cellname: str,
                     step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the name of the top cell.

        Args:
            cellname (str): Name for the top cell.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("cellname", cellname, step=step, index=index)

    def get_cellname(self, step: Optional[str] = None,
                     index: Optional[Union[str, int]] = None) -> str:
        """
        Returns the name of the top cell.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("cellname", step=step, index=index)

    def setup(self, task):
        if not self._has_value(field="cellname"):
            raise ValueError(f"{self.optype} '{self.name}' requires a cellname")
        self._require("cellname")


class AddTop(RenameTop):
    """
    Adds a new top cell holding an instance of the current top cell.

    Args:
        cellname (str, optional): name for the new top cell.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "add_top"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "cellname": ("str", "name for the new top cell")
        }


class RenameCell(KLayoutOperation):
    """
    Renames cells in the layout.

    Args:
        cells (set of tuple of str, optional): (old name, new name) pairs.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "rename_cell"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "cells": ("{(str,str)}", "(old name, new name) pairs of cells to rename")
        }

    def __init__(self, cells: Optional[Set[Tuple[str, str]]] = None,
                 name: Optional[str] = None):
        super().__init__(name, cells=cells)

    def set_cells(self, cells: Set[Tuple[str, str]],
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the cells to act on.

        Args:
            cells (set of tuple of str): (old name, new name) pairs.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("cells", cells, step=step, index=index)

    def add_cell(self, old: str, new: str,
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Adds a cell to act on.

        Args:
            old (str): Name of the cell in the layout.
            new (str): Name to use instead.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._add("cells", (old, new), step=step, index=index)

    def get_cells(self, step: Optional[str] = None,
                  index: Optional[Union[str, int]] = None) -> Set[Tuple[str, str]]:
        """
        Returns the cells to act on, as (old name, new name) pairs.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("cells", step=step, index=index)

    def setup(self, task):
        if not self._has_value(field="cells"):
            raise ValueError(f"{self.optype} '{self.name}' requires cells")
        self._require("cells")


class SwapCell(RenameCell):
    """
    Replaces instances of one cell with another and deletes the original.

    Args:
        cells (set of tuple of str, optional): (old name, new name) pairs.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "swap"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "cells": ("{(str,str)}", "(old name, new name) pairs of cells to swap")
        }


class DeleteLayers(KLayoutOperation):
    """
    Deletes all shapes on the given layers, in every cell.

    Args:
        layers (set of tuple of int, optional): (layer, purpose) pairs to delete.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "delete_layers"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "layers": ("{(int,int)}", "layer/purpose pairs to delete")
        }

    def __init__(self, layers: Optional[Set[Tuple[int, int]]] = None,
                 name: Optional[str] = None):
        super().__init__(name, layers=layers)

    def set_layers(self, layers: Set[Tuple[int, int]],
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the layers to delete.

        Args:
            layers (set of tuple of int): (layer, purpose) pairs.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("layers", layers, step=step, index=index)

    def add_layer(self, layer: int, purpose: int = 0,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Adds a layer to delete.

        Args:
            layer (int): Stream layer number.
            purpose (int, optional): Stream purpose (datatype) number.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._add("layers", (layer, purpose), step=step, index=index)

    def get_layers(self, step: Optional[str] = None,
                   index: Optional[Union[str, int]] = None) -> Set[Tuple[int, int]]:
        """
        Returns the layers to delete, as (layer, purpose) pairs.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("layers", step=step, index=index)

    def setup(self, task):
        if not self._has_value(field="layers"):
            raise ValueError(f"{self.optype} '{self.name}' requires layers")
        self._require("layers")


class MergeShapes(KLayoutOperation):
    """
    Merges overlapping shapes on the given layers, in every cell.

    Args:
        layers (set of tuple of int, optional): (layer, purpose) pairs to merge.
        all (bool, optional): merge shapes on every layer in the layout.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "merge_shapes"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "layers": ("{(int,int)}", "layer/purpose pairs to merge shapes on"),
            "all": ("bool", "merge shapes on every layer", {"defvalue": False})
        }

    def __init__(self, layers: Optional[Set[Tuple[int, int]]] = None,
                 all: Optional[bool] = None,
                 name: Optional[str] = None):
        super().__init__(name, layers=layers, all=all)

    def set_layers(self, layers: Set[Tuple[int, int]],
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the layers to merge shapes on.

        Args:
            layers (set of tuple of int): (layer, purpose) pairs.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("layers", layers, step=step, index=index)

    def add_layer(self, layer: int, purpose: int = 0,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Adds a layer to merge shapes on.

        Args:
            layer (int): Stream layer number.
            purpose (int, optional): Stream purpose (datatype) number.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._add("layers", (layer, purpose), step=step, index=index)

    def get_layers(self, step: Optional[str] = None,
                   index: Optional[Union[str, int]] = None) -> Set[Tuple[int, int]]:
        """
        Returns the layers to merge shapes on, as (layer, purpose) pairs.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("layers", step=step, index=index)

    def set_all(self, value: bool,
                step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets whether shapes are merged on every layer in the layout.

        Args:
            value (bool): Whether to merge shapes on every layer.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("all", value, step=step, index=index)

    def get_all(self, step: Optional[str] = None,
                index: Optional[Union[str, int]] = None) -> bool:
        """
        Returns whether shapes are merged on every layer in the layout.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("all", step=step, index=index)

    def setup(self, task):
        if not self._get("all") and not self._has_value(field="layers"):
            raise ValueError(f"{self.optype} '{self.name}' requires layers or all")
        self._require("all")
        if self._has_value(field="layers"):
            self._require("layers")


class ConvertProperty(KLayoutOperation):
    """
    Converts a stream property into text labels on the design.

    Args:
        source (tuple of int, optional): (layer, purpose) pair carrying the property.
        property (str, optional): stream property number or name.
        dest (tuple of int, optional): (layer, purpose) pair to write labels to.
            Defaults to the source pair.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "convert_property"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "source": ("(int,int)", "layer/purpose pair holding the property"),
            "property": ("str", "stream property number or name"),
            "dest": ("(int,int)", "layer/purpose pair to write the labels to")
        }

    def __init__(self, source: Optional[Tuple[int, int]] = None,
                 property: Optional[Union[int, str]] = None,
                 dest: Optional[Tuple[int, int]] = None,
                 name: Optional[str] = None):
        super().__init__(name,
                         source=source,
                         property=None if property is None else str(property),
                         dest=dest)

    def set_source(self, layer: int, purpose: int = 0,
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the layer holding the property.

        Args:
            layer (int): Stream layer number.
            purpose (int, optional): Stream purpose (datatype) number.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("source", (layer, purpose), step=step, index=index)

    def get_source(self, step: Optional[str] = None,
                   index: Optional[Union[str, int]] = None) -> Tuple[int, int]:
        """
        Returns the (layer, purpose) pair holding the property.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("source", step=step, index=index)

    def set_property(self, property: Union[int, str],
                     step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the stream property to convert.

        Args:
            property (int or str): Property number or name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("property", str(property), step=step, index=index)

    def get_property(self, step: Optional[str] = None,
                     index: Optional[Union[str, int]] = None) -> str:
        """
        Returns the stream property to convert.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("property", step=step, index=index)

    def set_dest(self, layer: int, purpose: int = 0,
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the layer the labels are written to.

        Args:
            layer (int): Stream layer number.
            purpose (int, optional): Stream purpose (datatype) number.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("dest", (layer, purpose), step=step, index=index)

    def get_dest(self, step: Optional[str] = None,
                 index: Optional[Union[str, int]] = None) -> Tuple[int, int]:
        """
        Returns the (layer, purpose) pair the labels are written to.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("dest", step=step, index=index)

    def setup(self, task):
        for field in ("source", "property"):
            if not self._has_value(field=field):
                raise ValueError(f"{self.optype} '{self.name}' requires a {field}")
            self._require(field)
        if self._has_value(field="dest"):
            self._require("dest")


class Write(KLayoutOperation):
    """
    Writes the current state of the layout to an output file.

    Every node writes its final layout automatically, so this is only needed to
    capture an intermediate state part way through a sequence.

    Args:
        filename (str, optional): name of the file to write into ``outputs/``.
        name (str, optional): identifier for this operation.
    """
    @property
    def optype(self):
        """Operation type identifier."""
        return "write"

    @property
    def params(self):
        """Parameters owned by this operation."""
        return {
            "filename": ("str", "name of the output file to write")
        }

    def __init__(self, filename: Optional[str] = None, name: Optional[str] = None):
        super().__init__(name, filename=filename)

    def set_filename(self, filename: str,
                     step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the name of the output file.

        Args:
            filename (str): Name of the file to write into ``outputs/``.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        return self._set("filename", filename, step=step, index=index)

    def get_filename(self, step: Optional[str] = None,
                     index: Optional[Union[str, int]] = None) -> str:
        """
        Returns the name of the output file.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        return self._get("filename", step=step, index=index)

    def setup(self, task):
        filename = self._get("filename")
        if not filename:
            raise ValueError(f"{self.optype} '{self.name}' requires a filename")
        self._require("filename")
        task.add_output_file(filename)


def get_operation_types() -> Dict[str, Type[KLayoutOperation]]:
    """
    Returns the mapping of operation type to the class implementing it.
    """
    types = {}

    def recurse(cls):
        for subcls in cls.__subclasses__():
            # optype is a constant property, so read it off a bare instance rather
            # than constructing one: an operation is free to require arguments.
            try:
                optype = subcls.__new__(subcls).optype
            except NotImplementedError:
                optype = None
            if optype:
                types.setdefault(optype, subcls)
            recurse(subcls)

    recurse(KLayoutOperation)
    return types


class OperationsTask(KLayoutStreamTask):
    '''
    Perform a sequence of operations on a stream file.

    Operations are objects, added in the order they should be applied. Each one
    is created with its arguments, handed to ``add_klayout_operation``,
    and returns a handle whose setters can adjust it later. Operations can be repeated and
    interleaved freely, and each node in a flow has its own sequence.

    >>> from siliconcompiler.tools.klayout import operations
    >>> task = operations.OperationsTask.find_task(project)
    >>> task.add_klayout_operation(operations.DeleteLayers([(63, 0), (550, 26)]))
    >>> task.add_klayout_operation(operations.Rotate(90))
    >>> task.add_klayout_operation(operations.Write("rotated.gds"))

    The handle can be kept and edited:

    >>> strip = task.add_klayout_operation(operations.DeleteLayers(name="strip"))
    >>> strip.add_layer(212, 51)

    Available operations:

    * :class:`.Merge` -- merge another stream into the top cell
    * :class:`.Add` -- add another stream as a new cell instance
    * :class:`.Rotate` -- rotate the layout
    * :class:`.Flatten` -- flatten the hierarchy of the top cell
    * :class:`.Outline` -- draw a box around the top cell bounding box
    * :class:`.RenameTop` -- rename the top cell
    * :class:`.AddTop` -- add a new top cell above the current one
    * :class:`.RenameCell` -- rename cells
    * :class:`.SwapCell` -- replace instances of one cell with another
    * :class:`.DeleteLayers` -- delete all shapes on the given layers
    * :class:`.MergeShapes` -- merge overlapping shapes on the given layers
    * :class:`.ConvertProperty` -- convert stream properties into text labels
    * :class:`.Write` -- write an intermediate copy of the layout

    Each node writes ``outputs/<topmodule>.<stream>.gz`` regardless of the
    operations performed, so :class:`.Write` is only needed to capture the layout
    part way through a sequence. A node with no operations is skipped.
    '''
    def __init__(self):
        super().__init__()

        optypes = ",".join(sorted(get_operation_types()))
        self.add_parameter(
            "operations", f"[(<{optypes}>,str)]",
            "ordered (operation type, operation name) pairs to perform")

    ###############################################################
    # Operations
    ###############################################################
    def __allocate_name(self, optype: str) -> str:
        """Returns an unused name for an operation of the given type."""
        used = set()
        for _, opname in self.__all_operations():
            used.add(opname)

        count = 0
        while f"{optype}{count}" in used:
            count += 1
        return f"{optype}{count}"

    def __all_operations(self) -> List[Tuple[str, str]]:
        """Returns every (type, name) pair recorded on any node."""
        param = self.get("var", "operations", field=None)
        ops = []
        for value, _, _ in param.getvalues():
            for entry in value:
                if entry not in ops:
                    ops.append(entry)
        return ops

    def add_klayout_operation(self, op: KLayoutOperation,
                              step: Optional[str] = None,
                              index: Optional[Union[str, int]] = None) -> KLayoutOperation:
        """
        Appends an operation to the sequence performed by a node.

        Args:
            op (:class:`.KLayoutOperation`): The operation to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.

        Returns:
            The operation, bound to this task.
        """
        if not isinstance(op, KLayoutOperation):
            raise TypeError("op must be a KLayoutOperation")

        opname = op.name
        if opname is None:
            opname = self.__allocate_name(op.optype)
        else:
            defined = [entry[0] for entry in self.__all_operations() if entry[1] == opname]
            if defined and defined[0] != op.optype:
                raise ValueError(f"'{opname}' is already defined as a "
                                 f"{defined[0]} operation")
            if defined and op._pending:
                raise ValueError(f"'{opname}' operation is already defined, "
                                 "use the object returned by add_klayout_operation to modify it")

        op._bind(self, opname)
        self.add("var", "operations", (op.optype, opname), step=step, index=index)

        return op

    def add_operation(self, op: Union[KLayoutOperation, str], args: Optional[str] = None,
                      step: Optional[str] = None,
                      index: Optional[Union[str, int]] = None) -> KLayoutOperation:
        """
        Deprecated, use ``add_klayout_operation``.

        The ``(operation, argument)`` form this used to take is translated where
        the translation is unambiguous, and rejected where the argument was a
        keypath to another parameter.
        """
        warnings.warn("add_operation is deprecated, use add_klayout_operation",
                      DeprecationWarning, stacklevel=2)

        if not isinstance(op, str):
            return self.add_klayout_operation(op, step=step, index=index)

        if not args:
            translate = {"rotate": Rotate, "flatten": Flatten}
            if op in translate:
                return self.add_klayout_operation(translate[op](), step=step, index=index)
        elif "," not in args:
            if op == "write":
                return self.add_klayout_operation(Write(args), step=step, index=index)
            translate = {"merge": Merge, "add": Add}
            if op in translate:
                return self.add_klayout_operation(translate[op](input=args),
                                                  step=step, index=index)

        types = get_operation_types()
        replacement = types[op].__name__ if op in types else None
        raise ValueError(
            f"'{op}' can no longer be configured with a keypath, "
            f"use {replacement or 'an operation object'} instead")

    def set_klayout_operations(self, operations: List[Tuple[str, str]],
                               step: Optional[str] = None,
                               index: Optional[Union[str, int]] = None):
        """
        Deprecated, use ``add_klayout_operation``.

        Replaces the sequence a node performs, translating each entry the same
        way ``add_operation`` does.
        """
        warnings.warn("set_klayout_operations is deprecated, use add_klayout_operation",
                      DeprecationWarning, stacklevel=2)

        self.unset("var", "operations", step=step, index=index)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            for op, args in operations:
                self.add_operation(op, args, step=step, index=index)

    def get_klayout_operations(self, step: Optional[str] = None,
                               index: Optional[Union[str, int]] = None) \
            -> List[KLayoutOperation]:
        """
        Returns the operations a node performs, in order.

        Args:
            step (str, optional): The specific step to read this configuration from.
            index (str, optional): The specific index to read this configuration from.
        """
        types = get_operation_types()

        ops = []
        for optype, opname in self.get("var", "operations", step=step, index=index):
            if optype not in types:
                raise LookupError(f"'{optype}' is not a recognized operation")
            op = types[optype].__new__(types[optype])
            KLayoutOperation.__init__(op)
            op._bind(self, opname)
            ops.append(op)
        return ops

    def remove_klayout_operation(self, op: Union[KLayoutOperation, str],
                                 step: Optional[str] = None,
                                 index: Optional[Union[str, int]] = None) -> bool:
        """
        Removes an operation from the sequence performed by a node.

        The parameters holding the operation's values are deleted once no node
        refers to it any more.

        Args:
            op (:class:`.KLayoutOperation` or str): The operation, or its name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.

        Returns:
            True if the operation was removed.
        """
        opname = op.name if isinstance(op, KLayoutOperation) else op

        current = self.get("var", "operations", step=step, index=index)
        remaining = [entry for entry in current if entry[1] != opname]
        if len(remaining) == len(current):
            return False

        optype = [entry[0] for entry in current if entry[1] == opname][0]
        self.set("var", "operations", remaining, step=step, index=index)

        if any(entry[1] == opname for entry in self.__all_operations()):
            # still referenced by another node
            return True

        # This is a one-off removal, so reach into the schema directly.
        edit = EditableSchema(self)
        for field in get_operation_types()[optype]().params:
            key = f"{opname}{KLayoutOperation.SEPARATOR}{field}"
            if self.valid("var", key):
                edit.remove("var", key)

        return True

    ###############################################################
    # Task
    ###############################################################
    def task(self):
        return "operations"

    def setup(self):
        super().setup()

        self.set_script("klayout_operations.py")

        operations = self.get_klayout_operations()
        if not operations:
            raise TaskSkip("no operations to perform")

        self.add_required_key("var", "operations")

        self._add_stream_input_file()
        self._add_stream_output_file()

        for op in operations:
            op.setup(self)
