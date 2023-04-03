import json
import os
import time
from multiprocessing import Process

import requests
from sherpa import multiprocessing

import flask
from flask import render_template
from flask import template_rendered
from flask.views import MethodView

# чтобы запускать фласк в отдельном процессе
# pip install parameter-sherpa
multiprocessing.set_start_method("fork")


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

    resp = requests.get(base_url)
    assert resp.status_code == 401

    p.terminate()
    p.join()


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


def test_redirect(browser, random_port):
    def target():
        flask_app = flask.Flask(__name__)

        @flask_app.route("/old_route")
        def old_route():
            return flask.redirect(flask.url_for("new_route"))

        @flask_app.route("/new_route")
        def new_route():
            return "This is the new route!"

        flask_app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()

    time.sleep(1)

    browser.get(f"http://localhost:{random_port}/old_route")
    code = browser.page_source

    p.terminate()
    p.join()

    assert wrap_html("This is the new route!") == code


def test_render_template(browser, random_port):
    def target():
        flask_app = flask.Flask(__name__, root_path=os.path.dirname(__file__))

        @flask_app.route("/")
        def index():
            return flask.render_template("template_end_to_end_render.html", message=23)

        flask_app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()

    time.sleep(1)

    browser.get(f"http://localhost:{random_port}")
    code = browser.page_source

    p.terminate()
    p.join()

    with open("tests/templates/template_end_to_end_render.html", encoding="utf-8") as f:
        file_data = f.read()

    file_data = (
        file_data.replace("{{ message }}", "23").replace("\n", "").replace(" ", "")
    )

    assert file_data == code.replace("\n", "").replace(" ", "")


def test_db(random_port):
    def target():
        from flask import Flask, request
        from flask_sqlalchemy import SQLAlchemy

        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        with app.app_context():
            db = SQLAlchemy(app)

            class MyModel(db.Model):
                id = db.Column(db.Integer, primary_key=True)
                name = db.Column(db.String(100), nullable=False)

                def __repr__(self):
                    return f"<Student {self.name}>"

            db.create_all()

        @app.route("/is_alive")
        def alive():
            return "Hello"

        @app.route("/create_user")
        def create_user():
            name = request.args.get("name")

            db.session.add(MyModel(name=name))
            db.session.commit()

            return "User created", 200

        @app.route("/read_user")
        def read_user():
            name = request.args.get("name")
            user = MyModel.query.filter_by(name=name).all()

            return str(user), 200

        @app.route("/read_all")
        def read_all():
            user = MyModel.query.all()

            return str(user), 200

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
            print("Server is not responding")
        time.sleep(0.1)

    base_url = f"{host}/create_user?name=name"

    resp = requests.get(base_url)
    assert resp.status_code == 200
    assert resp.content == b"User created"

    base_url = f"{host}/create_user?name=name1"

    resp = requests.get(base_url)
    assert resp.status_code == 200
    assert resp.content == b"User created"

    base_url = f"{host}/read_user?name=name"

    resp = requests.get(base_url)
    assert resp.status_code == 200
    assert resp.content == b"[<Student name>]"

    base_url = f"{host}/read_all"

    resp = requests.get(base_url)
    assert resp.status_code == 200
    assert resp.content == b"[<Student name>, <Student name1>]"


def test_blueprints(browser, random_port):
    def target():
        flask_app = flask.Flask(__name__)

        back = flask.Blueprint("backend", __name__)

        @flask_app.route("/")
        def index():
            return "index"

        @back.route("/backend")
        def backend():
            return "backend"

        flask_app.register_blueprint(back)

        flask_app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()

    time.sleep(1)

    browser.get(f"http://localhost:{random_port}/")
    code = browser.page_source

    assert wrap_html("index") == code

    browser.get(f"http://localhost:{random_port}/backend")
    code = browser.page_source

    assert wrap_html("backend") == code

    p.terminate()
    p.join()


def test_views(random_port):
    def target():
        flask_app = flask.Flask(__name__)

        class Index(MethodView):
            def get(self):
                return "GET"

            def post(self):
                return "POST"

            def delete(self):
                return "DELETE"

            def patch(self):
                return "PATCH"

        flask_app.add_url_rule("/", view_func=Index.as_view("index"))

        flask_app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()

    time.sleep(1)

    resp = requests.get(f"http://localhost:{random_port}/")

    assert resp.status_code == 200
    assert resp.content == b"GET"

    resp = requests.post(f"http://localhost:{random_port}/")

    assert resp.status_code == 200
    assert resp.content == b"POST"

    resp = requests.delete(f"http://localhost:{random_port}/")

    assert resp.status_code == 200
    assert resp.content == b"DELETE"

    resp = requests.patch(f"http://localhost:{random_port}/")

    assert resp.status_code == 200
    assert resp.content == b"PATCH"

    resp = requests.put(f"http://localhost:{random_port}/")

    assert resp.status_code == 405

    p.terminate()
    p.join()


def test_signals(browser, random_port):
    def target():
        flask_app = flask.Flask(__name__, root_path=os.path.dirname(__file__))

        flask_app.config["result"] = "None"

        @template_rendered.connect_via(flask_app)
        def when_template_rendered(sender, template, context, **extra):
            flask_app.config["result"] = f"Template {template.name} is rendered"

        @flask_app.route("/new")
        def new_r():
            return flask_app.config["result"]

        @flask_app.route("/")
        def index():
            return render_template("template_test.html", value=True)

        flask_app.run(port=random_port)

    p = Process(target=target, daemon=True)

    p.start()

    time.sleep(1)

    browser.get(f"http://localhost:{random_port}/new")
    code = browser.page_source

    assert wrap_html("None") == code

    browser.get(f"http://localhost:{random_port}/")
    code = browser.page_source

    assert wrap_html("Success!\n") == code

    browser.get(f"http://localhost:{random_port}/new")
    code = browser.page_source
    "<html><head></head><body>None</body></html>"

    assert wrap_html("Template template_test.html is rendered") == code

    p.terminate()
    p.join()
