import flask
import threading
import sys
import io
import os

import Compiler
import vm


def error(x):
    raise Exception(x)




app = flask.Flask(__name__)
Compiler.cUtils.Error = error



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
    
    xEditorContent = flask.request.get_json()['editor']

    try:
        xCompiler = Compiler.cCompiler()
        xAsm = xCompiler.Compile(xEditorContent)[0]

    except Exception as E:
        return str(E)
    
    else:
        xVM = vm.cMain()
        xVM.LoadFile(xAsm)
        
        xTempStd = sys.stdout
        sys.stdout = xStdOutCap = io.StringIO()
        
        xRunner = threading.Thread(target = xVM.Interpret)
        xRunner.start()
        xRunner.join(timeout = 30)
                    
        sys.stdout = xTempStd
        if not xRunner.is_alive():
            xOutput = xStdOutCap.getvalue()
            return xOutput
        
        xVM.xRunning = False
        xRunner.join()
        return 'Timeout reached, killing runner (sorry QwQ)'

    
    
if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0', port=80)