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
    
    xEditorContent = flask.request.get_json()['source']
    print(xEditorContent)

    try:
        xCompiler = Compiler.cCompiler()
        xAsm = xCompiler.Compile(xEditorContent)[0]

    except Exception as E:
        return str(E)



    try:
        xProg = vm.cProg(xAsm)

        #reset vm state
        vm.cEnv.xProgIndex = 0
        vm.cEnv.xRun = True
        vm.cEnv.Acc(0)
        vm.cEnv.Reg(0)
        vm.cEnv.xHeapAlloc = []
        (vm.cEnv.xMem[i](0) for i in range(vm.xIntLimit))

        
        xTempStd = sys.stdout
        xStdOutCap = io.StringIO()
        sys.stdout = xStdOutCap
        
        xRunner = threading.Thread(target = xProg.Run)
        xRunner.start()
        xRunner.join(timeout = 0.1)
                        
        sys.stdout = xTempStd

        if not xRunner.is_alive():
            xOutput = xStdOutCap.getvalue()
            print(xOutput)
            return xOutput

        else:
            xVM.xRunning = False
            xRunner.join()
            return 'Timeout reached, killing runner (sorry QwQ)'

    except Exception as E:
        print(E)
        
        return 'Error: VM crashed, probably some misspelled label, or other symbol mismatch.'
    
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, threaded=True)
    
