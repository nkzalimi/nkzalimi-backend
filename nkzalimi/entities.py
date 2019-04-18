import enum
import uuid

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.schema import (Column, ForeignKey, PrimaryKeyConstraint,
                               UniqueConstraint)
from sqlalchemy.sql.expression import null
from sqlalchemy.types import Boolean, Enum, Numeric, String, Unicode
from sqlalchemy_imageattach.entity import Image, image_attachment
from sqlalchemy_utc import UtcDateTime, utcnow
from sqlalchemy_utils import UUIDType

from .orm import Base


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
    id = Column(UUIDType, ForeignKey('request.id'),
                primary_key=True, default=uuid.uuid4)

    @property
    def object_type(self) -> str:
        return 'attachment'

    @property
    def object_id(self) -> str:
        return str(self.id)

    __tablename__ = 'attachment'


class BusinessEntity(Base):
    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)

    latest_revision_id = Column(UUIDType,
                                ForeignKey('business_entity_revision.id'))
    latest_revision = relationship('BusinessEntityRevision', uselist=False,
                                   lazy='joined', post_update=True,
                                   foreign_keys=latest_revision_id)

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
    data = Column(JSON)

    attachment = image_attachment('Attachment')

    __tablename__ = 'request'
    __mapper_args__ = {
        'polymorphic_on': 'kind'
    }


class CreationRequest(Request):
    __mapper_args__ = {
        'polymorphic_identity': 'creation'
    }


class MarkAsDuplicateRequest(Request):
    duplicates_with_id = Column(UUIDType, ForeignKey(BusinessEntity.id))
    duplicates_wuth = relationship(BusinessEntity, uselist=False)

    __mapper_args__ = {
        'polymorphic_identity': 'mark_as_duplicate'
    }


class RevisionRequest(Request):
    __mapper_args__ = {
        'polymorphic_identity': 'revision'
    }


class BlockUserRequest(Request):
    blocking_user_id = Column(UUIDType, ForeignKey(User.id))
    blocking_user = relationship(User, uselist=False,
                                 foreign_keys=blocking_user_id)
    
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

    revised_by_id = Column(UUIDType, ForeignKey(User.id), nullable=False)
    revised_by = relationship(User, uselist=False)

    revision_request_id = Column(UUIDType, ForeignKey(RevisionRequest.id))
    revision_request = relationship(RevisionRequest, uselist=False)

    name = Column(Unicode, nullable=False)
    category = Column(Unicode, nullable=False, index=True)
    status = Column(Enum(BusinessEntityStatus), nullable=False)
    
    address = Column(Unicode, nullable=False)
    address_sub = Column(Unicode, nullable=False)
    lat = Column(Numeric(15), nullable=False, index=True)
    lng = Column(Numeric(15), nullable=False, index=True)

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
