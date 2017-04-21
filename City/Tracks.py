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
"""
This module defines Notes, Scores, Beats and Players and a convenience class for midi file parsing.
"""

#Note has no instrument number
#This is determined by the Track
ONSETINDEX = 0
DURINDEX = 1
VELINDEX = 2
PITINDEX = 3


import bisect, random, math, logging, thread
from midiImport import *
from CsHelpers import *

log = logging.getLogger( 'City run' )
log.setLevel( logging.DEBUG )


class Note:
    def __init__(self, note = [0,0,0,0]): 
        self.data = note[:]
        self.index = 0
    def __repr__(self):
        return 'Note: '+' '.join(map(str,(self.data)))
    def __getitem__(self,index):
        return self.data[index]
    def __setitem__(self,index, value):
        self.data[index] = value
    def __getslice__(self,a,b):
        return self.data[a:b]
    def __len__(self):
        return len(self.data)
    def onset(self):
        return self[ONSETINDEX]
    def duration(self):
        return self[DURINDEX]
    def velocity(self):
        return self[VELINDEX]
    def pitch(self):
        return self[PITINDEX]
    def setOnset(self, val):
        self[ONSETINDEX] = val
    def setDuration(self, val):
        self[DURINDEX] = val
    def setVelocity(self, val):
        self[VELINDEX] = val
    def setPitch(self, val):
        self[PITINDEX] = val
    def offTime(self):
        return self.duration() + self.onset()


class Track:
    def __init__(self, data = []):
        "A Track can be initialised with a list of notes" 
        self.data = data[:]
        self.index = 0
        self.instrument = 1 
    def setInstrument(self, num):
        self.instrument = num
    def addNote(self, note):
        index = bisect.bisect_left(self.data, [note[ONSETINDEX]])
        self.data.insert(index, note)
    def __delitem__(self, index):
        del(self.data[index])        
    def __getitem__(self, index):
        if len(self) == 0:
            return False
        else:
            return self.data[index]
    def __getslice__(self, a,b):
        return Track(self.data[a:b])
    def __len__(self):
        return len(self.data) 
    def resetIterator(self, ndx = 0):
        self.index = ndx
    def findNoteAtTime(self, time):
        return bisect.bisect_left([n.data for n in self.data], [time])
    def getNoteAtTime(self, time):
        return self.data[self.findNoteAtTime(time)]
    def getParameter(self, ndx):
        return [i[ndx] for i in self.data]
    def getOnsets(self):
        return self.getParameter(ONSETINDEX)
    def getDurations(self):
        return self.getParameter(DURINDEX)
    def getVelocities(self):
        return self.getParameter(VELINDEX)
    def getPitches(self):
        return self.getParameter(PITINDEX)
    def modParameter(self, pndx, mult):
        "a bit of a hack, while I try and work out tempo"
        for n in self:
            n[pndx] *= mult
    def __repr__(self):
        return 'Track :' + str(self.data)


class Beat(Track):
    def __init__(self, beatnum, offset = 0, data = Track()):
        "Beat can be initialised with an existing track. The track is automatically sliced"
        self.data = data.data[:]
        self.index = 0
        self.instrument = 1
        self.offset = offset
        self.beatnum = beatnum
    def setBeatNum(self, beatnum):
        self.beatnum = beatnum
    def setOffset(self, beatnum):
        self.offset = offset
    def nudgeParameter(self, parameter, shiftAmount):
        "returns a new beat with onsets shifted by shiftAmount"
        newbeat = Beat(self.beatnum)
        for i in self.data:
            newp = i[parameter] + shiftAmount
            newl = []
            for p in range(len(i)):
                if p == parameter:
                    newl.append(newp)
                else: newl.append(i[p])
            newNote = Note(newl)
            newbeat.addNote(newNote)
        return newbeat    
    def relativeOnsets(self, start = 0):
        shift = -self[0].onset() - self.offset
        return self.nudgeParameter(ONSETINDEX, shift + start)
    def __repr__(self):
        return 'Beat ' + str(self.beatnum) + ':' + str(self.data)
        
def beat(track, time, beatlen, beatnum):
    "beat function extracts a beat object from a track, and assigns it a 'beat' number"
    ndx = track.findNoteAtTime(time)
    result = Beat(beatnum)
    if ndx >= len(track): return result
    timeOffset = track[ndx].onset() - time
    if timeOffset > beatlen:
        return result
    else:
        for n in track[ndx: ]:
            if n.onset() < track[ndx].onset() + beatlen:
                result.addNote(n)
            else: break
        return result
    
