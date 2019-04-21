import uuid
import typing

from flask import Flask, current_app, request
from flask_login import LoginManager
from raven.contrib.flask import Sentry
from sqlalchemy.orm.session import Session
from werkzeug.local import LocalProxy

from .app import App
from .entities import User


app = LocalProxy(lambda: current_app.config['APP'])
login_manager = LoginManager()


@LocalProxy
def session() -> Session:
    ctx = request._get_current_object()
    try:
        session = ctx._current_session
    except AttributeError:
        session = app.create_session()
        ctx._current_session = session
    return session


def close_session(exception=None):
    ctx = request._get_current_object()
    if hasattr(ctx, '_current_session'):
        s = ctx._current_session
        if exception is not None:
            s.rollback()
        s.close()


@login_manager.user_loader
def load_user(user_id: str) -> typing.Optional[User]:
    return session.query(User).filter_by(id=uuid.UUID(user_id)).one_or_none()


def create_web_app(app: App) -> Flask:
    from .api import bp as bp_api
    from .pages import bp as bp_pages
    from .user import bp as bp_user
    flask_app = Flask(__name__)
    if app.sentry_dsn is not None:
        sentry = Sentry(flask_app, dsn=app.sentry_dsn)
    flask_app.register_blueprint(bp_api)
    flask_app.register_blueprint(bp_pages)
    flask_app.register_blueprint(bp_user)
    flask_app.teardown_request(close_session)
    login_manager.init_app(flask_app)
    flask_app.config.update(app.web_config)
    flask_app.config['APP'] = app
    return flask_app
