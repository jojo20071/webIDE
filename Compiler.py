import argparse
from dataclasses import dataclass
import sys


class cUtils:
    xIntLimit = (2 ** 16) - 1
    xMemLimit = xIntLimit // 2
    
    @staticmethod
    def Error(xMessage):
        print("\n" * 5)
        print(xMessage)
        sys.exit(0)
        
        
        
    def LineError(xLine, xMessage):
        cUtils.Error("Error at Line {xLine}: {xMessage}".format(xLine = xLine, xMessage = xMessage))

    @staticmethod
    def Gen():
        x = 0
        while True:
            yield x
            x += 1

    @staticmethod    
    def UnescapeStr(xStr):
        return xStr.encode('utf-8').decode('unicode_escape')


class cObjTypes:
    def __init__(self):
        xGen = cUtils.Gen()

        self.STRING         = next(xGen)
        self.EXPR           = next(xGen)
        self.VAR            = next(xGen)
        self.CONST          = next(xGen)
        self.NAME           = next(xGen)

class cCommandTypes:
    def __init__(self):
        xGen = cUtils.Gen()

        self.PUT            = next(xGen)
        self.JUMPUNCON      = next(xGen)
        self.JUMPCON        = next(xGen)
        self.INPUT          = next(xGen)
        self.PRINT          = next(xGen)
        self.SUBUNCON       = next(xGen)
        self.SUBCON         = next(xGen)
        self.RETURN         = next(xGen)
        self.PUSH           = next(xGen)
        self.PULL           = next(xGen)
        self.NEWDYN         = next(xGen)
        self.NEWSTR         = next(xGen)
        self.STATICALLOC    = next(xGen)
        self.STATICSTRING   = next(xGen)
        self.LABEL          = next(xGen)
        self.PUTCHR         = next(xGen)
        self.ASM            = next(xGen)
        self.FREE           = next(xGen)

objTypes     = cObjTypes()
commandTypes = cCommandTypes()