class Midi2Score:
    def __init__(self, path):
        midiData = MidiFile()
        midiData.open(path)
        midiData.read()
        midiData.close()
        self.midiData = midiData
        self.ticksPerBeat = midiData.ticksPerQuarterNote
    def numTracks(self):
        return len(self.midiData.tracks)
    def getTrack(self, ndx):
        return self.midiData.tracks[ndx]
    def time2beats(self,time):
        return float(time) / self.ticksPerBeat
    def findNO(self, noff, nlst):
        pitlst = [n.pitch() for n in reversed(nlst)]
        return (len(pitlst) - 1) - pitlst.index(noff.pitch)
    def midiTrack2Notes(self, track):
        "returns a list of notes from a track"
        result = []
        for event in track.events:
            if event.type == "NOTE_ON":
                result.append(Note([self.time2beats(event.time), 0, event.velocity, event.pitch]))
            elif event.type == "NOTE_OFF":
                ndx = self.findNO(event, result)
                dur = self.time2beats(event.time) - result[ndx].onset()
                result[ndx].setDuration(dur)
            else:
                pass
        return result
    def midiTrack2ScoreTrack(self, mtrack):
        "returns a Track object from a midi file"
        notelist = self.midiTrack2Notes(mtrack)
        return Track(notelist)

   
class Scale:
    "a class for manipulating pitch data"
    def __init__(self, keyname, modality):
        "where keyname is a letter and modality is a string e.g. Scale('C#','minor'))"
        self.key = keyname
        self.modality = modality
        self.chromatic = range(12, 109)
        self.keyMap = {'C':0, 'C#':1,'D':2, 'D#':3, 'E':4, 'F':5, 'F#':6, 'G':7, 'G#':8,'A':9,'A#':10, 'B':11}
        self.scale = self.Scalemap(self.Mode(keyname, modality))
        self.subscale = self.Scalemap(self.Mode(keyname, "subscale"))
    def Scalemap(self, scale):
        lim = True
        oct = 0
        result = []
        stop = len(self.chromatic)
        while lim:
            for i in scale:
                ndx = i + oct * 12
                if ndx >= stop:
                    lim = False
                    break
                else:
                    result.append(self.chromatic[ndx])
            oct += 1
        return result
    def Transpose(self, incr, mode):
        result = [(n + incr) % 12 for n in mode]
        result.sort()
        return result
    def Mode(self, key, name):
        if name == "chromatic":
            return range(12)
        elif name == "major":
            return self.Transpose(self.keyMap[key], [0,2,4,5,7,9,11])
        elif name == "minor":
            return self.Transpose(self.keyMap[key], [0,2,3,5,7,8,10])
        elif name == "minor pentatonic":
            return self.Transpose(self.keyMap[key], [0,2,3,5,7,8])
        elif name == "subscale":
            return self.Transpose(self.keyMap[key], [0,2,5,7])
        else: return []
    def pitchMap(self, pitch, subscale = False):
        "Integers only. Given a pitch, recalculates a new pitch within the key and scale"
        if subscale:
            scale = self.subscale
        else:
            scale = self.scale
        if pitch in scale:
            return pitch
        else:
            pup = pitch + 1
            pdown = pitch - 1
            result = None
            for i in xrange(len(scale)):
                if pup in scale:
                    result = pup
                    break
                elif pdown in scale:
                        result = pdown
                        break
                else:
                    pup += 1
                    pdown -= 1
            return result
    def basePit(self, strack):
        "return the lowest tonic note in the track"
        tonics = filter(lambda x: x % 12 == self.keyMap[self.key], strack.getPitches())
        if tonics:
            return min(tonics)
        else:
            return self.keyMap[self.key] + 48


