"""Browser authentication endpoints; route handlers delegate all business logic."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse

from tutor_ai.identity.dependencies import CurrentPrincipal
from tutor_ai.identity.schemas import CsrfResponse, SessionResponse, SigninRequest, SignupRequest
from tutor_ai.identity.security import create_access_token
from tutor_ai.identity.service import IdentityService
from tutor_ai.identity.sessions import BrowserSession
from tutor_ai.platform.config import Settings
from tutor_ai.platform.errors import ApiError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_session_cookies(
    response: Response,
    *,
    settings: Settings,
    session_id: str,
    session: BrowserSession,
) -> None:
    """Issue access, refresh, and readable CSRF cookies with ADR-015 attributes."""
    principal = session.principal(session_id)
    response.set_cookie(
        "mentora_access",
        create_access_token(principal, settings),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "mentora_refresh",
        session_id,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
    )
    response.set_cookie(
        "mentora_csrf",
        session.csrf_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        "mentora_access", path="/", secure=settings.cookie_secure, samesite="lax"
    )
    response.delete_cookie(
        "mentora_refresh",
        path="/api/v1/auth",
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.delete_cookie("mentora_csrf", path="/", secure=settings.cookie_secure, samesite="lax")


def _service(request: Request) -> IdentityService:
    return IdentityService(request.app.state.settings, request.app.state.session_store)


def _session_response(session: BrowserSession) -> SessionResponse:
    return SessionResponse(
        user_id=session.user_id,
        tenant_id=session.tenant_id,
        role=session.role,
        csrf_token=session.csrf_token,
    )


@router.get("/csrf", response_model=CsrfResponse)
def issue_csrf_token(request: Request, response: Response) -> CsrfResponse:
    """Bootstrap double-submit CSRF before browser mutations such as sign-in."""
    settings: Settings = request.app.state.settings
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        "mentora_csrf",
        csrf_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return CsrfResponse(csrf_token=csrf_token)


@router.post("/signup", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, request: Request, response: Response) -> SessionResponse:
    _, _, _, session_id, session = _service(request).signup(
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
    )
    _set_session_cookies(
        response,
        settings=request.app.state.settings,
        session_id=session_id,
        session=session,
    )
    return _session_response(session)


@router.post("/signin", response_model=SessionResponse)
def signin(payload: SigninRequest, request: Request, response: Response) -> SessionResponse:
    _, _, session_id, session = _service(request).signin(
        email=str(payload.email),
        password=payload.password,
    )
    _set_session_cookies(
        response,
        settings=request.app.state.settings,
        session_id=session_id,
        session=session,
    )
    return _session_response(session)


@router.post("/refresh", response_model=SessionResponse)
def refresh(request: Request, response: Response) -> SessionResponse:
    refresh_session_id = request.cookies.get("mentora_refresh")
    if refresh_session_id is None:
        raise ApiError(401, "refresh_missing", "Não há refresh token para esta sessão.")
    session_id, session = _service(request).refresh(refresh_session_id)
    _set_session_cookies(
        response,
        settings=request.app.state.settings,
        session_id=session_id,
        session=session,
    )
    return _session_response(session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
) -> None:
    _service(request).logout(principal)
    _clear_session_cookies(response, request.app.state.settings)


@router.get("/oauth/google")
def begin_google_oauth(request: Request) -> RedirectResponse:
    """Start Google OAuth using a short-lived, single-use Redis state value."""
    settings: Settings = request.app.state.settings
    if (
        settings.google_oauth_client_id is None
        or settings.google_oauth_client_secret is None
        or settings.google_oauth_redirect_uri is None
    ):
        raise ApiError(503, "google_oauth_not_configured", "Google OAuth não está configurado.")

    state = secrets.token_urlsafe(32)
    state_key = f"auth:google-state:{hashlib.sha256(state.encode('utf-8')).hexdigest()}"
    request.app.state.redis.setex(state_key, 600, "1")
    query = urlencode(
        {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": str(settings.google_oauth_redirect_uri),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
    )
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")
    response.set_cookie(
        "mentora_oauth_state",
        state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth/oauth/google/callback",
    )
    return response


@router.get("/oauth/google/callback")
def complete_google_oauth(code: str, state: str, request: Request) -> RedirectResponse:
    """Exchange a verified Google authorization code for a local cookie session."""
    settings: Settings = request.app.state.settings
    if (
        settings.google_oauth_client_id is None
        or settings.google_oauth_client_secret is None
        or settings.google_oauth_redirect_uri is None
    ):
        raise ApiError(503, "google_oauth_not_configured", "Google OAuth não está configurado.")

    browser_state = request.cookies.get("mentora_oauth_state")
    if browser_state is None or not hmac.compare_digest(browser_state, state):
        raise ApiError(403, "oauth_state_invalid", "O estado OAuth é inválido ou expirou.")

    state_key = f"auth:google-state:{hashlib.sha256(state.encode('utf-8')).hexdigest()}"
    if request.app.state.redis.getdel(state_key) is None:
        raise ApiError(403, "oauth_state_invalid", "O estado OAuth é inválido ou expirou.")

    token_response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret.get_secret_value(),
            "redirect_uri": str(settings.google_oauth_redirect_uri),
            "grant_type": "authorization_code",
        },
        timeout=10.0,
    )
    token_response.raise_for_status()
    access_token = token_response.json().get("access_token")
    if not isinstance(access_token, str):
        raise ApiError(401, "google_oauth_failed", "O Google não retornou um access token.")

    profile_response = httpx.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10.0,
    )
    profile_response.raise_for_status()
    profile = profile_response.json()
    if not (
        isinstance(profile.get("sub"), str)
        and isinstance(profile.get("email"), str)
        and profile.get("email_verified") is True
    ):
        raise ApiError(401, "google_oauth_failed", "O Google não retornou um perfil verificado.")

    _, _, session_id, session = _service(request).signin_google(
        email=profile["email"],
        display_name=profile.get("name")
        if isinstance(profile.get("name"), str)
        else profile["email"],
        google_subject=profile["sub"],
    )
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(
        "mentora_oauth_state",
        path="/api/v1/auth/oauth/google/callback",
        secure=settings.cookie_secure,
        samesite="lax",
    )
    _set_session_cookies(response, settings=settings, session_id=session_id, session=session)
    return response
