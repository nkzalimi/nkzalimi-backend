from gevent.monkey import patch_all; patch_all()  # noqa

import argparse
import logging
import os
import pathlib

from gevent.pywsgi import WSGIServer
from ormeasy.alembic import upgrade_database

from nkzalimi.app import App
from nkzalimi.orm import Base, get_alembic_config
from nkzalimi.web import create_web_app


parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument('-H', '--host', default='0.0.0.0')
parser.add_argument('-p', '--port', type=int,
                    default=int(os.environ.get('PORT', 1585)),
                    help='port number to listen')
parser.add_argument('-d', '--debug', action='store_true', default=False)
parser.add_argument('--log-file', default='-', help='file to write logs')
parser.add_argument('--without-alembic-upgrade', action='store_true')
parser.add_argument('-s', '--shell', action='store_true', default=False)
parser.add_argument('config', type=pathlib.Path)


debug_loggers = {
    'sqlalchemy.engine.base.Engine': logging.INFO,
    'nkzalimi': logging.DEBUG,
}


def run_shell(wsgi_app: 'Flask'):
    from nkzalimi.web import app
    from ptpython.repl import embed
    l = locals()
    wsgi_app.app_context().push()
    l['session'] = app.create_session()
    embed(globals(), l)


def main():
    args = parser.parse_args()
    logging.basicConfig(
        format='%(levelname).1s | %(name)s | %(message)s',
        level=logging.INFO,
        **({} if args.log_file == '-' else {'filename': args.log_file})
    )
    if not args.config.is_file():
        parser.error('file not found: {!s}'.format(args.config))
    app = App.from_path(args.config)
    if not args.without_alembic_upgrade:
        config = get_alembic_config(app.database_engine)
        upgrade_database(config, app.database_engine, Base.metadata)
    wsgi_app = create_web_app(app)
    if args.shell:
        run_shell(wsgi_app)
    else:
        if args.debug:
            for logger, level in debug_loggers.items():
                logging.getLogger(logger).setLevel(level)
            wsgi_app.run(host=args.host, port=args.port, debug=True)
        else:
            logging.getLogger('gevent.pywsgi').info(
                'Running on http://%s:%d/',
                args.host, args.port
            )
            http_server = WSGIServer((args.host, args.port), wsgi_app)
            try:
                http_server.serve_forever()
            except KeyboardInterrupt:
                raise SystemExit


if __name__ == '__main__':
    main()
