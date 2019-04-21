import base64
import functools
import typing
import uuid

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from geoalchemy2.functions import ST_Distance_Sphere
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import or_
from sqlalchemy_utc import utcnow

from .entities import (BlockUserRequest, BusinessEntity, BusinessEntityStatus,
                       BusinessEntityRevision, CreationRequest,
                       MarkAsDuplicateRequest, Poll, Request, RevisionKind,
                       RevisionRequest)
from .serializer import serialize
from .util import latlng_to_point
from .web import session


bp = Blueprint('api', __name__, url_prefix='/api')


def error(type: str, message: str, status_code: int = 400):
    response = jsonify(
        result='error',
        error={
            'type': type,
            'message': message
        }
    )
    response.status_code = status_code
    return response


def success(**data):
    return jsonify(result='success', data=data)


def admin_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.admin:
            return error('admin_required', 'Administrator access is required.',
                         403)
        return f(*args, **kwargs)
    return wrapper


@bp.route('/user/')
@login_required
def get_user():
    return success(user=serialize(current_user))


@bp.route('/business_entities/')
def get_business_entities():
    next = request.args.get('next')
    if next:
        try:
            lat, lng, radius, offset, limit, status, keyword = \
                base64.b64decode(next).decode('utf-8').split('|', 5)
        except ValueError:
            return error(
                'invalid_arg_format', f'Invalid "next" parameter.', 400
            )
        if lat and lng:
            coordinate = latlng_to_point(latitude, longitude)
            radius = float(radius)
        else:
            coordinate = None
        limit = int(limit)
        if not keyword:
            keyword = None
        if status:
            status = BusinessEntityStatus(status)
        else:
            status = None
        offset = int(offset)
    else:
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')
        if latitude and longitude:
            coordinate = latlng_to_point(latitude, longitude)
            radius = request.args.get('radius')
            if radius:
                radius = float(radius)
                if radius > 100000.0:
                    radius = 100000.0
            else:
                radius = 5000.0
        else:
            coordinate = None
        limit = request.args.get('limit')
        if limit:
            limit = int(limit)
        else:
            limit = 100
        offset = request.args.get('offset')
        if offset:
            offset = int(offset)
        else:
            offset = 0
        status = request.args.get('status')
        if status:
            status = BusinessEntityStatus(status)
        keyword = request.args.get('keyword')
    q = session.query(BusinessEntity).join(BusinessEntity.latest_revision)
    if coordinate:
        q = q.filter(
            ST_Distance_Sphere(
                BusinessEntityRevision.coordinate, coordinate
            ) < radius
        ).order_by(
            ST_Distance_Sphere(
                BusinessEntityRevision.coordinate, coordinate
            )
        )
    else:
        q = q.order_by(BusinessEntity.created_at.desc())
    if status:
        q = q.filter(BusinessEntityRevision.status == status)
    if keyword:
        clause = f'%{keyword}%'
        q = q.filter(or_(
            BusinessEntityRevision.name.like(clause),
            BusinessEntityRevision.address.like(clause),
            BusinessEntityRevision.address_sub.like(clause)))
    q = q.limit(limit + 1).offset(offset)
    result = q.all()
    if len(result) == limit + 1:
        next_offset = offset + limit
        payload = '{}|{}|{}|{}|{}|{}|{}'.format(
            lat if lat else '',
            lng if lng else '',
            radius if radius else '',
            offset,
            limit,
            status.value if status else '',
            keyword if keyword else ''
        )
        next = base64.b64encode(payload.encode('utf-8'))
        result = result[:limit]
    else:
        next = None
    return success(business_entities=[serialize(i) for i in result],
                   next=next)
        

@bp.route('/business_entity/<uuid:entity_id>/')
def get_business_entity(entity_id: uuid.UUID):
    be = session.query(BusinessEntity).get(entity_id)
    if not be:
        return error('object_not_found', f'Entity "{entity_id}" not found',
                     404)
    requests = session.query(RevisionRequest).filter(
        RevisionRequest.business_entity == be,
        ~RevisionRequest.committed
    )
    return success(entity=serialize(be),
                   requests=[serialize(i) for i in requests])
    

