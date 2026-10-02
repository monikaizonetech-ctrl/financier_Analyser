from sqlalchemy.orm import Query


def paginate(query: Query, page: int = 1, page_size: int = 10):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total, page, page_size
