"""App views module."""
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, redirect, render_template, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_optional,
    jwt_required,
)
from sqlalchemy import desc
from werkzeug.datastructures import MultiDict

from aggrep import cache
from aggrep.api.email import send_email
from aggrep.api.forms import (
    ConfirmEmailForm,
    LoginForm,
    RegisterForm,
    RequestResetForm,
    ResetPasswordForm,
    UpdateEmailForm,
    UpdatePasswordForm,
)
from aggrep.models import (
    Bookmark,
    Category,
    Feed,
    Post,
    PostAction,
    PostView,
    Source,
    User,
)
from aggrep.utils import get_cache_key, now

N_RECENT_POSTS = 10
POST_LIMIT = 500
POPULAR = "popular"
LATEST = "latest"
RELEVANT = "relevant"

app = Blueprint("app", __name__, template_folder="templates")
api = Blueprint("api", __name__, url_prefix="/v1", template_folder="templates")


@api.before_app_request
@jwt_optional
def before_request():
    """Perform tasks before processing a request."""
    current_user = User.get_user_from_identity(get_jwt_identity())
    if current_user is not None:
        current_user.update(last_seen=datetime.utcnow())


# === Route Helpers === #


def sort_posts(posts, sort):
    """Sort posts by a predefined format."""
    if sort == POPULAR:
        posts = posts.order_by(desc(Post.ctr), desc(Post.published_datetime))
    else:
        posts = posts.order_by(desc(Post.published_datetime))

    return posts


def register_impression(post_id):
    """Register post impressions."""

    pa = PostAction.query.filter(PostAction.post_id == post_id).first()
    pa.impressions += 1
    pa.save()
    return True


def register_click(post_id):
    """Register post clicks."""

    pa = PostAction.query.filter(PostAction.post_id == post_id).first()
    pa.clicks += 1
    pa.save()
    return True


# === Post Routes === #


@app.route("/<uid>")
def follow_redirect(uid):
    """Follow a post redirect."""

    p = Post.from_uid(uid)
    register_click(p.id)
    return redirect(p.link)


@api.route("/posts")
@jwt_optional
def all_posts():
    """Get front page posts."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort = request.args.get("sort", POPULAR, type=str)

    identity = get_jwt_identity()
    current_user = User.get_user_from_identity(identity)
    cache_key = get_cache_key("all_posts", identity, page, per_page, sort)
    cached = cache.get(cache_key)

    if cached is None:
        delta = now() - timedelta(days=7)
        posts = Post.query.filter(Post.published_datetime >= delta)

        if current_user:
            sources = [s.id for s in current_user.excluded_sources]
            categories = [c.id for c in current_user.excluded_categories]
            posts = posts.filter(
                Post.feed.has(Feed.category.has(Category.id.notin_(categories))),
                Post.feed.has(Feed.source.has(Source.id.notin_(sources))),
            )

        posts = (
            posts.order_by(desc(Post.published_datetime)).limit(POST_LIMIT).from_self()
        )
        posts = sort_posts(posts, sort)

        if sort == POPULAR:
            title = "Popular Posts"
        else:
            title = "Latest Posts"

        cached = dict(**Post.to_collection_dict(posts, page, per_page), title=title)
        cache.set(cache_key, cached, timeout=60)

    for item in cached["items"]:
        register_impression(item["id"])

    return jsonify(**cached), 200


@api.route("/source/<source>")
@jwt_optional
def posts_by_source(source):
    """Get posts by a source."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort = request.args.get("sort", POPULAR, type=str)

    identity = get_jwt_identity()
    current_user = User.get_user_from_identity(identity)
    cache_key = get_cache_key(
        "posts_by_source", identity, page, per_page, sort, route_arg=source
    )
    cached = cache.get(cache_key)

    if cached is None:
        delta = now() - timedelta(days=7)
        src = Source.query.filter_by(slug=source).first()
        posts = Post.query.filter(
            Post.published_datetime >= delta,
            Post.feed.has(Feed.source.has(Source.slug == source)),
        )

        if current_user:
            categories = [c.id for c in current_user.excluded_categories]
            posts = posts.filter(
                Post.feed.has(Feed.category.has(Category.id.notin_(categories)))
            )

        posts = (
            posts.order_by(desc(Post.published_datetime)).limit(POST_LIMIT).from_self()
        )
        posts = sort_posts(posts, sort)

        if sort == POPULAR:
            title = "Popular Posts by {}".format(src.title)
        else:
            title = "Latest Posts by {}".format(src.title)

        cached = dict(
            **Post.to_collection_dict(posts, page, per_page, source=source), title=title
        )
        cache.set(cache_key, cached, timeout=60)

    for item in cached["items"]:
        register_impression(item["id"])

    return jsonify(**cached), 200


