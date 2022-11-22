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


plugin attr - runs plugin with name of attr


"""

import time
import glob
import argparse
import traceback
import json
import sys

cls         = lambda: print("\033[2J\033[H")
pprintDict  = lambda s: "\n".join([f"{x: <25}\t : {s[x]}".format() for x in s])


class cInt:
    def __init__(self, xInt = 0, xIntLimit = 65535):
        self.xInt = xInt
        self.xIntLimit = xIntLimit
        
        
    def Set(self, xNew):
        self.xInt = int(xNew) % self.xIntLimit
        
    def Add(self, xValue):
        self.Set(self.xInt + int(xValue))
        
        
    def Sub(self, xValue):
        self.Set(self.xInt - int(xValue))

    def __int__(self):
        return self.xInt
    
    
class cLine:
    def __init__(self, xInst = "", xAttr = None):
        self.xInst = xInst
        self.xAttr = xAttr
        
    def __str__(self):
        return "{: <10}{}".format(str(self.xInst), str(self.xAttr))


class cPluginEnv:
    xDebug = False


class cMain:
    def __init__(self):
        self.xFile          = ""
        
        self.xConfig = {
                "NoNL"          : False,
                "DisplayTime"   : False,
                "PrintCommand"  : False,           
            }
        
        self.xBitSize = 16
        self.xIntLimit = 2 ** self.xBitSize 
        
        self.xReg = cInt(0, self.xIntLimit)
        self.xAcc = cInt(0, self.xIntLimit)
        
        #just to avoid confusion:
        #the heap is part of the memory and in this case it's the top half
        self.xHeapStartAddress = self.xIntLimit // 2        
        self.xHeapSize = self.xIntLimit - self.xHeapStartAddress
        
        #memory addresses allocated on the heap
        self.xHeapAlloc = [] 
        
        self.xMem = [cInt(0, self.xIntLimit) for i in range(self.xIntLimit)]
        
        self.xStack = []
                
        self.xProgrammIndex = 0
        self.xLabels = {}
        
        self.xTotalIndex = 0

        #assign a pointer to the memory and stack to the plugin env
        #this work because when you copy a list in python, it will just copy a pointer to that list, which can also be modified
        self.xPluginEnv = cPluginEnv()
        self.xPluginEnv.xMem   = self.xMem
        self.xPluginEnv.xStack = self.xStack
        
        self.xRunning = True
                
    def Reset(self):                                    
        self.xReg = cInt(0, self.xIntLimit)
        self.xAcc = cInt(0, self.xIntLimit)
        self.xHeapAlloc = []         
        self.xMem = [cInt(0, self.xIntLimit) for i in range(self.xIntLimit)]        
        self.xStack = []


    
    def LoadFile(self, xRawSource):
        xLineStructureBuffer = []
        xLineIndex = 0
        xLineOffset = 0
        for xLineIterator in [x.strip().replace("  ", " ").split(" ") for x in xRawSource.split("\n") if x.replace(" ", "") != "" and x.strip()[0] != '"']:            
            xInst = xLineIterator[0]
            xAttr = xLineIterator[1] if len(xLineIterator) > 1 else None
            
            if xInst == "lab":
                if not xAttr is None:
                    self.xLabels[xAttr] = str(xLineIndex - xLineOffset)
                    xLineOffset += 1
                
                else:
                    print("Attribute Error: " + " ".join(xLineIterator))
                    sys.exit(0)
                
            else:
                xLineStructureBuffer.append(cLine(xInst = xInst, xAttr = xAttr))
        
            xLineIndex += 1
        
        self.xLineStructures = xLineStructureBuffer



    def RunTest(self, xFilePath):
        with open(xFilePath, "r") as xFile:
            xUnitTest = json.load(xFile)
            
        if "tests" not in xUnitTest:
            print('"tests" key not found in test file, aborting')
            return
        
        xTests    = xUnitTest["tests"]
        xLog      = ""
        xFailed   = []
        
        
        def Log(xMsg):
            nonlocal xLog
            xLog += xMsg + "\n"

        def Send(xMsg):
            Log(xMsg)
            print(xMsg)
        
        
        for xTest in xTests:
            Log("-----")
            
            if "entryCall" not in xTest or "outputStack" not in xTest:
                Send("skipping invalid test: " + str(xTest))
                continue

            xEntryCall = xTest["entryCall"]
            xExpectedStack = xTest["outputStack"]
            if xEntryCall not in self.xLabels:
                Send("skipping invalid entry call: {}".format(xEntryCall))
                continue
            
            if   "resetVM"     in xTest and xTest["resetVM"] == "True":           
                self.Reset()
                Log("\tresetting VM")
            if "runBeforeCall" in xTest and xTest["runBeforeCall"] == "True":     
                self.Interpret()
                Log("\trunning before call")            
            if "inputStack"    in xTest:
                self.xStack = list(xTest["inputStack"])
                Log("\tsetting stack {}".format(self.xStack))
            
            Log(f"calling {xEntryCall} with stack {self.xStack}".format())    
            self.xStack.append((len(self.xLineStructures) + 1) * 2)  #inject return address to jump to end of program
            self.Interpret(int(self.xLabels[xEntryCall]))
            xActualStack = self.xStack

            if xExpectedStack == xActualStack:
                Log("test passed")
            
            else:
                Log(f"test failed, expected {xExpectedStack} but got {xActualStack}".format())
                xFailed.append(xEntryCall)
        
        Send("\n" * 5)

        if len(xFailed) > 0:
            Send("failed:")
            Send("\n".join(xFailed))
            Send("")
            Send(f"{len(xTests)}/{len(xFailed)} failed".format())
        else:
            Send("all tests passed")
        
        Send("")
        
        if "log" in xUnitTest:
            with open(xUnitTest["log"], "w") as xFile:
                xFile.write(xLog)
        

    def Interact(self):        
        cls()
        print("-- S1monsAssembly4 v3 VM Interactive --\n")
        
        HELPTEXT = """
