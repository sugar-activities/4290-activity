#!/usr/bin/env python
#This python module is part of the Jam2Jam XO Activity, March, 2010
#
#Copyright (C) 2010 Thorin Kerr & Andrew Brown
#    
#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or any
#later version.
#   
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
import csnd
from heapq import heappush, heappop
from CsHelpers import *

class Csound:
    "precompiles a csound object"
    def __init__(self):
        self.csound = csnd.CppSound()
        self.csound.setPythonMessageCallback()
        self.csound.PreCompile()
    def __repr__(self):
        return "Precompiled Csound object"

class Sched( object ):
    queue = []
    time = 0
    def __init__(self,  kr=172.265625, tempo=60):
        self.kr = kr
        self.tempo = 60
    def _increment(self):
        "return the time increment value"
        return (1.0 / self.kr) * (60.0 / self.tempo) 
    def poll(self, inc):
        "increments the time value, and evaluates items scheduled in the past"
        self.time += (1.0 / self.kr) * (self.tempo / 60.0) #increment the time. The question is... should I let Csound store the time. No GIL that way. hmmm.
        for i in self.queue:
            if self.time >= i[0]:
                obj = heappop(self.queue)
                (obj[1] (*obj[2]))
            else: break
    def schedEvent(self, time, func, *args):
        heappush(self.queue, (time, func, args))
    def getTime(self):
        if self:
            return self.queue[0][0]
        else:
            return False
    def getFunc(self):
        if len(self) == 0:
            return False
        else:
            return self.queue[0][1]
    def getArgs(self):
        if len(self) == 0:
            return False
        else:
            return self.queue[0][2]
    def __len__(self):
        return len(self.queue)
    def __add__(self, integer):
        "returns now + time value"
        return self.now() + integer
    def __rshift__(self, beat):
        "returns the next nth beat time"
        return ceil(self.now()) + beat
    def __div__(self, barlength):
        "where barlength is the number of beats in a bar, returns a tuple of the current time represented in the form (bar no. , beat no)"
        return divmod(self.now(), barlength)
    def now(self):
        return self.time
    def reset(self, reset=0):
        self.time = reset
    
class CsoundChan:
    "an empty container for Csound channel data"
        #type is either Audio, Control, or String
        #Direction = INput or Output
        #subType = interger, linear or exponential
        #default = default value
        #minval = suggested minimum
        #maxval == suggested maximum
    pass
    


def channels(csound):
    "returns a list of Input and output software bus channels"
    Chanlist = csnd.CsoundChannelList(csound)
    result = []
    for ndx in range(Chanlist.Count()):
        ch = CsoundChan()
        ch.name = Chanlist.Name(ndx)
        if Chanlist.IsAudioChannel(ndx):
            ch.type = "Audio"
        elif Chanlist.IsControlChannel(ndx):
            ch.type = "Control"
        elif Chanlist.IsStringChannel(ndx):
            ch.type = "String"
        else: pass
        if Chanlist.IsInputChannel(ndx) and Chanlist.IsOutputChannel(ndx):
        	ch.direction = "bidirectional"
        elif Chanlist.IsInputChannel(ndx):
        	ch.direction = "input"
        elif Chanlist.IsOutputChannel(ndx):
        	ch.direction = "output"
        else: pass 
        if Chanlist.SubType(ndx) > 0:
            tmp = ['integer', 'linear', 'exponential']
            ch.subtype = (tmp[Chanlist.SubType(ndx) - 1])
            ch.default = (Chanlist.DefaultValue(ndx))
            ch.minval = (Chanlist.MinValue(ndx))
            ch.maxval = (Chanlist.MaxValue(ndx))
        result.append(ch)
    Chanlist.Clear()
    return result


class CsoundPerformer:
    def pollScheduler(self, schedObj):
        st =  schedObj.getTime()
        if st:
            t = self.perfTime()
            if t >= st:
                obj = heapq.heappop(schedObj.queue)
                (obj[1] (*obj[2]))
    def __init__(self, metro, orcObj, *cs):
        "SchedObj is a Csound timer instance, orcObJ is a CsOrcConstructor Object"
        #self.Timer = csnd.CsoundTimer()
        self.metro = metro
        #self.schedObj = schedObj
        self.orcObj = orcObj
        if len(cs) == 0:
            cs = Csound()
            self.csound = Csound.csound
        else: self.csound = cs[0] 
        self.csound.setOrchestra(orcObj.exportOrc())
        self.csound.setScore(orcObj.sco)
        
        if platform == "Sugar":
            self.csound.setCommand("csound -b256 -B2048 -+rtaudio=alsa -odac --expression-opt --sched=1 -d -m0 /tmp/tmp.orc /tmp/tmp.sco")
        else:
            self.csound.setCommand("csound -b256 -B2048 -odac --expression-opt -d -m0 /tmp/tmp.orc /tmp/tmp.sco")
        self.csound.exportForPerformance()
        self.csound.compile()
        self.Channels = channels(self.csound)
        self.perf = csnd.CsoundPerformanceThread(self.csound) 
        self.perf.Play()
        self.perf.SetProcessCallback(self.metro.poll, 0)
    def perfTime(self):
        return self.metro.now()
        #return self.Timer.GetRealTime()
    def Stop(self):
        self.perf.Stop()
        #self.perf.Join()
        self.csound.Cleanup()
    def setChannelValue(self, channame, value):
        self.csound.SetChannel(channame, value)
    def getChannelValue(self, channame):
        return self.csound.GetChannel(channame)
    def getChannelList(self):
        return csnd.CsoundChannelList(self.csound)
    def getChannelNames(self):
        chlst = self.getChannelList()
        return [chlst.Name(ch) for ch in range(chlst.Count())]
    def playParams(self, ins, start, dur, *params):
        "send score message to Csound with parameter values"
        if start < 0: start = 0
        s = ' '.join(map(str, (['i', ins, start, dur] + [str(n) for n in params])))
        self.perf.InputMessage(s)
    def playNote(self, ins, note):
        "send score message to Csound using a note object"
        start = note[0]
        dur = note[1]
        params = note[2:]
        self.perf.InputMessage(' '.join(['i', str(ins),str(start),str(dur)]+[str(n) for n in params]))