class cCodeGen:
    #used for holding s1 instruction
    class cCommand:
        def __init__(self, xInst, xArg):
            self.xInst = xInst
            self.xArg  = xArg
                    
        def __str__(self):
            return "{} {}".format(self.xInst, "" if self.xArg is None else self.xArg)
    
        @staticmethod
        def List2Self(xInputList):
            if len(xInputList) % 2 != 0:
                cUtils.Error("Internal Error while constructing cOutputCommand, this is a bug and if seen should be reported")

            xCommandBuffer = cCodeGen.cCommandBuffer()
            
            for xInputListIndex in range(0, len(xInputList), 2):
                xCommandInstance = cCodeGen.cCommand(*xInputList[xInputListIndex : xInputListIndex + 2])
                xCommandBuffer += xCommandInstance
            
            return xCommandBuffer
    
    class cCommandBuffer:
        def __init__(self, xCommandList = []):
            #make copy of list to avoid weird python list point stuff
            self.xCommandList = xCommandList[:]
            self.xChanged = True #track if xCommandList has been changed

        def Update(self, xCheck = False):
            if self.xChanged or not xCheck:
                self.xChanged = False
                self.xInsts = list(map(lambda x: x.xInst, self.xCommandList))
                self.xArgs  = list(map(lambda x: x.xArg,  self.xCommandList))
            
        def __iadd__(self, xNewElement):
            self.xChanged = True
            if   type(xNewElement) is cCodeGen.cCommandBuffer: self.xCommandList += xNewElement.xCommandList
            elif type(xNewElement) is cCodeGen.cCommand      : self.xCommandList.append(xNewElement)
            return self
        
        def __add__(self, xOtherValue):
            self.xChanged = True
            if   type(xOtherValue) is cCodeGen.cCommandBuffer: return cCodeGen.cCommandBuffer(self.xCommandList + xOtherValue.xCommandList)
            elif type(xOtherValue) is cCodeGen.cCommand      : return cCodeGen.cCommandBuffer(self.xCommandList + [xOtherValue])

        def GetInsts(self):
            self.Update(xCheck = True)
            return self.xInsts

        def GetArgs(self):
            self.Update(xCheck = True)
            return self.xArgs
        
        def __iter__(self):
            return iter(self.xCommandList)
        
        def __len__(self):
            return len(self.xCommandList)
        
                        
        def __str__(self):
            return "\n".join([str(x) for x in self.xCommandList])
            
    
    class cOptimizer:        
        @staticmethod
        def Optimize(xCommandBuffer):
                        
            xIndex = 0
            while xIndex < len(xCommandBuffer):
                
                #pha
                #pla
                #=> (nothing changes)
                #
                if xCommandBuffer.GetInsts()[xIndex:xIndex + 2] == ["pha", "pla"]:
                    xCommandBuffer.xCommandList.pop(xIndex)
                    xCommandBuffer.xCommandList.pop(xIndex)
                    xCommandBuffer.Update()
            
                #sAD x
                #lDA x
                #=> (value is still stored)
                #sAD x
                #(same with reg)
                elif xCommandBuffer.GetInsts()[xIndex:xIndex + 2] in [["sAD", "lDA"], ["sRD", "lDR"]] and \
                xCommandBuffer.GetArgs()[xIndex] == xCommandBuffer.GetArgs()[xIndex + 1]:
                    xCommandBuffer.xCommandList.pop(xIndex + 1)
                    xCommandBuffer.Update()

                #clr
                #set 0
                #=> (reg = 0; reg = 0 <=> reg = 0)
                #clr
                elif xCommandBuffer.GetInsts()[xIndex:xIndex + 2] == ["clr", "set"] and \
                int(xCommandBuffer.GetArgs()[xIndex + 1]) == 0:
                    xCommandBuffer.xCommandList.pop(xIndex + 1)
                    xCommandBuffer.Update()                        

                #clr
                #add
                #=> (0 + 0 = 0)
                #clr 
                elif xCommandBuffer.GetInsts()[xIndex:xIndex + 2] == ["clr", "add"]:
                    xCommandBuffer.xCommandList.pop(xIndex + 1)
                    xCommandBuffer.Update()                        

                else:
                    xIndex += 1
                

    
    
    
    
    
    
    
    
    def __init__(self):
        #16 bit system, but half of memory is used for the heap
        self.xIntLimit = cUtils.xIntLimit
        self.xMemLimit = cUtils.xMemLimit
        
        self.xMemUsedIndex = 0 #counter to track of full memory
        self.xTempAddresses = [] #keeps track of all addresses known to be temporary
        
        self.xVarMapper = {}
        self.xLabels = [] #only store the labels to generate intermediate ones and to not have labels twice
        self.xTempLabIndex = 0

        self.xOutputCode = self.cCommandBuffer()

    def CheckVarMapper(self, xIndex):
        if xIndex in self.xVarMapper.keys():
            return self.xVarMapper[xIndex]
            
        else:
            cUtils.LineError(self.xLineNumber, "Unable to map variable with name '{xName}'".format(xName = xIndex))

    def FormatLab(self, xIndex):
        return f"temp{xIndex}"

    def GetTempLab(self):
        xTempLabel = None
        while xTempLabel in self.xLabels + [None]:
            xTempLabel = self.FormatLab(self.xTempLabIndex)
            self.xTempLabIndex += 1
        
        self.xLabels.append(xTempLabel)
        return xTempLabel
    
    #this may fail, crash and die
    #so, just be careful
    def StaticNAlloc(self, xAllocCount):
        xAddressList = []
        for xI in range(xAllocCount):
            xAddressList.append(self.StaticAlloc())
            
        return xAddressList[0]
        
    def StaticAlloc(self):
        if self.xMemUsedIndex < self.xMemLimit:
            xResultAddress = self.xMemUsedIndex 
            self.xMemUsedIndex += 1
            
            return xResultAddress

        else:
            cUtils.Error("Error: Out of static memory")
    
    
    #alloc temp address, so an address that only need to matter in one command, for example to move data
    #this work by have a list of potentially available addresses and it will just allocate more if needed 
    def TempAlloc(self, xNeededAddressCount):
        while xNeededAddressCount > len(self.xTempAddresses):
            self.xTempAddresses.append(self.StaticAlloc())

        return self.xTempAddresses[0:xNeededAddressCount]
    
                
    def Generate(self, xCommandList):
        
        #compiler const
        xStringWritePtr = self.StaticAlloc()

        
        #compiler routines
        xCompilerRoutineBuffer = self.cCommandBuffer()
        
        #used for putting string on the heap in the new string command (baabnq: new '<your string>' _StringPtr;)
        #this takes the value for the reg, put it in memory at the xStringWritePtr and incrementing the pointer 
        #so what the new string command does, is it put the character in ascii in the reg and this routine will handle the rest
        xCompilerRoutineBuffer += cCodeGen.cCommand.List2Self([
            "lab", "_WriteChar",
            "sRP", xStringWritePtr,
            "lDA", xStringWritePtr,
            "set", 1,
            "add", None,
            "sAD", xStringWritePtr,
            
            "ret", None,
            
            ])
        
        for xCommandIter in xCommandList:
            self.xLine = xCommandIter.xLine
            self.xLineNumber = self.xLine + 1
            
            self.xCommand   = xCommandIter.xCommandType
            self.xArguments = xCommandIter.xArguments

                                                
            if self.xCommand == commandTypes.PUT:
                xAssignmentType     = self.xArguments[1]
                xBase               = self.xArguments[0]
                xOverrideObj        = self.xArguments[2]
                
                if xAssignmentType == "=":                        
                    if xBase.xValue not in self.xVarMapper.keys():
                        self.xVarMapper[xBase.xValue] = self.StaticAlloc()
                        
                    self.xOutputCode += xOverrideObj.Eval(self)
                    self.xOutputCode += xBase.Set(self)
        
                elif xAssignmentType == "<-":
                    if xBase.xValue not in self.xVarMapper.keys():
                        self.xVarMapper[xBase.xValue] = self.StaticAlloc()
                        
                    self.xOutputCode += xOverrideObj.LoadPointer(self)
                    self.xOutputCode += xBase.Set(self)
    

                elif xAssignmentType == "->":
                    self.xOutputCode += xBase.Eval(self)
                    self.xOutputCode += xOverrideObj.SetPointer(self)                        
                        
            elif self.xCommand == commandTypes.PRINT:
                xPrintObj = self.xArguments[0]
                
                xTempAddr = self.TempAlloc(1)[0]
                self.xOutputCode += xPrintObj.Eval(self) + cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "sAD", xTempAddr, 
                    "out", xTempAddr,
                    
                    ])
        
            elif self.xCommand == commandTypes.INPUT:
                xInputObj = self.xArguments[0]
                                    
                if xInputObj.xValue not in self.xVarMapper.keys():
                    self.xVarMapper[xInputObj.xValue] = self.StaticAlloc()
                
                xInputAddr = str(self.xVarMapper[xInputObj.xValue])
                self.xOutputCode += cCodeGen.cCommand.List2Self(["inp", xInputAddr])

            
            elif self.xCommand == commandTypes.JUMPUNCON:
                xTargetLabel = self.xArguments[0]        
                if xTargetLabel.xType != objTypes.NAME:
                    cUtils.LineError(self.xLineNumber, "Label must be Name")

                self.xOutputCode += cCodeGen.cCommand.List2Self(["got", xTargetLabel.xValue])
                
            elif self.xCommand == commandTypes.JUMPCON:
                xTargetLabelObj =  self.xArguments[0]    
                if xTargetLabelObj.xType != objTypes.NAME:
                    cUtils.LineError(self.xLineNumber, "Label must be Name")


                xTargetLabel =  xTargetLabelObj.xValue
                xJumpConType =  self.xArguments[2].xValue
                xConArg1 =      self.xArguments[1]
                xConArg2 =      self.xArguments[3]
                
                xTempAddr = self.TempAlloc(1)[0]

                #load values
                self.xOutputCode += xConArg1.Eval(self) + xConArg2.Eval(self) + cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "sAD", str(xTempAddr), 
                    "pla", None,
                    "lDR", str(xTempAddr)
                    
                    ])
                
                if xJumpConType == "==":
                    self.xOutputCode += cCodeGen.cCommand.List2Self(["jmA", xTargetLabel])
                    
                elif xJumpConType == ">":
                    self.xOutputCode += cCodeGen.cCommand.List2Self(["jmG", xTargetLabel])
                
                elif xJumpConType == "<":
                    self.xOutputCode += cCodeGen.cCommand.List2Self(["jmL", xTargetLabel])
                    
                elif xJumpConType == "!=":
                    xTempLab = self.GetTempLab()
                    self.xOutputCode += cCodeGen.cCommand.List2Self(["jmA", xTempLab, "got", xTargetLabel, "lab", xTempLab])
                
                
            elif self.xCommand == commandTypes.LABEL:
                xLabelName = self.xArguments[0]
                
                if xLabelName.xType != objTypes.NAME:
                    cUtils.LineError(self.xLineNumber, "Label must be Name")
                
                self.xLabels.append(xLabelName.xValue)
                self.xOutputCode += cCodeGen.cCommand.List2Self(["lab", str(xLabelName.xValue)])
                
            elif self.xCommand == commandTypes.SUBUNCON:
                xTargetLabel = self.xArguments[0]        
                if xTargetLabel.xType != objTypes.NAME:
                    cUtils.LineError(self.xLineNumber, "Label must be Name")

                self.xOutputCode += cCodeGen.cCommand.List2Self(["jmS", xTargetLabel.xValue])
            
            elif self.xCommand == commandTypes.SUBCON:
                xSubroutineLabelObj = self.xArguments[0]
                xSubroutineLabel    = xSubroutineLabelObj.xValue
                
                xJumpConType        = self.xArguments[2].xValue
                xConArg1            = self.xArguments[1]
                xConArg2            = self.xArguments[3]

                if xSubroutineLabelObj.xType != objTypes.NAME:
                    cUtils.LineError(self.xLineNumber, "Label must be Name")


                xTempAddr = self.TempAlloc(1)[0]
                                
                #this is for the jumping logic
                xSkipLab = self.GetTempLab()
                xCheckLab = self.GetTempLab()
                
                self.xOutputCode += xConArg1.Eval(self) + xConArg2.Eval(self) + cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "sAD", xTempAddr, 
                    "pla", None, 
                    "lDR", xTempAddr,
                    
                    ])

                if xJumpConType == "==":
                    self.xOutputCode += cCodeGen.cCommand.List2Self([
                        "jmA", xCheckLab, 
                        "got", xSkipLab, 
                        "lab", xCheckLab, 
                        "jmS", xSubroutineLabel, 
                        "lab", xSkipLab
                        
                        ])
                
                elif xJumpConType == ">":
                    self.xOutputCode += cCodeGen.cCommand.List2Self([
                        "jmG", xCheckLab, 
                        "got", xSkipLab, 
                        "lab", xCheckLab, 
                        "jmS", xSubroutineLabel, 
                        "lab", xSkipLab
                        
                        ])

                elif xJumpConType == "<":
                    self.xOutputCode += cCodeGen.cCommand.List2Self([
                        "jmL", xCheckLab, 
                        "got", xSkipLab, 
                        "lab", xCheckLab, 
                        "jmS", xSubroutineLabel, 
                        "lab", xSkipLab
                        
                        ])
                
                elif xJumpConType == "!=":
                    self.xOutputCode += cCodeGen.cCommand.List2Self([
                        "jmA", xSkipLab, 
                        "jmS", xSubroutineLabel, 
                        "lab", xSkipLab, 

                        ])

            elif self.xCommand == commandTypes.RETURN:
                self.xOutputCode += cCodeGen.cCommand.List2Self(["ret", None])
            
            elif self.xCommand == commandTypes.PUSH:
                xPushObj = self.xArguments[0]
                self.xOutputCode += xPushObj.Eval(self)

            elif self.xCommand == commandTypes.PULL:
                xPullObj = self.xArguments[0]
                
                if xPullObj.xValue not in self.xVarMapper.keys():
                    self.xVarMapper[xPullObj.xValue] = self.StaticAlloc()

                    
                self.xOutputCode += xPullObj.Set(self)
            
            elif self.xCommand == commandTypes.NEWSTR:
                xBasePointerObj = self.xArguments[1]
                xAllocStringObj = self.xArguments[0]
                xAllocString    = xAllocStringObj.xValue

                if xBasePointerObj.xType != objTypes.VAR:
                    cUtils.LineError(self.xLineNumber, "Base Pointer must be Variable")
                    
                if xAllocStringObj.xType != objTypes.STRING:
                    cUtils.LineError(self.xLineNumber, "Alloc Object must be String")



                #convert in into ascii and add a NULL terminator
                #the 0 is a placeholder for the size of the chunk
                xRawStringData = [0] + [ord(x) for x in cUtils.UnescapeStr(xAllocString)] + [0]

                #xRawStringData = [0]
                #for xLineIterator in xAllocString.split("\\n"):
                #    xRawStringData += [ord(x) for x in xLineIterator] + [10]

                #override the last newline with a NULL terminator
                #(yes, terminators are generally bad, but in this case it's fine because it's known to compile time that the terminator
                # won't be contained in the data, considering ascii)
                
                xAllocSize = len(xRawStringData)
                
                xRawStringData[-1] = 0
                xRawStringData[0] = xAllocSize #override placeholder
                
                
                
                if xBasePointerObj.xValue not in self.xVarMapper.keys():
                    self.xVarMapper[xBasePointerObj.xValue] = self.StaticAlloc()
                                         
                
                #allocate heap memory
                self.xOutputCode += cCodeGen.cCommand.List2Self([
                    "set", xAllocSize,
                    "ahm", None,
                    "sAD", xStringWritePtr,
                    "set", 1,
                    "add", None,
                    "pha", None,
                                        
                    ]) + xBasePointerObj.Set(self)
                    
                for xCharIter in xRawStringData:
                    self.xOutputCode += cCodeGen.cCommand.List2Self([
                        "set", xCharIter,
                        "jmS", "_WriteChar",
                        
                        ])
                    
                
                
                    
                

            elif self.xCommand == commandTypes.PUTCHR:
                xPrintObj = self.xArguments[0]
                self.xOutputCode += xPrintObj.Eval(self) + cCodeGen.cCommand.List2Self([
                    "pla",    None,
                    "putstr", None,
                    
                    ])

            elif self.xCommand == commandTypes.ASM:
                xAsmStringObj = self.xArguments[0]
                xAsmStringRaw = xAsmStringObj.xValue

                xTempMapper = {}

                for xTerminalIter in xAsmStringRaw.split(";"):
                    if xTerminalIter.strip() == "": continue
                    xAsmCommandStruct = xTerminalIter.strip().split(" ")
                    
                    #correct for length of command
                    if len(xAsmCommandStruct) < 2:
                        xAsmCommandStruct.append(None)
                    
                    elif len(xAsmCommandStruct) > 2:
                        cUtils.LineError(self.xLineNumber, "Invalid Assembly")
                    
                    #if the structure of command has been validated process the inline
                    elif len(xAsmCommandStruct[1]) > 0:
                        xArg = xAsmCommandStruct[1]
                        
                        #variable reference
                        if (xArg[0], xArg[-1]) == ("(", ")"):
                            xAsmCommandStruct[1] = self.CheckVarMapper(xArg[1:-1])
                            
                        #temp reference
                        elif xArg[0] == "-":
                            xArgClean = xArg[1:]
                            
                            #get temp if 
                            if xArgClean not in xTempMapper.keys():
                                #this is some black magic, because TempAlloc will always return the same list (you're meant to only call it once pre instruction, so you have to specify how much memory you need)
                                #but this needs a different temp value, each time called, so it will just ignore the mapped values, my taking the last on in the list
                                xTempMapper[xArgClean] = self.TempAlloc(len(xTempMapper) + 1)[-1]
                                
                            xAsmCommandStruct[1] = xTempMapper[xArgClean]
                    
                    
                    self.xOutputCode += cCodeGen.cCommand(*xAsmCommandStruct)
            
            #dynamic memory allocation is supported by S1monsAssembly directly
            #the baabnq compiler uses this feature by having a chunk of heap memory allocated, one longer that requested
            #it offset the base pointer to the chunk and uses the index 0 (now technically -1) to store the size of the chunk
            #this makes it possible to free an entire chunk easily just by call the S1monsAssembly fhm(free heap memory) command with the right size
            elif self.xCommand == commandTypes.NEWDYN:
                xBasePointerObj = self.xArguments[1]
                xAllocSizeObj = self.xArguments[0]
                
                if xBasePointerObj.xType != objTypes.VAR:
                    cUtils.LineError(self.xLineNumber, "Base Pointer must be Variable")
                    
                elif xAllocSizeObj.xType not in [objTypes.CONST, objTypes.VAR, objTypes.EXPR]:
                    cUtils.LineError(self.xLineNumber, "Alloc Size must be of the following types: Variable, Constant or Expression")
                
                
                if xBasePointerObj.xValue not in self.xVarMapper.keys():
                    self.xVarMapper[xBasePointerObj.xValue] = self.StaticAlloc()

            
                xTempAddr = self.TempAlloc(1)[0]
            
                self.xOutputCode += xAllocSizeObj.Eval(self) + cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "set", 1,
                    "add", None,
                    "sAD", xTempAddr, 
                    "lDR", xTempAddr,
                    "ahm", None,
                    "sAD", xTempAddr,
                    "sRP", xTempAddr,
                    "set", 1,
                    "add", None,
                    "pha", None,
                    
                    ]) + xBasePointerObj.Set(self)
                    
            elif self.xCommand == commandTypes.FREE:
                xFreeObj  = self.xArguments[0]
                xTempAddr = self.TempAlloc(1)[0]

                self.xOutputCode += xFreeObj.Eval(self) + cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "set", 1,
                    "sub", None,
                    "sAD", xTempAddr,
                    "lPR", xTempAddr,
                    "fhm", None,
                    
                    
                    ])
                
            elif self.xCommand == commandTypes.STATICALLOC:
                xBasePointerObj = self.xArguments[1]
                xAllocSizeObj = self.xArguments[0]
                
                if xAllocSizeObj.xType != objTypes.CONST:
                    cUtils.LineError(self.xLineNumber, "Alloc Size must be Constanst for static allocation")
                    
                elif xBasePointerObj.xType != objTypes.VAR:
                    cUtils.LineError(self.xLineNumber, "Base Pointer must be Variable")
                
                
                if xBasePointerObj.xValue not in self.xVarMapper.keys():
                    self.xVarMapper[xBasePointerObj.xValue] = self.StaticAlloc()

                        
                try:
                    xAllocSizeValue = xAllocSizeObj.xValue
                    xAllocSizeInt = int(xAllocSizeValue)

                except Exception as E:
                    cUtils.LineError(self.xLineNumber, f"Could not convert Alloc Size {xAllocSizeValue} to integer".format())

                if xAllocSizeInt == 0:
                    cUtils.LineError(self.xLineNumber, f"Alloc Size must not be 0")
                    
                xTempAddr = self.TempAlloc(1)[0]
                
                xAllocSizeFull = xAllocSizeInt + 1

                #plus one for length information
                xBasePointer = self.StaticNAlloc(xAllocSizeFull)
                self.xOutputCode += cCodeGen.cCommand.List2Self([
                    #write length information
                    "set", xBasePointer,
                    "sRD", xTempAddr,                    
                    "set", xAllocSizeFull,
                    "sRP", xTempAddr,
                
                    #write pointer
                    "clr", None,
                    "set", xBasePointer + 1,
                    "add", None,
                    "pha", None,
                    
                    ]) + xBasePointerObj.Set(self)


            elif self.xCommand == commandTypes.STATICSTRING:
                xBasePointerObj = self.xArguments[1]
                xAllocStringObj = self.xArguments[0]
                xAllocString    = xAllocStringObj.xValue

                if xBasePointerObj.xType != objTypes.VAR:
                    cUtils.LineError(self.xLineNumber, "Base Pointer must be Variable")
                    
                if xAllocStringObj.xType != objTypes.STRING:
                    cUtils.LineError(self.xLineNumber, "Alloc Object must be String")

                xRawStringData = [ord(x) for x in cUtils.UnescapeStr(xAllocString)]
                xFullData = [0] + xRawStringData + [0]
                
                xAllocSize = len(xFullData)                
                xFullData[0] = xAllocSize #override placeholder
                
                
                
                if xBasePointerObj.xValue not in self.xVarMapper.keys():
                    self.xVarMapper[xBasePointerObj.xValue] = self.StaticAlloc()
                                         
                
                #allocate heap memory
                self.xOutputCode += cCodeGen.cCommand.List2Self([
                    "clr", None,
                    "set", self.StaticNAlloc(xAllocSize),
                    "add", None,
                    "sAD", xStringWritePtr,
                    "set", 1,
                    "add", None,
                    "pha", None,
                                        
                    ]) + xBasePointerObj.Set(self)
                    
                for xCharIter in xFullData:
                    self.xOutputCode += cCodeGen.cCommand.List2Self([
                        "set", xCharIter,
                        "jmS", "_WriteChar",
                        
                        ])
            
        self.xOutputCode += cCodeGen.cCommand.List2Self(["brk", None])
        self.xOutputCode += xCompilerRoutineBuffer #append all the compiler routines after the break, just for general safety

        self.cOptimizer.Optimize(self.xOutputCode)

        return str(self.xOutputCode)

