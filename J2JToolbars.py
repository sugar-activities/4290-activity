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

import sugar.activity
from sugar.activity.activity import get_bundle_path
from olpcgames import activity
import gtk, gst, thread, tempfile, time, os, types
import pygame, olpcgames
from gettext import gettext as _

_NEW_TOOLBAR_SUPPORT = True

from sugar.graphics.toolbutton import ToolButton #used in both old and new toolbars, but I suspect the new toolbar could use ToolbarButton instead.

try:
    from sugar.graphics.toolbarbox import ToolbarBox #new toolbar
    from sugar.graphics.toolbarbox import ToolbarButton #new toolbar
    from sugar.activity.widgets import StopButton #new toolbar
    from mybutton import AltButton #new toolbar
except:
    _NEW_TOOLBAR_SUPPORT = True
    from sugar.graphics.toolcombobox import ToolComboBox  #only needs to be imported if using old toolbar

import logging
log = logging.getLogger('City run')
log.setLevel(logging.DEBUG)
log.info("imported AltButton, inherits from ToolbarButton\n")

ImagePath = get_bundle_path() + "/City/Images"

GST_PIPE = ['v4l2src', 'ffmpegcolorspace', 'pngenc']

class readScenes(object):
    def __init__(self, scpath):
        self.scpath = scpath
        self.scene_names = [dir for dir in os.listdir(self.scpath) if os.path.isdir(self.scpath + '/' + dir)]
        self.scene_data = []
        for n in self.scene_names:
            fp = self.scpath + "/" + n            
            mdfile = [open(fp + '/' + f) for f in os.listdir(fp) if os.path.isfile(fp + "/" + f) and f.startswith(n)]
            if mdfile:
                result = {"Name":n}
                defaults = {}
                for line in mdfile[0]:
                    if line.startswith('#') or line.startswith('\n'):
                        pass
                    else:
                        keyvals = line.split('=')
                        if len(keyvals) == 2:
                            key = keyvals[0].upper() 
                            val = (keyvals[1][:-1] if keyvals[1][-1] == '\n' else keyvals[1])
                            if key.startswith('TEMPO'):
                                result['Tempo'] = val.replace(' ','')
                            elif key.startswith('KEY'):
                                result['Key'] = val.replace(' ','')
                            elif key.startswith('MODE'):
                                result['Mode'] = val.replace(' ','')
                            else:
                                pass
                        else:
                            raise IOError, "Bad Scene Meta Data file: %s" %keyvals
                result['Defaults'] = {}
                self.scene_data.append(result)
            else:
                raise IOError, "Can't find Meta Data file in %s Scene" %n
    def scene_instruct(self, name):
        "returns a list of strings suitable to give to a ScenePlayer object for creating a scene"
        for scd in self.scene_data:
            if scd['Name'] == name:
                collected = [name]
                for k in ['Key', 'Mode', 'Tempo', 'Defaults']:
                    try:
                        collected.append(str(scd[k]))
                    except KeyError:
                        collected.append('None')                
                return collected
    def get_scene_list(self):
        "returns a list of scene strings for the toolbar, with City as the default"
        ordered_names = self.scene_names[:]
        if 'City' in ordered_names:
            ordered_names.insert(0,ordered_names.pop(ordered_names.index('City')))
        return [self.scene_instruct(s) for s in ordered_names]

class CameraSnap(object):
    """A class representing the OLPC camera."""
    def __init__(self):
        log.info("CameraSnap init")
        snap_file, self.snap_path = tempfile.mkstemp(suffix = '.png')
        pipe = GST_PIPE + ['filesink location=%s' % self.snap_path]
        self.pipe = gst.parse_launch('!'.join(pipe))
        self.bus = self.pipe.get_bus()
        log.info("tempfile is %s " %self.snap_path)
    def Snap(self):
        """Take a snapshot."""
        log.info("about to set pipe state to PLAY")
        self.pipe.set_state(gst.STATE_PLAYING)
        log.info("about to poll")
        thread.start_new_thread(self.bus.poll, (gst.MESSAGE_EOS, -1))
        for i in xrange(60):
            time.sleep(0.18)
            if os.path.getsize(self.snap_path) > 0: break
        else: raise IOError, "Error writing camera snap to file"
        return self.snap_path
    def Stop(self):
        self.pipe.set_state(gst.STATE_NULL)

