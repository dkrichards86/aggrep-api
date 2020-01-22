"""Database models."""
import short_url
from flask import current_app, url_for
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_searchable import make_searchable
from sqlalchemy_utils.types import TSVectorType
from werkzeug.security import check_password_hash, generate_password_hash

from aggrep import db
from aggrep.utils import decode_token, encode_token, now

make_searchable(db.metadata)


class PKMixin:
    """Mixin that adds a primary key to each model."""

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)


class CRUDMixin:
    """Mixin that adds convenience methods for CRUD (create, read, update, delete) operations."""

    @classmethod
    def create(cls, **kwargs):
        """Create a new record and save it the database."""
        instance = cls(**kwargs)
        return instance.save()

    def update(self, **kwargs):
        """Update specific fields of a record."""
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return self.save()

    def save(self):
        """Save the record."""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """Remove the record from the database."""
        db.session.delete(self)
        return db.session.commit()


class BaseModel(PKMixin, CRUDMixin, db.Model):
    """Base model class that includes CRUD convenience methods."""

    __abstract__ = True


class PaginatedAPIMixin:
    """Pagination mixin."""

    @staticmethod
    def to_collection_dict(query, page, per_page):
        """Paginate a collection."""
        resources = query.paginate(page, per_page, False)
        data = {
            "items": [item.to_dict() for item in resources.items],
            "page": page,
            "per_page": per_page,
            "total_pages": resources.pages,
            "total_items": resources.total,
        }
        return data


class Category(BaseModel):
    """Category model."""

    __tablename__ = "categories"
    slug = db.Column(db.String(32), unique=True, nullable=False)
    title = db.Column(db.String(140), unique=True, nullable=False)

    def to_dict(self):
        """Return as a dict."""
        return dict(id=self.id, slug=self.slug, title=self.title)

    def __repr__(self):
        """String representation."""
        return self.title


class Source(BaseModel):
    """Source model."""

    __tablename__ = "sources"
    slug = db.Column(db.String(32), unique=True, nullable=False)
    title = db.Column(db.String(140), nullable=False)

    def to_dict(self):
        """Return as a dict."""
        return dict(id=self.id, slug=self.slug, title=self.title)

    def __repr__(self):
        """String representation."""
        return self.title


class Status(BaseModel):
    """Feed status model."""

    __tablename__ = "feed_statuses"
    feed_id = db.Column(db.Integer, db.ForeignKey("feeds.id"), unique=True)
    update_datetime = db.Column(db.DateTime, nullable=False, default=now)
    update_frequency = db.Column(db.Integer, default=0)


class Feed(BaseModel):
    """Feed model."""

    __tablename__ = "feeds"
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"))
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    url = db.Column(db.String(255), nullable=False)

    # ORM Relationship
    source = db.relationship("Source", uselist=False, backref="feeds")
    category = db.relationship("Category", uselist=False, backref="feeds")
    status = db.relationship("Status", uselist=False, backref="feed")

    def to_dict(self):
        """Return as a dict."""
        return dict(
            source=self.source.to_dict(), category=self.category.to_dict(), url=self.url
        )


class Post(BaseModel, PaginatedAPIMixin):
    """Post model."""

    __tablename__ = "posts"
    feed_id = db.Column(db.Integer, db.ForeignKey("feeds.id"))
    title = db.Column(db.Unicode(255), nullable=False)
    desc = db.Column(db.UnicodeText)
    link = db.Column(db.String(255), nullable=False)
    published_datetime = db.Column(db.DateTime, nullable=False, default=now, index=True)
    ingested_datetime = db.Column(db.DateTime, nullable=False, default=now)
    actions = db.relationship("PostAction", uselist=False, backref="posts")
    search_vector = db.Column(TSVectorType("title", "desc"))

    feed = db.relationship("Feed", uselist=False, backref="posts")

    similar_posts = db.relationship(
        "Post",
        secondary="similarities",
        primaryjoin="Post.id==Similarity.source_id",
        secondaryjoin="Post.id==Similarity.related_id",
        lazy="dynamic",
    )

    @staticmethod
    def search(query, search_terms):
        """Search a post collection for search terms."""
        return query.from_self().filter(
            Post.search_vector.op("@@")(db.func.to_tsquery(search_terms))
        )

    @property
    def uid(self):
        """Generate a deterministic UID from post ID."""
        return short_url.encode_url(self.id, min_length=6)

    @staticmethod
    def from_uid(uid):
        """Given a deterministic UID, get the associated post."""
        return Post.query.get(short_url.decode_url(uid))

    @hybrid_property
    def ctr(self):
        """Post click through rate (object level)."""
        return float(self.actions.ctr)

    @ctr.expression
    def ctr(self):
        """Post click through rate (class level)."""

        return db.select([PostAction.ctr]).where(PostAction.post_id == self.id)

    def to_dict(self):
        """Return as a dict."""
        payload = dict(
            id=self.id,
            uid=self.uid,
            title=self.title,
            link=url_for("app.follow_redirect", uid=self.uid, _external=True),
            post_url=self.link,
            feed=self.feed.to_dict(),
            published_datetime=self.published_datetime,
        )
        return payload

    def __repr__(self):
        """String representation."""
        return "{}: {}".format(self.id, self.title)


