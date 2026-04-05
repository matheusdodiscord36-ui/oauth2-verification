import os
import requests
from flask import Flask, redirect, request, jsonify
from pymongo import MongoClient

# Carregar variáveis do Render
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
MONGO_URI = os.getenv("MONGO_URI")

# Criar app Flask
app = Flask(__name__)

# Conectar ao MongoDB
mongo = MongoClient(MONGO_URI)
db = mongo["verification_db"]
users = db["verified_users"]


@app.route("/")
def home():
    return "Backend de verificação funcionando! 🔥"


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


@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "Erro: Nenhum código recebido.", 400

    # Trocar code por token
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers).json()

    if "access_token" not in token_res:
        return "Erro ao receber access token.", 400

    access_token = token_res["access_token"]

    # Pegar informações do usuário
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    user_id = user_res["id"]

    # Salvar no MongoDB
    users.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "data": user_res}},
        upsert=True
    )

    # Redirecionar para o site de sucesso
    return redirect("https://seu-site-kimi.com/sucesso")  # depois você troca por seu site real


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)