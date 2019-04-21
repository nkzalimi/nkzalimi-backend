import datetime
import functools
import typing
import uuid

from .entities import (BusinessEntity, BusinessEntityRevision,
                       BusinessEntityStatus, CreationRequest, OAuthLogin,
                       OAuthProvider, Request, RequestKind, RevisionKind,
                       RevisionRequest, User)


@functools.singledispatch
def serialize(entity: typing.Any) -> typing.Any:
    raise NotImplementedError


@serialize.register
def _(entity: datetime.datetime) -> typing.Any:
    return entity.isoformat()


@serialize.register(BusinessEntityStatus)
@serialize.register(OAuthProvider)
@serialize.register(RevisionKind)
@serialize.register(RequestKind)
def _(entity) -> typing.Any:
    return entity.value


@serialize.register(uuid.UUID)
def _(entity) -> typing.Any:
    return str(entity)


@serialize.register
def _(entity: User) -> typing.Any:
    oauth_logins = {
        serialize(l.provider): l.uid for l in entity.oauth_logins
    }
    return {
        'id': serialize(entity.id),
        'created_at': serialize(entity.created_at),
        'admin': entity.admin,
        'blocked': entity.blocked,
        'display_name': entity.display_name,
        'oauth_logins': oauth_logins
    }


@serialize.register
def _(entity: BusinessEntity) -> typing.Any:
    latest = entity.latest_revision
    return {
        'id': serialize(entity.id),
        'created_at': serialize(entity.created_at),
        'name': latest.name,
        'category': latest.category,
        'status': serialize(latest.status),
        'address': f'{latest.address} {latest.address_sub}',
        'coordinate': [latest.latitude, latest.longitude]
    }


def serialize_request(entity: Request) -> typing.Mapping[str, typing.Any]:
    return {
        'id': serialize(entity.id),
        'created_at': serialize(entity.created_at),
        'submitted_by': serialize(entity.submitted_by),
        'upvotes': entity.upvotes,
        'downvotes': entity.downvotes,
        'committed': entity.committed,
        'kind': serialize(entity.kind)
    }


@serialize.register
def _(entity: CreationRequest) -> typing.Any:
    return {
        **serialize_request(entity),
        'creation': {
            'name': entity.name,
            'category': entity.category,
            'status': serialize(entity.status),
            'address': f'{entity.address} {entity.address_sub}',
            'coordinate': [entity.latitude, entity.longitude]
        }
    }


@serialize.register
def _(entity: RevisionRequest) -> typing.Any:
    return {
        **serialize_request(entity),
        'revision': {
            'business_entity_id': serialize(entity.business_entity_id),
            'kind': serialize(entity.revision_kind),
            'data': entity.data
        }
    }
