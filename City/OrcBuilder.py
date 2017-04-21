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
#!/usr/bin/env python

import csnd, sys
from CsHelpers import *


class Ftable:
    def __init__(self):
        self.start = 0
        self.num = 0
        self.size = 8192
        self.gen = 10
        self.name = "sine"
        self.args = [10,1]
    def varname(self):
        return "gi_"+self.name
    def __repr__(self):
        head = [self.varname(), 'ftgen', str(self.num)+', ']
        args = [str(self.start), str(self.size), str(self.gen)] + map(str, self.args) 
        return ' '.join(head) + ', '.join(args)
        
class FtableBreakPoint(Ftable):
    "constructs a Gen 2 ftable"
    def __init__(self, name, *args, **num):
        Ftable.__init__(self)        
        self.name = name
        self.gen = -2
        self.size = (2**i for i in xrange(2,100) if 2**i >= len(args)).next()
        self.args = args
        if num.has_key('num'): self.num = num['num']

class FtableSample(Ftable):
    "loads samples into GEN 1, and optional basepitch storage"
    def __init__(self, pathname, *basepit, **num):
        Ftable.__init__(self)
        self.gen = -1
        filename = pathname.rpartition('/')[-1]
        ndx = filename.find('.')
        if ndx != -1:
            self.name = removeillegals(filename[0:ndx])
        else: self.name = removeillegals(filename)
        self.size = 0
        self.args = ['"'+pathname+'"', 0, 0, 0]
        if len(basepit) > 0:
            self.basePitch = basepit[0]
        if num.has_key('num'): self.num = num['num']

class FtableLookup(Ftable):
    def __init__(self, name, skew, *sampletables, **num):
        "uses GEN17 to make an x,y lookup table suitable for mid pitch lookup. GEN17"
        #skew calculates the point at which the next table is lookup up.
        #pitnamedict is a dictionary of {basepitches:samplenames,...}
        Ftable.__init__(self)
        pitnamedict = {}
        for s in sampletables:
            pitnamedict[s.basePitch] = s.varname()
        sorted = []
        for key in pitnamedict:
            sorted.append([key, pitnamedict[key]])
        sorted.sort()
        args = []
        for i in range(len(sorted)):
            if i == 0: 
                args.append(i)
                args.append(sorted[i][1])
            else:
                args.append(int(round (sorted[i][0] - (sorted[i][0] - sorted[i-1][0]) * skew)))
                args.append(sorted[i][1])
        self.gen = -17
        self.name = name
        self.size = 128
        self.args = args
        if num.has_key('num'): self.num = num['num']

class OrcChan:
    def __init__(self, name, direction, rate, init):
        self.name = name
        self.direction = direction
        self.rate = rate
        self.initval = init
    def mode(self):
        return (1 if self.direction == 'input' else (2 if self.direction == 'output' else 3))
    def varname(self): 
        return 'g'+('a' if self.rate == 'audio' else ('k' if self.rate == 'control' else ('S' if self.rate == 'string' else 'i')))+'_'+self.name
    def initline(self):
        return self.varname() + '\t' + 'init' + '\t' + str(self.initval)
    def __repr__(self):
        final = self.varname() + ' '+'chnexport'+' \"'+self.name+'\", '+str(self.mode())+('\n'+self.initline() if (self.rate == 'audio' or self.rate == 'string') else ',2,1,0,1'+ '\n'+self.initline())
        return final

def orcChannelMaker(insnames, parameter, direction = "input", rate = "control", init = 1):
    "a simple function to generate numerous channels of the same type"
    result = []
    for i in insnames:
        name = i+parameter
        o = OrcChan(name, direction, rate, init)
        result.append(o)
    return result

#Not cognisant of scoreline parameter variables at this stage.
class OrcInstrument:
    def __init__(self, name='undefined'):
        self.name = name
        self.lines = []
        self.effect = False #if true, then an 'always on' scoreline is automatically added.
    def header(self): 
        return ["instr \t$"+self.name+"\n"]
    def varname(self):
        return "$"+self.name
    def insertLine(self, line):
        self.lines.append(line)
    def routeOut(self, asendvar, outINS, SetLvlIns, gkvarname = 1, *chan):
        "SO, gkvarname is 1 by default, but should be the gkvariable if going to mixout"
        SetLvlIns.setLevel(self, outINS, gkvarname)  
        self.insertLine("\tMixerSend "+asendvar+", p1, "+outINS.varname()+", "+str((chan[0] if len(chan)>0 else 0)))
    def routeIn(self, ainvar, *chan):
        self.lines.insert(0, ainvar+" MixerReceive "+"p1,"+str((chan[0] if len(chan)>0 else 0)))
    def __repr__(self):
        result = self.header() + self.lines
        return "\n".join(result) + '\n\nendin\n'
    
