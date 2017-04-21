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

import subprocess
import logging, olpcgames
import olpcgames.pausescreen as pausescreen
import olpcgames.mesh as mesh
from olpcgames import camera
from sugar.presence import presenceservice
from threading import Timer
from math import ceil, sqrt


from City.CsHelpers import *
from City.Parameters import Instrument
import City.City as City

log = logging.getLogger( 'City run' )
log.setLevel( logging.DEBUG )


log.info('PLATFORM = %s' %platform)
def buildInstruments(names, imgpath, screensize, scale):
    "returns a list of Instrument objects, loaded with images"
    Instruments = [Instrument(names[i]) for i in range(len(names))]
    imagefiles = ResourceList(imgpath, '.png')
    startx = 30
    for i in Instruments:
        for f in imagefiles:
            if i.name.startswith(f[:4]):
                i.loadImage(ImagePath+'/'+f, scale)
        i.x = screensize[0] * 0.8 - startx
        i.y = (screensize[1] - i.image.get_size()[1]) * 0.5
        i.Touch = True
        startx = startx + (screensize[0] * 0.8) / len(Instruments)
    return Instruments

def getInstrumentParameters(scene, inm):
    "return a list of parameters values for the instrument, in order of PNAMES"
    pobj = scene.Params
    result = []
    for pnm in PNAMES:
        result.append(pobj.getValue(pnm, inm))
    return result

def setInstrumentParameters(scene, inm, vlst):
    "sets parameters for an instrument"
    pobj = scene.Params
    for pnm,val in zip(PNAMES, vlst):
        pobj.setValue(pnm, inm, val)
    return True

KEYCODES = {276:"Nudge|Left", 275:"Nudge|Right", 274:"Nudge|Down", 273:"Nudge|Up",
            260:"Nudge|Left", 262:"Nudge|Right", 258:"Nudge|Down", 264:"Nudge|Up",
            263: "Instrument|Bass", 257:"Instrument|Chords", 265:"Instrument|Lead", 259:"Instrument|Drums",
            49: "Instrument|Bass", 50:"Instrument|Chords", 51:"Instrument|Lead", 52:"Instrument|Drums",
            112: "Parameter|Pitch", 118:"Parameter|Volume", 100:"Parameter|Density", 108:"Parameter|Length", 116:"Parameter|Timbre",
            304: "Modifier|Shift"}


