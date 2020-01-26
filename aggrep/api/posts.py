"""Posts module."""

from sqlalchemy import desc

from aggrep.constants import POPULAR, POST_DELTA, POST_LIMIT, SEARCH_DELTA
from aggrep.models import Category, Feed, Post, Source
from aggrep.utils import now


def sort_posts(posts, sort):
    """Sort posts by a predefined format."""
    if sort == POPULAR:
        posts = posts.order_by(desc(Post.ctr), desc(Post.published_datetime))
    else:
        posts = posts.order_by(desc(Post.published_datetime))

    return posts


def limit_posts(posts, limit=POST_LIMIT):
    """Restrict posts to the <limit> most recent."""
    return posts.order_by(desc(Post.published_datetime)).limit(limit).from_self()


def filter_user_categories(posts, current_user):
    """Filter posts to a user's preferences."""
    categories = [c.id for c in current_user.excluded_categories]

    return posts.filter(
        Post.feed.has(Feed.category.has(Category.id.notin_(categories)))
    )


def filter_user_sources(posts, current_user):
    """Filter posts to a user's preferences."""
    sources = [s.id for s in current_user.excluded_sources]

    return posts.filter(Post.feed.has(Feed.source.has(Source.id.notin_(sources))))


def get_all_posts():
    """Get all posts more recent than POST_DELTA."""
    delta = now() - POST_DELTA
    return Post.query.filter(Post.published_datetime >= delta)


def get_posts_by_source(source):
    """Get posts in a given source."""
    posts = get_all_posts()
    return posts.filter(Post.feed.has(Feed.source == source))


def get_posts_by_category(category):
    """Get posts for a given category."""
    posts = get_all_posts()
    return posts.filter(Post.feed.has(Feed.category == category))


def get_similar_posts(uid):
    """Get posts similar to a given post."""
    _post = Post.from_uid(uid)
    source_post = Post.query.filter(Post.id == _post.id)
    return source_post.union(_post.similar_posts)


def get_posts_by_search(query):
    """Get posts similar to a given post."""
    delta = now() - SEARCH_DELTA
    searchable_posts = Post.query.filter(Post.published_datetime >= delta)
    return searchable_posts.search(query, sort=True)
