import datetime
import functools
import typing
import uuid

from .entities import (BusinessEntity, BusinessEntityRevision,
                       BusinessEntityStatus, OAuthLogin, OAuthProvider,
                       RevisionKind, User)


@functools.singledispatch
def serialize(entity: typing.Any) -> typing.Any:
    raise NotImplementedError


@serialize.register
def _(entity: datetime.datetime) -> typing.Any:
    return entity.isoformat()


@serialize.register(BusinessEntityStatus)
@serialize.register(OAuthProvider)
@serialize.register(RevisionKind)
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
    first = entity.first_revision
    return {
        'id': serialize(entity.id),
        'created_at': serialize(entity.created_at),
        'submitted_by': serialize(first.request.submitted_by),
        'revised_by': serialize(latest.request.submitted_by),
        'name': latest.name,
        'category': latest.category,
        'status': serialize(latest.status),
        'address': f'{latest.address} {latest.address_sub}',
        'coordinate': [latest.latitude, latest.longitude]
    }
