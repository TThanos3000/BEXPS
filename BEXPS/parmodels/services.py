CURRENT_ORGANIZATION_SESSION_KEY = "current_organization_id"

import hashlib
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import OrganizationMembership

_CACHE_MISSING = object()


def build_cache_key(namespace, organization_id, *parts, params=None):
    raw_parts = [str(namespace), f"org:{organization_id}"]
    raw_parts.extend(str(part) for part in parts if part not in (None, ""))

    if params is not None:
        if hasattr(params, "lists"):
            query_parts = [
                (key, value)
                for key, values in params.lists()
                for value in values
            ]
        else:
            query_parts = list(params.items())
        raw_parts.append(urlencode(sorted(query_parts), doseq=True))

    raw_value = "|".join(raw_parts)
    digest = hashlib.sha256(raw_value.encode("utf-8")).hexdigest()[:20]
    return f"{namespace}:org:{organization_id}:{digest}"


def cache_get_or_set(key, factory, timeout):
    value = cache.get(key, _CACHE_MISSING)
    if value is not _CACHE_MISSING:
        return value
    value = factory()
    cache.set(key, value, timeout)
    return value


def get_current_membership(user, request=None):
    if not user.is_authenticated:
        return None

    memberships = (
        OrganizationMembership.objects
        .filter(user=user, status=OrganizationMembership.Status.ACTIVE)
        .select_related("organization", "department")
        .order_by("id")
    )

    if request is not None:
        organization_id = request.session.get(CURRENT_ORGANIZATION_SESSION_KEY)
        if organization_id:
            membership = memberships.filter(organization_id=organization_id).first()
            if membership:
                return membership
            request.session.pop(CURRENT_ORGANIZATION_SESSION_KEY, None)

    return memberships.first()


def get_current_organization(user, request=None):
    membership = get_current_membership(user, request=request)
    if membership:
        return membership.organization
    return None


def user_is_org_admin(user, request=None):
    membership = get_current_membership(user, request=request)
    return bool(
        membership
        and membership.role == OrganizationMembership.Role.ADMIN
    )


def send_organization_invitation_email(invitation, invite_url):
    inviter = invitation.invited_by
    invited_by = ""
    if inviter:
        invited_by = inviter.get_full_name() or inviter.email or inviter.username

    message = render_to_string(
        "emails/organization_invitation.txt",
        {
            "invitation": invitation,
            "organization": invitation.organization,
            "role": invitation.get_role_display(),
            "invite_url": invite_url,
            "expires_at": invitation.expires_at,
            "invited_by": invited_by,
        },
    )
    return send_mail(
        subject="Приглашение в организацию",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
        fail_silently=False,
    )
