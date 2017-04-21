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

import gtk
from sugar.graphics import style

class InstrumentPanel(gtk.EventBox):
    def __init__(self):
        gtk.EventBox.__init__(self)
        self.Box = gtk.VBox()
        self.status_label = gtk.Label()
        self.Box.pack_start(self.status_label, True, True, 10)
        self.score_label = gtk.Label()
        self.Box.pack_start(self.score_label, True, True, 10)
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("dark grey"))
        self.add(self.Box)
        self.show_all()

    def show(self, text):
        self.status_label.set_text(text)

       
