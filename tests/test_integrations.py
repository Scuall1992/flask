import json
import time
from multiprocessing import Process

import requests

# from sherpa import multiprocessing

# # чтобы запускать фласк в отдельном процессе
# # pip install parameter-sherpa
# multiprocessing.set_start_method("fork")


def test_auth(random_port):
    def target():
        from flask import Flask, jsonify, request
        from flask_jwt_extended import (
            JWTManager,
            create_access_token,
            jwt_required,
            get_jwt_identity,
        )

        app = Flask(__name__)

        # Set up JWT
        app.config[
            "JWT_SECRET_KEY"
        ] = "super-secret"  # replace with your own secret key
        jwt = JWTManager(app)
        print(jwt)
        # Mock user database
        users = {"user1": {"password": "password1"}, "user2": {"password": "password2"}}

        @app.route("/is_alive")
        def alive():
            return "Hello"

        # Authentication route
        @app.route("/login", methods=["POST"])
        def login():
            username = request.json.get("username", None)
            password = request.json.get("password", None)
            if not username or not password:
                return jsonify({"msg": "Username and password are required"}), 400
            if username not in users or users[username]["password"] != password:
                return jsonify({"msg": "Invalid credentials"}), 401
            access_token = create_access_token(identity=username)
            return jsonify({"access_token": access_token}), 200

        # Protected route
        @app.route("/protected")
        @jwt_required()
        def protected():
            current_user = get_jwt_identity()
            return jsonify({"msg": f"Hello, {current_user}!"}), 200

        app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()

    host = f"http://localhost:{random_port}"

    while True:
        try:
            response = requests.get(f"{host}/is_alive")
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.1)

    base_url = f"{host}/login"

    resp = requests.post(base_url, json=dict())
    assert resp.status_code == 400
    assert json.loads(resp.content) == {"msg": "Username and password are required"}

    wrong_params = {"username": "user12345", "password": "password11234"}
    resp = requests.post(base_url, json=wrong_params)
    assert resp.status_code == 401
    assert json.loads(resp.content) == {"msg": "Invalid credentials"}

    params = {"username": "user1", "password": "password1"}
    resp = requests.post(base_url, json=params)
    assert resp.status_code == 200
    resp = json.loads(resp.content)
    token = resp["access_token"]

    assert "access_token" in resp

    base_url = f"{host}/protected"
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(base_url, headers=headers)
    assert resp.status_code == 200

    resp = json.loads(resp.content)
    assert resp == {"msg": f'Hello, {params["username"]}!'}

    p.terminate()
    p.join()
