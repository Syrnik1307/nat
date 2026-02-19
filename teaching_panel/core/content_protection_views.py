from datetime import datetime, timedelta
import hashlib
import json
import uuid
from ipaddress import ip_address
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseGone, HttpResponseNotFound
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .content_protection_serializers import (
    ProtectedContentSerializer,
    SessionEventSerializer,
    SessionHeartbeatSerializer,
    SessionPlaybackUrlSerializer,
    SessionStartSerializer,
    SessionStatusSerializer,
)
from .models import ContentAccessSession, ContentSecurityEvent, ProtectedContent
from .services.security_alerts import notify_content_security_incident
from tenants.mixins import TenantViewSetMixin, TenantAPIViewMixin


RISK_THRESHOLD = getattr(settings, 'CONTENT_PROTECTION_RISK_THRESHOLD', 100)
SESSION_TTL_HOURS = getattr(settings, 'CONTENT_PROTECTION_SESSION_TTL_HOURS', 4)
HEARTBEAT_SECONDS = getattr(settings, 'CONTENT_PROTECTION_HEARTBEAT_SECONDS', 5)
HARD_BLOCK_CRITICAL = getattr(settings, 'CONTENT_PROTECTION_HARD_BLOCK_CRITICAL', True)
CRITICAL_EVENTS = set(getattr(settings, 'CONTENT_PROTECTION_CRITICAL_EVENTS', []))
PLAYBACK_TOKEN_TTL_SECONDS = getattr(settings, 'CONTENT_PROTECTION_PLAYBACK_TOKEN_TTL_SECONDS', 120)
PLAYBACK_SIGNING_SALT = getattr(settings, 'CONTENT_PROTECTION_PLAYBACK_SIGNING_SALT', 'content-protection-playback')
PLAYBACK_DEVICE_COOKIE = getattr(settings, 'CONTENT_PROTECTION_PLAYBACK_DEVICE_COOKIE', 'tp_playback_device')
PLAYBACK_BIND_IP = getattr(settings, 'CONTENT_PROTECTION_BIND_IP', True)
PLAYBACK_BIND_DEVICE = getattr(settings, 'CONTENT_PROTECTION_BIND_DEVICE', True)
PLAYBACK_BIND_USER_AGENT = getattr(settings, 'CONTENT_PROTECTION_BIND_USER_AGENT', True)
PLAYBACK_ALLOWED_REFERRER_HOSTS = set(getattr(settings, 'CONTENT_PROTECTION_PLAYBACK_ALLOWED_REFERRER_HOSTS', []))
PLAYBACK_ENFORCE_HOTLINK = getattr(settings, 'CONTENT_PROTECTION_ENFORCE_HOTLINK_PROTECTION', True)
PLAYBACK_URL_RATE_PER_MINUTE = getattr(settings, 'CONTENT_PROTECTION_PLAYBACK_URL_RATE_PER_MINUTE', 30)
PLAYBACK_REDIRECT_RATE_PER_MINUTE = getattr(settings, 'CONTENT_PROTECTION_PLAYBACK_REDIRECT_RATE_PER_MINUTE', 120)
PLAYBACK_NONCE_HISTORY_LIMIT = getattr(settings, 'CONTENT_PROTECTION_PLAYBACK_NONCE_HISTORY_LIMIT', 50)

EVENT_RISK_MAP = {
    ContentSecurityEvent.EVENT_TAB_HIDDEN: 10,
    ContentSecurityEvent.EVENT_WINDOW_BLUR: 8,
    ContentSecurityEvent.EVENT_FULLSCREEN_EXITED: 15,
    ContentSecurityEvent.EVENT_PRINT_SCREEN: 35,
    ContentSecurityEvent.EVENT_DEVTOOLS_OPENED: 30,
    ContentSecurityEvent.EVENT_SCREEN_RECORDING_SUSPECTED: 80,
    ContentSecurityEvent.EVENT_DISPLAY_CAPTURE_DETECTED: 90,
    ContentSecurityEvent.EVENT_MULTIPLE_SCREENS: 25,
    ContentSecurityEvent.EVENT_WATERMARK_TAMPER: 70,
    ContentSecurityEvent.EVENT_NETWORK_PROXY: 20,
    ContentSecurityEvent.EVENT_HEARTBEAT_ANOMALY: 0,
}

