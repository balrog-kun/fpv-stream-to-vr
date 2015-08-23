stream.py
=========

A simple python script to open a live video stream and send it to an
Oculus Rift DK2.  The parameters used to select the output port are at
the top of the script and can be modified for other VR goggles.

It currently uses a single 2D video source, duplicates
it and displays without any deformation.  This works great for wide-angle
/ fish-eye lens cameras used for FPV but won't look good for a narrow-angle
camera -- the image will look deformed.

    $ ./stream.py [ device-path [ scale ] ]

`device-path` may be a /dev path to a v4l2 video source such as an
analog receiver connected to a USB port through a TV-grabber (EasyCap and
similar), usually /dev/video*N*.  Default is `/dev/video1` since
`/dev/video0` is often a laptop's selfie camera.

`device-path` may also be `wifibroadcast` for the script to try reading
video from standard input as described on the [wifibroadcast project page]
(https://befinitiv.wordpress.com/wifibroadcast-analog-like-transmission-of-live-video-data/).
In that case you'll use something like
`sudo ./rx -b 8 -r 4 -f 1024 wlan0 | ./stream.py wifibroadcast`

`scale` can be an integer percentage to set the initial video scale.
Default is 100.  100 means use the full goggles resolution (about 110
degrees FOV on an oculus DK2).  20 or 30 percent will give a FOV
similar to Fatshark, Headplay and other goggles.

Keys
====

When the script runs the following keys can be used:

* Esc or 'q': exit.

* Left / right arrows: Move video slightly left/right, useful if analog
  signal has a black band on one side.

* Up / down arrows: decrease/increase video frame size by 5%.

* '[' / ']': slightly increase/decrease left-to-right-eye video frame
  distance, basically move the virtual screen closer / farther.

Ideas
=====

* Use the head tracker for video parameter adjustment (e.g. when holding
  space on the keyboard) or gimbal / aircraft steering (with some other
  key) though MAVlink messages.

* Add a ground-side OSD for wifibroadcast.  This would perhaps need to
  be a gstreamer plugin written in C for performance unless it was all
  OpenGL calls in which case it might not matter.  Could use transparency,
  colours, etc. to achieve something like the greenish fighter-jet glass
  cockpit style overlay.  Could also make use of basic 3D but that could
  be too distracting.

Dependencies
============

Gstreamer-1.0 or later is required, gobject and GTK libraries and their
python bindings.  Installing the gstreamer python bindings should in
theory pull everything else in as dependency (`apt-get install python-gst-1.0`).

Problems
========

Sometimes gstreamer will pop an internal error of some kind or a cryptic
X11 error on start.  The script can be retried and should eventually run.
