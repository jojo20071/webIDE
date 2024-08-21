"""
Acc - Accumolator
Reg - Register
mem - Memory

16-Bit Maschine

set attr - set attr into Reg

add none - Acc = Acc + Reg
sub none - Acc = Acc - Reg
shg none - Acc = Acc shifted greater
shs none - Acc = Acc shifted smaller

lor none - Acc = Acc (logical or) Reg
and none - Acc = Acc (logical and) Reg
xor none - Acc = Acc (logical xor) Reg
not none - Acc = Acc (logical not)

lDA attr - Load mem at attr into Acc
lDR attr - Load mem at attr into Reg
sAD attr - Save Acc into mem at attr
sRD attr - Save Reg into mem at attr

lPA atrr - Load mem pointed to by mem at attr into Acc
lPR atrr - Load mem pointed to by mem at attr into Reg
sAP atrr - Save Acc into mem pointed to by mem at attr
sRP atrr - Save Reg into mem pointed to by mem at attr

out attr - outputs mem at attr
inp attr - inputs  mem at attr

lab attr - define lable
got attr - goto attr
jm0 attr - goto attr if Acc = 0
jmA attr - goto attr if Acc = Reg
jmG attr - goto attr if Acc > Reg (jmG for jump great)
jmL attr - goto atrr if Acc < Reg (jmL for jump less)

jmS attr - goto attr as subroutine (pc gets push to stack)
ret none - return from subroutine (stack gets pop to pc)

pha none - push Acc to stack
pla none - pull from stack to Acc


brk none - stops programm
clr none - clears Reg and Acc

putstr none - print the Acc as ascii


ahm none - allocate a number of word given by the Reg and put a pointer to the base into the Acc
fhm none - free a number of word given by the Reg at the address given by the Acc

"""

import time
import glob
import argparse
import traceback
import json
import sys
import os
import ast
from dataclasses import dataclass
import operator as oper
from copy import deepcopy
from importlib import reload

from pprint import pprint



cls         = lambda: print("\033[2J\033[H")
pprintDict  = lambda s: "\n".join([f"{x: <25}\t : {s[x]}".format() for x in s])


xBitSize = 16
xIntLimit = 1 << xBitSize    



ANSI_ESCCODE_RESET   = "\033[0m"
ANSI_ESCCODE_GREEN   = "\033[32m"
ANSI_ESCCODE_RED     = "\033[31m"
ANSI_ESCCODE_MAGENTA = "\033[35m"

class cUtils:
    OK  = f"{ANSI_ESCCODE_GREEN  }OK{ ANSI_ESCCODE_RESET}"
    ERR = f"{ANSI_ESCCODE_RED    }ERR{ANSI_ESCCODE_RESET}"
    PNC = f"{ANSI_ESCCODE_MAGENTA}PNC{ANSI_ESCCODE_RESET}"

    
    @staticmethod
    def Error(xMsg):
        raise Exception(xMsg)

    @staticmethod
    def Lst(x):
        return list(map(lambda y: str(y), x))

    @staticmethod
    def TRes(xName, xBool):
        xStatus = cUtils.OK if xBool else cUtils.ERR
        
        print(f'[{xStatus}]\t{xName}')
        
    @staticmethod
    def TPanic(xName, xMsg):
        print(f'[{cUtils.PNC}]\t{xName} \n  => {xMsg}')
        
    @staticmethod
    def TReview(xTotal, i, xName):
        print(f"({xTotal}/{i}) {xName}\033[A")
        
    @staticmethod
    def TClear():
        print("\33[2K\033[A")
        
    @staticmethod
    def DictInv(x):
        return {k: v for (v, k) in x.items()}
        
    @staticmethod
    def List2Int(x):
        return [cInt(i) for i in x]

    @staticmethod
    def Int2List(x):
        return [int(i) for i in x]
        
        
    @staticmethod
    #dumps core trace of cEnv
    def CoreTrace(xProg):
        xLabelTrace = [ #pure, black, magic
                (lambda x: (
                     (r := ((x >> 1) - 1)),
                     (cUtils.DictInv(xProg.xLabels)[i.xArg] \
                        if (i := xProg.xInsts[r]).xOp == cProg.cImpl.fjms \
                        else '?') \
                     if r < len(xProg.xInsts) \
                     else '?'
                )[-1])(x) for x in cEnv.xStack
            ]
        
        x = "\n".join([
                    f'\tAcc:        {int(cEnv.Acc)}',
                    f'\tReg:        {int(cEnv.Reg)}',
                    f'\tHeap Alloc: [{", ".join(cUtils.Lst(cEnv.xHeapAlloc))}]',
                    f'\tStack:      [{", ".join(cUtils.Lst(cEnv.xStack))}]',
                    f'\tLabelTrace: [{", ".join(cUtils.Lst(xLabelTrace))}]'
                ])
        print(f'--- Core Trace ---\n{x}')