@api.route("/category/<category>")
@jwt_optional
def posts_by_category(category):
    """Get posts by a category."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort = request.args.get("sort", POPULAR, type=str)

    identity = get_jwt_identity()
    current_user = User.get_user_from_identity(identity)
    cache_key = get_cache_key(
        "posts_by_category", identity, page, per_page, sort, route_arg=category
    )
    cached = cache.get(cache_key)

    if cached is None:
        delta = now() - timedelta(days=7)
        cat = Category.query.filter_by(slug=category).first()
        posts = Post.query.filter(
            Post.published_datetime >= delta,
            Post.feed.has(Feed.category.has(Category.slug == category)),
        )

        if current_user:
            sources = [s.id for s in current_user.excluded_sources]
            posts = posts.filter(
                Post.feed.has(Feed.source.has(Source.id.notin_(sources)))
            )

        posts = (
            posts.order_by(desc(Post.published_datetime)).limit(POST_LIMIT).from_self()
        )
        posts = sort_posts(posts, sort)

        if sort == POPULAR:
            title = "Popular Posts in {}".format(cat.title)
        else:
            title = "Latest Posts in {}".format(cat.title)

        cached = dict(
            **Post.to_collection_dict(posts, page, per_page, category=category),
            title=title,
        )
        cache.set(cache_key, cached, timeout=60)

    for item in cached["items"]:
        register_impression(item["id"])

    return jsonify(**cached), 200


@api.route("/similar/<uid>")
@jwt_optional
def similar_posts(uid):
    """Get similar posts."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort = LATEST

    identity = get_jwt_identity()
    cache_key = get_cache_key(
        "similar_posts", identity, page, per_page, sort, route_arg=uid
    )
    cached = cache.get(cache_key)

    if cached is None:
        _post = Post.from_uid(uid)
        source_post = Post.query.filter(Post.id == _post.id)
        posts = source_post.union(_post.similar_posts)
        posts = sort_posts(posts, sort)

        title = "More Coverage"

        cached = dict(
            **Post.to_collection_dict(posts, page, per_page, uid=uid), title=title
        )
        cache.set(cache_key, cached, timeout=180)

    for item in cached["items"]:
        register_impression(item["id"])

    return jsonify(**cached), 200


@api.route("/search")
@jwt_optional
def search_posts():
    """Search posts."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    term = request.args.get("query", 1, type=str)
    sort = RELEVANT

    identity = get_jwt_identity()
    cache_key = get_cache_key(
        "similar_posts", identity, page, per_page, sort, route_arg=term
    )
    cached = cache.get(cache_key)

    if cached is None:
        delta = now() - timedelta(days=7)
        searchable_posts = Post.query.filter(Post.published_datetime >= delta)

        query = " & ".join(term.split(" "))

        posts = Post.search(searchable_posts, query)
        current_app.logger.info(term)
        current_app.logger.info(query)

        title = "Search Results"
        cached = dict(**Post.to_collection_dict(posts, page, per_page), title=title)
        cache.set(cache_key, cached, timeout=180)

    for item in cached["items"]:
        register_impression(item["id"])

    return jsonify(**cached), 200


@api.route("/bookmarks")
@jwt_required
def bookmarked_posts():
    """Manage a user's bookmarked posts."""
    current_user = User.get_user_from_identity(get_jwt_identity())

    if request.method == "GET":
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        posts = current_user.bookmarks

        for p in posts:
            register_impression(p.id)

        return (
            jsonify(
                **Post.to_collection_dict(posts, page, per_page),
                title="Bookmarked Posts",
            ),
            200,
        )


