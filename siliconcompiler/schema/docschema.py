from typing import Union, List

from .baseschema import BaseSchema


class DocsSchema(BaseSchema):
    @classmethod
    def make_docs(cls) -> Union[BaseSchema, List[BaseSchema]]:
        return cls()