exit                - exit vm
help                - display help
clear               - clear screen
run                 - execute loaded program
run <label>         - execute subroutine @<label>
set                 - list settings
set <name> <value>  - set setting <name> to <value>

push <value>        - push <value> to the stack
pop                 - pop value of the stack and print it
memory <address> <value> - set memory @<address> to <value> 
reset               - reset vm

stack               - print stack
memory <a1>:<a2>    - print memory location from @<a1> to @<a2>
allocs              - print allocated memory addresses
labels              - print label to address mapper

test <filePath>     - run test file @<filePath> with load file

test file format:
{
    "tests" :
    [
        {"runBeforeCall" : Bool, "resetVM" : Bool, "inputStack" : List::Int, "entryCall" : String, "outputStack" : List::Int},
        ...
    ],
    "log" : String
}


        """
                
        
        while True:
            try:
                xRaw = input(">>>").split(" ")
                xInj    = [x.strip() for x in xRaw]
                xInjLen = len(xInj)
                
                if xInjLen < 1: continue
                xOperation = xInj[0].lower()

                #metas    
                if   xOperation == "exit":                                                  break
                elif xOperation == "help":                                                  print(HELPTEXT) 
                elif xOperation == "clear":                                                 cls()
                elif xOperation == "run" and xInjLen == 1:                                  self.Interpret()
                elif xOperation == "run" and xInjLen == 2 and xInj[1] in self.xLabels:
                    self.xStack.append((len(self.xLineStructures) + 1) * 2) #inject return address to jump to end of program
                    self.Interpret(xEntryAddress = int(self.xLabels[xInj[1]]))                
                
                elif xOperation == "set" and xInjLen > 2:
                    (xSetting, xNewState) = xInj[1:3]
                    if xSetting in self.xConfig:
                        self.xConfig[xSetting] = bool(xNewState)
                        print(f"new state for '{xSetting}' is {xNewState}".format())        
            
                    else:
                        print(f"unrecognized setting '{xSetting}'".format())

                elif xOperation == "set" and xInjLen < 2:           print(pprintDict(self.xConfig))
            
                #sets
                elif xOperation == "push" and xInjLen > 1:          self.xStack.append(int(xInj[1]))
                elif xOperation == "pop"  and len(self.xStack) > 0: print(self.xStack.pop())
                elif xOperation == "memory" and xInjLen == 3:       self.xMem[int(xInj[1])].Set(int(xInj[2]))
                elif xOperation == "reset":                         self.Reset()
            
                #gets
                elif xOperation == "stack":                         print('V ' + ' \n| '.join(map(str, self.xStack[::-1])))
                elif xOperation == "memory" and xInjLen == 2 and ":" in xInj[1]:
                    x = list(map(int, xInj[1].split(":")))
                    print(list(map(int, self.xMem[x[0]:x[1]])))
                elif xOperation == "allocs":                        print(self.xHeapAlloc)
                elif xOperation == "labels":                        print(pprintDict(self.xLabels))
                
                elif xOperation == "test" and xInjLen > 1:
                    self.RunTest(xInj[1])
                
                else:
                    print(f"unrecognized injection {xInj}".format())
            
                print()
            
            except KeyboardInterrupt:
                print("KeyboardInterrupt\n")
                continue
        
            except Exception:
                print(traceback.format_exc())
    
    
    def Interpret(self, xEntryAddress = 0):
        self.xProgrammIndex = xEntryAddress
        self.xTotalIndex = 0
                
        try:
            xStartTime = time.time()
            while self.xProgrammIndex < len(self.xLineStructures) and self.xRunning:        
                xLine = self.xLineStructures[self.xProgrammIndex]
                if self.xConfig["PrintCommand"]: print(xLine)
                
                xInst = xLine.xInst
                xAttr = xLine.xAttr
                                                                                     
                #execute inst
                if xInst == "set":
                    self.xReg.Set(int(xAttr))
                    
                elif xInst == "add":
                    self.xAcc.Add(self.xReg)
                
                elif xInst == "sub":
                    self.xAcc.Sub(self.xReg)
                
                elif xInst == "shg":
                    self.xAcc.Set(int(self.xAcc) * 2)
                    
                elif xInst == "shs":
                    self.xAcc.Set(int(self.xAcc) // 2)
                
                elif xInst == "lor":
                    self.xAcc.Set(int(self.xAcc) | int(self.xReg))
    
                elif xInst == "and":
                    self.xAcc.Set(int(self.xAcc) & int(self.xReg))
    
                elif xInst == "xor":
                    self.xAcc.Set(int(self.xAcc) ^ int(self.xReg))
    
                elif xInst == "not":
                    xAccBin = bin(int(self.xAcc))[2:]
                    xFixLenAccBin = "0" * (self.xBitSize - len(xAccBin)) + xAccBin
                    
                    
                    xInverted = []
                    for xI in xFixLenAccBin:
                        if xI == "0":
                            xInverted.append("1")
                        
                        elif xI == "1":
                            xInverted.append("0")

                    self.xAcc.Set(int("".join(xInverted), 2))
    
                    
            
                elif xInst == "lDA":
                    self.xAcc.Set(int(self.xMem[int(xAttr)]))
                
                elif xInst == "lDR":
                    self.xReg.Set(int(self.xMem[int(xAttr)]))
                
                elif xInst == "sAD":
                    self.xMem[int(xAttr)].Set(self.xAcc)
                
                elif xInst == "sRD":
                    self.xMem[int(xAttr)].Set(self.xReg)
     
                elif xInst == "lPA":
                    self.xAcc.Set(int(self.xMem[int(self.xMem[int(xAttr)])]))
                
                elif xInst == "lPR":
                    self.xReg.Set(int(self.xMem[int(self.xMem[int(xAttr)])]))
    
                elif xInst == "sAP":
                    self.xMem[int(self.xMem[int(xAttr)])].Set(int(self.xAcc))
                
                elif xInst == "sRP":
                    self.xMem[int(self.xMem[int(xAttr)])].Set(int(self.xReg))
    
                
                elif xInst == "out":
                    print(int(self.xMem[int(xAttr)]), end = "" if self.xConfig["NoNL"] else "\n")
                
                elif xInst == "inp":
                    xInput = input(">>>")
                    self.xMem[int(xAttr)].Set(0 if xInput == "" else int(xInput))
                
                elif xInst == "got":
                    self.xProgrammIndex = int(self.xLabels[str(xAttr)])
                    continue
                
                elif xInst == "jm0":
                    if int(self.xAcc) == 0:
                        self.xProgrammIndex = int(self.xLabels[str(xAttr)])
                        continue
                    
                    
                elif xInst == "jmA":
                    if int(self.xAcc) == int(self.xReg):
                        self.xProgrammIndex = int(self.xLabels[str(xAttr)])
                        continue
                  
                elif xInst == "jmG":
                    if int(self.xAcc) > int(self.xReg):
                        self.xProgrammIndex = int(self.xLabels[str(xAttr)])
                        continue
                
                elif xInst == "jmL":
                    if int(self.xAcc) < int(self.xReg):
                        self.xProgrammIndex = int(self.xLabels[str(xAttr)])
                        continue
    
                        
                elif xInst == "brk":
                    break
                    
                elif xInst == "clr":
                    self.xReg.Set(0)
                    self.xAcc.Set(0)
                
                elif xInst == "jmS":
                    self.xStack.append((self.xProgrammIndex + 1) * 2)
                    self.xProgrammIndex = int(self.xLabels[str(xAttr)])
                    continue
                    
                    
                elif xInst == "ret":
                    if len(self.xStack) != 0:
                        self.xProgrammIndex = int(self.xStack.pop() / 2)
                        continue
                        
                elif xInst == "pha":
                    self.xStack.append(int(self.xAcc))
                    
                elif xInst == "pla":
                    if len(self.xStack) != 0:
                        self.xAcc.Set(int(self.xStack.pop()))
                                
                elif xInst == "putstr":
                    print(chr(int(self.xAcc)), end = "", flush = True)
                    
                elif xInst == "ahm":
                    xAllocSize = int(self.xReg)
                    
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
                        print("Program out of heap memory", file = StdOut)
                        exit()
                        
                    else:
                        for xAddrIndex in range(xBasePointer, xBasePointer + xAllocSize):
                            #append all the memory addresses to the alloc list, in order for them to properly freed 
                            self.xHeapAlloc.append(xAddrIndex)
                            
                            #and reset the address, just for safety
                            self.xMem[xAddrIndex].Set(0)
                        
                        #override the Acc to return the memory address to the user
                        self.xAcc.Set(xBasePointer)
                                                
                        
                elif xInst == "fhm":
                    xFreeSize = int(self.xReg)
                    xFreeBase = int(self.xAcc)
                    
                    for xFreeAddrIndex in range(xFreeBase, xFreeBase + xFreeSize):
                        if xFreeAddrIndex in self.xHeapAlloc: 
                            self.xHeapAlloc.remove(xFreeAddrIndex)
                        
                        self.xMem[xFreeAddrIndex].Set(0)
                        
                
                elif xInst == "plugin":
                    try:
                        xPluginName = xAttr.split("::")[0]
                        xMethodName = xAttr.split("::")[1]
                        
                        exec(str(xPluginName) + "." + str(xMethodName) + '(self.xPluginEnv)')

                    except NameError as E:
                        pass
                    
                    
                else:
                    print("Invaild command: " + str(xInst))
                    exit()
                
                self.xProgrammIndex += 1
                self.xTotalIndex += 1


        except KeyboardInterrupt:
            pass

        except KeyError as E:
            print("Error: label not found\n    {}".format(str(self.xLineStructures[self.xProgrammIndex])))
        
        if self.xConfig["DisplayTime"]: print(f"Execution took {str(self.xTotalIndex)} cycles and {time.time() - xStartTime} seconds")
        
if __name__ == '__main__':
    xArgParser = argparse.ArgumentParser(description = "S1monsAssembly4 Virtual Machine v2 (with external debugging)")    

    xArgParser.add_argument("-f", "--file", type=str, dest="path", action="store", nargs=1, required=True, help = "Assembler file to run")
    xArgParser.add_argument("-p", "--PluginPath", type=str, dest="PluginPath", action="store", nargs=1,    help = "Path to plugin files")
    xArgParser.add_argument("-l", "--NoNL", dest="NoNL", action="store_true", help = "'out' instruction will not put newline")
    xArgParser.add_argument("-i", "--interactive", dest="I", action="store_true", help = "run vm in interactive mode")
    xArgParser.add_argument("-t", "--Time", dest="Time", action="store_true", help = "display execution time")
    xArgParser.add_argument("-c", "--PrintCommand", dest="PrintCommand", action="store_true", help = "print the command being currently executed")
    xArgs = xArgParser.parse_args()
    

    try:
        xPath = xArgs.path[0]
        xFile = open(xPath, "r").read()
        
    except Exception as E:
        print("Error while loading file")
        sys.exit(0)




    xPLocals  = {}
    xPGlobals = {}


    if xArgs.PluginPath:
        try:            
            xPluginPath = xArgs.PluginPath[0]
            xPluginPaths = glob.glob(xPluginPath + "\\*.py")
            
            for xPathIter in xPluginPaths:
                xFileHandleIter = open(xPathIter)
                xFileHandle     = xFileHandleIter.read()
                xFileHandleIter.close()
                
                xPluginName = xPathIter.split("\\")[-1].split(".")[0]

                exec(xFileHandle, globals(), locals())

    
                
        except Exception as E:
            print("Error while loading Plugins:")
            print(E)
    
    
    cM = cMain()
    cM.LoadFile(xFile)
    
    cM.xConfig = {
            "NoNL"          : xArgs.NoNL,
            "DisplayTime"   : xArgs.Time,
            "PrintCommand"  : xArgs.PrintCommand,
        }
    
    cM.Interact() if xArgs.I else cM.Interpret()
