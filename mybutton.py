print "HERE IS MYEDITEDBUTTON\n"
import gtk
import gconf

from sugar.graphics.toolbarbox import ToolbarButton

from sugar.activity.widgets import ActivityToolbar

from sugar.graphics.xocolor import XoColor

from sugar.graphics.icon import Icon

from sugar.bundle.activitybundle import ActivityBundle


def _create_activity_icon(metadata):
    print "_create_activity_icon was called"
    if metadata.get('icon-color', ''):
        color = XoColor(metadata['icon-color'])
    else:
        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
    from sugar.activity.activity import get_bundle_path
    print "Where is the bundle path? :", get_bundle_path()
    bundle = ActivityBundle(get_bundle_path())
    icon = Icon(file=bundle.get_icon(), xo_color=color)
    return icon


class AltButton(ToolbarButton):
    def __init__(self, activity, **kwargs):
        print "alternativeMY ACTIviTy tOOLbARbUTTON init\n"
        toolbar = ActivityToolbar(activity, orientation_left=True)
        toolbar.stop.hide()
        toolbar.keep.hide()
        ToolbarButton.__init__(self, page=toolbar,**kwargs)
        icon = _create_activity_icon(activity.metadata)
        self.set_icon_widget(icon)
        icon.show()
 

class test2:
    def __init__(self):
        print "passed test2, old style class"


def test3(x):
    print "passed test3, just a function"


class MyAlternativeToolbarButton(ToolbarButton):
    def __init__(self, activity, **kwargs):
        print "MY Alternative tOOLbARbUTTON init\n"
        toolbar = ActivityToolbar(activity, orientation_left=True)
        toolbar.stop.hide()
        toolbar.keep.hide()
        ToolbarButton.__init__(self, page=toolbar,**kwargs)
        icon = _create_activity_icon(activity.metadata)
        self.set_icon_widget(icon)
        icon.show()
        

