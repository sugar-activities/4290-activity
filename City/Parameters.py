#!/usr/bin/env python
#This python module is part of the Jam2Jam XO Activity, March, 2010
#
#Copyright (C) 2012 Thorin Kerr & Andrew Brown
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
"""Describes an object for storing parameter values. 
All Controllers should write to this object. 
All Readers should read from the object"""

import random
from CsHelpers import * #import global names and functions

class Instrument():
    def __init__(self, name, x = 0, y = 0, w = 0, h = 0):
        self.name = name
        self.lastRect = pygame.Rect(x,y,w,h)
        self.Rect = pygame.Rect(x,y,w,h)
        self.image = None
        self.active_image = None
        self.inactive_image = None
        self.Touch = False
        self.active = False
    def loadImage(self, path, *scale):
        img = pygame.image.load(path)
        if scale:
            img = pygame.transform.scale(img, (int(img.get_width() * scale[0]), int(img.get_height() * scale[-1])))
        img = img.convert_alpha()
        self.active_image = img
        self.Rect.size = img.get_size()
        self.lastRect.size = img.get_size()
        imgcopy = self.active_image.copy()
        imgcopy.fill((255,5,55) , None, pygame.BLEND_MIN)
        imgcopy.fill((75,75,75) , None, pygame.BLEND_ADD) 
        self.inactive_image = imgcopy
        self.deactivate()
    def activate(self):
        self.image = self.active_image
        self.active = True
        self.Touch = True
    def deactivate(self):
        self.image = self.inactive_image
        self.active = False
        self.Touch = True        
    def x(self):
        return self.Rect[0]
    def y(self):
        return self.Rect[1]
    def lastCtr(self):
        return self.lastRect.center
    def ctr(self):
        return self.Rect.center
    def __setattr__(self, attr, value):
        if attr == 'x':
            self.lastRect[0] = self.Rect[0]
            self.Rect[0] = value
            self.Touch = True
        elif attr == 'y':
            self.lastRect[1] = self.Rect[1]
            self.Rect[1] = value
            self.Touch = True
        elif attr == 'ctr':
            self.lastRect[0] = self.Rect[0]
            self.lastRect[1] = self.Rect[1]
            self.Rect.center = value
            self.Touch = True
        else: 
            self.__dict__[attr] = value
    def __repr__(self):
        return ''.join(map(str, [self.name, " Instrument at location ", (self.x(), self.y())]))


class Parameter():
    def __init__(self, name):
        self.name = name
        self.Instrumentvalues = [[Instrument(ins), 0.5] for ins in INAMES]
        self.state = False
        self.active = False
        self.correspondant = None
    def getValue(self, insname):
        for ndx in range(len(self.Instrumentvalues)):
            if self.Instrumentvalues[ndx][0].name == insname:
                return self.Instrumentvalues[ndx][1]
    def setValue(self, ins, val):
        ndx = [i[0].name for i in self.Instrumentvalues].index(ins)
        self.Instrumentvalues[ndx][1] = val        
    def __repr__(self):
        return self.name

class Perimeter():
    def __init__(self):
        self.data = {}
        for n in PNAMES:
            self.data[n] = Parameter(n)
        csoundChannels = []
    def csoundChannels(self, cs):
        self.csound = cs
        self.csoundChannels = cs.Channels
    def getValue(self, name, instrument):
        return self.data[name].getValue(instrument)
    def setValue(self, name, instrument, value):
        if name == 'Tempo':
            for i in self.data['Tempo'].Instrumentvalues:
                i[1] = value
        else:
            self.data[name].setValue(instrument, value)
            namelen = len(name)
            if  len(self.csoundChannels) > 0:
                for ch in self.csoundChannels:
                    param = ch.name[-namelen:]
                    if param == name:
                        ins = ch.name[:-len(param)]
                        if (ins == instrument and
                                (ch.direction == "input" or "bidirectional") and
                                    ch.type == "Control"):
                            self.csound.setChannelValue(ch.name, value)
    def getPlist(self):
        "returns a list of all parameters"
        return self.data.values()
    def getPdict(self):
        return self.data


if __name__ == '__main__':        
    P = Perimeter()
    print "Value for Drum density is :", P.getValue('Density', 'Drums') 
    print "setting new value"
    P.setValue('Density', 'Drums', 0.75)
    print "Value for Drum density is :", P.getValue('Density', 'Drums')
    c = check(P)
    c.setp(0.9)
    c.getp()
    