class OrcSetLevelInstrument(OrcInstrument):
    def __init__(self):
        OrcInstrument.__init__(self)
        self.name = "mixerSetLevels"
        self.routemap = {}
    def setLevel(self, sendINS, bussINS, gkvarname):
        self.routemap[sendINS.name] = bussINS.name
        self.insertLine("\t MixerSetLevel "+sendINS.varname()+", "+bussINS.varname()+", "+str(gkvarname)+"\n") #change this to the gkvariable name
    def mixout(self, ainvar, *chan):
        "sends output of an instrument to a mixer buss"
        self.insertLine("\tMixerSend "+ainvar+", p1, "+"$output, "+str((chan[0] if len(chan)>0 else 0)))


class OrcMixoutInstrument(OrcInstrument):
    def __init__(self):
        OrcInstrument.__init__(self)
        self.name = "output"
        self.routeIn("am")
        self.insertLine("""
            am eqfil am, 900, 200, 0.2
            a3 nreverb am, 0.12, 1, 0, 8, gi_rvbc1, 4, gi_rvba1
            a4 nreverb am, 0.12, 1, 0, 8, gi_rvbc2, 4, gi_rvba2
            a3 = am + a3*0.23
            a4 = am + a4*0.23
            outs a3, a4
            ;outs am, am
            MixerClear        
            """)
        


class OrcConstructor:
    def __init__(self):
        self.orc = ""
        self.sco = "f0 28800 \n"
        self.sr = 44100
        self.ksmps = 100
        self.nchnls = 2
        self.dbfs = 1
        self.macros = []
        self.ftabs = []
        self.chans = []
        self.instruments = []
        self.csline = []
        self.nameNumber = {}
        self.insertftables(Ftable()) #insert a sine by default
    def insertLines(self, lines):
        self.csline.append(lines)
    def insertInsnums(self, Instruments):
        insnumgen = (i for i in xrange(1, 100))
        for i in Instruments:
            num = insnumgen.next()
            self.nameNumber[i.name] = num
            self.macros.append("#define "+i.name+" #"+str(num)+"#")
            if i.effect:
                self.sco = self.sco + "i%s 0 -1 \n" %num
    def insertftables(self, *tabs):
        "inserts Orcfunction tables using Ftable objects"
        for t in tabs:
            self.ftabs.append(t)
    def insertChannels(self, *OrcChans):
        "inserts a Orcchannel objects into a Csound orc"
        for c in OrcChans:
            self.chans.append(c)
    def appendInstruments(self, *CsIns):
        for i in CsIns:
            self.instruments.append(i)
    def prependInstrument(self, CsIns):
        "inserts an instrument at the front of the orchestra"
        self.instruments.insert(0, CsIns)
    def exportOrc(self):
        self.insertInsnums(self.instruments)
        header = [x+y for x,y in zip(['sr = ', 'ksmps = ', 'nchnls = ', '0dbfs = '], map(str,[self.sr, self.ksmps, self.nchnls, self.dbfs]))]
        insnums = self.macros
        ftabs = map(str, self.ftabs)
        lines = map(str, self.csline)
        chans = map(str, self.chans)
        Ins = map(str, self.instruments)
        result = header + insnums + ftabs + chans + lines + Ins
        return '\n'.join(result)
    def __repr__(self):
        return "CSound orchestra object" + str(self.__dict__)

class sndInfo:
    def __init__(self, path, *csd):
        "query information of an audio file at path. csd is a precompiled csound instance"
        if len(csd) == 0:
            cs = Csound()
            self.cs = Csound.csound
        else: self.cs = csd[0] #can pass a precompiled csound as an argument
        self.contents = ''
        args = csnd.CsoundArgVList()
        args.Append('sndinfo')
        args.Append('-i')
        args.Append(path)
        old_stdout = sys.stdout
        sys.stdout = self
        err = self.cs.RunUtility('sndinfo', args.argc(), args.argv())
        sys.stdout = old_stdout        
        self._lines()
        header = [l for l in self.lines if l.__contains__('\tsrate')]
        self.header = header[0].split(',')
    def write(self, c):
        self.contents += c
    def _lines(self):
        self.lines = self.contents.splitlines()
    def sr(self):
        srl = [c for c in self.header[0] if c.isdigit()]
        return int(''.join(srl))
    def chans(self):
        if self.header[1].__contains__('monaural'):
            return 1
        else: return 2
    def type(self):
        return self.header[2]
    def duration(self):
        s = self.header[3]
        return float(''.join([n for n in s if n.isdigit() or n == '.']))
    def findNoteAttribute(self, attr):
        result = 0
        for i in self.lines:
            if i.startswith(attr, 2):
                result = int(''.join([n for n in i if n.isdigit()]))
        return result
    def BaseNote(self):
        "return the Base Note"
        return self.findNoteAttribute('Base')

