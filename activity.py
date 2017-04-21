#This python module is part of the Jam2Jam XO Activity, March, 2012
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


import pygame, olpcgames
from olpcgames import activity
import sugar.activity
from sugar.activity.activity import get_bundle_path
ImagePath = get_bundle_path() + "/City/Images"


import gtk.gdk

from gettext import gettext as _
import logging, os
log = logging.getLogger( 'City run' )
log.setLevel( logging.DEBUG )
log.info( """ LOG From activity.py!!""")

from olpcgames import mesh, util

_NEW_TOOLBAR_SUPPORT = True

try:
    from sugar.graphics.toolbarbox import ToolbarBox #superfluous import here, but we need to detect sugar versions post 0.86
    from J2JToolbars import J2J_Toolbar_Redirect
    from J2JToolbars import Jam2JamActivityToolbar, Jam2JamParameterToolbar, Jam2JamSceneToolbar
except:
    _NEW_TOOLBAR_SUPPORT = False
    from sugar.activity.activity import ActivityToolbox        
    from J2JToolbars import Jam2JamToolBar #NOW ONLY GETS IMPORTED WHEN OLD TOOLBARS ARE USED


class Activity(activity.PyGameActivity):
    """Your Sugar activity"""
    game_name = 'run:main'
    game_title = _('Jam2Jam')
    game_size = None
    _ScenePath = (get_bundle_path() + "/City/Scenes")

    def __init__(self, handle):
        self.handle = handle
        activity.PyGameActivity.__init__(self, handle)
        self.snap_store = []
        self.cameras_loaded = []
        self.playArea = None
        self.jamScene = None
        self.play_pause_state = 'Playing'
        
    def load_image(self, picpath):
        picsurf = pygame.image.load(picpath)
        picsurf = picsurf.convert()
        picsurfwidth = picsurf.get_width()
        destwidth = self.playArea.width
        scale = float(destwidth) / picsurfwidth
        newarea = (int(picsurfwidth * scale),  int(picsurf.get_height() * scale))
        picsurf = pygame.transform.scale(picsurf, newarea)
        self.snap_store.append(picsurf)

    def build_toolbar(self):
        if _NEW_TOOLBAR_SUPPORT:
            log.info("building NEW toolbar\n")
            return self.build_new_toolbar()
        else:
            log.info("buiding OLD toolbar \n")
            return self.build_old_toolbar()
    def build_old_toolbar(self):
        toolbox = ActivityToolbox(self)
        activityToolbar = toolbox.get_activity_toolbar()
        activityToolbar.keep.props.visible = False
        self.J2JToolbar = Jam2JamToolBar(self)
        
        toolbox.add_toolbar("Transform", self.J2JToolbar)
        self.set_toolbox(toolbox)
        self.J2JToolbar.show()
        toolbox.show()
        
        self.toolbox.set_current_toolbar(1)

        self.connect("shared", self.shared_cb)
        self.connect("joined", self.joined_cb)
        
        if self.get_shared():
            self.joined_cb()
        log.info ("FINISHED building toolbar")
        return toolbox
    def build_new_toolbar(self):
        log.info ("building new toolbar")

        activity_toolbar = Jam2JamActivityToolbar(self)
        Horizontal_Toolbar = Jam2JamParameterToolbar(self)
        Vertical_Toolbar = Jam2JamParameterToolbar(self)
        Scene_Toolbar = Jam2JamSceneToolbar(self)
        self.J2JToolbar = J2J_Toolbar_Redirect(activity_toolbar, Horizontal_Toolbar, Vertical_Toolbar, Scene_Toolbar) #the pygame interface


        activity_toolbar.addToolBarButton("Horizontal", "horizontal5", Horizontal_Toolbar)
        
        activity_toolbar.addToolBarButton("Vertical", "vertical5", Vertical_Toolbar)
        activity_toolbar.addSeparator()
        activity_toolbar.addToolBarButton("Music", "music2", Scene_Toolbar)
        activity_toolbar.addSeparator()

        activity_toolbar.addButton('Camera',
                                   ImagePath + "/camera-external.svg",
                                   ImagePath + "/camera-busy.svg",
                                   "Take a picture", "processing, please wait",
                                   activity_toolbar.camera_cb)

        activity_toolbar.addButton('PlayPause',
                                   ImagePath + "/media-playback-pause.svg",
                                   ImagePath + "/media-playback-start.svg",
                                   "Pause", "Play",
                                   activity_toolbar.play_pause_cb)

        activity_toolbar.addStopButton()

        parameters = ['Pitch', 'Timbre', 'Density', 'Volume', 'Length']

        for p in parameters:
            h = Horizontal_Toolbar.addButton(p,
                                         ImagePath + "/" + p.lower() + "1.svg",
                                         ImagePath + "/" + p.lower() + "2.svg",
                                         p, p + "-active",
                                         Horizontal_Toolbar.set_horizontal_cb)
            v = Vertical_Toolbar.addButton(p,
                                         ImagePath + "/" + p.lower() + "1.svg",
                                         ImagePath + "/" + p.lower() + "2.svg",
                                         p, p + "-active",
                                         Vertical_Toolbar.set_vertical_cb)            
            if p == 'Density': Horizontal_Toolbar.set_horizontal_cb(h)
            if p == 'Pitch': Vertical_Toolbar.set_horizontal_cb(v)                    
        Horizontal_Toolbar.show()
        Vertical_Toolbar.show()

        scenes = ['City', 'Country', 'Latin', 'Blues', 'Reggae']
        for s in scenes:
            bs = Scene_Toolbar.addButton(s, ImagePath + "/" + s.lower() + "1.svg",
                                         ImagePath + "/" + s.lower() + "2.svg",
                                         s, s + "-active",
                                         Scene_Toolbar.scene_change_cb)            
            if s == 'City': Scene_Toolbar.scene_change_cb(bs)
        
        self.connect("shared", self.shared_cb)
        self.connect("joined", self.joined_cb)
        if self.get_shared(): self.joined_cb()

        self.set_toolbar_box(activity_toolbar.toolbar_box)
        activity_toolbar.toolbar_box.show()
        vpb = activity_toolbar.nameID['Horizontal']
        vpb.set_expanded(True)
        return activity_toolbar.toolbar_box
        
    def shared_cb(self, *args, **kwargs):
        log.info( 'Shared CB: %s, %s', args, kwargs )
        try:
            mesh.activity_shared(self)
        except Exception, err:
            log.error( """Failure signaling activity sharing to mesh module: %s""", util.get_traceback(err) )
        else:
            log.info( 'mesh activity shared message sent' )
        try:
            self._pgc.grab_focus()
        except Exception, err:
            log.warn( 'Focus failed: %s', err )
        else:
            assert self._pgc.is_focus(), """Did not successfully set pygame canvas focus"""
        sharermessage = "Shared:StartBeat"
        olpcgames.eventwrap.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action=sharermessage))
    def joined_cb(self, *args, **kwargs):
        log.info( 'joined CB: %s, %s', args, kwargs )
        mesh.activity_joined(self)
        self._pgc.grab_focus()
        joinedmessage = "Joined:CeasePlayer"
        olpcgames.eventwrap.post(olpcgames.eventwrap.Event(pygame.USEREVENT, action=joinedmessage))
