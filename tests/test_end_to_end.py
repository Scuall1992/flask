import os
import time
from multiprocessing import Process

import requests
from sherpa import multiprocessing

import flask

# чтобы запускать фласк в отдельном процессе
# pip install parameter-sherpa
multiprocessing.set_start_method("fork")


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