class PostAction(BaseModel):
    """PostAction model."""

    __tablename__ = "post_actions"
    post_id = db.Column(
        db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    clicks = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    ctr = db.Column(db.Numeric(4, 3), default=0)

    post = db.relationship("Post", uselist=False, backref="post_actions")


class SimilarityProcessQueue(BaseModel):
    """Similarity queue model."""

    __tablename__ = "similarity_queue"
    post_id = db.Column(
        db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), unique=True
    )

    post = db.relationship("Post")


class Similarity(BaseModel):
    """Similarity model."""

    __tablename__ = "similarities"
    source_id = db.Column(
        db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    related_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"))


class JobType(BaseModel):
    """JobType model."""

    __tablename__ = "job_types"
    job = db.Column(db.String(40), nullable=False)

    def __repr__(self):
        """String representation."""
        return "Job Type: {}".format(self.job)


class JobLock(BaseModel):
    """Job lock model."""

    __tablename__ = "joblock"
    job_type = db.Column(
        db.Integer, db.ForeignKey("job_types.id", ondelete="CASCADE"), unique=True
    )
    lock_datetime = db.Column(db.DateTime, nullable=False, default=now)

    job = db.relationship("JobType", uselist=False, backref="joblock")

    def __repr__(self):
        """String representation."""
        return "Job Lock: {} at {}".format(self.job.job, self.lock_datetime)


class Bookmark(BaseModel):
    """Bookmark model."""

    __tablename__ = "bookmarks"
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    post_id = db.Column(
        db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    action_datetime = db.Column(db.DateTime, nullable=False, default=now)

    post = db.relationship("Post", uselist=False, backref="bookmarks")


db.Index("ix_user_bookmark", Bookmark.user_id, Bookmark.post_id)


class PostView(BaseModel):
    """Post view model."""

    __tablename__ = "post_views"
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    post_id = db.Column(
        db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    action_datetime = db.Column(db.DateTime, nullable=False, default=now)

    post = db.relationship("Post", uselist=False, backref="post_views")


user_excluded_sources = db.Table(
    "user_excluded_sources",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
    db.Column("source_id", db.Integer(), db.ForeignKey("sources.id")),
)


user_excluded_categories = db.Table(
    "user_excluded_categories",
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
    db.Column("category_id", db.Integer(), db.ForeignKey("categories.id")),
)


class User(BaseModel):
    """User model."""

    email = db.Column(db.String(255), unique=True, index=True)
    password = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean(), default=True)
    confirmed = db.Column(db.Boolean(), default=False)
    last_seen = db.Column(db.DateTime)

    # ORM relationships
    excluded_sources = db.relationship(
        "Source",
        secondary=user_excluded_sources,
        lazy="subquery",
        backref=db.backref("user_excluded_sources", lazy=True),
    )
    excluded_categories = db.relationship(
        "Category",
        secondary=user_excluded_categories,
        lazy="subquery",
        backref=db.backref("user_excluded_categories", lazy=True),
    )

    bookmarks = db.relationship(
        "Post",
        secondary="bookmarks",
        order_by="desc(Bookmark.action_datetime)",
        lazy="dynamic",
    )
    post_views = db.relationship(
        "Post",
        secondary="post_views",
        order_by="desc(PostView.action_datetime)",
        lazy="dynamic",
    )

    def set_password(self, password):
        """Set a user's password."""
        self.password = generate_password_hash(password)
        self.save()

    def check_password(self, password):
        """Check a user's password."""
        return check_password_hash(self.password, password)

    @staticmethod
    def get_user_from_identity(identity):
        """Get a user from a JWT."""
        return User.query.filter_by(email=identity).first()

    def get_reset_password_token(self):
        """Get a password reset token."""
        expires_in = 60 * 15  # 15 minutes
        secret = current_app.config["SECRET_KEY"]
        return encode_token("reset_password", self.id, secret, expires_in=expires_in)

    @staticmethod
    def verify_reset_password_token(token):
        """Verify a password reset token."""
        secret = current_app.config["SECRET_KEY"]
        id = decode_token("reset_password", secret, token)
        if id is None:
            return None

        return User.query.get(id)

    def get_email_confirm_token(self):
        """Get an email confirmation token."""
        expires_in = 60 * 60 * 24  # 24 hours
        secret = current_app.config["SECRET_KEY"]
        return encode_token("email_confirm", self.id, secret, expires_in=expires_in)

    @staticmethod
    def verify_email_confirm_token(token):
        """Verify an email confirmation token."""
        secret = current_app.config["SECRET_KEY"]
        id = decode_token("email_confirm", secret, token)
        if id is None:
            return None

        return User.query.get(id)

    def to_dict(self):
        """Return as a dict."""
        return dict(email=self.email, confirmed=self.confirmed)

    def __repr__(self):
        """String representation."""
        return self.email