EVENT_SEVERITY_DEFAULTS = {
    ContentSecurityEvent.EVENT_TAB_HIDDEN: ContentSecurityEvent.SEVERITY_WARNING,
    ContentSecurityEvent.EVENT_WINDOW_BLUR: ContentSecurityEvent.SEVERITY_INFO,
    ContentSecurityEvent.EVENT_FULLSCREEN_EXITED: ContentSecurityEvent.SEVERITY_WARNING,
    ContentSecurityEvent.EVENT_PRINT_SCREEN: ContentSecurityEvent.SEVERITY_WARNING,
    ContentSecurityEvent.EVENT_DEVTOOLS_OPENED: ContentSecurityEvent.SEVERITY_WARNING,
    ContentSecurityEvent.EVENT_SCREEN_RECORDING_SUSPECTED: ContentSecurityEvent.SEVERITY_CRITICAL,
    ContentSecurityEvent.EVENT_DISPLAY_CAPTURE_DETECTED: ContentSecurityEvent.SEVERITY_CRITICAL,
    ContentSecurityEvent.EVENT_MULTIPLE_SCREENS: ContentSecurityEvent.SEVERITY_WARNING,
    ContentSecurityEvent.EVENT_WATERMARK_TAMPER: ContentSecurityEvent.SEVERITY_CRITICAL,
    ContentSecurityEvent.EVENT_NETWORK_PROXY: ContentSecurityEvent.SEVERITY_WARNING,
    ContentSecurityEvent.EVENT_HEARTBEAT_ANOMALY: ContentSecurityEvent.SEVERITY_INFO,
}


def _hash_value(raw_value):
    return hashlib.sha256((raw_value or '').encode('utf-8')).hexdigest()


def _normalize_ip_for_binding(raw_ip):
    if not raw_ip:
        return ''

    try:
        parsed = ip_address(raw_ip)
        if parsed.version == 4:
            parts = raw_ip.split('.')
            if len(parts) == 4:
                return '.'.join(parts[:3])
            return raw_ip

        exploded = parsed.exploded.split(':')
        return ':'.join(exploded[:4])
    except ValueError:
        return raw_ip


def _get_client_host(request):
    ip = _extract_ip(request) or 'unknown'
    return ip.replace(':', '_')


def _is_rate_limited(request, key_prefix, limit_per_minute):
    if limit_per_minute <= 0:
        return False

    cache_key = f'{key_prefix}:{_get_client_host(request)}'
    current = cache.get(cache_key)
    if current is None:
        cache.set(cache_key, 1, timeout=60)
        return False

    try:
        current = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=60)
        return False

    return current > limit_per_minute


def _extract_referrer_host(request):
    referrer = request.META.get('HTTP_REFERER', '').strip()
    if not referrer:
        return ''

    try:
        parsed = urlparse(referrer)
        return (parsed.hostname or '').lower()
    except ValueError:
        return ''


def _is_referrer_allowed(request):
    if not PLAYBACK_ALLOWED_REFERRER_HOSTS:
        return True

    host = _extract_referrer_host(request)
    if not host:
        return False

    for allowed in PLAYBACK_ALLOWED_REFERRER_HOSTS:
        norm = allowed.lower().strip()
        if not norm:
            continue
        if host == norm or host.endswith(f'.{norm}'):
            return True

    return False


def _register_playback_nonce(session, nonce, expires_at):
    metadata = session.metadata or {}
    nonces = metadata.get('playback_nonces', {})

    nonces[nonce] = {
        'used': False,
        'expires_at': expires_at.isoformat(),
        'created_at': timezone.now().isoformat(),
    }

    if len(nonces) > PLAYBACK_NONCE_HISTORY_LIMIT:
        keys = list(nonces.keys())
        to_delete = len(nonces) - PLAYBACK_NONCE_HISTORY_LIMIT
        for key in keys[:to_delete]:
            nonces.pop(key, None)

    metadata['playback_nonces'] = nonces
    session.metadata = metadata
    session.save(update_fields=['metadata'])


