import json
import os

import pytest
import werkzeug

import flask
from flask.helpers import get_debug_flag


def test_url_for(app, req_ctx):
    @app.route("/")
    def index():
        return "hello"

    assert flask.url_for("index") == "/"

    assert flask.url_for("index", _scheme="http") == "http://localhost/"

    assert flask.url_for("index", _anchor="x y") == "/#x%20y"

    assert (
        flask.url_for("index", _anchor="x y%$^&!@#$%^&*()")
        == "/#x%20y%$%5E&!@#$%%5E&*()"
    )

    with pytest.raises(werkzeug.routing.exceptions.BuildError):
        flask.url_for("index2", _anchor="x y%$^&!@#$%^&*()")

    from flask.views import MethodView

    class MyView(MethodView):
        def get(self, id=None):
            if id is None:
                return "List"
            return f"Get {id:d}"

        def post(self):
            return "Create"

    myview = MyView.as_view("myview")
    app.add_url_rule("/myview/", methods=["GET"], view_func=myview)
    app.add_url_rule("/myview/<int:id>", methods=["GET"], view_func=myview)
    app.add_url_rule("/myview/create", methods=["POST"], view_func=myview)

    assert flask.url_for("myview", _method="GET") == "/myview/"
    assert flask.url_for("myview", id=42, _method="GET") == "/myview/42"
    assert flask.url_for("myview", _method="POST") == "/myview/create"

    for method in ["DELETE", "PUT", "PATCH"]:
        with pytest.raises(werkzeug.routing.exceptions.BuildError):
            flask.url_for("myview", _method=method)


def test_config_from_prefixed_env(monkeypatch):
    monkeypatch.setenv("FLASK_STRING", "value")
    monkeypatch.setenv("FLASK_BOOL", "true")
    monkeypatch.setenv("FLASK_INT", "1")
    monkeypatch.setenv("FLASK_FLOAT", "1.2")
    monkeypatch.setenv("FLASK_LIST", "[1, 2]")
    monkeypatch.setenv("FLASK_DICT", '{"k": "v"}')

    monkeypatch.setenv("FLASK_WRONG_BOOL", "true_123")
    monkeypatch.setenv("FLASK_WRONG_INT", "1_123")
    monkeypatch.setenv("FLASK_WRONG_FLOAT", "1.2_123")
    monkeypatch.setenv("FLASK_WRONG_LIST", "[awd1, 2_123")
    monkeypatch.setenv("FLASK_WRONG_DICT", '{"k": "v"}_123')
    monkeypatch.setenv("NOT_FLASK_OTHER", "other")

    app = flask.Flask(__name__)
    app.config.from_prefixed_env()

    assert app.config["STRING"] == "value"
    assert app.config["BOOL"] is True
    assert app.config["INT"] == 1
    assert app.config["FLOAT"] == 1.2
    assert app.config["LIST"] == [1, 2]
    assert app.config["DICT"] == {"k": "v"}

    assert type(app.config["BOOL"]) == bool
    assert type(app.config["INT"]) == int
    assert type(app.config["FLOAT"]) == float
    assert type(app.config["LIST"]) == list
    assert type(app.config["DICT"]) == dict

    assert app.config["WRONG_BOOL"] == "true_123"
    assert app.config["WRONG_INT"] == "1_123"
    assert app.config["WRONG_FLOAT"] == "1.2_123"
    assert app.config["WRONG_LIST"] == "[awd1, 2_123"
    assert app.config["WRONG_DICT"] == '{"k": "v"}_123'

    assert type(app.config["WRONG_BOOL"]) == str
    assert type(app.config["WRONG_INT"]) == str
    assert type(app.config["WRONG_FLOAT"]) == str
    assert type(app.config["WRONG_LIST"]) == str
    assert type(app.config["WRONG_DICT"]) == str

    assert "OTHER" not in app.config


def test_render_template_string(app, client):
    @app.route("/a")
    def a():
        return flask.render_template_string("{{ config }}", config=42)

    @app.route("/b")
    def b():
        return flask.render_template_string("{{ config }}", config="42")

    @app.route("/c")
    def c():
        return flask.render_template_string("{{ config }}", config=[0, 1])

    @app.route("/d")
    def d():
        return flask.render_template_string("{{ config }}", config={1: 2})

    rv = client.get("/a")
    assert rv.data == b"42"

    rv = client.get("/b")
    assert rv.data == b"42"

    rv = client.get("/c")
    assert rv.data == b"[0, 1]"

    rv = client.get("/d")
    assert rv.data == b"{1: 2}"