class cParser:
    class cCommand:
        def __init__(self, xCommandType, xArguments, xStartToken):
            self.xCommandType   = xCommandType
            self.xArguments     = xArguments
            self.xLine          = xStartToken.xLine
            self.xLineContent   = xStartToken.xLineContent
    
        def __str__(self):
            return str(self.xLine) + "\t" + "{xMessage: <25}".format(xMessage = str(self.xCommandType)) + "\t" + str([str(x) for x in self.xArguments])



    class cObj:
        class cExpr:
            def __init__(self, xInput):
                GetBracketCount = lambda x: x.count("(") - x.count(")")
                
                if GetBracketCount(xInput) != 0:
                    cUtils.Error(f"Bracket mismatch: {xInput}".format())
                
                
                self.xInput = xInput           
                self.xInputTerminals = self.xInput.split(" ")
                
                self.xOpDecoder = {
                    "+" : "add", 
                    "-" : "sub",
                    "|" : "lor",
                    "&" : "and",
                    "'" : "not",
                    "^" : "xor",
                    "<<": "shg",
                    ">>": "shs"
                }

                xCurrentBracketLevel = 0
                xLowerBracketLevel   = None
                
                xUpperIndex = None
                
                
                #find lowest operator
                for xInputIndex in range(len(self.xInputTerminals)):
                    xInputIter = self.xInputTerminals[xInputIndex]

                    if "(" in xInputIter: xCurrentBracketLevel += xInputIter.count("(")
                    if ")" in xInputIter: xCurrentBracketLevel -= xInputIter.count(")")
                                            
                    if xLowerBracketLevel is None or xLowerBracketLevel > xCurrentBracketLevel:
                        xLowerBracketLevel = xCurrentBracketLevel
                                            
                    if xInputIter in self.xOpDecoder.keys() and xCurrentBracketLevel == xLowerBracketLevel:
                        xUpperIndex = xInputIndex
                        
                
                if xUpperIndex is not None:
                    xSubExprStr1 = " ".join(self.xInputTerminals[:xUpperIndex])
                    xSubExprStr2 = " ".join(self.xInputTerminals[xUpperIndex + 1:])
                    
                    self.xSubExpr1 = self.__class__(xSubExprStr1[GetBracketCount(xSubExprStr1):])
                    self.xSubExpr2 = self.__class__(xSubExprStr2[:len(xSubExprStr2) + GetBracketCount(xSubExprStr2)])
                    self.xOperator = self.xInputTerminals[xUpperIndex]
                    self.OptimizeConstSubExpr()
                    
                
                else:
                    self.xOperator = None 
                self.xIsConst = self.xOperator is None and self.xInput.isdigit()
   
   
            #if both subexpr are contant the current expr can be optimized
            def OptimizeConstSubExpr(self):
                if all([self.xSubExpr1.xIsConst, self.xSubExpr2.xIsConst]):
                    try:
                        xSubValue1 = int(self.xSubExpr1.xInput)
                        xSubValue2 = int(self.xSubExpr2.xInput)

                    except ValueError:
                        return
                    
                    try:
                        xResult = {
                            "+"  : xSubValue1 + xSubValue2, 
                            "-"  : xSubValue1 - xSubValue2,
                            "|"  : xSubValue1 | xSubValue2,
                            "&"  : xSubValue1 & xSubValue2,
                            "^"  : xSubValue1 ^ xSubValue2,
                            "<<" : xSubValue1 << xSubValue2,
                            ">>" : xSubValue1 >> xSubValue2
                            }[self.xOperator]

                    except KeyError:
                        cUtils.Error(f"Invalid operator in constant expression: {self.xOperator}".format())
                    
                    self.xInput    = str(xResult % (cUtils.xIntLimit + 1))
                    self.xOperator = None
                    
            def Eval(self, xCodeGen):
                if self.xOperator is None:
                    if self.xInput.isdigit():
                        return cCodeGen.cCommand.List2Self([
                            "clr", None,
                            "set", int(self.xInput),
                            "add", None,
                            "pha", None,
                            
                            ])
                        
                    else:
                        return cCodeGen.cCommand.List2Self([
                            "lDA", xCodeGen.CheckVarMapper(self.xInput), 
                            "pha", None,
                            
                            ])
                        
                else:
                    xSubExpr1Code = self.xSubExpr1.Eval(xCodeGen)
                    xSubExpr2Code = self.xSubExpr2.Eval(xCodeGen)

                    xAssemblyOp = self.xOpDecoder[self.xOperator]
                    if xAssemblyOp in ["shs", "shg"]:
                        xTempAddresses = xCodeGen.TempAlloc(2)
                        xIndexAddr  = xTempAddresses[0]
                        xChangeAddr = xTempAddresses[1]
                        
                        xLoopLab = xCodeGen.GetTempLab()
                        xExitLab = xCodeGen.GetTempLab()                    
                        
                        #this code contains a loop to run the bit shift instructions multiple times
                        #because S1monsAssembler bit shift instructions only shift by one; they don't take an argument
                        return xSubExpr1Code + xSubExpr2Code + cCodeGen.cCommand.List2Self([
                     "pla", None,
                     "sAD", xIndexAddr, 
                     "pla", None,
                     "sAD", xChangeAddr, 
                     
                     "lab", str(xLoopLab), 
                     
                     "lDA", str(xIndexAddr), 
                     "jm0", xExitLab, 
                     "set", "1" ,
                     "sub", None,
                     "sAD", str(xIndexAddr), 

                     "lDA", str(xChangeAddr), 
                     xAssemblyOp, None, 
                     "sAD", str(xChangeAddr), 
                     
                     "got", xLoopLab, 
                     "lab", xExitLab, 
                     
                     "lDA", str(xChangeAddr), 
                     "pha", None,
                     
                     ])
        
                        
                    else:
                        xTempAddr = xCodeGen.TempAlloc(1)[0]
                        
                        return xSubExpr1Code + xSubExpr2Code + cCodeGen.cCommand.List2Self([
                            "pla", None,
                            "sAD", xTempAddr, 
                            "pla", None,
                            "lDR", xTempAddr, 
                            xAssemblyOp, None, 
                            "pha", None,
                            
                            ])



                
            def __str__(self):
                #return based on self.xOperator
                if self.xOperator is None:
                    return str(self.xInput)
                    
                else:
                    return "{" + str(self.xSubExpr1) + " " + str(self.xOperator) + " " + str(self.xSubExpr2) + "}"


        def __init__(self, xValue):
            if len(xValue) > 1 and ("'", "'") == (xValue[0], xValue[-1]):
                self.xType = objTypes.STRING
                self.xValue = xValue[1:-1]
            
            elif any([xOpIter in xValue for xOpIter in ["+", "-", "|", "&", "^", "<<", ">>", "(", ")"]]):
                self.xType = objTypes.EXPR
                self.xValue = self.cExpr(xValue)

            elif len(xValue) > 1 and xValue[0] == "_":
                self.xType = objTypes.VAR
                self.xValue = xValue
    
            elif str(xValue).isdigit():
                self.xType = objTypes.CONST
                self.xValue = xValue
                    
            else:
                self.xType = objTypes.NAME
                self.xValue = xValue
                
                
        #the code will eval to the stack
        def Eval(self, xCodeGen):
            if self.xType == objTypes.VAR:
                return cCodeGen.cCommand.List2Self([
                    "lDA", xCodeGen.CheckVarMapper(self.xValue),
                    "pha", None,
                    
                    ])
                        
            elif self.xType == objTypes.CONST:
                return cCodeGen.cCommand.List2Self([
                    "clr", None,
                    "set", self.xValue,
                    "add", None,
                    "pha", None,
                    
                    ])

            
            elif self.xType == objTypes.EXPR:
                return self.xValue.Eval(xCodeGen)
        
            else:
                cUtils.LineError(xCodeGen.xLineNumber, "Can not evaluate Name")
        
        
        def LoadPointer(self, xCodeGen):
            if self.xType == objTypes.VAR:
                return cCodeGen.cCommand.List2Self([
                    "lPA", xCodeGen.CheckVarMapper(self.xValue),
                    "pha", None,
                    
                    ])
                            
            elif self.xType == objTypes.CONST:
                return cCodeGen.cCommand.List2Self([
                    "lDA", self.xValue,
                    "pha", None,
                    
                    ])

            elif self.xType == objTypes.EXPR:
                xTempAddr = xCodeGen.TempAlloc(1)[0]
                
                return self.xValue.Eval(xCodeGen) + cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "sAD", xTempAddr,
                    "lPA", xTempAddr,
                    "pha", None,
                    
                    ])
                

            else:
                cUtils.LineError(xCodeGen.xLineNumber, "Can only evaluate Variable, Constant or Expression as Pointer")       
            
                    
        #this will return set code
        #set take the last value on the stack and overrides this obj with it          
        def Set(self, xCodeGen):
            if self.xType == objTypes.VAR:
                return cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "sAD", xCodeGen.CheckVarMapper(self.xValue),
 
                    ])
            
            else:
                cUtils.LineError(xCodeGen.xLineNumber, "Can only set variable")                   
                
                
        
        def SetPointer(self, xCodeGen):
            if self.xType == objTypes.VAR:
                return cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "sAP", xCodeGen.CheckVarMapper(self.xValue),
                
                    ])
                
            elif self.xType == objTypes.CONST:
                return cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "sAD", self.xValue,
                    
                    ])

            elif self.xType == objTypes.EXPR:
                xTempAddr = xCodeGen.TempAlloc(1)[0]

                return self.xValue.Eval(xCodeGen) + cCodeGen.cCommand.List2Self([
                    "pla", None,
                    "sAD", xTempAddr,
                    "pla", None,
                    "sAP", xTempAddr,
                    
                    ])
            
            else:
                cUtils.LineError(xCodeGen.xLineNumber, "")
                
                
                
                
        def __str__(self):
            return str(self.xValue)
        
    
    def __init__(self):
        self.xImportPathList = []
    
    #xImportParent is a list of the file potentially importing this file, to check for circle reference
    def Parse(self, xTokens = [], xUseParents = []):
        xTokenBuffer = []
        xCommandBuffer = []
        
        #make a copy of the tokens, because we want to keep the original
        xTokenSource = xTokens[:] 
        
        while len(xTokenSource) > 0:
            #move one token at a time from the xTokenSource to the xTokenBuffer
            xTokenBuffer.append(xTokenSource.pop(0))

            xTokenContents  = [xTokenIter.xTokenContent for xTokenIter in xTokenBuffer]
            xTokenTypes     = [xTokenIter.xTokenType    for xTokenIter in xTokenBuffer]
                        
            #scan for bullshit, syntax errors, my brain said goodbye
            for xScanDupTerminal in [tokenTypes.COMMAND, tokenTypes.ENDOFSTATEMENT]:
                if xTokenTypes.count(xScanDupTerminal) > 1:
                    #get error line by magic (find error source and look up it's index in the token buffer, then get the line of the error token with the .xLine variable)
                    xErrorLine = xTokenBuffer[xTokenTypes.index(xScanDupTerminal)].xLine
                    cUtils.LineError(xErrorLine, "Invalid Syntax")

            #put
            if xTokenTypes[-5:] in [[tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ASSIGNMENT, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT], 
                                    [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ASSIGNMENT, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT], 
                                    [tokenTypes.COMMAND, tokenTypes.EXPR, tokenTypes.ASSIGNMENT, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT],
                                    [tokenTypes.COMMAND, tokenTypes.EXPR, tokenTypes.ASSIGNMENT, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT],
                                    ] and \
               xTokenContents[-5] == "put":
                xBase           = self.cObj(xTokenContents[-4])
                xAssignmentType =           xTokenContents[-3]
                xOverride       = self.cObj(xTokenContents[-2])
                
                xCommandBuffer.append(self.cCommand(commandTypes.PUT, [xBase, xAssignmentType, xOverride], xTokenBuffer[-5]))
            
            #jump uncon
            elif xTokenTypes[-3:] == [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-3] == "jump":
                xTargetLabel = self.cObj(xTokenContents[-2])
                
                xCommandBuffer.append(self.cCommand(commandTypes.JUMPUNCON, [xTargetLabel], xTokenBuffer[-3]))

            
            
            #jump con
            elif xTokenTypes[-7:] in [[tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.JUMPCONDOP, tokenTypes.NAME, tokenTypes.CONDOP, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT], 
                                      [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.JUMPCONDOP, tokenTypes.EXPR, tokenTypes.CONDOP, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT],
                                      [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.JUMPCONDOP, tokenTypes.NAME, tokenTypes.CONDOP, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT],
                                      [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.JUMPCONDOP, tokenTypes.EXPR, tokenTypes.CONDOP, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT],
                                    ] and \
                xTokenContents[-7] == "jump":
                xTargetLabel, _, xValueA, xConditionalOp, xValueB = [self.cObj(xToken) for xToken in  xTokenContents[-6:-1]]
                
                xCommandBuffer.append(self.cCommand(commandTypes.JUMPCON, [xTargetLabel, xValueA, xConditionalOp, xValueB], xTokenBuffer[-7]))
                                
            #input
            elif xTokenTypes[-3:] == [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-3] == "input":
                xOverrideVar = self.cObj(xTokenContents[-2])
                
                xCommandBuffer.append(self.cCommand(commandTypes.INPUT, [xOverrideVar], xTokenBuffer[-3]))

            #print
            elif xTokenTypes[-3:] in [[tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT], [tokenTypes.COMMAND, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT]] and \
                xTokenContents[-3] == "print":
                xOutputObject = self.cObj(xTokenContents[-2])
                
                xCommandBuffer.append(self.cCommand(commandTypes.PRINT, [xOutputObject], xTokenBuffer[-3]))

            #sub uncon
            elif xTokenTypes[-3:] == [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-3] == "sub":
                xTargetLabel = self.cObj(xTokenContents[-2])
                
                xCommandBuffer.append(self.cCommand(commandTypes.SUBUNCON, [xTargetLabel], xTokenBuffer[-3]))

            
            
            #sub con
            elif xTokenTypes[-7:] in [[tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.JUMPCONDOP, tokenTypes.NAME, tokenTypes.CONDOP, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT], 
                                      [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.JUMPCONDOP, tokenTypes.EXPR, tokenTypes.CONDOP, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT],
                                      [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.JUMPCONDOP, tokenTypes.NAME, tokenTypes.CONDOP, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT],
                                      [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.JUMPCONDOP, tokenTypes.EXPR, tokenTypes.CONDOP, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT],
                                    ] and \
                xTokenContents[-7] == "sub":
                xTargetLabel, _, xValueA, xConditionalOp, xValueB = [self.cObj(xToken) for xToken in  xTokenContents[-6:-1]]
                
                xCommandBuffer.append(self.cCommand(commandTypes.SUBCON, [xTargetLabel, xValueA, xConditionalOp, xValueB], xTokenBuffer[-7]))

            #return
            elif xTokenTypes[-2:] == [tokenTypes.COMMAND, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-2] == "return":
                
                xCommandBuffer.append(self.cCommand(commandTypes.RETURN, [], xTokenBuffer[-2]))                
                
            #push
            elif xTokenTypes[-3:] in [[tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT], [tokenTypes.COMMAND, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT]] and \
                xTokenContents[-3] == "push":
                xPushValue = self.cObj(xTokenContents[-2])
                
                xCommandBuffer.append(self.cCommand(commandTypes.PUSH, [xPushValue], xTokenBuffer[-3]))                

            #pull
            elif xTokenTypes[-3:] == [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-3] == "pull":
                xPullDest = self.cObj(xTokenContents[-2])
 
                xCommandBuffer.append(self.cCommand(commandTypes.PULL, [xPullDest], xTokenBuffer[-3]))           

            #new (dynamic alloc)
            elif xTokenTypes[-4:] in [[tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT], [tokenTypes.COMMAND, tokenTypes.EXPR, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT]] and \
                xTokenContents[-4] == "new":
                xWordSize = self.cObj(xTokenContents[-3])
                xDestPtr  = self.cObj(xTokenContents[-2])

                xCommandBuffer.append(self.cCommand(commandTypes.NEWDYN, [xWordSize, xDestPtr], xTokenBuffer[-4]))                

            #new (string alloc)
            elif xTokenTypes[-4:] == [tokenTypes.COMMAND, tokenTypes.STRING, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-4] == "new":
                xTargetString   = self.cObj(xTokenContents[-3])
                xDestPtr        = self.cObj(xTokenContents[-2])
                
                xCommandBuffer.append(self.cCommand(commandTypes.NEWSTR, [xTargetString, xDestPtr], xTokenBuffer[-4]))

            #static (static alloc)
            elif xTokenTypes[-4:] in [[tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT]] and \
                xTokenContents[-4] == "static":
                xWordSize = self.cObj(xTokenContents[-3])
                xDestPtr  = self.cObj(xTokenContents[-2])

                xCommandBuffer.append(self.cCommand(commandTypes.STATICALLOC, [xWordSize, xDestPtr], xTokenBuffer[-4]))                

            #static (string alloc)
            elif xTokenTypes[-4:] == [tokenTypes.COMMAND, tokenTypes.STRING, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-4] == "static":
                xTargetString   = self.cObj(xTokenContents[-3])
                xDestPtr        = self.cObj(xTokenContents[-2])
                
                xCommandBuffer.append(self.cCommand(commandTypes.STATICSTRING, [xTargetString, xDestPtr], xTokenBuffer[-4]))

            
            #lab
            elif xTokenTypes[-3:] == [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-3] == "lab":
                xLabel = self.cObj(xTokenContents[-2])

                xCommandBuffer.append(self.cCommand(commandTypes.LABEL, [xLabel], xTokenBuffer[-3]))
            
            #putchr
            elif xTokenTypes[-3:] in [[tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT], [tokenTypes.COMMAND, tokenTypes.EXPR, tokenTypes.ENDOFSTATEMENT]] and \
                xTokenContents[-3] == "putchr":
                xStrValue = self.cObj(xTokenContents[-2])
            
                xCommandBuffer.append(self.cCommand(commandTypes.PUTCHR, [xStrValue], xTokenBuffer[-3]))

            #asm
            elif xTokenTypes[-3:] == [tokenTypes.COMMAND, tokenTypes.STRING, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-3] == "asm":
                xAsmContent = self.cObj(xTokenContents[-2])
            
                xCommandBuffer.append(self.cCommand(commandTypes.ASM, [xAsmContent], xTokenBuffer[-3]))

            #free
            elif xTokenTypes[-3:] == [tokenTypes.COMMAND, tokenTypes.NAME, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-3] == "free":
                xFreePtr = self.cObj(xTokenContents[-2])
            
                xCommandBuffer.append(self.cCommand(commandTypes.FREE, [xFreePtr], xTokenBuffer[-3]))

            elif xTokenTypes[-3:] == [tokenTypes.COMMAND, tokenTypes.STRING, tokenTypes.ENDOFSTATEMENT] and \
                xTokenContents[-3] == "use":
                #the use statement is evaled here
                                
                #remove the ' at the start and end of the path
                xImportPath = xTokenContents[-2][1:-1].strip()
                
                if xImportPath not in self.xImportPathList:
                    self.xImportPathList.append(xImportPath)
                    
                    #try to load path as file
                    try:
                        with open(xImportPath, "r", encoding = 'utf-8') as f:
                            xImportFile = f.read()
                                        
                    except FileNotFoundError:
                        cUtils.LineError(xTokenBuffer[-3].xLine + 1, "Unable to load library file with path '{xPath}'".format(xPath = xImportPath))
                    
                    #if a circle reference is detected, the action needs to be passed back to the main caller, to handle the error
                    #this is done by returning a special error value
                    if xImportPath in xUseParents:
                        #just return an instance of the exception class, because i'm too lazy to make my own
                        return Exception()
                    
                    
                    
                    
                    xImportedCommandStream = self.Parse(cTokenizer().Tokenize(xImportFile, xPrintLine = False), xUseParents + [xImportPath])                
                    #check if error has been returned to catch
                    if type(xImportedCommandStream) is Exception:
                        #after the error has been returned back to the main file parser, call the error
                        if len(xUseParents) == 0:
                            cUtils.LineError(xTokenBuffer[-3].xLine + 1, "Circle Reference while loading imported library")
                            
                        else:
                            return Exception()
    
                    xCommandBuffer += xImportedCommandStream
    
                        
            else:                        
                continue
            
            xTokenBuffer = []

        
        return xCommandBuffer