def _consume_playback_nonce(session, nonce):
    metadata = session.metadata or {}
    nonces = metadata.get('playback_nonces', {})
    item = nonces.get(nonce)
    if not item:
        return False, 'nonce_not_found'

    if item.get('used'):
        return False, 'nonce_already_used'

    expires_at_raw = item.get('expires_at')
    if expires_at_raw:
        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
            if timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
            if timezone.now() >= expires_at:
                return False, 'nonce_expired'
        except ValueError:
            return False, 'nonce_invalid_expiry'

    item['used'] = True
    item['used_at'] = timezone.now().isoformat()
    nonces[nonce] = item
    metadata['playback_nonces'] = nonces
    session.metadata = metadata
    session.save(update_fields=['metadata'])
    return True, ''


def _log_playback_denial(session, request, reason, extra=None):
    payload = {
        'phase': 'playback_deny',
        'reason': reason,
        'ip': _extract_ip(request),
        'referrer': request.META.get('HTTP_REFERER', ''),
        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
    }
    if extra:
        payload.update(extra)

    ContentSecurityEvent.objects.create(
        session=session,
        event_type=ContentSecurityEvent.EVENT_NETWORK_PROXY,
        severity=ContentSecurityEvent.SEVERITY_WARNING,
        score_delta=20,
        metadata=payload,
    )
    notify_content_security_incident(
        session=session,
        incident_type='playback_deny',
        reason=reason,
        severity='warning',
        metadata=payload,
    )


def _extract_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _expire_session_if_needed(session):
    if session.status == ContentAccessSession.STATUS_ACTIVE and session.is_expired():
        session.status = ContentAccessSession.STATUS_EXPIRED
        session.ended_at = timezone.now()
        session.save(update_fields=['status', 'ended_at'])


def _apply_risk_and_block_if_needed(session, delta, reason):
    if delta <= 0:
        return

    session.risk_score += delta
    if session.risk_score >= RISK_THRESHOLD:
        session.status = ContentAccessSession.STATUS_BLOCKED
        session.block_reason = reason[:255]
        session.blocked_at = timezone.now()
        session.ended_at = timezone.now()
        session.save(update_fields=['risk_score', 'status', 'block_reason', 'blocked_at', 'ended_at'])
        notify_content_security_incident(
            session=session,
            incident_type='session_blocked_threshold',
            reason=reason,
            severity='critical',
            metadata={'delta': delta, 'risk_threshold': RISK_THRESHOLD},
        )
    else:
        session.save(update_fields=['risk_score'])


def _block_session_now(session, reason):
    if session.status == ContentAccessSession.STATUS_BLOCKED:
        return
    session.status = ContentAccessSession.STATUS_BLOCKED
    session.block_reason = reason[:255]
    session.blocked_at = timezone.now()
    session.ended_at = timezone.now()
    session.save(update_fields=['status', 'block_reason', 'blocked_at', 'ended_at'])
    notify_content_security_incident(
        session=session,
        incident_type='session_blocked_hard',
        reason=reason,
        severity='critical',
        metadata={'hard_block': True},
    )


class ProtectedContentViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProtectedContentSerializer

    def get_queryset(self):
        user = self.request.user
        base_queryset = super().get_queryset().select_related('group', 'created_by').filter(is_active=True)

        if user.role == 'admin':
            return base_queryset

        if user.role == 'teacher':
            return base_queryset.filter(Q(group__teacher=user) | Q(group__isnull=True)).distinct()

        if user.role == 'student':
            return base_queryset.filter(group__students=user).distinct()

        return ProtectedContent.objects.none()

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(created_by=self.request.user, tenant=tenant)


class ContentSessionStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SessionStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content = ProtectedContent.objects.filter(
            id=serializer.validated_data['content_id'],
            is_active=True,
        ).first()
        if not content:
            return Response({'detail': 'Контент не найден'}, status=status.HTTP_404_NOT_FOUND)

        if not content.user_has_access(request.user):
            return Response({'detail': 'Нет доступа к контенту'}, status=status.HTTP_403_FORBIDDEN)

        active_session = ContentAccessSession.objects.filter(
            content=content,
            user=request.user,
            status=ContentAccessSession.STATUS_ACTIVE,
            expires_at__gt=timezone.now(),
        ).order_by('-started_at').first()

        if active_session:
            return Response({
                'session_token': active_session.session_token,
                'status': active_session.status,
                'risk_score': active_session.risk_score,
                'expires_at': active_session.expires_at,
                'risk_threshold': RISK_THRESHOLD,
                'heartbeat_seconds': HEARTBEAT_SECONDS,
                'content': {
                    'id': content.id,
                    'title': content.title,
                    'yandex_embed_url': content.yandex_embed_url,
                    'watermark_enabled': content.watermark_enabled,
                },
            })

        access_session = ContentAccessSession.objects.create(
            tenant=content.tenant,
            content=content,
            user=request.user,
            ip_address=_extract_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            expires_at=timezone.now() + timedelta(hours=SESSION_TTL_HOURS),
            metadata={'source': 'iframe-yandex-disk'},
        )

        return Response({
            'session_token': access_session.session_token,
            'status': access_session.status,
            'risk_score': access_session.risk_score,
            'expires_at': access_session.expires_at,
            'risk_threshold': RISK_THRESHOLD,
            'heartbeat_seconds': HEARTBEAT_SECONDS,
            'content': {
                'id': content.id,
                'title': content.title,
                'yandex_embed_url': content.yandex_embed_url,
                'watermark_enabled': content.watermark_enabled,
            },
        }, status=status.HTTP_201_CREATED)


class ContentSessionHeartbeatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SessionHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = ContentAccessSession.objects.filter(
            session_token=serializer.validated_data['session_token'],
            user=request.user,
        ).select_related('content').first()

        if not session:
            return Response({'detail': 'Сессия не найдена'}, status=status.HTTP_404_NOT_FOUND)

        _expire_session_if_needed(session)

        if session.status != ContentAccessSession.STATUS_ACTIVE:
            return Response({
                'status': session.status,
                'risk_score': session.risk_score,
                'blocked_reason': session.block_reason,
                'action': 'block' if session.status == ContentAccessSession.STATUS_BLOCKED else 'stop',
            }, status=status.HTTP_403_FORBIDDEN)

        score_delta = 0
        flags = {
            'is_visible': serializer.validated_data.get('is_visible', True),
            'is_focused': serializer.validated_data.get('is_focused', True),
            'is_fullscreen': serializer.validated_data.get('is_fullscreen', True),
            'devtools_open': serializer.validated_data.get('devtools_open', False),
            'recorder_suspected': serializer.validated_data.get('recorder_suspected', False),
            'display_capture_detected': serializer.validated_data.get('display_capture_detected', False),
            'multiple_screens_detected': serializer.validated_data.get('multiple_screens_detected', False),
        }

        if not flags['is_visible']:
            score_delta += 5
        if not flags['is_focused']:
            score_delta += 3
        if not flags['is_fullscreen']:
            score_delta += 7
        if flags['devtools_open']:
            score_delta += 25
        if flags['recorder_suspected']:
            score_delta += 80
        if flags['display_capture_detected']:
            score_delta += 90
        if flags['multiple_screens_detected']:
            score_delta += 20

        if HARD_BLOCK_CRITICAL and (flags['recorder_suspected'] or flags['display_capture_detected']):
            ContentSecurityEvent.objects.create(
                session=session,
                event_type=(
                    ContentSecurityEvent.EVENT_DISPLAY_CAPTURE_DETECTED
                    if flags['display_capture_detected']
                    else ContentSecurityEvent.EVENT_SCREEN_RECORDING_SUSPECTED
                ),
                severity=ContentSecurityEvent.SEVERITY_CRITICAL,
                score_delta=100,
                metadata=flags,
            )
            _block_session_now(session, 'Критический сигнал записи/захвата экрана')
            return Response({
                'status': session.status,
                'risk_score': session.risk_score,
                'blocked_reason': session.block_reason,
                'risk_threshold': RISK_THRESHOLD,
                'action': 'block',
            }, status=status.HTTP_403_FORBIDDEN)

        session.last_heartbeat_at = timezone.now()
        session.metadata = {
            **(session.metadata or {}),
            'last_heartbeat': {
                **flags,
                **serializer.validated_data.get('metadata', {}),
            },
        }
        session.save(update_fields=['last_heartbeat_at', 'metadata'])

        if score_delta > 0:
            ContentSecurityEvent.objects.create(
                session=session,
                event_type=ContentSecurityEvent.EVENT_HEARTBEAT_ANOMALY,
                severity=(
                    ContentSecurityEvent.SEVERITY_CRITICAL
                    if score_delta >= 80
                    else ContentSecurityEvent.SEVERITY_WARNING
                    if score_delta >= 20
                    else ContentSecurityEvent.SEVERITY_INFO
                ),
                score_delta=score_delta,
                metadata=flags,
            )

        _apply_risk_and_block_if_needed(session, score_delta, 'Превышен порог риска по heartbeat сигналам')

        return Response({
            'status': session.status,
            'risk_score': session.risk_score,
            'blocked_reason': session.block_reason,
            'risk_threshold': RISK_THRESHOLD,
            'action': 'block' if session.status == ContentAccessSession.STATUS_BLOCKED else 'continue',
        })