class cInt:
    _fs = {
        "add"      : oper.add,
        "sub"      : oper.sub,
        "rshift"   : oper.rshift,
        "lshift"   : oper.lshift,
        "floordiv" : oper.floordiv,
    }

    def __init__(self, xInt = 0, xIntLimit = xIntLimit):
        self.x : int = xInt
        self.l : int = xIntLimit

    @classmethod
    def _build(cls):
        for f in cls._fs:
            setattr(cls, f'__{f}__',   cls._makeAttr(f))
            setattr(cls, f'__i{f}__', cls._makeIAttr(f))        

    @staticmethod
    def _makeAttr(f):
        return lambda self, v: self.op(v, cInt._fs[f])

    @staticmethod
    def _makeIAttr(f):
        return lambda self, v: self.iop(v, cInt._fs[f])

    def op(self, v, f):
        return f(self.x, int(v)) % self.l
        
    def iop(self, v, f):
        self.x = self.op(v, f)
        return self
        
    #call used to set value
    #def __call__(self, v):    self.x = self.op(v, lambda x,y:y)
    def __call__(self, v):    
        if type(v) is int: self.x = v
        else: self.x = v.x % self.l
    def __int__(self): return self.x
    def __str__(self): return str(self.x)
    
    #copy
    def c(self):
        return cInt(xInt = self.x, xIntLimit=self.l)

cInt._build()    
    
class cConfig:
    NoNL         = False
    DisplayTime  = False
    PrintCommand = False
    Log          = None
    Test         = None
    Opti         = False
    PrintSub     = False
   
    PrintError   = True #trace error in interactive mode

    @classmethod
    def ReadArgs(self, xArgs):
        for x in ["NoNL", "DisplayTime", "PrintCommand", "Log", "Test", "Inter", "Opti", "PrintSub"]:
            xSetng = getattr(xArgs, x)
            setattr(self, x, xSetng)
    

