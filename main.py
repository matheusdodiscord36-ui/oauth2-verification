import os
import secrets
from urllib.parse import urlencode

import requests
from pymongo import MongoClient
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

# ---------- Variáveis do Render ----------
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
MONGO_URI = os.getenv("MONGO_URI")
BOT_NAME = os.getenv("BOT_NAME", "IceX")
SERVER_NAME = os.getenv("SERVER_NAME", "IceX")
SCOPE = os.getenv("identify")

# ---------- Checagem básica ----------
missing = [
    name for name, value in {
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
        "REDIRECT_URI": REDIRECT_URI,
        "MONGO_URI": MONGO_URI,
    }.items()
    if not value
]
if missing:
    raise RuntimeError(f"Variáveis de ambiente faltando: {', '.join(missing)}")

# ---------- App Flask ----------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# ---------- MongoDB ----------
mongo = MongoClient(MONGO_URI)
db = mongo["verification_db"]
users = db["verified_users"]


def discord_auth_url(state: str) -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "state": state,
    }
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


def get_user_doc(user_id: str):
    if not user_id:
        return None
    return users.find_one({"user_id": str(user_id)})


def get_avatar_url(user_doc: dict | None) -> str:
    if not user_doc:
        return "https://cdn.discordapp.com/embed/avatars/0.png"

    data = user_doc.get("data", {})
    user_id = str(user_doc.get("user_id", ""))
    avatar = data.get("avatar")
    discriminator = str(data.get("discriminator", "0"))

    if avatar:
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=256"

    try:
        default_index = int(discriminator) % 5
    except Exception:
        default_index = 0

    return f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"


@app.route("/")
def home():
    return render_template("index.html", server_name=SERVER_NAME, bot_name=BOT_NAME)


@app.route("/login")
def login():
    return redirect(url_for("verify"))


@app.route("/verify")
def verify():
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    auth_url = discord_auth_url(state)

    return render_template(
        "loading.html",
        auth_url=auth_url,
        server_name=SERVER_NAME,
        bot_name=BOT_NAME,
    )


@app.route("/callback")
def callback():
    if request.args.get("error"):
        return redirect(url_for("error", message="Autenticação cancelada ou negada."))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("error", message="Nenhum código OAuth2 recebido."))

    state = request.args.get("state")
    if not state or state != session.get("oauth_state"):
        return redirect(url_for("error", message="Falha na validação de segurança (state)."))

    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data=token_data,
        headers=headers,
        timeout=15
    )

    if token_res.status_code != 200:
        return redirect(url_for("error", message="Erro ao trocar o code por token."))

    try:
        token_json = token_res.json()
    except Exception:
        return redirect(url_for("error", message="Resposta inválida do Discord ao gerar token."))

    access_token = token_json.get("access_token")
    if not access_token:
        return redirect(url_for("error", message="Access token não retornado pelo Discord."))

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15
    )

    if user_res.status_code != 200:
        return redirect(url_for("error", message="Não foi possível buscar os dados do usuário."))

    user_data = user_res.json()
    user_id = str(user_data["id"])

    existing = users.find_one({"user_id": user_id})

    users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "verified": True,
                "username": user_data.get("username"),
                "global_name": user_data.get("global_name"),
                "avatar": user_data.get("avatar"),
                "discriminator": user_data.get("discriminator"),
                "data": user_data,
            }
        },
        upsert=True
    )

    session["last_user_id"] = user_id
    session.pop("oauth_state", None)

    if existing and existing.get("verified"):
        return redirect(url_for("already_verified", user_id=user_id))

    return redirect(url_for("success", user_id=user_id))


@app.route("/success")
def success():
    user_id = request.args.get("user_id") or session.get("last_user_id")
    user_doc = get_user_doc(user_id)

    return render_template(
        "success.html",
        user_id=user_id,
        user=user_doc,
        username=(user_doc or {}).get("username") if user_doc else None,
        avatar_url=get_avatar_url(user_doc),
        server_name=SERVER_NAME,
        bot_name=BOT_NAME,
    )


@app.route("/already-verified")
def already_verified():
    user_id = request.args.get("user_id") or session.get("last_user_id")
    user_doc = get_user_doc(user_id)

    return render_template(
        "already_verified.html",
        user_id=user_id,
        user=user_doc,
        username=(user_doc or {}).get("username") if user_doc else None,
        avatar_url=get_avatar_url(user_doc),
        server_name=SERVER_NAME,
        bot_name=BOT_NAME,
    )


@app.route("/blocked")
def blocked():
    reason = request.args.get("reason", "Acesso bloqueado.")
    return render_template(
        "blocked.html",
        reason=reason,
        server_name=SERVER_NAME,
        bot_name=BOT_NAME,
    )


@app.route("/rate-limited")
def rate_limited():
    return render_template(
        "rate_limited.html",
        server_name=SERVER_NAME,
        bot_name=BOT_NAME,
    )


@app.route("/error")
def error():
    message = request.args.get("message", "Ocorreu um erro inesperado.")
    return render_template(
        "error.html",
        message=message,
        server_name=SERVER_NAME,
        bot_name=BOT_NAME,
    )


@app.route("/api/user")
def api_user():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id não fornecido"}), 400

    user = get_user_doc(user_id)
    if not user:
        return jsonify({"error": "usuário não encontrado"}), 404

    data = user.get("data", {})
    return jsonify({
        "id": str(user.get("user_id")),
        "username": user.get("username") or data.get("username"),
        "global_name": user.get("global_name") or data.get("global_name"),
        "avatar": get_avatar_url(user),
        "verified": bool(user.get("verified", False)),
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "IceX Verify",
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