@api.route("/bookmarks/ids", methods=["GET", "POST", "DELETE"])
@jwt_required
def bookmarked_post_ids():
    """Manage a user's bookmarked post IDs."""
    current_user = User.get_user_from_identity(get_jwt_identity())

    if request.method == "GET":
        return jsonify(bookmarks=[b.uid for b in current_user.bookmarks]), 200
    elif request.method == "POST":
        payload = request.get_json() or {}
        uid = payload.get("uid")

        if uid is None:
            return jsonify(msg="No post UID provided."), 400

        post = Post.from_uid(uid)
        if post is None:
            return jsonify(msg="Post UID is invalid."), 400

        is_bookmarked = Bookmark.query.filter_by(
            user_id=current_user.id, post_id=post.id
        ).first()
        if not is_bookmarked:
            Bookmark.create(user_id=current_user.id, post_id=post.id)
        return (
            jsonify(
                dict(
                    bookmarks=[b.uid for b in current_user.bookmarks],
                    msg="Bookmark saved!",
                )
            ),
            200,
        )

    elif request.method == "DELETE":
        payload = request.get_json() or {}
        uid = payload.get("uid")
        post = Post.from_uid(uid)

        instance = Bookmark.query.filter_by(
            user_id=current_user.id, post_id=post.id
        ).first()
        instance.delete()
        return (
            jsonify(
                dict(
                    bookmarks=[b.uid for b in current_user.bookmarks],
                    msg="Bookmark removed!",
                )
            ),
            200,
        )


@api.route("/views", methods=["GET", "POST"])
@jwt_required
def viewed_posts():
    """Manage a user's viewed posts."""
    current_user = User.get_user_from_identity(get_jwt_identity())

    if request.method == "GET":
        posts = current_user.post_views.limit(N_RECENT_POSTS).from_self()

        for p in posts:
            register_impression(p.id)

        return (
            jsonify(
                **Post.to_collection_dict(posts, 1, N_RECENT_POSTS),
                title="Recently Viewed Posts",
            ),
            200,
        )
    elif request.method == "POST":
        payload = request.get_json() or {}
        uid = payload.get("uid")

        if uid is None:
            return jsonify(msg="No post UID provided."), 400

        post = Post.from_uid(uid)
        if post is None:
            return jsonify(msg="Post UID is invalid."), 400

        is_viewed = PostView.query.filter_by(
            user_id=current_user.id, post_id=post.id
        ).first()
        if not is_viewed:
            PostView.create(user_id=current_user.id, post_id=post.id)
        return (jsonify(dict(msg="View saved.")), 200)


# === Taxonomy Routes === #


@api.route("/sources")
def sources():
    """Get all sources."""
    return (
        jsonify(
            sources=[
                s.to_dict() for s in Source.query.order_by(Source.title.asc()).all()
            ]
        ),
        200,
    )


@api.route("/categories")
def categories():
    """Get all categories."""
    return (
        jsonify(
            categories=[
                c.to_dict() for c in Category.query.order_by(Category.id.asc()).all()
            ]
        ),
        200,
    )


@api.route("/manage/sources", methods=["GET", "POST"])
@jwt_required
def manage_sources():
    """Manage a user's excluded sources."""
    current_user = User.get_user_from_identity(get_jwt_identity())
    sources = Source.query.order_by(Source.title.asc()).all()
    all_source_ids = [s.id for s in sources]

    if request.method == "POST":
        data = request.get_json()
        excluded_sources = data["excluded_sources"]
        excluded_objects = Source.query.filter(Source.id.in_(excluded_sources)).all()
        current_user.excluded_sources = excluded_objects
        current_user.save()

    user_excludes = [c.id for c in current_user.excluded_sources]
    user_includes = list(set(all_source_ids).difference(set(user_excludes)))

    return (
        jsonify(
            msg="Your preferred sources have been updated.",
            excluded_sources=user_excludes,
            included_sources=user_includes,
        ),
        200,
    )


@api.route("/manage/categories", methods=["GET", "POST"])
@jwt_required
def manage_categories():
    """Manage a user's excluded categories."""
    current_user = User.get_user_from_identity(get_jwt_identity())
    categories = Category.query.order_by(Category.title.asc()).all()
    all_category_ids = [c.id for c in categories]

    if request.method == "POST":
        data = request.get_json()
        excluded_categories = data["excluded_categories"]
        excluded_objects = Category.query.filter(
            Category.id.in_(excluded_categories)
        ).all()
        current_user.excluded_categories = excluded_objects
        current_user.save()

    user_excludes = [c.id for c in current_user.excluded_categories]
    user_includes = list(set(all_category_ids).difference(set(user_excludes)))
    return (
        jsonify(
            msg="Your preferred categories have been updated.",
            excluded_categories=user_excludes,
            included_categories=user_includes,
        ),
        200,
    )


# === Auth Routes === #


@api.route("auth/token/confirm")
@jwt_required
def auth_token_confirm():
    """Confirm a user's token."""
    current_user = User.get_user_from_identity(get_jwt_identity())
    payload = dict(
        msg="Token verification successful!",
        user=current_user.to_dict(),
        access_token=create_access_token(identity=current_user.email),
    )
    return jsonify(payload), 200


