from flask import Blueprint

from .entities import *


bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/')
def hello():
    return 'world!'