#old toolbar    
class Jam2JamToolBar(gtk.Toolbar):
    def __init__(self, activity):
        gtk.Toolbar.__init__(self)
        self.activity = activity
        self.parameters = ['Density', 'Pitch', 'Length', 'Timbre', 'Volume'] # no tempo here.
        scene_stuff = readScenes(self.activity._ScenePath)
        self.scenes = scene_stuff.get_scene_list()
        #example of scene data. This gets read from file
        #self.scenes = [['City', 'A', 'minor pentatonic'], ['City', 'G#', 'major']] #this data needs to be obtained from directories
        self.play_pause_state = 'Playing'
        self.scene_init = True
        
        # Separator
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        self.insert(separator, -1)

        #Horizontal Parameter control combobox
        self._add_widget(gtk.Label(_('Horizontal:')))
        self._Hparameter_combo = ToolComboBox()
        for i, f in enumerate(self.parameters):
            self._Hparameter_combo.combo.append_item(i, f)
        self._Hparameter_combo.combo.connect('changed', self._Hparameter_change_cb)
        self._add_widget(self._Hparameter_combo)
        self._Hparameter_combo.combo.set_active(0)

        # Separator
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)

        #Vertical Parameter control combobox
        self._add_widget(gtk.Label(_('Vertical:')))
        self._Vparameter_combo = ToolComboBox()
        for j, k in enumerate(self.parameters):
            self._Vparameter_combo.combo.append_item(j, k)
        self._Vparameter_combo.combo.connect('changed', self._Vparameter_change_cb)
        self._add_widget(self._Vparameter_combo)
        self._Vparameter_combo.combo.set_active(1)

        # Separator
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)

        #Scene Selection control combobox
        self._add_widget(gtk.Label(_('Scene:')))
        self._Scene_combo = ToolComboBox()
        for l, m in enumerate(self.scenes):
            self._Scene_combo.combo.append_item(l, m[0])
        self._Scene_combo.combo.connect('changed', self._Scene_change_cb)
        self._add_widget(self._Scene_combo)
        #ought to do this safely somehow.
        self._Scene_combo.combo.set_active(0)
        self.scene_init = False

        # Separator
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)
        
        #Camera Button
        self.camera_ready = True
        camera_icon = ImagePath + "/camera-external.svg"
        camera_busy_icon = ImagePath + "/camera-busy.svg"        
        self.camera_image, self.camera_busy_image = gtk.Image(), gtk.Image()
        self.camera_image.set_from_file(camera_icon)
        self.camera_busy_image.set_from_file(camera_busy_icon)
        self.camera_image.show()
        #camera_busy_image.show()
        self._cameraButton = ToolButton()
        self._cameraButton.set_icon_widget(self.camera_image)
        self._cameraButton.connect('clicked', self._cameraSnap_cb)
        self._cameraButton.set_tooltip(_('Snapshot'))
        self.insert(self._cameraButton, -1)
        self._cameraButton.show()

        # Separator
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)

        #Play/Pause Button
        pause_icon = ImagePath + "/media-playback-pause.svg"
        play_icon = ImagePath + "/media-playback-start.svg"
        self.pause_image = gtk.Image()
        self.pause_image.set_from_file(pause_icon)
    
        self.play_image = gtk.Image()
        self.play_image.set_from_file(play_icon)

        self._pauseButton = ToolButton()
        self._pauseButton.connect('clicked', self._pause_cb)
        self.pause_image.show()
        self._pauseButton.set_icon_widget(self.pause_image)
        self._pauseButton.set_tooltip(_('Pause'))
        #self._toggleplay_pause()
        self.insert(self._pauseButton, -1)
        self._pauseButton.show()

        # Separator
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)


    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)
        tool_item.add(widget)
        widget.show()
        self.insert(tool_item, -1)
        tool_item.show()

    def _toggleplay_pause(self):
        if self.play_pause_state == "Playing":
            self.activity.jamScene.music_player.pause()
            self.play_image.show()
            self._pauseButton.set_icon_widget(self.play_image)
            self._pauseButton.set_tooltip(_('Play'))
            self.play_pause_state = "Paused"
        else:
            self.activity.jamScene.music_player.resume()
            self.pause_image.show()
            self._pauseButton.set_icon_widget(self.pause_image)
            self._pauseButton.set_tooltip(_('Pause'))
            self.play_pause_state = "Playing"
        try:
            self.activity._pgc.grab_focus()
        except AttributeError:
            pass

    def _show_busy_camera(self):
        self.camera_ready = False
        self.camera_busy_image.show()
        self._cameraButton.set_icon_widget(self.camera_busy_image)
        self._cameraButton.set_tooltip(_('Please wait...'))

    def _show_active_camera(self):
        self.camera_image.show()
        self._cameraButton.set_icon_widget(self.camera_image)
        self._cameraButton.set_tooltip(_('Snap'))
        self.camera_ready = True
        
    def _Hparameter_change_cb(self, widget):
        param = "Parameter|Horizontal|" + self.parameters[self._Hparameter_combo.combo.get_active()]
        olpcgames.eventwrap.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action=param))
        try:
            self.activity._pgc.grab_focus()
        except AttributeError:
            pass

    def _Vparameter_change_cb(self, widget):
        param = "Parameter|Vertical|" + self.parameters[self._Vparameter_combo.combo.get_active()]
        olpcgames.eventwrap.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action=param))
        try:
            self.activity._pgc.grab_focus()
        except AttributeError:
            pass

    def _Scene_change_cb(self, widget):
        if self.scene_init:
            pass
        else:
            selection = self.scenes[self._Scene_combo.combo.get_active()]
            scene = "Reload|" + '|'.join(map(lambda x: str(x), selection))
            olpcgames.eventwrap.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action=scene))
            try:
                self.activity._pgc.grab_focus()
            except AttributeError:
                pass

            ### functions to assist calls from pygame
    def deactivate_scene_change(self):
        self._Scene_combo.set_sensitive(False)
    def reactivate_scene_change(self):
        self._Scene_combo.set_sensitive(True)
    def set_horizontal_parameter(self, param):
        ndx = self.parameters.index(param)
        self._Hparameter_combo.combo.set_active(ndx)
    def set_vertical_parameter(self, param):
        ndx = self.parameters.index(param)
        self._Vparameter_combo.combo.set_active(ndx)
        
    def _cameraSnap_cb(self, widget):
        "Here I could wrap a camera event..."
        def snaptime():
            snap = CameraSnap()
            self.activity.cameras_loaded.append(snap)
            picpath = snap.Snap()
            self.activity.load_image(picpath)
            snap.Stop()
            self._show_active_camera()
        self.activity._pgc.grab_focus()
        if self.camera_ready:
            self._show_busy_camera()
            thread.start_new_thread(snaptime, ())
        else:
            log.info('Ignoring request to use camera, as camera is currently busy')

    def _pause_cb(self, widget):
        self._toggleplay_pause()
        log.info("Play/Pause Button pressed")
        