class jamScene( object ):
    def __init__(self, screen, scene = 'City', key = 'A', mode = 'minor', tempo = 120, initial_parameters = {}):
        self.scene = City.ScenePlayer(scene, key, mode, tempo, initial_parameters)
        self.music_player = City.makePlayer(self.scene)
        self.beatEstimator = beatEstimator(self.music_player.tempoMult, 0.17, self.music_player.beatlimit)
        self.pending_instrument_assignment = []
        self.latency_counter = 0
        self.latency = [0.07]
        self.latency_time_ID = {}
        self._syncloop_running = 0
        global schedEvent, now
        schedEvent = self.scene.TimeQueue.schedEvent
        now = self.scene.cs.perfTime        
        self.screen = screen        
        screenRect = screen.get_rect()
        print "SCREENRECT IS .........", screenRect
        self.screenSize = screen.get_size()
        print "SCREENSIZE IS ---------", self.screenSize
        self.playArea = pygame.Rect(screenRect.left,screenRect.top, screenRect.width, screenRect.height * 0.8)
        if olpcgames.ACTIVITY:
            olpcgames.ACTIVITY.playArea = self.playArea
            olpcgames.ACTIVITY.jamScene = self
        self.panelArea = pygame.Rect(screenRect.left,screenRect.height * 0.8, screenRect.width, screenRect.height * 0.2)
        self.TemplateInstruments = buildInstruments(INAMES, ImagePath, self.playArea.size, 2)
        for oni in self.TemplateInstruments:
            oni.activate()
        self.PanelInstruments = buildInstruments(INAMES, ImagePath, self.panelArea.size, 1.5)
        for pnl in self.PanelInstruments:
            pnl.Touch = True
            pnl.activate()
        imagesize = self.TemplateInstruments[0].image.get_size()
        self.panelSize = (self.screenSize[0], imagesize[1] + 10)
        #movement limits
        self.xmin = self.playArea.left + imagesize[0] * 0.5
        self.xmax = self.playArea.right - imagesize[0] * 0.5
        self.ymax = self.playArea.bottom - imagesize[1] * 0.5
        self.ymin = self.playArea.top + imagesize[1] * 0.5
        #interface key codes
        self.keycode = KEYCODES
        #various states
        self.keyActions = []
        self.selectedInstrument =  self.TemplateInstruments[0] 
        self.occupiedInstruments =  {self.selectedInstrument.name: None} 
        self.myself = None
        self.sharer = False
        self.connected = False
        self.timeTally = []
        self.running = True
        self.Vparam = "Pitch"
        self.Hparam = "Density"
        #interface controls
        self.movingInstrument = False
        #initial draw
        panelColour = (0,0,0)
        self.snap_store = (olpcgames.ACTIVITY.snap_store if platform == 'Sugar' else [])
        self.feedbackgroundImage = None
        if self.screenSize == (1200, 780):
            self.setbackgroundImage(pygame.image.load(ImagePath + "/jam2jamXO_4.png").convert())
        else:
            bgi = pygame.image.load(ImagePath +  "/jam2jamXO_4.png").convert()
            bgi_scaled = pygame.transform.scale(bgi, self.playArea.size)
            self.setbackgroundImage(bgi_scaled)
        self.panel = pygame.Surface((self.panelArea.width, self.panelArea.height))
        self.panel.fill(panelColour)
        self.screen.blit(self.panel, self.panelArea)
        pygame.display.flip()
        for pnl in self.PanelInstruments: pnl.y = pnl.y() + self.playArea.height 
    def setbackgroundImage(self, img):
        self.backgroundImage = img
        self.screen.blit(self.backgroundImage, (0,0), self.playArea)
        self.selectedInstrument.Touch = True
    def updatePanel(self):
        "redraw panel icons"
        for pi in self.PanelInstruments:
            if not pi.Touch:
                pass
            else:
                if pi.name in self.occupiedInstruments:
                    pi.deactivate()
                else:
                    pi.activate()
                self.screen.blit(pi.image, pi.Rect)
                pi.Touch = False
    def runloop(self):
        "main game loop"
        clock = pygame.time.Clock()
        imgcnt = 0
        self.music_player.playLoop(now())
        while self.running:
            events = (pausescreen.get_events(sleep_timeout = 43200) if platform == 'Sugar' else pygame.event.get())
            for event in events:
                self.eventAction(event)
            for act in self.keyActions:
                self.interfaceAction(act)
            if self.feedbackgroundImage:
                self.setbackgroundImage(self.feedbackgroundImage)
                self.feedbackgroundImage = None
            self.updateInspos()
            self.updatePanel()
            if platform == 'Sugar': currentcnt = len(self.snap_store)
            else: currentcnt = 0
            if imgcnt == currentcnt:
                pass
            else:
                self.music_player.picture_cycle = [self, True]
                imgcnt = currentcnt
            pygame.display.flip()
            clock.tick(25)
    def updateInspos(self):
        "animate selected instrument."
        ins = self.selectedInstrument
        if ins.Touch:
            xval = self.scene.Params.getValue(self.Hparam, ins.name)
            yval = self.scene.Params.getValue(self.Vparam, ins.name)
            xpos = rescale(xval, 0,1,self.xmin, self.xmax)
            ypos = rescale(yval, 0,1,self.ymax, self.ymin) 
            self.screen.blit(self.backgroundImage, ins.Rect, ins.Rect)
            ins.ctr = (xpos, ypos)
            ins.Touch = False
            self.screen.blit(ins.image, ins.Rect)
    def sendSync(self):
        "Tell audio loop to broadcast time and beat messages"
        if self._syncloop_running:
            self.music_player.sendSync = True
            log.info("sent sync")
            schedEvent(now() + 10.7, self.sendSync)
    def setselectedInstrument(self, ins):
        "select the instrument onscreen"
        self.selectedInstrument = ins
        if ins.name not in self.occupiedInstruments:
            self.occupiedInstruments.update({ins.name:str(self.myself)})
        self.selectedInstrument.Touch = True
    def eventAction(self, event):
        "detect events, and select action"
        if event.type == pygame.QUIT:
            self.music_player.freeze()
            self.running = False
        elif event.type == pygame.USEREVENT:
            if hasattr(event, "action"):
                if event.action.startswith("Parameter"):
                    args = event.action.split('|')
                    if args[1] == "Horizontal":
                        self.Hparam = args[2]
                        self.selectedInstrument.Touch = True                        
                    elif args[1] == "Vertical":
                        self.Vparam = args[2]
                        self.selectedInstrument.Touch = True
                    else:
                        raise ValueError, 'Unknown Parameter Action %s' %args
                elif event.action.startswith('Reload'):
                    #should look always like this: "Reload|name|key:mode|tempo|defaults"
                    args = event.action.split('|')
                    name = args[1]
                    key = ('E' if args[2] == 'None' else args[2])
                    mode = ('minor' if args[3] == 'None' else args[3])
                    tempo = (117 if args[4] == 'None' else int(args[4])) 
                    d = eval(args[5])
                    defaults = (d if d else {})
                    self.load_scene(name, key, mode, tempo, defaults) #this call blocks
                    if self.pending_instrument_assignment: #now check if we are waiting to assign instruments and params.
                        self.receiveMessage("AuthorisedInstrument|%s|%s" %(self.pending_instrument_assignment[0], self.pending_instrument_assignment[1]), self.myself)
                elif event.action.startswith("Shared"):
                    self.sharer = "Pending"
                    log.info("Sharing activity")
                elif event.action.startswith("Joined"):
                    log.info("Joined Activity")
                else:
                    log.debug("unknown parameter change: %s", event.action) 
            else: log.debug("ignoring USEREVENT %s", event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x,y = event.pos
            Ins = self.selectedInstrument
            if Ins.Rect.collidepoint(x,y):
                self.movingInstrument = Ins
            else:
                for Panndx in range(len(self.PanelInstruments)):
                    Pan = self.PanelInstruments[Panndx]
                    if Pan.Rect.collidepoint(x,y):
                        if Pan.active: self.requestInstrument(Pan.name)
                        break
        elif event.type == pygame.MOUSEMOTION:
            if self.movingInstrument:
                insname = self.movingInstrument.name
                self.scene.Params.setValue(self.Hparam, insname, rescale(event.pos[0], self.playArea.left, self.playArea.right, 0, 1))
                self.scene.Params.setValue(self.Vparam, insname, limit(rescale(event.pos[1], self.playArea.bottom, self.playArea.top, 0, 1), 0,1))
                self.movingInstrument.Touch = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.movingInstrument = False
        elif platform == 'Sugar' and event.type == mesh.CONNECT:
            log.info( """Connected to the mesh!| %s""", event )
            self.connected = True
            self.music_player.resetBeat()
        elif event.type == pygame.KEYDOWN:
            try:
                iaction = self.keycode[event.key]
                self.keyActions.append(iaction)
            except KeyError:
                pass
        elif event.type == pygame.KEYUP:
            try:
                self.keyActions.remove(self.keycode[event.key])
            except ValueError: pass
            except KeyError: pass
        elif self.connected and event.type == mesh.PARTICIPANT_ADD:
            if not self.myself: self.myself = mesh.my_handle()
            if event.handle == self.myself:
                if self.sharer == "Pending": self.sharer = self.myself
            elif len(self.occupiedInstruments) == 4:
                pass
            else:
                if self.sharer == self.myself:
                    giveupInstrument = [p for p in self.PanelInstruments if p.active][0].name 
                    giveupparameters = getInstrumentParameters(self.scene, giveupInstrument) 
                    mesh.send_to(event.handle, "Welcome|%s|%s|%s" %(self.scene.scene_name, giveupInstrument, giveupparameters)) 
                    self.stealInstrument(giveupInstrument, handle = event.handle) 
                    if self.connected: mesh.broadcast('Occupied|%s' %self.occupiedInstruments) 
                    olpcgames.ACTIVITY.J2JToolbar.deactivate_scene_change()
                    if len(self.occupiedInstruments) >= 2 and not self._syncloop_running:
                        self._syncloop_running = True
                        self.sendSync()
                else:
                    self.latency_checker()
                    log.info("Waiting to be assigned instrument from sharer")
        elif self.connected and event.type == mesh.PARTICIPANT_REMOVE:
            "return instrument to the sharer if a jammer leaves."
            try:
                relname = [n for n in self.occupiedInstruments if self.occupiedInstruments[n] == str(event.handle)][0]
                relpanel = [p for p in self.PanelInstruments if p.name == relname][0]
                del self.occupiedInstruments[relname]
                relpanel.Touch = True
                if self.sharer == self.myself:
                    self.music_player.mutelist.remove(relname)
                if len(self.occupiedInstruments) == 1:
                    olpcgames.ACTIVITY.J2JToolbar.reactivate_scene_change()
                if len(self.occupiedInstruments) <= 1:
                        self._syncloop_running = False
            except IndexError: log.debug("Index error while removing jammer %s occ = %s" %(str(event.handle), self.occupiedInstruments))
            except KeyError: pass
            except ValueError: pass
            if self.sharer == self.myself: mesh.broadcast('Occupied|%s' %self.occupiedInstruments)
            log.info( """Removed jammer| %s""", event )
        elif self.connected and (event.type == mesh.MESSAGE_MULTI or event.type == mesh.MESSAGE_UNI):
            if event.handle == self.myself:
                pass
            else:
                self.receiveMessage(event.content, event.handle)
    def interfaceAction(self, iaction):
        if iaction.startswith("Nudge"):
            direction = iaction.split("|")[1]
            insname = self.selectedInstrument.name
            if direction == "Left" or direction == "Right":
                param = self.Hparam
            else:
                param = self.Vparam
            currentValue = self.scene.Params.getValue(param, insname)
            newvalue = limit((currentValue - 0.03 if direction == "Left" or direction == "Down" else currentValue + 0.03), 0, 1)
            self.scene.Params.setValue(param, insname, newvalue)
            self.selectedInstrument.Touch = True
            if newvalue == 0 or newvalue == 1:
                try:
                    self.keyActions.remove(iaction)
                except ValueError: pass
        elif iaction.startswith("Instrument"):
            ins = iaction.split('|')[1]
            self.requestInstrument(ins)
            try:
                self.keyActions.remove(iaction)
            except ValueError: pass
        elif iaction.startswith("Parameter"):
            pm = iaction.split('|')[1]
            if "Modifier|Shift" in self.keyActions:
                print "shift key is on"
                if olpcgames.ACTIVITY:
                    olpcgames.ACTIVITY.J2JToolbar.set_vertical_parameter(pm)
                else:
                    self.Vparam = pm
            else:
                print "shift key is off"
                if olpcgames.ACTIVITY:
                    olpcgames.ACTIVITY.J2JToolbar.set_horizontal_parameter(pm)
                else:
                    self.Hparam = pm
            try:
                self.keyActions.remove(iaction)
            except ValueError: pass    
        else: pass
    def stealInstrument(self, stealname, releasename = False, handle = False):
        "attempts to deactivate an instrument, and make it unavailable for selection"
        if not handle: handle = self.myself
        if stealname == self.selectedInstrument.name:
            log.info("ignoring request to steal %s: already active" %stealname)
            return False
        elif stealname in self.occupiedInstruments and not releasename:
            log.info ("ignoring request to steal %s: already occupied and no release instrument provided" %stealname)
            return False
        else:
            paneli = [pnli for pnli in self.PanelInstruments if pnli.name == stealname][0]
            self.occupiedInstruments.update({stealname:str(handle)})
            self.music_player.mutelist.append(stealname)
            if releasename:
                relname = releasename
                relpanel = [p for p in self.PanelInstruments if p.name == relname][0]
                try:
                    del self.occupiedInstruments[relname]
                    relpanel.Touch = True
                    self.music_player.mutelist.remove(relname)
                except KeyError: pass
                except ValueError: pass
            paneli.Touch = True
            return True
    def requestInstrument(self, name):
        "instrument selections should go through this first. To request an instrument, you need to give one up"
        if name in self.occupiedInstruments:
            log.info('failed instrument selection, as instrument currently occupied')
        else:
            if self.connected and (self.sharer != self.myself):
                releasename = self.selectedInstrument.name 
                iparams = getInstrumentParameters(self.scene, releasename) 
                requestname = name 
                mesh.send_to(self.sharer, 'JammerRequest|%s|%s|%s' %(releasename, requestname, iparams))
            else:
                self.reselectInstruments(name)
                if self.connected: mesh.broadcast('Occupied|%s' %self.occupiedInstruments)
    def receiveMessage(self, instruction, handle):
        if instruction.startswith("Welcome"):
            messages = instruction.split("|")
            self.sharer = handle
            jam_scene = messages[1]
            self.pending_instrument_assignment = [messages[2],messages[3]] 
            self.select_activity_scene(jam_scene) 
            if self.sharer != self.myself:
                olpcgames.ACTIVITY.J2JToolbar.deactivate_scene_change()
        elif instruction.startswith("Beat"):
            splitvals = instruction.split('|')
            receivedBeat = int(splitvals[1])
            time_now = now()
            self.beatEstimator.addBeat(receivedBeat, time_now)
            if abs(receivedBeat - self.beatEstimator.beat_match(time_now)) > 0.17:
                pass
            else:
                latency = (sum(self.latency) / len(self.latency))
                tmult = self.music_player.tempoMult
                latency = latency * 0.25 + 0.04 #this might be XO 1.0 specific
                beatadvance = int(ceil(latency * 1/tmult)) 
                scheduled_time = now() + ((beatadvance * tmult) - latency)
                self.music_player.Cease()
                self.music_player.playLoop(scheduled_time, (receivedBeat + beatadvance) % self.music_player.beatlimit)
        elif instruction.startswith("JammerRequest"):
            "In theory only the sharer ever gets this message" 
            split = instruction.split('|')
            releasename = split[1]
            requestname = split[2]
            iparams = eval(split[3])
            stealresult = self.stealInstrument(requestname, releasename, handle)
            if stealresult:
                setInstrumentParameters(self.scene, releasename, iparams)
                rqparams = getInstrumentParameters(self.scene, requestname)
                mesh.send_to(handle, "AuthorisedInstrument|%s|%s" %(requestname, rqparams))
                mesh.broadcast('Occupied|%s' %self.occupiedInstruments)
            else:
                mesh.send_to(handle, "DeniedInstrument|%s")
        elif instruction.startswith("AuthorisedInstrument"):
            "In theory only a 'joiner' receives this message"
            msg = instruction.split('|')
            ai = msg[1]
            params = eval(msg[2])
            setInstrumentParameters(self.scene, ai, params)
            self.reselectInstruments(ai)
        elif instruction.startswith("DeniedInstrument"):
            di = instruction.split('|')[1]
            log.info("Instrument request for %s was denied by sharer." %di)
        elif instruction.startswith("Occupied"):
            insdict = eval(instruction.split('|')[1])
            self.occupiedInstruments = insdict
            for pni in self.PanelInstruments:
                if pni.name in insdict:
                    pni.deactivate()
                else:
                    pni.activate()
        elif instruction.startswith("LateReq"):
            id = instruction.split('|')[1]
            mesh.send_to(handle, "LateResp|%s" %id)
        elif instruction.startswith("LateResp"):
            id = int(instruction.split('|')[1])
            try:
                t = self.latency_time_ID[id]
                del self.latency_time_ID[id]
                result = (now() - t) / 2
                avglat = sum(self.latency) / len(self.latency)
                diffs = [(val - avglat) ** 2 for val in self.latency]
                stddev = sqrt(sum(diffs) / len(diffs))
                if id == 0:
                    del self.latency[0]
                    self.latency.append(result)
                elif result > (avglat + stddev):
                    pass
                elif result < (avglat - stddev) and len(self.latency) > 6:
                    pass
                elif len(self.latency) > 12:
                    del self.latency[0]
                    self.latency.append(result)
                else:
                    self.latency.append(result)
            except KeyError:
                log.info('Unmatched time ID %s' %id)
        else:
            log.debug("UNKNOWN INSTRUCTION RECEIVED :%s", instruction)
    def reselectInstruments(self, name):
        "Swaps the instrument on screen and selects the active Panel Instruments available to this user"
        oldInstrument = self.selectedInstrument 
        oldname = oldInstrument.name
        if (self.sharer == self.myself) or not self.connected:
            del self.occupiedInstruments[oldname]
            self.occupiedInstruments.update({name:str(self.myself)})
        self.screen.blit(self.backgroundImage, oldInstrument.Rect, oldInstrument.Rect)
        oldInstrument.Touch = False
        self.setselectedInstrument([i for i in self.TemplateInstruments if i.name == name][0])
        for w in self.PanelInstruments:
            if w.name == name or w.name == oldname:
                w.Touch = True
        if self.connected:
            if self.sharer == self.myself:
                self.music_player.mutelist = [j for j in self.occupiedInstruments if j != self.selectedInstrument.name]
            else:
                self.music_player.mutelist = [k.name for k in self.TemplateInstruments if k.name != self.selectedInstrument.name]
    def load_scene(self, name, key, mode, tempo, defaults = {}):
        self.music_player.freeze()
        self.music_player.cs.perf.Stop()
        self.music_player.cs.perf.Join()
        self.music_player.cs.csound.cleanup()
        sc = City.ScenePlayer(name, key, mode, tempo, defaults)
        mp = City.makePlayer(sc)
        global schedEvent, now
        schedEvent = sc.TimeQueue.schedEvent
        now = sc.cs.perfTime
        self.scene = sc
        self.music_player = mp
        self.music_player.playLoop(now())
        self.selectedInstrument.Touch = True
        self.music_player.picture_cycle = [self, True]

    def select_activity_scene(self, scene_name, key = None, mode = None, tempo = None, defaults = None):
        current_scene_name = self.scene.scene_name
        if scene_name == current_scene_name:
            if self.pending_instrument_assignment:
                self.receiveMessage("AuthorisedInstrument|%s|%s" %(self.pending_instrument_assignment[0], self.pending_instrument_assignment[1]), self.myself)
        elif not olpcgames.ACTIVITY:
            k = (key if key else 'G')
            m = (mode if mode else 'major')
            t = (int(tempo) if tempo else 164)
            d = (eval(defaults) if defaults else {})
            self.load_scene(scene_name, k,m,t,d)
        else:
            toolbar = olpcgames.ACTIVITY.J2JToolbar
            try:
                ndx = [n[0] for n in toolbar.scenes].index(scene_name)
                toolbar._Scene_combo.combo.set_active(ndx)
            except ValueError:
                log.info('request to change to unknown scene: %s', scene_name)
    def latency_checker(self):
        if self.sharer:
            self.latency_time_ID[self.latency_counter] = now()
            mesh.send_to(self.sharer,  "LateReq|%s" %self.latency_counter)
            self.latency_counter += 1
        if self.latency_counter < 10:
            Timer(3.5, self.latency_checker, ()).start()
        elif self.latency_counter < 50:
            Timer(6.75, self.latency_checker, ()).start()
        else:
            log.info('turning off latency checking')

#pygame main loop
def main():
    # check automatic power management
    try:
        sugar_pm_check = subprocess.Popen("sugar-control-panel -g automatic_pm", shell=True, stdout=subprocess.PIPE)
        sugar_pm_result = sugar_pm_check.communicate()[0]
        if sugar_pm_result.startswith("on"):
            subprocess.Popen("sugar-control-panel -s automatic_pm off", shell=True)
            _spm_off = True
        else:
            _spm_off = False
    except OSError:
        _spm_off = False
        log.info("Failed to detect and set automatic power management")
    screenSize_X, screenSize_Y = (olpcgames.ACTIVITY.game_size if platform=="Sugar"  else (1024,640))
    toolbarheight = 45
    screen = pygame.display.set_mode((screenSize_X, screenSize_Y - toolbarheight))
    a_,b_,c_,d_ = pygame.cursors.load_xbm("arrow40b.xbm", "arrow40b-mask.xbm")
    pygame.mouse.set_cursor(a_,b_,c_,d_)
    jam = jamScene(screen, tempo = 120)
    jam.runloop()
    pygame.quit()
    jam.music_player.freeze()
    jam.music_player.cs.perf.Stop()
    jam.music_player.cs.csound.cleanup()
    if _spm_off: subprocess.Popen("sugar-control-panel -s automatic_pm on", shell=True)
            
if __name__ == '__main__':
    logging.basicConfig()
    print "running as main"
    main()
    