class cProg:
    @dataclass
    class cInst:
        xOp  : "" = None
        xArg : "" = 0
        
        def __call__(self):
            self.xOp(cEnv, int(self.xArg))
            
        def __str__(self):
            return f'{self.xOp.__name__[1:]} {self.xArg}'
        
        def LabRes(self, xLabels):
            if type(self.xArg) is int or self.xArg.isdigit(): return #good
            elif self.xArg not in xLabels: 
                cUtils.Error(f"Invaild Label: {self.xArg}")
                
            self.xArg = xLabels[self.xArg]

    xInsts = []
    xLabels = {}
    xTests = {}    
    
    def __init__(self, xRaw):
        spce = lambda x: x.replace("  ", " ").strip()
        xLines = [xs.split(" ") for x in xRaw.split("\n") if len(xs := spce(x)) > 0 and xs[0] != '"']

        while len(xLines) > 0:
            #parse line and discard
            (xOpRaw, *xArgsList) = xLines.pop(0) + ['0']
            xOp = xOpRaw.lower()
            xArgs = xArgsList[0]

            #check for label
            if xOp == "lab":
                #add to mapper and continue
                self.xLabels[xArgs] = len(self.xInsts)
                continue
            
            
            #check if op exists
            xOpMName = 'f' + xOp
            if not hasattr(cProg.cImpl, xOpMName):
                cUtils.Error(f"Invaild Instruction: '{xOp}'")
                continue
            
            self.xInsts.append(self.cInst(
                xOp  = getattr(cProg.cImpl, xOpMName),
                xArg = xArgs
            ))
                        
        #resolve labels
        for x in self.xInsts:
            x.LabRes(self.xLabels)
            
        #search unittests
        if cConfig.Test:
            self.xTests = {
                i: self.xLabels[i] 
                for i in self.xLabels 
                if i.startswith(cConfig.Test)
            }
            
        #invert labels, for opti
        cEnv._xLabelsInv = {v: k for k, v in self.xLabels.items()}
        
    #command implementations
    class cImpl:
        
        def fset(self, x): self.Reg(x)
        
        def fadd(self, x): self.Acc += self.Reg
        def fsub(self, x): self.Acc -= self.Reg
        def fshg(self, x): self.Acc(self.Acc << 1)
        def fshs(self, x): self.Acc(self.Acc >> 1)
        def flor(self, x): self.Acc(self.Acc.op(self.Reg, lambda x,y: x|y))
        def fand(self, x): self.Acc(self.Acc.op(self.Reg, lambda x,y: x&y))
        def fxor(self, x): self.Acc(self.Acc.op(self.Reg, lambda x,y: x^y))
        def fnot(self, x): self.Acc(xIntLimit - int(self.Acc))

        def flda(self, x): self.Acc(self.xMem[x])
        def fldr(self, x): self.Reg(self.xMem[x])
        def fsad(self, x): self.xMem[x](self.Acc)
        def fsrd(self, x): self.xMem[x](self.Reg)

        def flpa(self, x): self.Acc(self.xMem[int(self.xMem[x])])
        def flpr(self, x): self.Reg(self.xMem[int(self.xMem[x])])
        def fsap(self, x): self.xMem[int(self.xMem[x])](self.Acc)
        def fsrp(self, x): self.xMem[int(self.xMem[x])](self.Reg)

        def fout(self, x):
            xEnd = "" if cConfig.NoNL else "\n"
            print(int(self.xMem[x]), end = xEnd)

        def finp(self, x):
            self.xMem[x](int(input()))
        
        def fgot(self, x):                                      self._jmp(self, x)
        def fjm0(self, x): 
                            if int(self.Acc) == 0:              self._jmp(self, x)
        def fjma(self, x): 
                            if int(self.Acc) == int(self.Reg):  self._jmp(self, x)
        def fjmg(self, x): 
                            if int(self.Acc) > int(self.Reg):   self._jmp(self, x)
        def fjml(self, x): 
                            if int(self.Acc) < int(self.Reg):   self._jmp(self, x)
        
        def fbrk(self, x): self.xRun = False
        def fclr(self, x):
            self.Acc(0)
            self.Reg(0)
        
        def fjms(self, x):
            if cConfig.Opti and \
                (xLabel := self._xLabelsInv[x]) in self._xJmsOptiDict:
                    self._xJmsOptiDict[xLabel](self)
                    
            else:
                if cConfig.PrintSub:
                    print(self._xLabelsInv[x])
            
            
                xNextInst = (self.xProgIndex + 1) << 1
                self.xStack.append(xNextInst)
                self._jmp(self, x)
        
        def fret(self, x):
            self._slen(self, "Stack Underflow")
            self._jmp(self, self.xStack.pop() >> 1)

        def fpha(self, x): 
            self.xStack.append(self.Acc.c())

        def fpla(self, x):
            self._slen(self, "Stack Underflow")
            self.Acc(self.xStack.pop())
    
        def fputstr(self, x):
            print(chr(int(self.Acc)), end = "", flush = True)
            
        def fahm(self, x):
            xAllocSize = int(self.Reg)
            
            #find the correct number of word in a row that are free
            xBasePointer = None
            for xHeapIndex in range(self.xHeapStartAddress, self.xHeapStartAddress + self.xHeapSize):
                #terminate the loop if the xHeapIndex plus the size that the memory row need to by is greater than the heap itself
                #because any check would be out of range and thus useless anyway
                if xHeapIndex + xAllocSize > self.xHeapStartAddress + self.xHeapSize:
                    break

                #otherwise check for a matching row
                if all([xHeapIndex + xCheckIndex not in self.xHeapAlloc for xCheckIndex in range(xAllocSize)]):
                    xBasePointer = xHeapIndex
                    break
            
            if xBasePointer is None:
                cUtils.Error("Heap out of memory")
                
            for xAddrIndex in range(xBasePointer, xBasePointer + xAllocSize):
                #append all the memory addresses to the alloc list, in order for them to properly freed 
                self.xHeapAlloc.append(xAddrIndex)
                
                #and reset the address, just for safety
                self.xMem[xAddrIndex](0)
            
            #override the Acc to return the memory address to the user
            self.Acc(xBasePointer)
                        
        def ffhm(self, x):
            xFreeSize = int(self.Reg)
            xFreeBase = int(self.Acc)
            
            for xFreeAddrIndex in range(xFreeBase, xFreeBase + xFreeSize):
                if xFreeAddrIndex in self.xHeapAlloc: 
                    self.xHeapAlloc.remove(xFreeAddrIndex)
                
                self.xMem[xFreeAddrIndex](0)

    def Time(self):
        return time.time() - self.xStartTime

    def Call(self, xIndex, x = [], xReset = True):
        xOoB = (len(self.xInsts) + 1) * 2 #out of bounds

        cEnv.xProgIndex = xIndex
        cEnv.xStack = cUtils.List2Int(x + [xOoB]) #out of bounds return value
        cEnv.xRun = True
        
        if xReset:
            cEnv.Acc(0)
            cEnv.Reg(0)
            cEnv.xHeapAlloc = []
            for i in range(xIntLimit): cEnv.xMem[i](0)

        p.Run()
        return cUtils.Int2List(cEnv.xStack)


    def Test(self):
    
        xTests = self.xTests.items()

        xFailTotal = 0
        xSuccTotal = 0
        xTotal = len(xTests)

        for i, (xName, xTest) in enumerate(xTests):
            
            cUtils.TReview(xTotal, i, xName)
            
            #run test
            try:
                xRet = self.Call(xTest)
                xTestEval = int(xRet[0]) != 0
            
            except KeyboardInterrupt: #on user interrupt
                #after fail test, vm will continue running like format
                xFailTotal += 1
                
                #give core trace
                cUtils.CoreTrace(self)

            except IndexError: #on interface fail
                xFailTotal += 1
                cUtils.TPanic(xName, "Malformed Unittest Interface")
                                        
            else: #on test finish
                cUtils.TClear()
                cUtils.TRes(xName, xTestEval)
                
                #check test evaluation
                if not xTestEval: xFailTotal += 1
                else            : xSuccTotal += 1
                
        print("\n")
        print(f'Total tests    : {xTotal}')
        print(f'Total fails    : {xFailTotal}')
        print(f'Total successes: {xSuccTotal}')
        
        if xFailTotal == 0: print("\nAll tests passed")


    def Run(self):
        xLogFile = []
        xMemOld = []
        self.xStartTime = time.time()
        
        try:
            xCycleCount = 0
            while cEnv.xRun and cEnv.xProgIndex < len(self.xInsts):

                #save mem for mem diff
                if cConfig.Log: xMemOld = [i.x for i in cEnv.xMem]

                #actual vm call                                
                (xInst := self.xInsts[cEnv.xProgIndex])()
                if cConfig.PrintCommand: print(xInst)

                #render log
                if cConfig.Log:
                    #mem delta
                    xMemDiff = { i : (cEnv.xMem[i].x, xMemOld[i]) 
                                for i in range(xIntLimit) 
                                if xMemOld[i] != cEnv.xMem[i].x
                            }
                    
                    xLogFile += [
                        f'[{str(self.Time())[:10]}] {cEnv.xProgIndex}: {xInst}',
                        f'\tAcc: {int(cEnv.Acc)}',
                        f'\tReg: {int(cEnv.Reg)}',
                        f'\tHAl: {cUtils.Lst(cEnv.xHeapAlloc)}',
                        f'\tStk: {cUtils.Lst(cEnv.xStack)}',
                        f'\tMem: {str(xMemDiff)}'
                                ]

                cEnv.xProgIndex += 1
                xCycleCount += 1

        except KeyboardInterrupt:
            if cConfig.Test:
                raise KeyboardInterrupt
       
        except Exception as E:
            print(E)

        if cConfig.DisplayTime:
            print(f"Execution took {str(xCycleCount)} cycles and {self.Time()} seconds")

        if cConfig.Log:
            with open(cConfig.Log, "w") as xFile:
                xFile.write('\n'.join(xLogFile))


    def Interact(self):
        clear()
        print("S1VM interactive ('help' for help)")
        
        xImports = []
        while True:
            try:
                xTerm = input(">>> ")
                
                #check empty input
                if xTerm.strip() == "": continue
                
                #reload
                for xMod in xImports:
                    xToks = xMod.split(" ")
                    exec(f'reload({xToks[1]})', globals(), locals())
                    exec(xMod,                  globals(), locals())

                xAst = ast.parse(xTerm)
                xByte = compile(xAst, "<ast>", "exec")
                
                #record import
                if 'import' in xTerm:
                    if 'from' in xTerm:
                        exec(f'import {xTerm.split(" ")[1]}', globals(), locals())
                    xImports.append(xTerm)

                #switch eval and exec
                xBody = xAst.body[0]
                if type(xBody) == ast.Expr:
                    xBody.lineno = 0
                    xBody.col_offset = 0
                    xExpr = compile(ast.Expression(xBody.value, lineno=0, col_offset=0), "<ast>", "eval")
                    
                    xRet = eval(xExpr, globals(), locals()) 
                    print(xRet)
                    
                else:
                    exec(xByte, globals(), locals())

            except KeyboardInterrupt: print()
            except Exception as xExp:
                if cConfig.PrintError:
                    import traceback
                    traceback.print_exc()
                else:
                    print(xExp)