def orcLoadSamples(orc, Cs, fnlookupname, *paths):
    "Inserts Gen1 ftables for samples located in paths, and an associated GEN17 midi pitch lookup table based on base pitch in soundfile into orc"
    sfns = []
    for p in paths:
        for f in ResourceList(p,'.aif'):
            snd = sndInfo(p+'/'+f, Cs.csound) 
            bn = snd.BaseNote()             
            fn = FtableSample(p+'/'+f, bn)
            orc.insertftables(fn)           
            sfns.append(fn)                 
    flookup = FtableLookup(fnlookupname, 0.3, *sfns)
    orc.insertftables(flookup)             
    return flookup                          

if __name__ == '__main__':
    print "running OrcBuilder as __main__"

    from CsSched import *
    Csynth = Csound()
    TimeQueue = Sched()

    #Create a csound orchestra
    orc = OrcConstructor()
    orc.sr = 22050
    orc.ksmps = 256

    #Function tables
    lookuptabs = [orcLoadSamples(orc, Csynth, instr+"Lookup", eval(instr+"AudioPath")) for instr in INAMES]
    ftabs = [FtableBreakPoint("rvbc1", -558, -594, -638, -678, -711, -745, -778, -808,  0.8,  0.79,  0.78,  0.77,  0.76,  0.75,  0.74,  0.73),
    FtableBreakPoint("rvbc2", -517, -540, -656, -699, -752, -799, -818, -841,  0.8,  0.79,  0.78,  0.77,  0.76,  0.75,  0.74,  0.73),
    FtableBreakPoint("rvba1", -278, -220, -170, -122,  0.4,  0.52,  0.64,  0.76),
    FtableBreakPoint("rvba2", -333, -263, -166, -105,  0.5,  0.52,  0.64,  0.76)]
    orc.insertftables(*ftabs)

    #Control Channels: Should conform to the Parameter naming convention already in use.
    volumechans = orcChannelMaker(INAMES, "Volume")
    timbrechans = orcChannelMaker(INAMES, "Timbre", init = 0.5)
    orc.insertChannels(*volumechans)
    orc.insertChannels(*timbrechans)
    #timbrechans[0].varname()

    #Instruments
    #first, establish a setlevel instrument
    setlevels = OrcSetLevelInstrument()
    setlevels.effect = True
    #then work backwards. 
    #A mixer:
    mixerout = OrcMixoutInstrument()
    mixerout.effect = True

    #sampler instruments
    samplerbody = """
        idur = p3
        iamp = p4 * (0dbfs / 127)
        kcps init cpsmidinn(p5)
        isamp table p5, %s
        a1 loscil iamp, kcps, isamp
        a1 dcblock a1 
        kdeclick linseg 0, 0.001, 1, idur - 0.03 - 0.001, 1, 0.03, 0
        a1 = a1 * kdeclick 
        """
    #timbre instruments    
    #be aware that samplerates lower than 22050 tend to blow up the rezzy filter
    #at this level of resonance.
    timbrebody = ("""
        idur = p3
        ires = 4.75
        kfco expcurve %s, 14
        kfco = kfco * """ + str(orc.sr*0.5 * 0.65 + 200) + """
        
        a1 rezzy a1, kfco, ires
        """)

    SamplerInstruments, TimbreInstruments = [OrcInstrument(i+'Sampler') for i in INAMES], [OrcInstrument(i+'Timbre') for i in INAMES]

    #it would be nice to abstract this one, but it's quite complex. Maybe later.
    for Si, Ti in zip(SamplerInstruments, TimbreInstruments):
        Si.insertLine(samplerbody % [x for x in [n.varname() for n in lookuptabs] if x.__contains__(Si.name[:-7])][0])
        Ti.insertLine(timbrebody % [y for y in [j.varname() for j in timbrechans] if y.__contains__(Ti.name[:-6])][0])
        Si.routeOut('a1', Ti, setlevels)
        Ti.routeOut('a1', mixerout, setlevels)
        Ti.routeIn('a1')
        Ti.effect = True
        orc.appendInstruments(Si, Ti)


    #finally, add the mixer and level instruments
    orc.appendInstruments(mixerout)
    orc.prependInstrument(setlevels)
    #get numbers from names:
    #orc.nameNumber['BassSampler']
    print orc.exportOrc()

