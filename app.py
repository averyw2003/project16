import hmac
import os
import secrets
from functools import wraps
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from supabase import Client, create_client
from werkzeug.security import check_password_hash

load_dotenv()

app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
VISITOR_PASSWORD_HASH = os.environ.get("VISITOR_PASSWORD_HASH")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

missing_settings = [
    name
    for name, value in {
        "SECRET_KEY": SECRET_KEY,
        "ADMIN_PASSWORD_HASH": ADMIN_PASSWORD_HASH,
        "VISITOR_PASSWORD_HASH": VISITOR_PASSWORD_HASH,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SECRET_KEY": SUPABASE_SECRET_KEY,
    }.items()
    if not value
]

if missing_settings:
    raise RuntimeError(
        "Ontbrekende environment variables: " + ", ".join(missing_settings)
    )

app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=16 * 1024,
)

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)

TABLE_NAME = "cadeaus"


def valid_url(value: str) -> bool:
    """Sta uitsluitend normale externe http(s)-productlinks toe."""
    if not value:
        return True

    try:
        parts = urlsplit(value)
        return (
            parts.scheme.lower() in {"http", "https"}
            and bool(parts.netloc)
            and not any(char.isspace() for char in value)
        )
    except ValueError:
        return False


def csrf_token() -> str:
    """Maak één CSRF-token per sessie."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def validate_csrf() -> None:
    """Bescherm iedere POST, inclusief de AJAX-toggle."""
    if request.method != "POST":
        return

    supplied_token = (
        request.form.get("csrf_token", "")
        or request.headers.get("X-CSRF-Token", "")
    )
    expected_token = session.get("csrf_token", "")

    if (
        not supplied_token
        or not expected_token
        or not hmac.compare_digest(supplied_token, expected_token)
    ):
        abort(
            400,
            description="Ongeldig beveiligingstoken. Ververs de pagina en probeer opnieuw.",
        )


def admin_only(view):
    """Bescherm beheerpagina's en alle muterende routes."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("authenticated"):
            return view(*args, **kwargs)

        if request.path == "/toggle":
            return jsonify(ok=False, error="not_authenticated"), 401

        return redirect(url_for("login"))

    return wrapped

def visitor_only(view):
    """Laat alleen bezoekers met het gedeelde wachtwoord toe."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("visitor_authenticated"):
            return view(*args, **kwargs)

        return redirect(url_for("visitor_login"))

    return wrapped

def load_presents() -> list[dict]:
    """Lees cadeaus uit Supabase, gesorteerd op aanmaakmoment en ID."""
    response = (
        supabase.table(TABLE_NAME)
        .select("id,name,link,image_url,bought,created_at")
        .order("created_at")
        .order("id")
        .execute()
    )

    presents = response.data or []

    # Extra defensieve validatie van bestaande links uit de database.
    for present in presents:
        present["link"] = present.get("link") or ""
        present["image_url"] = present.get("image_url") or ""
        present["bought"] = bool(present.get("bought", False))

    if not valid_url(present["link"]):
        present["link"] = ""

    if not valid_url(present["image_url"]):
        present["image_url"] = ""

    return presents


def get_present_or_404(present_id: int) -> dict:
    """Haal één cadeau op. ID's voorkomen fouten na verwijderen/sorteren."""
    response = (
        supabase.table(TABLE_NAME)
        .select("id,name,link,image_url,bought,created_at")
        .eq("id", present_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        abort(404)

    return response.data[0]


@app.after_request
def add_security_headers(response):
    """Lichte browserbescherming; alle scripts/styles zijn lokaal."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self'; "
        "script-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    return response


@app.route("/")
@visitor_only
def index():
    presents = load_presents()

    return render_template(
        "index.html",
        presents=presents,
        bought_count=sum(present["bought"] for present in presents),
    )


@app.route("/visitor-login", methods=["GET", "POST"])
def visitor_login():
    if request.method == "POST":
        password = request.form.get("password", "")

        if check_password_hash(VISITOR_PASSWORD_HASH, password):
            session["visitor_authenticated"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("index"))

        return render_template(
            "visitor_login.html",
            error="Onjuist wachtwoord.",
        ), 401

    return render_template("visitor_login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")

        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            # Voorkomt session fixation en maakt een nieuw token.
            session.clear()
            session["authenticated"] = True
            session["visitor_authenticated"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin"))

        return render_template(
            "login.html",
            error="Onjuist wachtwoord.",
        ), 401

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@admin_only
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@admin_only
def admin():
    return render_template("admin.html", presents=load_presents())


@app.route("/add_present", methods=["POST"])
@admin_only
def add_present():
    name = request.form.get("name", "").strip()
    link = request.form.get("link", "").strip()
    image_url = request.form.get("image_url", "").strip()

    if not name or len(name) > 120:
        return render_template(
            "admin.html",
            presents=load_presents(),
            error="Vul een cadeaunaam in van maximaal 120 tekens.",
        ), 400

    if len(link) > 2000 or not valid_url(link):
        return render_template(
            "admin.html",
            presents=load_presents(),
            error="Gebruik voor de productlink een geldige http(s)-URL.",
        ), 400

    if len(image_url) > 2000 or not valid_url(image_url):
        return render_template(
            "admin.html",
            presents=load_presents(),
            error="Gebruik voor de afbeeldingslink een geldige http(s)-URL.",
        ), 400

    supabase.table(TABLE_NAME).insert(
        {
            "name": name,
            "link": link or None,
            "image_url": image_url or None,
            "bought": False,
        }
    ).execute()

    return redirect(url_for("admin"))


@app.route("/delete_present", methods=["POST"])
@admin_only
def delete_present():
    try:
        present_id = int(request.form.get("id", ""))
    except ValueError:
        abort(400)

    get_present_or_404(present_id)

    (
        supabase.table(TABLE_NAME)
        .delete()
        .eq("id", present_id)
        .execute()
    )

    return redirect(url_for("admin"))


@app.route("/toggle", methods=["POST"])
@visitor_only
def toggle():
    try:
        present_id = int(request.form.get("id", ""))
    except ValueError:
        return jsonify(ok=False, error="invalid_id"), 400

    checked = request.form.get("checked", "")
    if checked not in {"true", "false"}:
        return jsonify(ok=False, error="invalid_checked"), 400

    get_present_or_404(present_id)

    (
        supabase.table(TABLE_NAME)
        .update({"bought": checked == "true"})
        .eq("id", present_id)
        .execute()
    )

    presents = load_presents()

    return jsonify(
        ok=True,
        boughtCount=sum(present["bought"] for present in presents),
        total=len(presents),
    )


@app.errorhandler(400)
def bad_request(error):
    return (
        render_template(
            "error.html",
            title="Verzoek niet geldig",
            message=getattr(error, "description", "Het verzoek kon niet worden verwerkt."),
        ),
        400,
    )


@app.errorhandler(404)
def not_found(error):
    return (
        render_template(
            "error.html",
            title="Niet gevonden",
            message="Deze pagina of dit cadeau bestaat niet (meer).",
        ),
        404,
    )


@app.errorhandler(500)
def server_error(error):
    return (
        render_template(
            "error.html",
            title="Er ging iets mis",
            message="Probeer het later opnieuw.",
        ),
        500,
    )


if __name__ == "__main__":
    app.run(debug=False)