@pytest.mark.parametrize(
    (
        "test_value",
        "expected_value",
    ),
    [
        (0, b"0\n"),
        (-1, b"-1\n"),
        (1, b"1\n"),
        (23, b"23\n"),
        (3.14, b"3.14\n"),
        ("s", b'"s"\n'),
        ("longer string", b'"longer string"\n'),
        (True, b"true\n"),
        (False, b"false\n"),
        (None, b"null\n"),
    ],
)
def test_jsonify(test_value, expected_value, app, client):
    url = "/jsonify"
    app.add_url_rule(url, url, lambda x=test_value: flask.jsonify(x))
    rv = client.get(url)
    assert rv.mimetype == "application/json"
    assert rv.data == expected_value


@pytest.mark.parametrize(
    (
        "test_value",
        "expected_value",
    ),
    [
        ({"a": 0}, b'{"a":0}\n'),
        ({"b": 23}, b'{"b":23}\n'),
        ({"c": 3.14}, b'{"c":3.14}\n'),
        ({"d": "d"}, b'{"d":"d"}\n'),
        ({"e": "hello"}, b'{"e":"hello"}\n'),
        ({"f": True}, b'{"f":true}\n'),
        ({"g": False}, b'{"g":false}\n'),
        ({"h": ["blabla", 102, True]}, b'{"h":["blabla",102,true]}\n'),
        ({"i": {"test": "dict"}}, b'{"i":{"test":"dict"}}\n'),
        ({"j": -230}, b'{"j":-230}\n'),
        ({"k": None}, b'{"k":null}\n'),
    ],
)
def test_jsonify_dictionaries(test_value, expected_value, app, client):
    url = "/jsonify"
    app.add_url_rule(url, url, lambda x=test_value: flask.jsonify(x))
    rv = client.get(url)
    assert rv.mimetype == "application/json"
    assert rv.data == expected_value


class Config:
    """Base config, uses staging database server."""

    TESTING = False
    DB_SERVER = "192.168.1.56"
    TEST_CONFIG_DATA = 0


def test_env_config(app):
    app.config.from_object("test_unit.Config")

    assert app.config["TESTING"] == Config.TESTING
    assert app.config["DB_SERVER"] == Config.DB_SERVER
    assert app.config["TEST_CONFIG_DATA"] == Config.TEST_CONFIG_DATA


@pytest.mark.parametrize(
    ("debug", "expect"),
    [
        ("", False),
        ("0", False),
        ("False", False),
        ("No", False),
        ("True", True),
    ],
)
def test_get_debug_flag(monkeypatch, debug, expect):
    monkeypatch.setenv("FLASK_DEBUG", debug)
    assert get_debug_flag() == expect


def test_config_from_file_json():
    app = flask.Flask(__name__)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(current_dir, "config.json"), "w") as f:
        f.write(
            """{
    "TEST_KEY": "foo",
    "SECRET_KEY": "config"
}
"""
        )

    app.config.from_file(os.path.join(current_dir, "config.json"), json.load)

    assert app.config["TEST_KEY"] == "foo"
    assert app.config["SECRET_KEY"] == "config"


@pytest.mark.parametrize(
    ("methods", "request_method", "expected"),
    [
        ([], "GET", 405),
        ([], "POST", 405),
        ([], "DELETE", 405),
        ([], "PATCH", 405),
        ([], "PUT", 405),
        (["GET"], "GET", 200),
        (["GET"], "POST", 405),
        (["GET"], "DELETE", 405),
        (["GET"], "PATCH", 405),
        (["GET"], "PUT", 405),
        (["GET", "POST", "DELETE", "PATCH", "PUT"], "GET", 200),
        (["GET", "POST", "DELETE", "PATCH", "PUT"], "POST", 200),
        (["GET", "POST", "DELETE", "PATCH", "PUT"], "DELETE", 200),
        (["GET", "POST", "DELETE", "PATCH", "PUT"], "PATCH", 200),
        (["GET", "POST", "DELETE", "PATCH", "PUT"], "PUT", 200),
    ],
)
def test_http_methods(app, client, methods, request_method, expected):
    @app.route("/", methods=methods)
    def index():
        return ""

    if request_method == "GET":
        assert client.get("/").status_code == expected
    elif request_method == "POST":
        assert client.post("/").status_code == expected
    elif request_method == "DELETE":
        assert client.delete("/").status_code == expected
    elif request_method == "PATCH":
        assert client.patch("/").status_code == expected
    elif request_method == "PUT":
        assert client.put("/").status_code == expected


def test_session(app, client):
    app.config.update(SERVER_NAME="example.com")

    @app.route("/")
    def index():
        flask.session["testing"] = "42"
        return "Hello World"

    @app.route("/session")
    def session():
        return flask.session["testing"]

    rv = client.get("/", "http://example.com/")
    assert rv.status_code == 200
    assert "domain=.example.com" in rv.headers["set-cookie"].lower()
    assert "httponly" in rv.headers["set-cookie"].lower()

    rv = client.get("/session", "http://example.com/")
    assert rv.data == b"42"
