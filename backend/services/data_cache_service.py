from functools import lru_cache

from models import Goal, Skill, Tool, User
from utils.cache_utils import ttl_cache


@ttl_cache(ttl_seconds=300)
@lru_cache(maxsize=128)
def get_tools_page_cached(page: int, limit: int):
    offset = (page - 1) * limit
    query = Tool.query.order_by(Tool.id.asc())
    total = query.count()
    tools = query.offset(offset).limit(limit).all()
    return {
        'items': [tool.to_dict() for tool in tools],
        'total': total,
    }


@ttl_cache(ttl_seconds=300)
@lru_cache(maxsize=128)
def get_skills_page_cached(page: int, limit: int):
    offset = (page - 1) * limit
    query = Skill.query.order_by(Skill.id.asc())
    total = query.count()
    skills = query.offset(offset).limit(limit).all()
    return {
        'items': [skill.to_dict() for skill in skills],
        'total': total,
    }


@ttl_cache(ttl_seconds=300)
@lru_cache(maxsize=128)
def get_profile_payload_cached(page: int, limit: int):
    user = User.query.first()
    goals = Goal.query.order_by(Goal.id.asc()).all()
    skills_payload = get_skills_page_cached(page, limit)
    tools_payload = get_tools_page_cached(page, limit)

    return {
        'user': user.to_dict() if user else {'name': 'Nutzer'},
        'skills': skills_payload['items'],
        'goals': [goal.to_dict() for goal in goals],
        'tools': tools_payload['items'],
        'pagination': {
            'page': page,
            'limit': limit,
            'skills_total': skills_payload['total'],
            'tools_total': tools_payload['total'],
            'skills_pages': (skills_payload['total'] + limit - 1) // limit,
            'tools_pages': (tools_payload['total'] + limit - 1) // limit,
        }
    }


def clear_data_caches():
    get_profile_payload_cached.cache_clear()
    get_tools_page_cached.cache_clear()
    get_skills_page_cached.cache_clear()
