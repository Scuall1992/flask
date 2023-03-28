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
