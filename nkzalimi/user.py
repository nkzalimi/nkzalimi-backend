from flask import Blueprint, abort, redirect, request, url_for
from flask_login import login_user
from requests import get as requests_get, post as requests_post
from requests_oauthlib import OAuth1Session
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.urls import url_decode

from .entities import GithubLogin, OAuthSession, TwitterLogin, User
from .web import app, session


bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/oauth/authorized/github/')
def login_github():
    at_response = requests_post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': app.github_oauth_client_id,
            'client_secret': app.github_oauth_client_secret,
            'code': request.args['code'],
            'accept': 'application/json'
        }
    )
    assert at_response.status_code == 200
    response_data = url_decode(at_response.text)
    access_token = response_data['access_token']
    user_response = requests_get('https://api.github.com/user',
                                 params={'access_token': access_token})
    assert user_response.status_code == 200
    user_data = user_response.json()
    try:
        login = session.query(GithubLogin).filter_by(
            uid=user_data['login']
        ).one()
    except NoResultFound:
        login = GithubLogin(user=User(), uid=user_data['login'])
        login.user.display_name = login.identifier()
        session.add(login)
        session.commit()
    login_user(login.user)
    return redirect(url_for('pages.index'))


@bp.route('/login/twitter/')
def request_login_twitter():
    sess = OAuth1Session(
        client_key=app.twitter_oauth_client_id,
        client_secret=app.twitter_oauth_client_secret
    )
    url = 'https://api.twitter.com/oauth/request_token'
    data = url_decode(sess.get(url).text)
    oauth_token = data['oauth_token']
    oauth_token_secret = data['oauth_token_secret']
    session.add(OAuthSession(id=oauth_token, secret=oauth_token_secret))
    session.commit()
    redirect_url = 'https://api.twitter.com/oauth/authenticate?oauth_token={}' \
        .format(oauth_token)
    return redirect(redirect_url)


@bp.route('/oauth/authorized/twitter/')
def login_twitter():
    oauth_token = request.args['oauth_token']
    oauth_verifier = request.args['oauth_verifier']
    try:
        oauth_session = session.query(OAuthSession).filter_by(
            id=oauth_token
        ).one()
    except NoResultFound:
        abort(400)
    session.delete(oauth_session)
    session.commit()
    sess = OAuth1Session(
        client_key=app.twitter_oauth_client_id,
        client_secret=app.twitter_oauth_client_secret,
        resource_owner_key=oauth_session.id,
        resource_owner_secret=oauth_session.secret
    )
    res = sess.post('https://api.twitter.com/oauth/access_token',
                    data={'oauth_verifier': oauth_verifier})
    assert res.status_code < 400
    data = url_decode(res.text)
    try:
        login = session.query(TwitterLogin).filter_by(
            uid=data['screen_name']
        ).one()
    except NoResultFound:
        login = TwitterLogin(user=User(), uid=data['screen_name'])
        login.user.display_name = login.identifier()
        session.add(login)
        session.commit()
    login_user(login.user)
    return redirect(url_for('pages.index'))
