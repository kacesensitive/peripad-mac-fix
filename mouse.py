import ctypes, time
from ctypes import (
    c_void_p, c_int32, c_uint32, c_uint8, c_long, c_char_p, c_int,
    POINTER, CFUNCTYPE, byref, addressof
)
from Quartz.CoreGraphics import (
    CGEventCreateMouseEvent, CGEventPost, CGEventCreate, CGEventGetLocation,
    CGDisplayBounds, CGGetActiveDisplayList,
    kCGEventMouseMoved, kCGHIDEventTap, kCGMouseButtonLeft,
)

IOKit = ctypes.CDLL('/System/Library/Frameworks/IOKit.framework/IOKit')
CF = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')

CF.CFRunLoopGetCurrent.restype = c_void_p
CF.CFRunLoopRun.restype = None
CF.CFStringCreateWithCString.restype = c_void_p
CF.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]
CF.CFNumberCreate.restype = c_void_p
CF.CFNumberCreate.argtypes = [c_void_p, c_int32, c_void_p]
CF.CFDictionaryCreateMutable.restype = c_void_p
CF.CFDictionaryCreateMutable.argtypes = [c_void_p, c_long, c_void_p, c_void_p]
CF.CFDictionarySetValue.argtypes = [c_void_p, c_void_p, c_void_p]

kCFTypeDictKey = addressof(c_int.in_dll(CF, 'kCFTypeDictionaryKeyCallBacks'))
kCFTypeDictVal = addressof(c_int.in_dll(CF, 'kCFTypeDictionaryValueCallBacks'))
kCFRunLoopDefaultMode = c_void_p.in_dll(CF, 'kCFRunLoopDefaultMode')

IOKit.IOHIDManagerCreate.restype = c_void_p
IOKit.IOHIDManagerCreate.argtypes = [c_void_p, c_uint32]
IOKit.IOHIDManagerSetDeviceMatching.argtypes = [c_void_p, c_void_p]
IOKit.IOHIDManagerOpen.restype = c_int32
IOKit.IOHIDManagerOpen.argtypes = [c_void_p, c_uint32]
IOKit.IOHIDManagerScheduleWithRunLoop.argtypes = [c_void_p, c_void_p, c_void_p]

ReportCallback = CFUNCTYPE(
    None, c_void_p, c_int32, c_void_p, c_uint32, c_uint32,
    POINTER(c_uint8), c_long
)
IOKit.IOHIDManagerRegisterInputReportCallback.argtypes = [c_void_p, ReportCallback, c_void_p]

# tuning
SENSITIVITY = 0.05
LIFT_TIMEOUT = 0.10

# state
prev_x = None
prev_y = None
last_touch = 0.0

def screen_bounds():
    err, ids, count = CGGetActiveDisplayList(16, None, None)
    rects = [CGDisplayBounds(d) for d in ids[:count]]
    x0 = min(r.origin.x for r in rects)
    y0 = min(r.origin.y for r in rects)
    x1 = max(r.origin.x + r.size.width for r in rects)
    y1 = max(r.origin.y + r.size.height for r in rects)
    return x0, y0, x1, y1

X0, Y0, X1, Y1 = screen_bounds()
print(f'screen bounds: ({X0},{Y0}) to ({X1},{Y1})')

def move_by(dx, dy):
    cur = CGEventGetLocation(CGEventCreate(None))
    nx = max(X0, min(X1 - 1, cur.x + dx))
    ny = max(Y0, min(Y1 - 1, cur.y + dy))
    ev = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (nx, ny), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, ev)

def cb(context, result, sender, rtype, rid, report, length):
    global prev_x, prev_y, last_touch
    if rid != 7 or length < 5:
        return
    x = report[1] | (report[2] << 8)
    y = report[3] | (report[4] << 8)
    now = time.time()
    if prev_x is None or (now - last_touch) > LIFT_TIMEOUT:
        prev_x, prev_y = x, y
    else:
        dx = (x - prev_x) * SENSITIVITY
        dy = (y - prev_y) * SENSITIVITY
        if dx or dy:
            move_by(dx, dy)
        prev_x, prev_y = x, y
    last_touch = now

cb_ref = ReportCallback(cb)

def main():
    mgr = IOKit.IOHIDManagerCreate(None, 0)
    d = CF.CFDictionaryCreateMutable(None, 0, kCFTypeDictKey, kCFTypeDictVal)
    vid_k = CF.CFStringCreateWithCString(None, b'VendorID', 0x08000100)
    pid_k = CF.CFStringCreateWithCString(None, b'ProductID', 0x08000100)
    vid = c_int32(0x258a); pid = c_int32(0x000c)
    CF.CFDictionarySetValue(d, vid_k, CF.CFNumberCreate(None, 3, byref(vid)))
    CF.CFDictionarySetValue(d, pid_k, CF.CFNumberCreate(None, 3, byref(pid)))
    IOKit.IOHIDManagerSetDeviceMatching(mgr, d)
    IOKit.IOHIDManagerRegisterInputReportCallback(mgr, cb_ref, None)
    IOKit.IOHIDManagerScheduleWithRunLoop(mgr, CF.CFRunLoopGetCurrent(), kCFRunLoopDefaultMode)
    r = IOKit.IOHIDManagerOpen(mgr, 0)
    if r != 0:
        print(f'open failed: {r:#x}')
        return
    print('cursor driver running. ctrl-c to stop.')
    CF.CFRunLoopRun()

main()