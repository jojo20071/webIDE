import flask
import threading
import sys
import io
import os
import subprocess

def error(x):
    raise Exception(x)

app = flask.Flask(__name__)



@app.route("/")
def home():
    return flask.render_template("index.html")    

@app.route("/favicon.ico")
def favicon():
    return flask.send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

@app.route("/run", methods = ['POST', 'GET'])
def run():
    if flask.request.method == 'GET':
        return flask.redirect('/')
    
    xEditorContent = flask.request.get_json()['source']
    print(xEditorContent)

    with open("source.baabnq", "w") as xFile:
        xFile.write(xEditorContent)

    xCompilerOut = subprocess.run(
        ["python", "Compiler.py", "-i", "source.baabnq"], 
        timeout=1,
        capture_output=True    
    ).stdout.decode("ascii")
    
    print(xCompilerOut)
    
    xErrorLine = xCompilerOut.split("\n")[-2]
    if ('error' in xErrorLine.lower()):
        return xErrorLine


    xVMOut = subprocess.run(
        ["python", "vm.py", "-f", "build.s1"], 
        timeout=1,
        capture_output=True
    )
    print(xVMOut)

    return (
        xVMOut.stderr if 
        xVMOut.returncode else 
        xVMOut.stdout
    ).decode("ascii")
    
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, threaded=True)
    
