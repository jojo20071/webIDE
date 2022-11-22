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
        xRunner.join(timeout = 3)
                    
        sys.stdout = xTempStd
        if xRunner.is_alive():
            return 'Timeout reached, killing runner (sorry QwQ)'
            xVM.xProgrammIndex = len(xVM.xLineStructures) + 1
            
        else:
            xOutput = xStdOutCap.getvalue()
            return xOutput
                            
        xRunner.join()

    
    
if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0', port=80)