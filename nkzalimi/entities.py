import enum
import uuid

from geoalchemy2.types import Geometry
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import (Column, ForeignKey, PrimaryKeyConstraint,
                               UniqueConstraint)
from sqlalchemy.sql.expression import null
from sqlalchemy.types import Boolean, Enum, Integer, Numeric, String, Unicode
from sqlalchemy_imageattach.entity import Image, image_attachment
from sqlalchemy_utc import UtcDateTime, utcnow
from sqlalchemy_utils import UUIDType

from .orm import Base
from .util import latlng_to_point


class OAuthProvider(enum.Enum):
    facebook = 'facebook'
    instagram = 'instagram'
    twitter = 'twitter'
    github = 'github'


class BusinessEntityStatus(enum.Enum):
    pending = 'pending'
    kids_exclusive = 'kids_exclusive'
    kids_exclusive_withdrawn = 'kids_exclusive_withdrawn'
    kids_friendly = 'kids_friendly'
    out_of_business = 'out_of_business'
    paused = 'paused'
    duplicate = 'duplicate'


class RevisionKind(enum.Enum):
    name = 'name'
    category = 'category'
    status = 'status'
    location = 'location'


class User(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    display_name = Column(Unicode, nullable=False)
    admin = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(UtcDateTime, nullable=False, default=utcnow(),
                        index=True)
    blocked_at = Column(UtcDateTime)

    @hybrid_property
    def blocked(self) -> bool:
        return self.blocked_at is not None

    @blocked.expression
    def blocked(cls):
        return cls.blocked_at.isnot(null())

    def is_authenticated(self):
        return True

    def is_active(self):
        return not self.blocked

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    __tablename__ = 'user'


class OAuthLogin(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    user_id = Column(UUIDType, ForeignKey(User.id), nullable=False, index=True)
    user = relationship(User, backref='oauth_logins')

    provider = Column(Enum(OAuthProvider), nullable=False)
    uid = Column(String, nullable=False)

    def identifier(self) -> str:
        return '{0}@{1}'.format(self.provider.value, self.uid)

    __tablename__ = 'oauth_login'
    __table_args__ = (
        UniqueConstraint('provider', 'uid',
                         name='uc_oauth_login_provider_uid'),
    )
    __mapper_args__ = {
        'polymorphic_on': provider
    }


class FacebookLogin(OAuthLogin):
    __mapper_args__ = {
        'polymorphic_identity': OAuthProvider.facebook
    }


class InstagramLogin(OAuthLogin):
    __mapper_args__ = {
        'polymorphic_identity': OAuthProvider.instagram
    }


class TwitterLogin(OAuthLogin):
    __mapper_args__ = {
        'polymorphic_identity': OAuthProvider.twitter
    }


class GithubLogin(OAuthLogin):
    __mapper_args__ = {
        'polymorphic_identity': OAuthProvider.github
    }


class OAuthSession(Base):
    id = Column(String, primary_key=True)
    secret = Column(String, nullable=False)

    created_at = Column(UtcDateTime, nullable=False, default=utcnow())

    __tablename__ = 'oauth_session'


class Attachment(Base, Image):
    request_id = Column(UUIDType, ForeignKey('request.id'),
                        index=True, nullable=False)
    index = Column(Integer, nullable=False)

    request = relationship('Request', uselist=False, backref='attachments')

    @property
    def object_type(self) -> str:
        return 'attachment'

    @property
    def object_id(self) -> str:
        return str(self.id)

    __table_args__ = (
        PrimaryKeyConstraint('request_id', 'index'),
    )
    __tablename__ = 'attachment'


class BusinessEntity(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    latest_revision_id = Column(UUIDType,
                                ForeignKey('business_entity_revision.id'),
                                unique=True)
    latest_revision = relationship('BusinessEntityRevision', uselist=False,
                                   lazy='joined', post_update=True,
                                   foreign_keys=latest_revision_id,
                                   backref=backref('business_entity',
                                                   uselist=False))

    first_revision_id = Column(UUIDType,
                               ForeignKey('business_entity_revision.id'))
    first_revision = relationship('BusinessEntityRevision', uselist=False,
                                  foreign_keys=first_revision_id,
                                  post_update=True)

    created_at = Column(UtcDateTime, nullable=False, default=utcnow(),
                        index=True)

    __tablename__ = 'business_entity'


class Request(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    created_at = Column(UtcDateTime, nullable=False, default=utcnow(),
                        index=True)

    submitted_by_id = Column(UUIDType, ForeignKey(User.id), nullable=False)
    submitted_by = relationship(User, uselist=False,
                                foreign_keys=submitted_by_id)

    kind = Column(Enum('creation', 'mark_as_duplicate', 'revision',
                       'block_user', name='request_kind'),
                  nullable=False, index=True)

    __tablename__ = 'request'
    __mapper_args__ = {
        'polymorphic_on': 'kind'
    }


class CreationRequest(Request):
    id = Column(UUIDType, ForeignKey(Request.id), primary_key=True)

    name = Column(Unicode, nullable=False)
    category = Column(Unicode, nullable=False)
    
    address = Column(Unicode, nullable=False)
    address_sub = Column(Unicode, nullable=False)
    coordinate = Column(Geometry(geometry_type='POINT'), nullable=False)
    
    def create(self) -> 'BusinessEntity':
        assert self.committed is None, 'This revision has already committed'
        revision = BusinessEntityRevision(
            request=self,
            name=self.name,
            category=self.category,
            status=BusinessEntityStatus.pending,
            address=self.address,
            address_sub=self.address_sub,
            coordinate=self.coordinate
        )
        new = BusinessEntity()
        new.latest_revision = revision
        new.first_revision = revision
        return new

    __tablename__ = 'creation_request'
    __mapper_args__ = {
        'polymorphic_identity': 'creation'
    }


class MarkAsDuplicateRequest(Request):
    id = Column(UUIDType, ForeignKey(Request.id), primary_key=True)

    business_entity_id = Column(UUIDType, ForeignKey(BusinessEntity.id),
                                nullable=False)
    business_entity = relationship(BusinessEntity, uselist=False,
                                   foreign_keys=business_entity_id)
    
    duplicates_with_id = Column(UUIDType, ForeignKey(BusinessEntity.id),
                                nullable=False)
    duplicates_with = relationship(BusinessEntity, uselist=False,
                                   foreign_keys=duplicates_with_id)

    def mark_as_duplicate(self) -> 'BusinessEntityRevision':
        assert self.business_entity, 'No business entity on {}'.format(self)
        business_entity = self.business_entity
        latest = business_entity.latest_revision
        new = BusinessEntityRevision(
            replacing=latest,
            request=self,
            name=latest.name,
            category=latest.category,
            status=BusinessEntityStatus.duplicate,
            address=latest.address,
            address_sub=latest.address_sub,
            coordinate=latest.coordinate
        )
        return new

    __tablename__ = 'mark_as_duplicate_request'
    __mapper_args__ = {
        'polymorphic_identity': 'mark_as_duplicate'
    }


class RevisionRequest(Request):
    id = Column(UUIDType, ForeignKey(Request.id), primary_key=True)

    business_entity_id = Column(UUIDType, ForeignKey(BusinessEntity.id),
                                nullable=False)
    business_entity = relationship(BusinessEntity, uselist=False,
                                   foreign_keys=business_entity_id)

    revision_kind = Column(Enum(RevisionKind), nullable=False)
    data = Column(JSON, nullable=False)

    def revise(self) -> 'BusinessEntityRevision':
        assert self.committed is None, 'This revision has already committed'
        business_entity = self.business_entity
        latest = business_entity.latest_revision
        new = BusinessEntityRevision(
            replacing=latest,
            request=self,
            name=latest.name,
            category=latest.category,
            status=latest.status,
            address=latest.address,
            address_sub=latest.address_sub,
            coordinate=latest.coordinate
        )
        if self.revision_kind is RevisionKind.name:
            new.name = self.data
        elif self.revision_kind == RevisionKind.category:
            new.category = self.data
        elif self.revision_kind == RevisionKind.status:
            new.status = BusinessEntityStatus(self.data)
        elif self.revision_kind is RevisionKind.location:
            new.address = self.data['address']
            new.address_sub = self.data['address_sub']
            new.coordinate = latlng_to_point(
                self.data['coordinate'][0], self.data['coordniate'][1]
            )
        business_entity.latest_revision = new
        return new

    __tablename__ = 'revision_request'
    __mapper_args__ = {
        'polymorphic_identity': 'revision'
    }


class BlockUserRequest(Request):
    id = Column(UUIDType, ForeignKey(Request.id), primary_key=True)
    
    blocking_user_id = Column(UUIDType, ForeignKey(User.id), nullable=False)
    blocking_user = relationship(User, uselist=False,
                                 foreign_keys=blocking_user_id)

    def block(self):
        self.blocking_user.blocked_at = utcnow()

    __tablename__ = 'block_user_request'
    __mapper_args__ = {
        'polymorphic_identity': 'block_user'
    }


class BusinessEntityRevision(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    replacing_id = Column(
        UUIDType, ForeignKey('business_entity_revision.id')
    )
    replacing = relationship('BusinessEntityRevision', remote_side=id,
                             uselist=False)
    replaced_by = relationship('BusinessEntityRevision',
                               remote_side=replacing_id, uselist=False)

    created_at = Column(UtcDateTime, nullable=False, default=utcnow(),
                        index=True)

    request_id = Column(UUIDType, ForeignKey(Request.id), nullable=False,
                        unique=True)
    request = relationship(Request, uselist=False,
                           backref=backref('committed', uselist=False))

    name = Column(Unicode, nullable=False)
    category = Column(Unicode, nullable=False, index=True)
    status = Column(Enum(BusinessEntityStatus), nullable=False)
    
    address = Column(Unicode, nullable=False)
    address_sub = Column(Unicode, nullable=False)
    coordinate = Column(Geometry(geometry_type='POINT'), nullable=False,
                        index=True)

    __tablename__ = 'business_entity_revision'


class Poll(Base):
    user_id = Column(UUIDType, ForeignKey(User.id), nullable=False)
    user = relationship(User, uselist=False, backref='polls')

    request_id = Column(UUIDType, ForeignKey(Request.id), nullable=False,
                        index=True)
    request = relationship(Request, uselist=False, backref='polls')
    
    __tablename__ = 'poll'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'request_id'),
    )
