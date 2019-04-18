from alembic.command import downgrade, stamp
from alembic.config import Config
from alembic.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

__all__ = ('Base', 'Session', 'downgrade_database', 'get_alembic_config',
           'get_database_revision', 'initialize_database')


Base = declarative_base()
Session = sessionmaker()


def get_alembic_config(engine):
    if isinstance(engine, Engine):
        url = str(engine.url)
    elif isinstance(engine, str):
        url = str(engine)
    else:
        raise TypeError('engine must be a string or an instance of sqlalchemy.'
                        'engine.Engine, not ' + repr(engine))
    cfg = Config()
    cfg.set_main_option('script_location', 'nkzalimi:migrations')
    cfg.set_main_option('sqlalchemy.url', url)
    cfg.set_main_option('url', url)
    return cfg


def initialize_database(engine):
    Base.metadata.create_all(engine, checkfirst=False)
    alembic_cfg = get_alembic_config(engine)
    stamp(alembic_cfg, 'head')


def get_database_revision(engine):
    config = get_alembic_config(engine)
    script = ScriptDirectory.from_config(config)
    result = [None]

    def get_revision(rev, context):
        result[0] = rev and script.get_revision(rev)
        return []
    with EnvironmentContext(config, script, fn=get_revision, as_sql=False,
                            destination_rev=None, tag=None):
        script.run_env()
    return None if result[0] == () else result[0]


def downgrade_database(engine, revision):
    config = get_alembic_config(engine)
    downgrade(config, revision)
