import pytest
import werkzeug

import flask


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
