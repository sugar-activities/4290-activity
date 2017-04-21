#! /usr/bin/env python
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

""" This file should be imported by all other files, so-as to defined cross-module global variables."""
print "loading CsHelpers"
import os,sys
import pygame
pygame.mixer.quit()

platform = "undefined"

try:
    import olpcgames
    import olpcgames.util
    if olpcgames.ACTIVITY:
        platform = "Sugar"
except ImportError:
    pass

if platform == "undefined":
    if sys.platform.startswith('darwin'):
        platform = 'MacOSX'
    elif sys.platform.startswith('win'):
        platform = "Win32"
    else: pass

def modulePath():
    "returns a string of the current path used for python modules"
    if __name__ == '__main__':
        return os.getcwd()
    else: return os.path.dirname(os.path.abspath(__file__))

ModulePath = modulePath()
InstrumentPath = ModulePath + "/CsInstruments"
ImagePath = ModulePath + "/Images"
ScenePath = ModulePath + "/Scenes"

PNAMES = ["Pitch", "Volume", "Timbre", "Tempo", "Length", "Density"]
INAMES = ["Drums", "Lead", "Chords", "Bass"]
SCENENAMES = [dir for dir in os.listdir(ScenePath) if os.path.isdir(ScenePath + '/' + dir)]

class SceneData( object ):
    def __init__(self, scene_name):
        self.scene_name = scene_name
        self.scene_path = ScenePath + "/" + scene_name
        self.MidiFilePath = self.scene_path + "/MidiFiles"
        self.AudioPath = self.scene_path + "/AudioFiles"
        self.BassAudioPath = self.AudioPath + "/BassAudio"
        self.LeadAudioPath = self.AudioPath + "/LeadAudio"
        self.ChordsAudioPath = self.AudioPath + "/ChordsAudio"
        self.DrumsAudioPath = self.AudioPath + "/DrumsAudio"

class beatCluster( object ):
    "An object which calculates a beat/time line, based on recorded beat time values"
    def __init__(self, tempo_factor, beatlimit):
        self.times = []
        self.beat_id = 0
        self.beatlimit = beatlimit
        self.tempo_factor = tempo_factor
        self.modulo_offset = 0
    def beat2Time(self, beat):
        "returns a time value based on a beat"
        t = self._average_time()
        bdiff = beat - self.beat_id
        tdiff = bdiff * self.tempo_factor
        result =  t + tdiff
        return result
    def time2Beat(self, time):
        "returns a beat value, when given a time"
        t = self._average_time()
        mtime = (time - self.modulo_offset) % (self.beat2Time(self.beatlimit) - self.modulo_offset) + self.modulo_offset
        tdiff = mtime - t
        bdiff = (tdiff * (1/self.tempo_factor))
        b = self.beat_id + bdiff
        return b % self.beatlimit
    def _average_time(self):
        return sum(self.times) / len(self.times)
    def addTime(self, beat, time):
        "store times"
        if not self.times:
            self.beat_id = beat
            self.times.append(time)
            self.modulo_offset = self.beat2Time(0)
        else:
            bdiff = beat - self.beat_id 
            tdiff = bdiff * self.tempo_factor 
            mtime = (time - self.modulo_offset) % (self.beat2Time(self.beatlimit) - self.modulo_offset) + self.modulo_offset
            result = mtime - tdiff
            self.times.append(result)
    def __len__(self):
        return len(self.times)
    
            

class beatEstimator( object ):
    "An object to collect beat and time values, and estimate when the next beat should be received"
    def __init__(self, tempo_factor, tolerance, beatlimit):
        self.beat_groups = []
        self.tempo_factor = tempo_factor
        self.tolerance = tolerance
        self.beatlimit = beatlimit
    def addBeat(self, beat, time):
        "records the time a beat was received, and either adds it to an existing cluster or creates a new cluster, provide"
        if not self.beat_groups:
            bc = beatCluster(self.tempo_factor, self.beatlimit)
            bc.addTime(beat, time)
            self.beat_groups.append(bc)
        else:
            bt, bc = self.beat_match(time, True) # beatCluster.time2Beat(time). returns the expected beat of largest beatcluster, and the beatcluster itself
            if abs(bt- beat) < self.tolerance: #where tolerance refers to a fractio of the beat.
                print "adding to optimal beat cluster"
                bc.addTime(beat, time)
            else: #check the other beats
                for b in filter(lambda xb: xb != bc, self.beat_groups):
                    otherbt = b.time2Beat(time)
                    if abs(otherbt - beat) < self.tolerance:
                        print "adding to other beat"
                        b.addTime(beat, time)
                        break
                else:
                    print "creating new beat cluster"
                    # if no match, append a new beat
                    newbc = beatCluster(self.tempo_factor, self.beatlimit)
                    newbc.addTime(beat, time)
                    self.beat_groups.append(newbc)
    def beat_match(self, time, include_reference = False):
        "returns the expected time of the beat, referenced from the optimal beat"
        optimal_bc = self.beat_groups[0]
        for lb in self.beat_groups:
            if len(lb) >= len(optimal_bc): optimal_bc = lb
        if include_reference:            
            return (optimal_bc.time2Beat(time), optimal_bc)
        else:
            return optimal_bc.time2Beat(time)


        
def getInstruments(*names):
    "concatenate Instruments from the Instrument Path"
    result = ""
    for i in names:
        Instrument = open(InstrumentPath + "/" + i, 'r')
        result += Instrument.read() + '\n'
    return result

def limit(n, low, hi):
    "set lower and upp bounds for values"
    if n < low: return low
    elif n > hi: return hi
    else: 
        return n

def rescale(n, oldmin, oldmax, newmin, newmax):
    oldrange = float(oldmax) - oldmin
    newrange = float(newmax) - newmin
    oldsize = float(n) - oldmin
    return (newrange / oldrange) * oldsize + newmin


def ResourceList(path, suffix):
    "returns a list of files in the directory"
    return [f for f in os.listdir(path) if f[-len(suffix):] == suffix and f[0] != '.']


def removeillegals(s):
    "removes illegal csound characters from names"
    result = ''
    for i in s:
        if i.isalnum() or i == '_':
            result += i
    return result
            

def aselect(lst, *indices):
    result = []
    for i in range(len(lst)):
        if i not in indices:
            result.append(lst[i])
    return result

def select(lst, *indices):
    result = []
    for i in range(len(lst)):
        if i in indices:
            result.append(lst[i])
    return result



if __name__ == '__main__':
    print ResourceList(InstrumentPath, ".orc")
    print ResourceList(MidiFilePath, ".mid")


    

