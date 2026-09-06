from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.session import Base
from app.domain.story_agent_tools import StoryAgentTools


def test_agent_tools_return_only_theme_title_and_structure_and_cap_ten():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    for index in range(12):
        db.add(models.Article(
            source_url=f"https://source.test/{index}", original_title=f"Title {index}",
            theme_tags=["family"], structure={"hook": str(index)}, analysis_status="completed",
        ))
    db.commit()
    tools = StoryAgentTools(db)
    assert tools.list_themes() == [{"theme": "family", "count": 12}]
    examples = tools.get_examples("family", 50)
    assert len(examples) == 10
    assert set(examples[0]) == {"title", "structure"}
    assert "source_url" not in examples[0]
