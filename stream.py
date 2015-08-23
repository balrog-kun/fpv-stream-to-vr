#!/usr/bin/env python

import sys

input_path = '/dev/video1'
oculus_width = 1920
oculus_height = 1080

if len(sys.argv) > 1:
    input_path = sys.argv[1]

# Set output_port to an output name recognized by xrandr to override where
# we output the video - if output_port is None we'll look for
# the first monitor that is 1920x1080.  If not None, we'll ignore
# oculus_width and oculus_height and assume the resolution reported by
# xrandr with half of the screen area for each eye.
#output_port = 'HDMI1'
output_port = None

if input_path == 'wifibroadcast':
    input_pipeline = 'fdsrc ! h264parse ! avdec_h264'
else:
    input_pipeline = 'v4l2src device=' + input_path + ' ! deinterlace'

# Don't write the stream to disk by default
dump_pipeline = ''
#dump_pipeline = 'orig. ! queue ! filesink location=capture.raw'

default_scale = 100
if len(sys.argv) > 2:
    default_scale = int(sys.argv[2])

import subprocess, re, gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, Gtk, Gdk

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo

class GTK_Main(object):
    def __init__(self, w, h, x, y):
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_decorated(False)
        window.move(x, y)
        window.resize(w, h)
        window.fullscreen()
        window.connect("destroy", Gtk.main_quit, "WM destroy")
        window.connect("key_press_event", self.on_key_press)
        self.gst_window = Gtk.DrawingArea()
        window.add(self.gst_window)
        window.show_all()

        # TODO: disable screen saver and autosuspend (gsettings?)

        self.per_eye_w = w / 2
        self.per_eye_h = h
        self.video_scale = default_scale
        self.left_x = 0
        self.right_x = w / 2
        self.offset_x = 0

        self.caps = Gst.Caps.new_empty_simple('video/x-raw')

        # Set up the gstreamer pipeline
        self.player = Gst.parse_launch(input_pipeline + ' ! ' +
                'tee name=orig ! ' +
                'videoscale ! ' +
                'capsfilter name=caps ! ' +
                'tee name=tee ! ' +
                'queue ! ' +
                'videomixer name=mixer background=black ! ' +
                'video/x-raw,width=' + str(w) + ',height=' + str(h) + ' ! ' +
                'xvimagesink double-buffer=false sync=false ' +
                'tee. ! ' +
                'queue ! ' +
                'mixer. ' +
                dump_pipeline)
        self.mixer = self.player.get_by_name('mixer')
        self.caps_elem = self.player.get_by_name('caps')

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)

        self.geom_update()

        self.player.set_state(Gst.State.PLAYING)
        sys.stderr.write('Gstreamer pipeline created and started\n')

    def geom_update(self):
        video_w = self.per_eye_w * self.video_scale / 100
        video_h = self.per_eye_h * self.video_scale / 100
        h_pad = (self.per_eye_w - video_w) / 2
        v_pad = (self.per_eye_h - video_h) / 2

        # TODO: reimplement x offset in a way that one eye's video never
        # shows in the other eye's half of the screen

        sink0 = self.mixer.get_static_pad('sink_0')
        sink1 = self.mixer.get_static_pad('sink_1')

        sink0.set_property('xpos', self.left_x + self.offset_x + h_pad)
        sink1.set_property('xpos', self.right_x + self.offset_x + h_pad)
        sink0.set_property('ypos', v_pad)
        sink1.set_property('ypos', v_pad)

        self.caps_elem.set_property('caps', None) # Release lock for a moment
        self.caps.set_value('width', video_w)
        self.caps.set_value('height', video_h)
        self.caps_elem.set_property('caps', self.caps)

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            sys.stderr.write('Stream ended\n')
            Gtk.main_quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            sys.stderr.write('Error: ' + str(err) + '\n' + str(debug))
            Gtk.main_quit()

    def on_sync_message(self, bus, message):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            Gdk.threads_enter()
            imagesink.set_window_handle(
                    self.gst_window.get_property('window').get_xid())
            Gdk.threads_leave()
            sys.stderr.write('Gstreamer synced\n')

    def on_key_press(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)

        if keyname in [ 'q', 'Q', 'Escape' ]:
            Gtk.main_quit()
        elif keyname == 'Left':
            self.offset_x -= 4
            self.geom_update()
        elif keyname == 'Right':
            self.offset_x += 4
            self.geom_update()
        elif keyname == 'Up' and self.video_scale > 20:
            self.video_scale -= 5
            self.geom_update()
        elif keyname == 'Down' and self.video_scale < 120:
            self.video_scale += 5
            self.geom_update()
        elif keyname == 'bracketleft':
            self.left_x -= 1
            self.right_x += 1
            self.geom_update()
        elif keyname == 'bracketright':
            self.left_x += 1
            self.right_x -= 1
            self.geom_update()

# Find the selected screen using xrandr directly
#
# Should either use one of the libxrandr bindings libraries but none is popular
# enough to be packaged by distributions, or use gtk.gdk:
# scr = gtk.gdk.screen_get_default()
# n = scr.get_n_monitors()
# [ scr.get_monitor_plug_name(i) for i in range(0, n) ]
# [ scr.get_monitor_geometry(i) for i in range(0, n) ]
# also subscribe to scr signal "monitor-changed"
#
# We'd still need to use xrandr to actually rotate the screen, it seems.

p = subprocess.Popen([ 'xrandr', '-q' ], stdout=subprocess.PIPE)
output = p.communicate()[0]
monitor_line = None
resolution_str1 = ' ' + str(oculus_width) + 'x' + str(oculus_height) + '+'
resolution_str2 = ' ' + str(oculus_height) + 'x' + str(oculus_width) + '+'

for line in output.split('\n'):
    if output_port and line.startswith(output_port):
        monitor_line = line
        break
    if not output_port and (resolution_str1 in line or resolution_str2 in line):
        monitor_line = line
        break

if not monitor_line:
    if output_port:
        sys.stderr.write(outout_port + ' not found\n')
    else:
        sys.stderr.write('No screen found with the right resolution\n')
    sys.exit(-1)

if not output_port:
    output_port = monitor_line.split()[0]
if 'disconnected' in monitor_line:
    sys.stderr.write(output_port + ' seems to be disconnected\n')
    sys.exit(-1)

match = re.search(r'\b([0-9]+)x([0-9]+)\+([0-9]+)\+([0-9]+)\b', monitor_line)
w, h, x, y = [ int(n) for n in match.groups() ]

sys.stderr.write('Using ' + output_port + ' for output\n')

# If screen seems to be in vertical/portrait mode (height > width), rotate it
if h > w:
    sys.stderr.write('Setting --rotate left\n')
    subprocess.check_call([ 'xrandr',
            '--output', output_port,
            '--rotate', 'left' ])
    w, h = h, w

GObject.threads_init()
Gst.init(None)
GTK_Main(w, h, x, y)
Gtk.main()
