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

from CsHelpers import *
import CsSched, Parameters, OrcBuilder, Tracks
import random

class ScenePlayer( SceneData ):
    def __init__(self, scene_name = 'City', key = 'A', mode = 'minor', tempo = 120, defaults = {}):
        SceneData.__init__(self, scene_name)
        self.tempo = tempo
        self.Csynth = CsSched.Csound()
        self.TimeQueue = CsSched.Sched()
        self.Params = Parameters.Perimeter()
        self.orc = OrcBuilder.OrcConstructor()
        self.makeOrc()
        self.cs = CsSched.CsoundPerformer(self.TimeQueue, self.orc, self.Csynth.csound)
        self.Params.csoundChannels(self.cs)
        self.loadTracks(key, mode)
        self.setParameters(defaults)
    def setParameters(self, pdict):
        "dict is a dictionary in the form: {Instrument:{parameter:value}}"
        for i in pdict:
            for p in pdict[i]:
                print "setting: ", p,i,pdict[i][p]
                self.Params.setValue(p,i,pdict[i][p])
    def makeOrc(self, sr = 22050, ksmps = 128):
        orc = self.orc
        orc.sr = sr
        orc.ksmps = ksmps
        lookuptabs = [OrcBuilder.orcLoadSamples(orc, self.Csynth, instr+"Lookup", eval("self."+instr+"AudioPath")) for instr in INAMES]
        ftabs = [OrcBuilder.FtableBreakPoint("rvbc1", -558, -594, -638, -678, -711, -745, -778, -808,  0.8,  0.79,  0.78,  0.77,  0.76,  0.75,  0.74,  0.73),
                 OrcBuilder.FtableBreakPoint("rvbc2", -517, -540, -656, -699, -752, -799, -818, -841,  0.8,  0.79,  0.78,  0.77,  0.76,  0.75,  0.74,  0.73),
                 OrcBuilder.FtableBreakPoint("rvba1", -278, -220, -170, -122,  0.4,  0.52,  0.64,  0.76),
                 OrcBuilder.FtableBreakPoint("rvba2", -333, -263, -166, -105,  0.5,  0.52,  0.64,  0.76)]
        orc.insertftables(*ftabs)
        volumechans = self.commonChannels("Volume", 0.8)
        timbrechans = self.commonChannels("Timbre", 0.5)
        orc.insertChannels(*volumechans)
        orc.insertChannels(*timbrechans)
        setlevels = OrcBuilder.OrcSetLevelInstrument()
        setlevels.effect = True
        mixerout = OrcBuilder.OrcMixoutInstrument()
        mixerout.effect = True
        samplerbody = """
            idur = p3
            iamp = p4 * (0dbfs / 127)
            kcps init cpsmidinn(p5)
            isamp table p5, %s
            a1 loscil iamp, kcps, isamp
            a1 dcblock a1 
            kdeclick linseg 0, 0.008, 1, idur - 0.05 - 0.008, 1, 0.05, 0
            a1 = a1 * kdeclick """
        timbrebody = ("""
            idur = p3
            ires = 5.75
            kfco expcurve %s + 0.01, 17
            kfco = kfco * """ + str(orc.sr*0.5 * 0.45) + """ + 1200
            a2 rezzy a1, kfco, ires
            a1 balance a2, a1
            a1 = a1 * 0.2 + a2 * 0.4
            """)
        SamplerInstruments, TimbreInstruments = [OrcBuilder.OrcInstrument(i+'Sampler') for i in INAMES], [OrcBuilder.OrcInstrument(i+'Timbre') for i in INAMES]
        for Si, Ti in zip(SamplerInstruments, TimbreInstruments):
            Si.insertLine(samplerbody % [x for x in [n.varname() for n in lookuptabs] if x.__contains__(Si.name[:-7])][0])
            Ti.insertLine(timbrebody % [y for y in [j.varname() for j in timbrechans] if y.__contains__(Ti.name[:-6])][0])
            Si.routeOut('a1', Ti, setlevels, [c for c in [v.varname() for v in volumechans] if c.__contains__(Si.name[:-7])][0])
            Ti.routeOut('a1', mixerout, setlevels)
            Ti.routeIn('a1')
            Ti.effect = True
            orc.appendInstruments(Si, Ti)
        orc.appendInstruments(mixerout)
        orc.prependInstrument(setlevels)
        return True
    def commonChannels(self, chnName, default):
        "returns a list of channel objects for INAMES"
        return OrcBuilder.orcChannelMaker(INAMES, chnName, init = default)
    def loadTracks(self, key, mode):
        "see sc below"
        self.scale = Tracks.Scale(key, mode)
        midifiles = ResourceList(self.MidiFilePath, ".mid")
        for m in midifiles:
            score = Tracks.Midi2Score(self.MidiFilePath + "/" + m)
            track = score.midiTrack2ScoreTrack(score.getTrack(0))
            if m.startswith('Lead'):
                self.leadtrack = track
            elif m.startswith('Bass'):
                self.basstrack = track
            elif m.startswith('Chords'):
                self.chordstrack = track
            elif m.startswith('Drums'):
                self.drumstrack = track
            else:
                raise ValueError, "Can't match MIDI file %s to instrument" %m

def makePlayer(scene):
    "create and return a player"
    player = Tracks.beatDebugPlayer(scene.cs, scene.TimeQueue, scene.Params, scene.scale)
    player.setBPM(scene.tempo)
    lead = scene.orc.nameNumber['LeadSampler']
    bass = scene.orc.nameNumber['BassSampler']
    chords = scene.orc.nameNumber['ChordsSampler']
    drums = scene.orc.nameNumber['DrumsSampler']
    player.beatInstrumentMap(1, Lead = [scene.leadtrack, lead], Bass = [scene.basstrack,bass], 
                        Chords = [scene.chordstrack, chords], Drums = [scene.drumstrack, drums])
    return player

