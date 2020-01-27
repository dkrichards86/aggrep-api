from aggrep import ma
from aggrep.models import Category, Feed, Post, Source, User


class CategorySchema(ma.ModelSchema):
    class Meta:
        model = Category
        fields = ("id", "slug", "title",)


class SourceSchema(ma.ModelSchema):
    class Meta:
        model = Source
        fields = ("id", "slug", "title",)


class FeedSchema(ma.ModelSchema):
    class Meta:
        model = Feed
        fields = ("source", "category",)

    category = ma.Nested(CategorySchema)
    source = ma.Nested(SourceSchema)


class PostSchema(ma.ModelSchema):
    class Meta:
        model = Post
        fields = ("id", "uid", "title", "link", "post_url", "feed", "published_datetime",)

    feed = ma.Nested(FeedSchema)


class UserSchema(ma.ModelSchema):
    class Meta:
        model = User
        fields = ("email", "confirmed",)


categories_schema = CategorySchema(many=True)
sources_schema = SourceSchema(many=True)
feed_schema = FeedSchema()
posts_schema = PostSchema(many=True)
user_schema = UserSchema()