#prog instance from cMain
p = None
        
#interactive funcs
help = """
'exit()'          -> exit
'clear()'         -> clear screen
    
namespaces:
    -p
        -Run
        -Call
        -xInsts
        -xLabels
        -xTests
    -cConfig
        -NoNL         : False
        -DisplayTime  : False
        -PrintCommand : False
        -Log          : None
        -Test         : None
    -cEnv
        -Acc
        -Reg
        -xHeapSize
        -xHeapAlloc
        -xMem
        -xStack
        -xProgIndex
        -xRun
    
"""

def exit():     sys.exit(0)
def clear():    os.system("clear")
 
    
class cEnv:
        
    Acc = cInt()
    Reg = cInt()

    xHeapStartAddress = xIntLimit // 2
    xHeapSize = xIntLimit - xHeapStartAddress
    
    #memory addresses allocated on the heap
    xHeapAlloc = [] 
    xMem = [cInt() for _ in range(xIntLimit)]
    xStack = []
            
    xProgIndex = 0
    xRun = True

    _xLabelsInv = {}
    _xJmsOptiDict = {
            "Stack::Swap" : (lambda self: self._OptiSwap(self))
        
        }


    def _jmp(self, x): self.xProgIndex = x - 1
    def _slen(self, xMsg): #error on empty string
        if len(self.xStack) == 0:
            cUtils.Error(xMsg)
            
    #swaps top two stack values
    def _OptiSwap(self):
        s = self.xStack
        s.append(s.pop(-2))
        