class cTokenTypes:
    def __init__(self):
        xGen = cUtils.Gen()
        
        self.STRING         = next(xGen)
        self.EXPR           = next(xGen)
        self.COMMAND        = next(xGen)
        self.OPERATOR       = next(xGen)
        self.JUMPCONDOP     = next(xGen)
        self.ASSIGNMENT     = next(xGen)
        self.CONDOP         = next(xGen)
        self.NAME           = next(xGen)
        self.ENDOFSTATEMENT = next(xGen)

tokenTypes   = cTokenTypes()



class cTokenizer:
    @dataclass
    class cToken:
        xTokenContent : str
        xTokenType    : int
        xLine         : int
        xLineContent  : str
        #self.xIndex        
                        
        def __str__(self):
            return str(self.xLine + 1) + "\t" + "{xMessage: <25}".format(xMessage = str(self.xTokenContent)) + str(self.xTokenType)
    
    
    def __init__(self):
        self.xCommands = ["put", "jump", "input", "print", "sub", "return", "push", "pull", "new", "lab", "putchr", "asm", "use", "free", "static"]
        self.xOperators = ["+", "-", "|", "&", "^", "<<", ">>"]
        self.xBrackets = ("(", ")")
        self.xAssignmentType = ["<-", "->", "="]
        self.xCOps = ["==", ">", "<", "!="]
        self.xStringMark = "'"
        self.xEOS = ";" #end of statement
        self.xJumpConditionalOperator = "~"
        
        self.xBracketLevel = 0
    
    
    def Tokenize(self, xRawInput = "", xPrintLine = True):
        xLines = xRawInput.split("\n")
        
        #keeps track of if string or other multi-terminal token is being tokenized and what type of multi-terminal token is being tracked
        xKeepTokenBuffer = False
        xConsumingComment = False
        xTerminalBuffer  = []
        
        xTokenBuffer = []
        
        
        for xLineIndex in range(len(xLines)):
            xLineIter = xLines[xLineIndex]
            if xPrintLine: 
                print(f"{xLineIndex+1: <10} {xLineIter}")
            
            for xSplitLineIter in xLineIter.split(" "):
                #check for comment and keep consuming terminal while on the same line
                if len(xSplitLineIter) > 0 and xSplitLineIter[0] == '"':
                    xConsumingComment = True
                    
                if xConsumingComment:
                    continue
                
                  
                #check for end of statement (aka ;)
                xEndOfStatement = len(xSplitLineIter) > 0 and xSplitLineIter[-1] == self.xEOS

                #exclude the ";", because it's not needed for the actual token
                xTerminalIter = xSplitLineIter[:-1] if xEndOfStatement else xSplitLineIter
                
                if xKeepTokenBuffer:

                    if self.xStringMark in xSplitLineIter:
                        xTerminalBuffer.append(xTerminalIter)                    

                        xKeepTokenBuffer = False
                        xTokenBuffer.append(self.cToken(" ".join(xTerminalBuffer), tokenTypes.STRING, xLineIndex, xLineIter))
                        xTerminalBuffer = []
                        
                    else:
                        xTerminalBuffer.append(xSplitLineIter)
                        continue #skip end of statement check


                #strings
                elif self.xStringMark in xSplitLineIter:
                    xMarkCount = xSplitLineIter.count(self.xStringMark)
                    
                    if xMarkCount % 2 == 1:
                        xKeepTokenBuffer = True
                        xTerminalBuffer.append(xSplitLineIter)
                        continue #skip end of statement check

                    else:
                        xTokenBuffer.append(self.cToken(xTerminalIter, tokenTypes.STRING, xLineIndex, xLineIter))
                
                #brackets
                elif self.xBrackets[0] in xTerminalIter or self.xBrackets[1] in xTerminalIter:
                    
                    xBracketsOpened = xTerminalIter.count("(")
                    xBracketsClosed = xTerminalIter.count(")")
                    xBracketDelta = xBracketsOpened - xBracketsClosed

                    self.xBracketLevel += xBracketDelta
                    xTerminalBuffer.append(xTerminalIter)
                    
                    if self.xBracketLevel == 0:
                        xTokenBuffer.append(self.cToken(" ".join(xTerminalBuffer), tokenTypes.EXPR, xLineIndex, xLineIter))
                        xTerminalBuffer = []
                    
                    
                    
                elif self.xBracketLevel > 0:
                    xTerminalBuffer.append(xTerminalIter)

                
                
                

                elif xTerminalIter in self.xCommands:
                    xTokenBuffer.append(self.cToken(xTerminalIter, tokenTypes.COMMAND, xLineIndex, xLineIter))

                elif xTerminalIter in self.xOperators:
                    xTokenBuffer.append(self.cToken(xTerminalIter, tokenTypes.OPERATOR, xLineIndex, xLineIter))

                elif xTerminalIter == self.xJumpConditionalOperator:
                    xTokenBuffer.append(self.cToken(xTerminalIter, tokenTypes.JUMPCONDOP, xLineIndex, xLineIter))
                    
                elif xTerminalIter in self.xAssignmentType:
                    xTokenBuffer.append(self.cToken(xTerminalIter, tokenTypes.ASSIGNMENT, xLineIndex, xLineIter))
                    
                elif xTerminalIter in self.xCOps:
                    xTokenBuffer.append(self.cToken(xTerminalIter, tokenTypes.CONDOP, xLineIndex, xLineIter))
                
                elif xTerminalIter.strip() != "":
                    xTokenBuffer.append(self.cToken(xTerminalIter, tokenTypes.NAME, xLineIndex, xLineIter))
                    
                if (not xKeepTokenBuffer) and len(xTokenBuffer) >= 3 and xTokenBuffer[-2].xTokenType == tokenTypes.OPERATOR:
                    xExprTokens = [xTokenBuffer.pop(-3 + xPopIndex) for xPopIndex in range(3)]
                    xExprContent = " ".join([str(xTokenIter.xTokenContent) for xTokenIter in xExprTokens])
                    
                    xTokenBuffer.append(self.cToken(xExprContent, tokenTypes.EXPR, xExprTokens[0].xLine, xLineIter))
                    
                    

                #append end of statement token if needed
                if xEndOfStatement:
                    xTokenBuffer.append(self.cToken(self.xEOS, tokenTypes.ENDOFSTATEMENT, xLineIndex, xLineIter))
        
            xConsumingComment = False
        
        return xTokenBuffer

