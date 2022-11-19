import flask


app = flask.Flask(__name__)

@app.route("/")
def home():
    return flask.render_template("index.html")    

@app.route("/run", methods = ['POST', 'GET'])
def run():
    print(flask.request.method)
    if flask.request.method == 'GET':
        return flask.redirect('/')
    
    xEditorContent = flask.request.get_json()['editor']
    print(xEditorContent)

    return 'a'
    
if __name__ == '__main__':
    app.run(debug = True)