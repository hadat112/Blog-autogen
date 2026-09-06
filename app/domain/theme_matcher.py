import re


def match_theme_tags(title, content, rules):
    haystack = re.sub(r"\s+", " ", f"{title or ''} {content or ''}").lower()
    tags = []
    for rule in rules:
        if not getattr(rule, "is_active", False):
            continue
        if any(str(keyword).strip().lower() in haystack for keyword in (rule.keywords or [])):
            tags.append(rule.tag)
    return sorted(set(tags))