class J2J_Toolbar_Redirect( object ):
    "This object provides an API interface for pygame calls to the new toolbars"
    def __init__(self, activity_toolbar, horizontal_toolbar, vertical_toolbar, scene_toolbar):
        self.horizontal_toolbar = horizontal_toolbar
        self.vertical_toolbar = vertical_toolbar
        self.activity_toolbar = activity_toolbar
    def deactivate_scene_change(self):
        "The music style menu gets frozen when jamming on a network"
        stb = self.activity_toolbar.nameID['Music']
        stb.set_sensitive(False)
    def reactivate_scene_change(self):
        stb = self.activity_toolbar.nameID['Music']
        stb.set_sensitive(True)
    def set_horizontal_parameter(self, param):
        log.info("set_horizontal_parameter received %s" %param)
        self.horizontal_toolbar.set_horizontal_parameter(param)
    def set_vertical_parameter(self, param):
        log.info("set_vertical_parameter received %s" %param)        
        self.vertical_toolbar.set_vertical_parameter(param)


#should probably tidy these toolbars up. Subclass them.
class Jam2JamActivityToolbar( gtk.Toolbar ):
    def __init__(self, activity):
        log.info('entering __init__ in Jam2JamActivityToolbar')
        self.toolbar_box = ToolbarBox()
        log.info('made the activity toolbar_box')
        self.activity = activity
        activity_button = AltButton(activity)
        log.info ('made the ALT BUTTON')
        self.toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()
        self.nameID = {}

    def addCallback(self, func):
        "used to add a callback function to buttons, make sure you do this before trying to add the button"
        result = types.MethodType(func, self)
        self.__setattr__(func.__name__, result)

    def addToolBarButton(self, nameID, icon_name, toolbar=None):
        "I wonder if this can be merged with the ad button below?"
        button = ToolbarButton(
            page=toolbar,
            icon_name=icon_name)
        self.toolbar_box.toolbar.insert(button, -1)
        button.show()
        toolbar.show()
        self.nameID.update({nameID:button})
        
    def addSeparator(self):
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.toolbar_box.toolbar.insert(separator, -1)
        
    def addButton(self, nameID, image1path, image2path, tooltip1, tooltip2, cb):
        button = ToolButton()
        log.info("addButtonIMAGE PATH ____   " + image1path )
        button.image1 = gtk.Image()
        button.image1.set_from_file(image1path)
        button.image2 = gtk.Image()
        button.image2.set_from_file(image2path)
        button.image1.show()
        button.tooltip1, button.tooltip2 = tooltip1, tooltip2
        button.set_icon_widget(button.image1)
        button.connect('clicked', cb)
        button.set_tooltip(_(button.tooltip1))
        button.nameID = nameID
        self.toolbar_box.toolbar.insert(button, -1)
        button.show()
        self.nameID.update({nameID:button})
        
    def addStopButton(self):
        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        separator.show()
        self.toolbar_box.toolbar.insert(separator, -1)        
        stop_button = StopButton(self.activity)
        stop_button.props.accelerator = '<Ctrl><Shift>Q'
        self.toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()
        
    def getToolItem(self, nameID):
        return self.nameID[nameID]

    def play_pause_cb(self, button):
        if self.activity.play_pause_state == "Playing":
            self.activity.jamScene.music_player.pause()
            button.image2.show()
            button.set_icon_widget(button.image2)
            button.set_tooltip(_('Play'))
            self.activity.play_pause_state = "Paused"
        else:
            self.activity.jamScene.music_player.resume()
            button.image1.show()
            button.set_icon_widget(button.image1)
            button.set_tooltip(_('Pause'))
            self.activity.play_pause_state = "Playing"
        try:
            self.activity._pgc.grab_focus()
        except AttributeError:
            pass

    def camera_cb(self, button):
        "Here I could wrap a camera event..."
        if not hasattr(self, 'camera_ready'): self.camera_ready = True
        def show_busy_camera(button):
            self.camera_ready = False
            button.image2.show()
            button.set_icon_widget(button.image2)
            button.set_tooltip(_('Please wait...'))
        def show_active_camera(button):
            button.image1.show()
            button.set_icon_widget(button.image1)
            button.set_tooltip(_('Snap'))
            self.camera_ready = True
        def snaptime(button):
            snap = CameraSnap()
            self.activity.cameras_loaded.append(snap)
            picpath = snap.Snap()
            self.activity.load_image(picpath)
            snap.Stop()
            show_active_camera(button)
        self.activity._pgc.grab_focus()
        if self.camera_ready:
            show_busy_camera(button)
            thread.start_new_thread(snaptime, (button,))
        else:
            log.info('Ignoring request to use camera, as camera is currently busy')

        
