from src.modules.knowledgebase.model.emum.knowledgebase_category_enum import (
    KnowledgebaseCategoryEnum,
)


def test_category_enum_excludes_blog() -> None:
    """Ensure BLOG is excluded from knowledgebase categories."""
    assert "BLOG" not in KnowledgebaseCategoryEnum.__members__
