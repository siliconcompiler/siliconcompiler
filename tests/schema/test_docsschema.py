from siliconcompiler.schema import DocsSchema, BaseSchema


def test_make_docs():
    assert isinstance(DocsSchema.make_docs(), BaseSchema)