@bp.route('/request/creation/', methods=['PUT'])
@login_required
def put_creation_request():
    data = request.json
    name = data['name']
    category = data['category']
    status = BusinessEntityStatus(data['status'])
    address = data['address']
    address_sub = data['address_sub']
    coordinate = latlng_to_point(data['latitude'], data['longitude'])
    req = CreationRequest(
        submitted_by=current_user,
        name=name,
        category=category,
        status=status,
        address=address,
        address_sub=address_sub,
        coordinate=coordinate
    )
    session.add(req)
    session.commit()
    return success(request=serialize(req))


@bp.route('/request/revision/', methods=['PUT'])
@login_required
def put_revision_request():
    data = request.json
    business_entity_id = data['business_entity_id']
    kind = RevisionKind(data['kind'])
    data = data['data']
    if session.query(RevisionRequest).filter(
            ~RevisionRequest.committed,
            RevisionRequest.submitted_by == current_user,
            RevisionRequest.business_entity_id == business_entity_id
    ).count() > 0:
        return error(
            'previous_request_present',
            f'There is an existing request on "{business_entity_id}.',
            400
        )
    be = session.query(BusinessEntity).get(business_entity_id)
    if be is None:
        return error('object_not_found', f'Entity "{entity_id}" not found',
                     404)
    if kind is RevisionKind.status:
        bes = BusinessEntityStatus(data)
        latest = be.latest_revision
        if bes is BusinessEntityStatus.kids_exclusive_withdrawn and \
           latest.status is BusinessEntityStatus.kids_friendly:
            return error('invalid_parameter',
                         f'Invalid state transition: {latest.status} to {bes}',
                         400)
    req = RevisionRequest(
        submitted_by=current_user,
        business_entity=be,
        revision_kind=kind,
        data=data
    )
    session.add(req)
    session.commit()
    return success(request=serialize(req))


@bp.route('/requests/<uuid:request_id>/', methods=['GET'])
def get_request(request_id: uuid.UUID):
    req = session.query(Request).get(request_id)
    if not req:
        return error('object_not_found', f'Request "{request_id}" not found',
                     404)
    return success(request=serialize(req))


@bp.route('/requests/<uuid:request_id>/', methods=['DELETE'])
def delete_request(request_id: uuid.UUID):
    req = session.query(Request).get(request_id)
    if not req:
        return error('object_not_found', f'Request "{request_id}" not found',
                     404)
    if req.committed:
        return error('request_alread_committed',
                     f'Request "{request_id}" has already been committed.',
                     400)
    session.delete(req)
    session.commit()
    return success()


@bp.route('/requests/<uuid:request_id>/poll/', methods=['POST'])
def poll_request(request_id: uuid.UUID):
    data = request.json
    upvote = data['upvote']
    req = session.query(Request).get(request_id)
    if not req:
        return error('object_not_found', f'Request "{request_id}" not found',
                     404)
    if req.committed:
        return error('request_already_committed',
                     f'Request "{request_id}" has been already committed.',
                     400)
    poll = session.query(Poll).filter_by(
        request=req, user=current_user
    ).one_or_none()
    if poll:
        poll.upvote = upvote
    else:
        poll = Poll(request=req, user=current_user, upvote=upvote)
        session.add(poll)
    session.commit()
    return success(request=serialize(req))


@bp.route('/requests/<uuid:request_id>/commit/', methods=['POST'])
@admin_required
def commit_request(request_id: uuid.UUID):
    req = session.query(Request).get(request_id)
    if not req:
        return error('object_not_found', f'Request "{request_id}" not found',
                     404)
    if req.committed:
        return error('request_already_committed',
                     f'Request "{request_id}" has been already committed.',
                     400)
    if isinstance(req, CreationRequest):
        be = req.create()
        req.committed_at = utcnow()
        session.add(be)
        session.commit()
        return success(business_entity=serialize(be))
    elif isinstance(req, MarkAsDuplicateRequest):
        ber = req.mark_as_duplicate()
        req.committed_at = utcnow()
        session.add(ber)
        session.commit()
        return success(business_entity=serialize(req.business_entity))
    elif isinstance(req, RevisionRequest):
        ber = req.revise()
        req.committed_at = utcnow()
        session.add(ber)
        session.commit()
        return success(business_entity=serialize(ber.business_entity))
    elif isinstance(req, BlockUserRequest):
        req.block()
        req.committed_at = utcnow()
        session.commit()
        return success(user=serialize(req.blocking_user))
    else:
        return error(
            'invalid_request', f'Request {req} is not a valid request.', 400
        )
