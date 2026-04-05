import os
import requests
from flask import Flask, redirect, request
from pymongo import MongoClient

# ---------- Variáveis do Render ----------
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
MONGO_URI = os.getenv("MONGO_URI")

# ---------- App Flask ----------
app = Flask(__name__)

# ---------- MongoDB ----------
mongo = MongoClient(MONGO_URI)
db = mongo["verification_db"]
users = db["verified_users"]


@app.route("/")
def home():
    return "Backend de verificação funcionando! 🔥"


# ---------- Rota de Login ----------
@app.route("/login")
def login():
    oauth_url = (
        "https://discord.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        "&scope=identify"
    )
    return redirect(oauth_url)


# ---------- Rota Callback (corrigida e segura) ----------
@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "Erro: nenhum código recebido.", 400

    # Trocar code por token
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Requisição para trocar code -> access_token
    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data=data,
        headers=headers,
        timeout=15
    )

    # Se retornar erro, mostrar erro REAL (sem crashar)
    if token_res.status_code != 200:
        return (
            f"Erro ao trocar code por token:<br>"
            f"STATUS: {token_res.status_code}<br>"
            f"RESPOSTA: {token_res.text}"
        ), 400

    # Decodificação segura do JSON
    try:
        token_json = token_res.json()
    except Exception:
        return (
            f"Discord retornou resposta inválida:<br>"
            f"{token_res.text}"
        ), 400

    access_token = token_json.get("access_token")
    if not access_token:
        return (
            f"Discord não retornou o access_token.<br>"
            f"{token_json}"
        ), 400

    # Pegar informações do usuário
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15
    )

    if user_res.status_code != 200:
        return (
            f"Erro ao buscar informações do usuário:<br>"
            f"STATUS: {user_res.status_code}<br>"
            f"RESPOSTA: {user_res.text}"
        ), 400

    user_data = user_res.json()
    user_id = user_data["id"]

    # Salvar no banco
    users.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "data": user_data}},
        upsert=True
    )

    # Redirecionar para o seu site (altere depois)
    return redirect("https://oauth2-verification.onrender.com")


# ---------- Rodar no Render ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
