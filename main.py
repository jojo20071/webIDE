import flask


app = flask.Flask(__name__)

@app.route("/")
def home():
    return flask.render_template("index.html")    

@app.route("/run", methods = ['POST', 'GET'])
def run():
    xEditorContent = flask.request.form.get("editor")
    print(xEditorContent)

    return flask.render_template("index.html", xEditorPreset = xEditorContent)

if __name__ == '__main__':
    app.run(debug = True)