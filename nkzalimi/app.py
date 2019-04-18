import collections
import typing

from settei import config_property
from settei.presets.flask import WebConfiguration
from sqlalchemy.engine import Engine, create_engine
from werkzeug.datastructures import ImmutableDict
from werkzeug.utils import cached_property

from .orm import Session


class App(WebConfiguration):
    database_url = config_property(
        'database.url', str
    )

    sentry_dsn = config_property(
        'sentry.dsn', str, 'Sentry API DSN', default=None
    )

    github_oauth_client_id = config_property(
        'github.oauth_client_id', str
    )

    github_oauth_client_secret = config_property(
        'github.oauth_client_secret', str
    )

    twitter_oauth_client_id = config_property(
        'twitter.oauth_client_id', str
    )

    twitter_oauth_client_secret = config_property(
        'twitter.oauth_client_secret', str
    )

    @cached_property
    def database_engine(self) -> Engine:
        url = self.database_url
        db_options = dict(self.get('database', ()))
        db_options.pop('url', None)
        return create_engine(url, **db_options)

    def create_session(self, bind: Engine=None) -> Session:
        if bind is None:
            bind = self.database_engine
        return Session(bind=bind)

    @cached_property
    def web_config(self) -> typing.Mapping[str, typing.Any]:
        web_config = self.config.get('web', {})
        if not isinstance(web_config, collections.abc.Mapping):
            web_config = {}
        return ImmutableDict((k.upper(), v) for k, v in web_config.items())