class ContentSessionEventView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SessionEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = ContentAccessSession.objects.filter(
            session_token=serializer.validated_data['session_token'],
            user=request.user,
        ).first()

        if not session:
            return Response({'detail': 'Сессия не найдена'}, status=status.HTTP_404_NOT_FOUND)

        _expire_session_if_needed(session)
        if session.status != ContentAccessSession.STATUS_ACTIVE:
            return Response({'detail': 'Сессия не активна', 'status': session.status}, status=status.HTTP_403_FORBIDDEN)

        event_type = serializer.validated_data['event_type']
        delta = EVENT_RISK_MAP.get(event_type, 0)
        severity = serializer.validated_data.get('severity') or EVENT_SEVERITY_DEFAULTS.get(
            event_type,
            ContentSecurityEvent.SEVERITY_INFO,
        )

        ContentSecurityEvent.objects.create(
            session=session,
            event_type=event_type,
            severity=severity,
            score_delta=delta,
            metadata=serializer.validated_data.get('metadata', {}),
        )

        if HARD_BLOCK_CRITICAL and event_type in CRITICAL_EVENTS:
            _block_session_now(session, f'Критическое событие безопасности: {event_type}')
            return Response({
                'status': session.status,
                'risk_score': session.risk_score,
                'blocked_reason': session.block_reason,
                'risk_threshold': RISK_THRESHOLD,
                'action': 'block',
            }, status=status.HTTP_403_FORBIDDEN)

        _apply_risk_and_block_if_needed(session, delta, f'Событие безопасности: {event_type}')

        return Response({
            'status': session.status,
            'risk_score': session.risk_score,
            'blocked_reason': session.block_reason,
            'risk_threshold': RISK_THRESHOLD,
            'action': 'block' if session.status == ContentAccessSession.STATUS_BLOCKED else 'continue',
        })


class ContentSessionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_token):
        session = ContentAccessSession.objects.filter(
            session_token=session_token,
            user=request.user,
        ).first()

        if not session:
            return Response({'detail': 'Сессия не найдена'}, status=status.HTTP_404_NOT_FOUND)

        _expire_session_if_needed(session)

        data = SessionStatusSerializer(session).data
        data['risk_threshold'] = RISK_THRESHOLD
        return Response(data)


class ContentSessionEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_token):
        session = ContentAccessSession.objects.filter(
            session_token=session_token,
            user=request.user,
        ).first()

        if not session:
            return Response({'detail': 'Сессия не найдена'}, status=status.HTTP_404_NOT_FOUND)

        if session.status == ContentAccessSession.STATUS_ACTIVE:
            session.status = ContentAccessSession.STATUS_ENDED
            session.ended_at = timezone.now()
            session.save(update_fields=['status', 'ended_at'])

        return Response({'status': session.status, 'risk_score': session.risk_score})


class ContentSessionPlaybackUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if _is_rate_limited(request, 'content_playback_url', PLAYBACK_URL_RATE_PER_MINUTE):
            return Response({'detail': 'Слишком много запросов к playback URL'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = SessionPlaybackUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = ContentAccessSession.objects.filter(
            session_token=serializer.validated_data['session_token'],
            user=request.user,
        ).select_related('content').first()

        if not session:
            return Response({'detail': 'Сессия не найдена'}, status=status.HTTP_404_NOT_FOUND)

        _expire_session_if_needed(session)
        if session.status != ContentAccessSession.STATUS_ACTIVE:
            return Response({'detail': 'Сессия не активна', 'status': session.status}, status=status.HTTP_403_FORBIDDEN)

        device_hash = _hash_value(serializer.validated_data['device_id'])
        ip_hash = _hash_value(_normalize_ip_for_binding(_extract_ip(request))) if PLAYBACK_BIND_IP else ''
        user_agent_hash = _hash_value(request.META.get('HTTP_USER_AGENT', '')[:500]) if PLAYBACK_BIND_USER_AGENT else ''

        payload = {
            'session_token': str(session.session_token),
            'content_id': session.content_id,
            'user_id': request.user.id,
            'device_hash': device_hash,
            'ip_hash': ip_hash,
            'user_agent_hash': user_agent_hash,
        }

        nonce = uuid.uuid4().hex
        expires_at = timezone.now() + timedelta(seconds=PLAYBACK_TOKEN_TTL_SECONDS)
        payload['nonce'] = nonce
        _register_playback_nonce(session, nonce, expires_at)

        signer = TimestampSigner(salt=PLAYBACK_SIGNING_SALT)
        signed_token = signer.sign(json.dumps(payload, separators=(',', ':')))
        playback_url = f'/api/content-protection/playback/{signed_token}/'

        response = Response({
            'playback_url': playback_url,
            'ttl_seconds': PLAYBACK_TOKEN_TTL_SECONDS,
            'bound': {
                'user': True,
                'ip': PLAYBACK_BIND_IP,
                'device': PLAYBACK_BIND_DEVICE,
                'user_agent': PLAYBACK_BIND_USER_AGENT,
            },
        })

        if PLAYBACK_BIND_DEVICE:
            response.set_cookie(
                PLAYBACK_DEVICE_COOKIE,
                device_hash,
                max_age=86400,
                secure=not settings.DEBUG,
                httponly=True,
                samesite='Lax',
            )

        return response


class ContentPlaybackRedirectView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, signed_token):
        if _is_rate_limited(request, 'content_playback_redirect', PLAYBACK_REDIRECT_RATE_PER_MINUTE):
            return HttpResponse('Слишком много запросов', status=429)

        signer = TimestampSigner(salt=PLAYBACK_SIGNING_SALT)

        try:
            payload_raw = signer.unsign(signed_token, max_age=PLAYBACK_TOKEN_TTL_SECONDS)
            payload = json.loads(payload_raw)
        except SignatureExpired:
            return HttpResponseGone('Срок действия ссылки истёк')
        except (BadSignature, ValueError, json.JSONDecodeError):
            return HttpResponseForbidden('Недействительная ссылка')

        session = ContentAccessSession.objects.filter(
            session_token=payload.get('session_token'),
            content_id=payload.get('content_id'),
            user_id=payload.get('user_id'),
        ).select_related('content').first()

        if not session:
            return HttpResponseNotFound('Сессия не найдена')

        _expire_session_if_needed(session)
        if session.status != ContentAccessSession.STATUS_ACTIVE:
            _log_playback_denial(session, request, 'session_not_active', {'status': session.status})
            return HttpResponseForbidden('Сессия не активна')

        nonce = payload.get('nonce', '')
        nonce_ok, nonce_reason = _consume_playback_nonce(session, nonce)
        if not nonce_ok:
            _log_playback_denial(session, request, nonce_reason)
            return HttpResponseForbidden('Одноразовая ссылка уже использована или недействительна')

        if PLAYBACK_ENFORCE_HOTLINK and not _is_referrer_allowed(request):
            _log_playback_denial(session, request, 'hotlink_referrer_denied')
            return HttpResponseForbidden('Источник перехода не разрешён')

        if PLAYBACK_BIND_IP:
            current_ip_hash = _hash_value(_normalize_ip_for_binding(_extract_ip(request)))
            if current_ip_hash != payload.get('ip_hash', ''):
                _log_playback_denial(session, request, 'ip_mismatch')
                return HttpResponseForbidden('IP не совпадает')

        if PLAYBACK_BIND_USER_AGENT:
            current_ua_hash = _hash_value(request.META.get('HTTP_USER_AGENT', '')[:500])
            if current_ua_hash != payload.get('user_agent_hash', ''):
                _log_playback_denial(session, request, 'user_agent_mismatch')
                return HttpResponseForbidden('Устройство не совпадает')

        if PLAYBACK_BIND_DEVICE:
            cookie_device_hash = request.COOKIES.get(PLAYBACK_DEVICE_COOKIE, '')
            if not cookie_device_hash or cookie_device_hash != payload.get('device_hash', ''):
                _log_playback_denial(session, request, 'device_cookie_mismatch')
                return HttpResponseForbidden('Проверка устройства не пройдена')

        target_url = session.content.yandex_embed_url
        if not target_url:
            return HttpResponseNotFound('Источник видео не найден')

        response = redirect(target_url)
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
        response['Cross-Origin-Resource-Policy'] = 'same-site'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-store, max-age=0'
        return response


class ContentProtectionIncidentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', None) not in ('admin', 'teacher'):
            return Response({'detail': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)

        limit_raw = request.query_params.get('limit', '50')
        try:
            limit = max(1, min(int(limit_raw), 200))
        except ValueError:
            limit = 50

        blocked_sessions = ContentAccessSession.objects.filter(
            status=ContentAccessSession.STATUS_BLOCKED,
        ).select_related('content', 'user').order_by('-blocked_at')[:limit]

        deny_events = ContentSecurityEvent.objects.filter(
            event_type=ContentSecurityEvent.EVENT_NETWORK_PROXY,
            metadata__phase='playback_deny',
        ).select_related('session', 'session__content', 'session__user').order_by('-created_at')[:limit]

        blocked_payload = [
            {
                'kind': 'blocked_session',
                'session_token': str(item.session_token),
                'content_id': item.content_id,
                'content_title': item.content.title if item.content else '',
                'user_id': item.user_id,
                'user_email': getattr(item.user, 'email', ''),
                'reason': item.block_reason,
                'timestamp': item.blocked_at or item.ended_at,
                'risk_score': item.risk_score,
            }
            for item in blocked_sessions
        ]

        deny_payload = [
            {
                'kind': 'playback_deny',
                'session_token': str(item.session.session_token),
                'content_id': item.session.content_id,
                'content_title': item.session.content.title if item.session.content else '',
                'user_id': item.session.user_id,
                'user_email': getattr(item.session.user, 'email', ''),
                'reason': (item.metadata or {}).get('reason', ''),
                'timestamp': item.created_at,
                'risk_score': item.session.risk_score,
                'metadata': item.metadata or {},
            }
            for item in deny_events
        ]

        return Response({
            'blocked_sessions': blocked_payload,
            'playback_denials': deny_payload,
            'counts': {
                'blocked_sessions': len(blocked_payload),
                'playback_denials': len(deny_payload),
            },
        })