@api.route("/auth/login", methods=["POST"])
def auth_login():
    """Log a user into the application."""
    if get_jwt_identity():
        return jsonify(dict(msg="You are already logged in.")), 400

    if not request.is_json:
        return jsonify(dict(msg="Invalid request.")), 400

    form = LoginForm(MultiDict(request.get_json()))
    if form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            return jsonify(dict(msg="Invalid email address or password")), 400
        payload = dict(
            msg="Login Successful",
            user=user.to_dict(),
            access_token=create_access_token(identity=user.email),
        )
        return jsonify(payload), 200
    else:
        payload = dict(msg="Unable to complete login.", errors=dict())
        for field, errors in form.errors.items():
            for error in errors:
                key = getattr(form, field).label.text
                payload["errors"][key] = error
        return jsonify(payload), 400


@api.route("/auth/register", methods=["POST"])
def auth_register():
    """Register a new user."""
    if get_jwt_identity():
        return jsonify(dict(msg="You are already registered.")), 400

    if not request.is_json:
        return jsonify(dict(msg="Invalid request.")), 400

    form = RegisterForm(MultiDict(request.get_json()))
    if form.validate():
        user = User.create(email=form.email.data)
        user.set_password(form.password.data)
        token = user.get_email_confirm_token()
        email_data = dict(
            subject="[Aggregate Report] Welcome!",
            recipients=[user.email],
            text_body=render_template(
                "email/welcome.txt",
                user=user,
                token=token,
                ui_url=current_app.config["UI_URL"],
            ),
            html_body=render_template(
                "email/welcome.html",
                user=user,
                token=token,
                ui_url=current_app.config["UI_URL"],
            ),
        )
        send_email(email_data)
        payload = dict(
            msg="Registration Successful!",
            user=user.to_dict(),
            access_token=create_access_token(identity=form.email.data),
        )
        return jsonify(payload), 200
    else:
        payload = dict(msg="Unable to complete registration.", errors=dict())
        for field, errors in form.errors.items():
            for error in errors:
                key = getattr(form, field).label.text
                payload["errors"][key] = error
        return jsonify(payload), 400


@api.route("/auth/email/update", methods=["POST"])
@jwt_required
def auth_email_update():
    """Update an email address."""
    current_user = User.get_user_from_identity(get_jwt_identity())

    if not request.is_json:
        return jsonify(dict(msg="Invalid request.")), 400

    form = UpdateEmailForm(MultiDict(request.get_json()))
    if form.validate():
        current_user.update(email=form.email.data, confirmed=False)

        token = current_user.get_email_confirm_token()
        email_data = dict(
            subject="[Aggregate Report] Confirm your email!",
            recipients=[current_user.email],
            text_body=render_template(
                "email/confirm_email.txt",
                user=current_user,
                token=token,
                ui_url=current_app.config["UI_URL"],
            ),
            html_body=render_template(
                "email/confirm_email.html",
                user=current_user,
                token=token,
                ui_url=current_app.config["UI_URL"],
            ),
        )
        send_email(email_data)
        payload = dict(
            msg="Your email has been updated. Please check your email for a confirmation link.",
            auth=dict(
                user=current_user.to_dict(),
                access_token=create_access_token(identity=current_user.email),
            ),
        )
        return jsonify(payload), 200
    else:
        payload = dict(msg="Unable to update email.", errors=dict())
        for field, errors in form.errors.items():
            for error in errors:
                key = getattr(form, field).label.text
                payload["errors"][key] = error
        return jsonify(payload), 400


@api.route("/auth/email/confirm/request", methods=["POST"])
@jwt_required
def auth_email_confirm_request():
    """Request an email confirmation token."""
    current_user = User.get_user_from_identity(get_jwt_identity())

    if not request.is_json:
        return jsonify(dict(msg="Invalid request.")), 400

    if current_user.confirmed:
        return jsonify(dict(msg="User is already confirmed")), 200

    token = current_user.get_email_confirm_token()
    email_data = dict(
        subject="[Aggregate Report] Confirm your email!",
        recipients=[current_user.email],
        text_body=render_template(
            "email/confirm_email.txt",
            user=current_user,
            token=token,
            ui_url=current_app.config["UI_URL"],
        ),
        html_body=render_template(
            "email/confirm_email.html",
            user=current_user,
            token=token,
            ui_url=current_app.config["UI_URL"],
        ),
    )
    send_email(email_data)
    payload = dict(msg="A confirmation email has been sent to your email address.")
    return jsonify(payload), 200