class beatDebugPlayer:
    "This player expects beats to be relative to zero already"
    TRACKDATA_NDX = 0
    INSNUM_NDX = 1
    def __init__(self, cssynth, timer, perimeter, scaleObj):
        "params is the parameter object"
        print "THREAD ID: PLAYER INIT" , thread.get_ident()        
        self.cs = cssynth
        self.beat = 0
        self.scoreTracks = {}
        self.drumPitches = []
        self.trackMap = {}
        self.activity = {}
        self.timer = timer
        self.perimeter = perimeter
        self.scale = scaleObj
        self.basepits = {}
        self.tempoMult = 1 #the tempo() method changes this
        self.den = 0
        self.beatlimit = 0
        self.sendSync = False
        self.loop_idcounter = 1
        self.mutelist = []
        self.picture_cycle = []
        self.frozen = False
        self.mute_all = False
    def pause(self):
        self.mute_all = True
    def oldpause(self, *lid):
        if lid and self.activity.has_key(lid[0]):
            self.activity[lid[0]] = 'Pause'
            return True
        else:
            #if no loop id is specified, or the id is just plain wrong, try and stop the last loop added set to play.
            for k in sorted(self.activity.keys(), reverse = True):
                if self.activity[k] == 'Play':
                    self.activity[k] = 'Pause'
                    return True
            else:
                return False
    def Stop(self):
        self.activity = 'Stop'
        self.resetBeat()
        self.cs.Stop()
    def Cease(self, *lid):
        if lid and self.activity.has_key(lid[0]):
            self.activity[lid[0]] = 'Cease'
            return True
        else:
            for k in sorted(self.activity.keys(), reverse = True):
                if self.activity[k] == 'Play' or self.activity[k] == 'Pause':
                    self.activity[k] = 'Cease'
                    log.info("Ceasing loop id %s" %k)
                    return True
            else:
                return False
    def resume(self):
        self.mute_all = False
    def oldresume(self, *lid):
        if lid and self.activity.has_key(lid[0]):
            self.activity[lid[0]] = 'Play'
            return True
        else:
            for k in sorted(self.activity.keys(), reverse = True):
                if self.activity[k] == 'Pause': 
                    self.activity[k] = 'Play'
                    print "resuming id ", k
                    return True
            else:
                return False
    def resetBeat(self, *num):
        if num:
            self.beat = num[0]
        else:
            self.beat = 0
    def Track2beatList(self, Strack, beatlen, tracklen):
        "return a list of beats from the track, reletavised to zero"
        result = []
        for i in range(tracklen):
            if i > len(Strack) - 1:
                result.append(Beat(i))
            else:
                result.append(beat(Strack, i, beatlen - 0.01, i))
        return [(b.relativeOnsets(b[0].onset() % 1) if b[0] else b) for b in result]
    def beatInstrumentMap(self, beatlength, **kargs):
        "kargs is a dictionary. Assign beatlists to Csound instruments kbeats. Keys = 5"
        for key in kargs:
            strack = kargs[key][self.TRACKDATA_NDX]
            self.scoreTracks[key] = strack
            if key == 'Drums':
                self.drumPitches = sorted(list(set(self.scoreTracks["Drums"].getPitches())))
                tracklen = int(sorted(list(set(self.scoreTracks["Drums"].getOnsets())))[-1])
                while tracklen % 4:
                    tracklen += 1
            kargs[key][self.TRACKDATA_NDX] = self.Track2beatList(strack, beatlength, tracklen)
            self.basepits[key] = self.scale.basePit(strack)
        self.trackMap = kargs
        self.beatlimit = self.beatLimit()
    def getInstrument(self, trackname):
        "Get an Instrument associated with the track"
        return self.trackMap[trackname][self.INSNUM_NDX]
    def getBeatData(self, trackname):
        "The following three functions ought to be improved"
        return self.trackMap[trackname][self.TRACKDATA_NDX]
    def beatLists(self):
        "return a list of all the trackdata"
        return [self.getBeatData(keyname) for keyname in self.trackMap.keys()]
    def beatLimit(self):
        return len(self.beatLists()[0])
    def setBPM(self, bpm):
        "tempomult * 1 = 120bpm. Turns out ticksPerQuarter in midiImport.py always returns 480 "
        print "bpm, " ,bpm, bpm / 120.0
        self.tempoMult = (60.0 / bpm)
    def tempo(self):
        "sets current tempo"
        print "tempo"
        tempoparam = self.perimeter.getValue('Tempo', 'Drums') #Only look at one parameter, since tempo is global.
        self.tempoMult = 1/(tempoparam + 1.5)
    def articulate(self, insname):
        if insname == 'Drums':
            return 1
        else: 
            pval = self.perimeter.getValue('Length', insname) + 0.5
            if pval < 1:
                return pval
            else:
                return rescale(pval, 1, 1.5, 1, 6)
    def noteChecker(self, keyname, t, modulo, varGreaterThan, varLessThan):
        dval = self.density(keyname)
        densval = (dval + (random.uniform(-.112, .112)) if dval != 1 or 0 else (0.99 if dval == 1 else 0.01)) 
        return (True if t % modulo == 0 and varGreaterThan <= limit(densval, 0, 1) < varLessThan else False)
    def density(self, insname):
        "could introduce some randomness here"
        if insname == "Keys":
            regions = [0, 1, 0.75, 2]
        else:
            regions = [0, 0.5, 0.5, 1, 0.75, 2]
        val = 1 - self.perimeter.getValue('Density', insname)
        valnew = rescale(val, 0, 1, 0, len(regions) - 1)
        valnew -= random.uniform(0, 0.6)
        if valnew < 0: valnew = 0 
        return regions[int(round(valnew))]
    def pitchCalc(self, insname, pitch, onset):
        "Calculate a new pitch based on the old"
        pitchparam = self.perimeter.getValue('Pitch', insname)
        if pitchparam > 0.4 and pitchparam < 0.6:
            return pitch        
        if insname == 'Drums':
            l = self.drumPitches
            if pitchparam <= 0.4:
                if pitch in l[0:int(math.ceil(len(l) * (pitchparam + 0.01) * 2))]:
                    return pitch
                else:
                    return False
            elif pitchparam >= 0.6:
                if pitch in l[int(math.floor((len(l) - 1) * (pitchparam - 0.5) * 2)):len(l)]:
                    return pitch
                else: return False
            else:
                return False
        else:
            basepit = self.basepits[insname]
            pitchparam = self.perimeter.getValue('Pitch', insname)
            newpitch = basepit + (pitch - basepit) * pitchparam * 2
            if onset % 1 == 0:
                return self.scale.pitchMap(int(round(newpitch)), True)
            else:
                return self.scale.pitchMap(int(round(newpitch)))
    def freeze(self):
        "stop access to all input into the player, usually done when reloading a scene"
        self.cs.perf.SetProcessCallback(lambda: None, None)
        for lids in self.activity:
            self.activity[lids] = 'Cease'
        self.frozen = True
        print "frozen  = ", self.frozen
    def playBeat(self, time, beatnum):
        if self.frozen: return None
        if self.sendSync:
            self.timer.schedEvent(time, olpcgames.mesh.broadcast, "Beat|%s" %beatnum)
            self.sendSync = False
        if self.picture_cycle:
            activity = self.picture_cycle[0]
            pics = activity.snap_store
            updated = self.picture_cycle[1]
            if not pics:
                pass
            elif updated:
                ndx = len(pics) - 1
                activity.feedbackgroundImage = pics[ndx]
            else:
                ndx = beatnum % len(pics)
                activity.feedbackgroundImage = pics[ndx]
            self.picture_cycle[1] = False
        for keyname in [i for i in self.trackMap.keys() if i not in self.mutelist]:
            ins = self.getInstrument(keyname)
            beatCollect = self.getBeatData(keyname)[beatnum]
            if beatCollect:
                for note in beatCollect:
                    den = self.density(keyname)
                    pitch = self.pitchCalc(keyname, note[PITINDEX], note[ONSETINDEX])
                    if not pitch:
                        pass
                    elif den == 0:
                        self.cs.playParams(ins, (note[ONSETINDEX] * self.tempoMult) + (time - self.cs.perfTime()), 
                            (note[DURINDEX] * self.articulate(keyname) if keyname == 'Drums' or keyname == 'Keys'
                            else note[DURINDEX] * self.tempoMult * self.articulate(keyname)),
                            note[VELINDEX],
                            pitch)
                    elif (note[ONSETINDEX] + beatCollect.beatnum) % den == 0:
                        self.cs.playParams(ins, (note[ONSETINDEX] * self.tempoMult) + (time - self.cs.perfTime()), 
                            max(note[DURINDEX] * self.tempoMult, (den * 0.8) * 0.5) * self.articulate(keyname),
                            note[VELINDEX], 
                            pitch)
                    else:
                        pass
    def playLoop(self, time, reset_beat = False, loop_ID = False):
        if self.frozen: return None
        elif loop_ID:
            lid = loop_ID
        else:
            lid = self.loop_idcounter
            self.activity.update({lid:'Play'})
            self.loop_idcounter += 1
        if reset_beat:
            self.beat = reset_beat
        #self.tempo() # was used to dynamically calculate tempo. Now disabled.
        if self.mute_all:
            self.timer.schedEvent(time + 0.5 * self.tempoMult, self.playLoop, time + 1 * self.tempoMult, False, lid)
        elif self.activity[lid] == 'Play':
            self.playBeat(time, self.beat)
            self.beat = (self.beat + 1) % self.beatlimit
            self.timer.schedEvent(time, self.playLoop, time + (1 * self.tempoMult), False, lid)
        elif self.activity[lid] == 'Pause':
            self.timer.schedEvent(time + 0.5 * self.tempoMult, self.playLoop, time + 1 * self.tempoMult, False, lid)
        elif self.activity[lid] == 'Cease':
            pass
        else:
            self.resume()


if __name__ == '__main__':
    print "running test code for Tracks.py \n"
    mpath = raw_input("enter a path to a midi file :")
    mfile = Midi2Score(mpath)
    print "just reading track one for now..."


    







