import json
import time
from multiprocessing import Process

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sherpa import multiprocessing

import flask

# чтобы запускать фласк в отдельном процессе
# pip install parameter-sherpa
multiprocessing.set_start_method("fork")


@pytest.fixture
def random_port():
    import random

    ports = range(7000, 12000)
    return random.choice(ports)


@pytest.fixture
def browser():
    chrome_options = Options()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)

    yield driver
    driver.quit()


def wrap_html(s):
    return f"<html><head></head><body>{s}</body></html>"


def test_hello_world(browser, random_port):
    def target():
        flask_app = flask.Flask(__name__)

        @flask_app.route("/")
        def index():
            return "Hello World!"

        flask_app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()

    time.sleep(1)

    browser.get(f"http://localhost:{random_port}")
    code = browser.page_source

    p.terminate()
    p.join()

    assert wrap_html("Hello World!") == code


def test_post_data(browser, random_port):
    def target():
        flask_app = flask.Flask(__name__)

        @flask_app.route("/", methods=["POST"])
        def index():
            arg1 = flask.request.form["arg1"]
            arg2 = flask.request.form["arg2"]

            res = {
                "arg1": arg1,
                "arg2": arg2,
            }

            return str(res)

        flask_app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()
    time.sleep(1)

    base_url = f"http://localhost:{random_port}"
    params = {"arg1": "value1", "arg2": "value2"}

    response = requests.post(base_url, data=params)
    code = response.text

    p.terminate()
    p.join()

    assert str(params) == code


def test_get_query_arguments(browser, random_port):
    def target():
        flask_app = flask.Flask(__name__)

        @flask_app.route("/")
        def index():
            name = flask.request.args.get("name")
            return name

        flask_app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()
    time.sleep(1)

    browser.get(f"http://localhost:{random_port}?name=name")
    code = browser.page_source

    p.terminate()
    p.join()

    assert wrap_html("name") == code


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
