from typing import Union, List

from .baseschema import BaseSchema


class DocsSchema(BaseSchema):
    """A base class for customizing documentation generation.

    This class provides a hook (`make_docs`) that can be overridden by subclasses
    to control how a schema is represented in documentation.
    """

    @classmethod
    def make_docs(cls) -> Union[BaseSchema, List[BaseSchema]]:
        """Generate the documentation representation for this schema.

        By default, this method returns a standard instance of the class itself.
        Subclasses can override this method to return a modified or different
        schema instance, or even a list of schemas, to customize how they
        appear in the generated documentation.

        Returns:
            An instance or list of instances of `BaseSchema` that represents
            the schema for documentation purposes.
        """
        return cls()
