import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

COOKIE = "helpdesk_session"


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=131072, r=8, p=1, maxmem=268435456
    ).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt, digest = encoded.split("$")
        actual = hashlib.scrypt(
            password.encode(), salt=salt.encode(), n=131072, r=8, p=1, maxmem=268435456
        ).hex()
        return hmac.compare_digest(actual, digest)
    except ValueError:
        return False


DUMMY_PASSWORD_HASH = password_hash(secrets.token_urlsafe(32))


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request):
    from .main import connect_db

    token = request.cookies.get(COOKIE, "")
    with connect_db() as connection:
        user = connection.execute(
            "SELECT u.id, u.email, u.role, s.csrf_token FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=%s AND s.expires_at>now()",
            (token_hash(token),),
        ).fetchone()
    if user is None:
        raise HTTPException(401, "Autentificare necesară.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        require_same_origin(request)
        if not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), user["csrf_token"]
        ):
            raise HTTPException(403, "Sesiune invalidă. Reautentifică-te.")
    return user


def require_same_origin(request: Request):
    origin = request.headers.get("origin")
    allowed = os.getenv("APP_ORIGIN", "http://127.0.0.1:5173")
    if origin and origin != allowed:
        raise HTTPException(403, "Origine nepermisă.")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cerere cross-site nepermisă.")


def throttle(request: Request, action: str):
    from .main import connect_db

    # One shared bucket per direct peer; proxy headers are not trusted.
    key = token_hash(
        action + ":" + (request.client.host if request.client else "unknown")
    )
    with connect_db() as connection:
        connection.execute(
            "DELETE FROM auth_rate_limits WHERE window_start < now() - interval '10 minutes'"
        )
        row = connection.execute(
            """INSERT INTO auth_rate_limits(key, attempts) VALUES (%s,1)
            ON CONFLICT(key) DO UPDATE SET attempts=auth_rate_limits.attempts+1
            RETURNING attempts""",
            (key,),
        ).fetchone()
    if row["attempts"] > 30:
        raise HTTPException(429, "Prea multe încercări. Reîncearcă peste 10 minute.")


def install_auth(app):
    import psycopg

    def connect_db():
        from . import main

        return main.connect_db()

    @app.post("/auth/register", status_code=201)
    def register(body: Credentials, request: Request):
        require_same_origin(request)
        throttle(request, "register")
        email = body.email.strip().lower()
        if "@" not in email or any(c.isspace() for c in email):
            raise HTTPException(422, "Adresă email invalidă.")
        try:
            with connect_db() as connection:
                connection.execute(
                    "INSERT INTO users(email,password_hash) VALUES (%s,%s)",
                    (email, password_hash(body.password)),
                )
        except psycopg.errors.UniqueViolation:
            raise HTTPException(409, "Contul nu poate fi creat cu această adresă.")
        return {"message": "Cont creat. Autentifică-te."}

    @app.post("/auth/login")
    def login(body: Credentials, request: Request, response: Response):
        require_same_origin(request)
        throttle(request, "login")
        with connect_db() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE email=%s", (body.email.strip().lower(),)
            ).fetchone()
            encoded = user["password_hash"] if user else DUMMY_PASSWORD_HASH
            valid = verify_password(body.password, encoded)
            if not user or not valid:
                raise HTTPException(401, "Email sau parolă incorectă.")
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            connection.execute(
                "DELETE FROM sessions WHERE token_hash=%s OR expires_at<=now()",
                (token_hash(request.cookies.get(COOKIE, "")),),
            )
            connection.execute(
                "INSERT INTO sessions VALUES (%s,%s,%s,%s)",
                (
                    token_hash(token),
                    user["id"],
                    csrf,
                    datetime.now(timezone.utc) + timedelta(hours=8),
                ),
            )
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            samesite="lax",
            max_age=28800,
            path="/",
        )
        return {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "csrf_token": csrf,
        }

    @app.get("/auth/me")
    def me(request: Request):
        return current_user(request)

    @app.post("/auth/logout")
    def logout(request: Request, response: Response):
        current_user(request)
        with connect_db() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash=%s",
                (token_hash(request.cookies.get(COOKIE, "")),),
            )
        response.delete_cookie(COOKIE, path="/")
        return {"message": "Deconectat."}