class cMain:    
    @classmethod
    def ParseArgs(self):
        xArgParser = argparse.ArgumentParser(description = "S1VM")
    
        xArgParser.add_argument("-f", "--file",         dest="path",            action="store",         help = "source file", nargs=1, required=True, type=str)
        xArgParser.add_argument("-n", "--NoNL",         dest="NoNL",            action="store_true",    help = "'out' instruction will not put newline")
        xArgParser.add_argument("-t", "--Time",         dest="DisplayTime",     action="store_true",    help = "display execution time")
        xArgParser.add_argument("-c", "--PrintCommand", dest="PrintCommand",    action="store_true",    help = "print the command being currently executed")
        xArgParser.add_argument("-l", "--Log",          dest="Log",             action="store",         help = "log vm state in file")        
        xArgParser.add_argument("-u", "--Unittest",     dest="Test",            action="store",         help = "search for and run unittest given a namespace")
        xArgParser.add_argument("-i", "--Interact",     dest="Inter",           action="store_true",    help = "run semi-python interactive environment")
        xArgParser.add_argument("-o", "--Optimize",     dest="Opti",            action="store_true",    help = "optimize execution")
        xArgParser.add_argument("-s", "--PrintSub",     dest="PrintSub",        action="store_true",    help = "print sub calls")
        
        return xArgParser.parse_args()
    
    @classmethod
    def Main(self):
        xArgs = self.ParseArgs()
        cConfig.ReadArgs(xArgs)
    
        xPath = next(iter(xArgs.path))
        if not os.path.isfile(xPath):
            cUtils.Error(f"Invaild Path: {xPath}")
    
        with open(xPath, "r") as xFD:
            xFile = xFD.read()

        
        xProg = cProg(xFile)

        global p
        p = xProg
        
        if cConfig.Test:        xProg.Test()
        elif cConfig.Inter:     xProg.Interact()
        else:                   xProg.Run()
            
if __name__ == '__main__':
    cMain.Main()