class cCompiler:
    def __init__(self):
        self.xTokenizer = cTokenizer()
        self.xParser    = cParser()
        self.xCodeGen   = cCodeGen()

    
    def Compile(self, xRawInput):
        xTokenList      = self.xTokenizer.Tokenize(xRawInput)
        xCommandList    = self.xParser.Parse(xTokenList)
        xOutputAssembly = self.xCodeGen.Generate(xCommandList)
        
        xUsed  = self.xCodeGen.xMemUsedIndex
        xTotal = cUtils.xMemLimit
        
        print(f"\nStatically allocated Memory: {round(xUsed / xTotal * 100, 5)}% ({xTotal} / {xUsed})")
        
        return xOutputAssembly, self.xCodeGen.xVarMapper


if __name__ == '__main__':

    xParser = argparse.ArgumentParser(
        prog='Compiler',
        description='Baabnq Compiler',
        epilog='Good luck :3')
    
    xParser.add_argument('-i', '--input', dest="inPath", required=True)
    xParser.add_argument('-o', '--output', dest="outPath", default="build.s1")
    xArgs = xParser.parse_args()
    
    with open(xArgs.inPath, "r", encoding = 'utf-8') as xInFile:
        xIn = xInFile.read()
    
    xCompiler = cCompiler()
    xAsm, xVarMapper = xCompiler.Compile(xIn)
    xOut = f'{xAsm}\n\n\n\n\n "Compiled from source: {xArgs.inPath}'

    with open(xArgs.outPath, "w") as xOutFile:
        xOutFile.write(xOut)
    
    print("\nCompilation was successful")
    
    
    
    