@api.route("/auth/email/confirm/token", methods=["POST"])
def auth_email_confirm_token():
    """Verify an email confirmation token and update the model."""
    if not request.is_json:
        return jsonify(dict(msg="Invalid request.")), 400

    form = ConfirmEmailForm(MultiDict(request.get_json()))
    if form.validate():
        user = User.verify_email_confirm_token(form.token.data)
        if not user:
            payload = dict(msg="Confirmation token is invalid.")
            return jsonify(payload), 400

        user.update(confirmed=True)
        payload = dict(msg="Your email address has been confirmed.")
        return jsonify(payload), 200
    else:
        payload = dict(msg="Unable to verify the email account.", errors=dict())
        for field, errors in form.errors.items():
            for error in errors:
                key = getattr(form, field).label.text
                payload["errors"][key] = error
        return jsonify(payload), 400


@api.route("/auth/password/update", methods=["POST"])
@jwt_required
def auth_password_update():
    """Update a user's password."""
    current_user = User.get_user_from_identity(get_jwt_identity())

    if not request.is_json:
        return jsonify(dict(msg="Invalid request.")), 400

    form = UpdatePasswordForm(MultiDict(request.get_json()))
    if form.validate():
        if not current_user.check_password(form.curr_password.data):
            payload = dict(msg="Password incorrect.")
            return jsonify(payload), 400

        current_user.set_password(form.new_password.data)
        email_data = dict(
            subject="[Aggregate Report] Your password has been updated",
            recipients=[current_user.email],
            text_body=render_template(
                "email/password_updated.txt",
                user=current_user,
                ui_url=current_app.config["UI_URL"],
            ),
            html_body=render_template(
                "email/password_updated.html",
                user=current_user,
                ui_url=current_app.config["UI_URL"],
            ),
        )
        send_email(email_data)
        payload = dict(msg="Your password has been updated.")
        return jsonify(payload), 200
    else:
        payload = dict(msg="Unable to update your password.", errors=dict())
        for field, errors in form.errors.items():
            for error in errors:
                key = getattr(form, field).label.text
                payload["errors"][key] = error
        return jsonify(payload), 400


@api.route("/auth/password/reset", methods=["POST"])
def auth_password_reset():
    """Request password reset link."""
    if not request.is_json:
        return jsonify(dict(msg="Invalid request.")), 400

    form = RequestResetForm(MultiDict(request.get_json()))
    if form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_password_token()
            email_data = dict(
                subject="[Aggregate Report] Reset your password",
                recipients=[user.email],
                text_body=render_template(
                    "email/reset_instructions.txt",
                    user=user,
                    token=token,
                    ui_url=current_app.config["UI_URL"],
                ),
                html_body=render_template(
                    "email/reset_instructions.html",
                    user=user,
                    token=token,
                    ui_url=current_app.config["UI_URL"],
                ),
            )
            send_email(email_data)

            payload = dict(
                msg="A confirmation link has been sent to your email address."
            )
            return jsonify(payload), 200
        else:
            payload = dict(msg="The email address provided does not exist.")
            return jsonify(payload), 400
    else:
        payload = dict(msg="Request Unsuccessful", errors=dict())
        for field, errors in form.errors.items():
            for error in errors:
                key = getattr(form, field).label.text
                payload["errors"][key] = error
        return jsonify(payload), 400


@api.route("/auth/password/reset/confirm", methods=["POST"])
def auth_password_reset_confirm():
    """Reset a password from reset link."""
    if not request.is_json:
        return jsonify(dict(msg="Invalid request.")), 400

    form = ResetPasswordForm(MultiDict(request.get_json()))
    if form.validate():
        user = User.verify_reset_password_token(form.token.data)
        if not user:
            payload = dict(msg="Reset token is invalid.")
            return jsonify(payload), 400

        user.set_password(form.new_password.data)
        email_data = dict(
            subject="[Aggregate Report] Your password has been reset",
            recipients=[user.email],
            text_body=render_template(
                "email/password_updated.txt",
                user=user,
                ui_url=current_app.config["UI_URL"],
            ),
            html_body=render_template(
                "email/password_updated.html",
                user=user,
                ui_url=current_app.config["UI_URL"],
            ),
        )
        send_email(email_data)
        payload = dict(msg="Your password has been updated.")
        return jsonify(payload), 200
    else:
        payload = dict(msg="Unable to complete password update.", errors=dict())
        for field, errors in form.errors.items():
            for error in errors:
                key = getattr(form, field).label.text
                payload["errors"][key] = error
        return jsonify(payload), 400
