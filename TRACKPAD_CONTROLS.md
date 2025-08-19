# 🎮 Trackpad & Touch Controls Guide

## 🖱️ Input Methods Supported

Your game now intelligently detects and adapts to different input devices!

### **Trackpad Controls (MacBook, Laptop)**

#### Camera Controls:
- **Pinch to Zoom**: Pinch two fingers together/apart to zoom in/out
- **Two-Finger Swipe**: Swipe with two fingers to pan the camera
- **Edge Scrolling**: Move mouse to screen edges (still works)
- **WASD/Arrow Keys**: Keyboard camera movement (still works)

#### Selection Controls:
- **Tap**: Select unit
- **Tap & Drag**: Box select multiple units
- **Two-Finger Tap**: Right-click equivalent (move command)
- **Shift + Tap**: Add to selection
- **Cmd/Ctrl + Tap**: Toggle selection

### **Mouse Controls (Desktop)**

#### Camera Controls:
- **Mouse Wheel**: Zoom in/out
- **Edge Scrolling**: Move mouse to screen edges
- **WASD/Arrow Keys**: Keyboard camera movement

#### Selection Controls:
- **Left Click**: Select unit
- **Click & Drag**: Box select
- **Right Click**: Move command
- **Shift + Click**: Add to selection
- **Ctrl + Click**: Toggle selection

### **Touch Controls (Tablet/Phone)**

#### Camera Controls:
- **Pinch**: Zoom in/out
- **Single Finger Drag**: Pan camera
- **Double Tap**: Center on location

#### Selection Controls:
- **Tap**: Select unit
- **Tap & Hold + Drag**: Box select
- **Two-Finger Tap**: Move command

## 🔧 Configuration

The input system automatically detects your device type and configures itself appropriately:

- **Mac Users**: Trackpad mode enabled by default
- **Windows Laptop**: Trackpad detected on first scroll
- **Desktop**: Mouse mode by default
- **Mobile**: Touch mode enabled

### Manual Configuration (Coming Soon)

Settings will be accessible in the game menu to:
- Toggle between input modes
- Adjust sensitivity
- Invert controls
- Customize key bindings

## 🎯 Testing Your Controls

### Trackpad Test:
1. **Pinch Test**: Place two fingers on trackpad and pinch
   - Camera should zoom smoothly
2. **Two-Finger Swipe**: Swipe left/right/up/down with two fingers
   - Camera should pan in that direction
3. **Selection**: Tap to select, two-finger tap to move

### Mouse Test:
1. **Wheel Zoom**: Scroll mouse wheel
   - Camera should zoom
2. **Edge Pan**: Move mouse to screen edges
   - Camera should pan
3. **Selection**: Click to select, right-click to move

## 📊 Input Detection Info

The game shows detected input method in the console:
```
Input devices detected - Touch: false, Trackpad: true
```

### Platform Detection:
- **Mac**: Always assumes trackpad
- **Windows/Linux**: Detects based on scroll behavior
- **Mobile**: Touch enabled

## 🚀 Performance Notes

- Trackpad gestures are hardware-accelerated
- Two-finger pan is smoother than edge scrolling
- Pinch zoom maintains zoom point under fingers
- All gestures work at 60 FPS

## 🐛 Troubleshooting

### Trackpad not working?
1. Check browser console for detection message
2. Try pinching with Cmd/Ctrl held (backup method)
3. Refresh page and try scrolling with two fingers

### Too sensitive/not sensitive enough?
- Sensitivity settings coming in next update
- Current defaults optimized for MacBook trackpads

### Gestures conflicting with browser?
- Game prevents default browser zoom/scroll
- If issues persist, try fullscreen mode (F11)

## 🎮 Control Summary Card

```
TRACKPAD USERS:
├─ Zoom: Pinch in/out
├─ Pan: Two-finger swipe
├─ Select: Tap
└─ Move: Two-finger tap

MOUSE USERS:
├─ Zoom: Scroll wheel
├─ Pan: Edge scroll
├─ Select: Left click
└─ Move: Right click

TOUCH USERS:
├─ Zoom: Pinch
├─ Pan: Drag
├─ Select: Tap
└─ Move: Long press
```

Enjoy your new trackpad-optimized RTS controls! 🎉