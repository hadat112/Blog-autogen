from sqlalchemy.orm import Session

from app.db import models


def _clean_keywords(values):
    result = []
    seen = set()
    for value in values or []:
        keyword = str(value).strip().lower()
        if keyword and keyword not in seen:
            result.append(keyword)
            seen.add(keyword)
    if not result:
        raise ValueError("At least one keyword is required")
    return result


class ThemeRuleService:
    def __init__(self, db: Session):
        self.db = db

    def list(self):
        return self.db.query(models.ThemeRule).order_by(models.ThemeRule.tag.asc()).all()

    def get(self, rule_id):
        return self.db.query(models.ThemeRule).filter(models.ThemeRule.id == rule_id).first()

    def create(self, data):
        tag = data.tag.strip().lower()
        if self.db.query(models.ThemeRule).filter(models.ThemeRule.tag == tag).first():
            raise ValueError("Theme tag already exists")
        rule = models.ThemeRule(tag=tag, keywords=_clean_keywords(data.keywords), is_active=data.is_active)
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update(self, rule_id, data):
        rule = self.get(rule_id)
        if not rule:
            return None
        tag = data.tag.strip().lower()
        duplicate = self.db.query(models.ThemeRule).filter(
            models.ThemeRule.tag == tag,
            models.ThemeRule.id != rule_id,
        ).first()
        if duplicate:
            raise ValueError("Theme tag already exists")
        rule.tag = tag
        rule.keywords = _clean_keywords(data.keywords)
        rule.is_active = data.is_active
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete(self, rule_id):
        rule = self.get(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        return True