class Jam2JamParameterToolbar(gtk.Toolbar):
    def __init__(self, activity):
        gtk.Toolbar.__init__(self)
        self.activity = activity
        self.parameters = ['Pitch', 'Timbre', 'Density', 'Volume', 'Length'] # no tempo here yet.
        self.scene_init = True
        self.activeButton = None

    def addButton(self, nameID, image1path, image2path, tooltip1, tooltip2, cb):
        button = ToolButton()
        button.image1 = gtk.Image()
        button.image1.set_from_file(image1path)
        button.image2 = gtk.Image()
        button.image2.set_from_file(image2path)
        button.image1.show()
        button.nameID = nameID
        button.tooltip1, button.tooltip2 = tooltip1, tooltip2
        button.set_icon_widget(button.image1)
        button.connect('clicked', cb) 
        button.set_tooltip(_(button.tooltip1))
        button.active = False
        self.insert(button, -1)
        button.show()
        return button

    def toggleButtonIcon(self, button):
        if button.active:
            button.image1.show()
            button.set_icon_widget(button.image1)
            button.set_tooltip(_(button.tooltip1))
            button.active = False
        else:
            button.image2.show()
            button.set_icon_widget(button.image2)
            button.set_tooltip(_(button.tooltip2))
            button.active = True
            

    def addSeparator(self):
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)

    def set_horizontal_parameter(self, param):
        buttons = self.get_children()
        for b in buttons:
            if b.nameID == param:
                self.set_horizontal_cb(b)
                break
        else:
            raise TypeError('%s keystroke is not a recognised parameter' %param)

    def set_horizontal_cb(self, button):
        log.info('button pressed - %s' %button.nameID)
        if self.activeButton: self.toggleButtonIcon(self.activeButton)
        self.activeButton = button
        self.toggleButtonIcon(self.activeButton)
        param = "Parameter|Horizontal|" + button.nameID
        olpcgames.eventwrap.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action=param))
        try:
            self.activity._pgc.grab_focus()
        except AttributeError:
            pass

    def set_vertical_parameter(self, param):
        buttons = self.get_children()
        for b in buttons:
            if b.nameID == param:
                self.set_vertical_cb(b)
                break
        else:
            raise TypeError('%s keystroke is not a recognised parameter' %param)        

    def set_vertical_cb(self, button):
        log.info('button pressed - %s' %button.nameID)
        if self.activeButton: self.toggleButtonIcon(self.activeButton)
        self.activeButton = button
        self.toggleButtonIcon(self.activeButton)
        param = "Parameter|Vertical|" + button.nameID
        olpcgames.eventwrap.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action=param))
        try:
            self.activity._pgc.grab_focus()
        except AttributeError:
            pass
        

class Jam2JamSceneToolbar(gtk.Toolbar):
    "Toolbar which sets musicl styles"
    def __init__(self, activity):
        gtk.Toolbar.__init__(self)
        self.activity = activity
        scene_stuff = readScenes(self.activity._ScenePath)
        self.scenes = scene_stuff.get_scene_list()
        log.info("SCENE DATA IS %s" %self.scenes)
        #format of self.scenes
        #self.scenes = [['City', 'A', 'minor pentatonic'], ['City', 'G#', 'major']] #this data is read from file
        self.play_pause_state = 'Playing'
        self.activeButton = None
        #self.scene_init = True

    def addButton(self, nameID, image1path, image2path, tooltip1, tooltip2, cb):
        button = ToolButton()
        button.image1 = gtk.Image()
        button.image1.set_from_file(image1path)
        button.image2 = gtk.Image()
        button.image2.set_from_file(image2path)
        button.image1.show()
        button.nameID = nameID
        button.tooltip1, button.tooltip2 = tooltip1, tooltip2
        button.set_icon_widget(button.image1)
        button.connect('clicked', cb) 
        button.set_tooltip(_(button.tooltip1))
        button.active = False
        self.insert(button, -1)
        button.show()
        return button

    def toggleButtonIcon(self, button):
        if button.active:
            button.image1.show()
            button.set_icon_widget(button.image1)
            button.set_tooltip(_(button.tooltip1))
            button.active = False
        else:
            button.image2.show()
            button.set_icon_widget(button.image2)
            button.set_tooltip(_(button.tooltip2))
            button.active = True
            
    def _get_scene_data(self, button):
        button_name = button.nameID
        for item in self.scenes:
            if item[0] == button_name: return item
        else:
            raise IOError('could not match button name %s to scene data %s' %(button_name, self.scenes))
            
    def scene_change_cb(self, button):
        log.info("scene change requested: %s" %button.nameID)
        if self.activeButton: self.toggleButtonIcon(self.activeButton)
        self.activeButton = button
        self.toggleButtonIcon(self.activeButton)        
        selection = self._get_scene_data(button)
        #Scene message should look like this: "Reload|name|key:mode|tempo|defaults"
        scene = "Reload|" + '|'.join(map(lambda x: str(x), selection))
        olpcgames.eventwrap.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action=scene))
        try:
            self.activity._pgc.grab_focus()
        except AttributeError:
            pass

    def addSeparator(self):
        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)

