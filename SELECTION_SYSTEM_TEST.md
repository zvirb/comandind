# 🎮 Selection System Testing Guide

## Quick Test Instructions

Open your browser to: **http://localhost:3004**

### ✅ Test Checklist

1. **Basic Selection**
   - [ ] Click on a unit (green box should appear)
   - [ ] Click on empty space (selection should clear)
   - [ ] Click on different unit (selection should switch)

2. **Box Selection**
   - [ ] Click and drag to create selection box
   - [ ] Release to select all units in box
   - [ ] Green selection boxes should appear on all selected units

3. **Multi-Selection**
   - [ ] Hold Shift + Click to add units to selection
   - [ ] Hold Shift + Drag to add more units
   - [ ] Hold Ctrl + Click to toggle individual units

4. **Movement Commands**
   - [ ] Select one or more units
   - [ ] Right-click anywhere on the map
   - [ ] Units should move to that location
   - [ ] Green circle marker should appear at destination

5. **Control Groups**
   - [ ] Select some units
   - [ ] Press Ctrl+1 to create control group 1
   - [ ] Click elsewhere to deselect
   - [ ] Press 1 to reselect the group

6. **Keyboard Shortcuts**
   - [ ] Ctrl+A: Select all units
   - [ ] Escape: Clear selection
   - [ ] Delete: Remove selected units (testing)

### 🔍 Visual Indicators

- **Green Box**: Unit is selected
- **Health Bar**: Shows unit health (green/yellow/red)
- **Green Circle**: Movement command marker

### 🐛 Troubleshooting

If selection isn't working:

1. **Check Console** (F12 → Console tab)
   - Look for red error messages
   - Units should log creation messages

2. **Verify Units Exist**
   - You should see 6 units and 4 buildings on screen
   - Units: 3 GDI (top), 3 NOD (middle)
   - Buildings: 2 GDI, 2 NOD

3. **Test Mouse Events**
   - Right-click should NOT show context menu
   - Left-click and drag should show green selection box

### 📊 Expected Console Output

When working correctly, you should see:
```
🎮 Creating C&C test units with ECS...
Created GDI unit entity: Medium Tank (ID: 1)
Created GDI unit entity: Mammoth Tank (ID: 2)
Created GDI unit entity: Orca (ID: 3)
Created NOD unit entity: Light Tank (ID: 4)
Created NOD unit entity: Stealth Tank (ID: 5)
Created NOD unit entity: Recon Bike (ID: 6)
...
```

### 🎯 Current Status

The selection system has been fully implemented with:
- ✅ SelectableComponent for all units/buildings
- ✅ CommandComponent for orders
- ✅ SelectionSystem for managing selection
- ✅ Visual feedback (selection boxes, health bars)
- ✅ Mouse and keyboard input handling
- ✅ Movement commands

The game should now have full RTS-style unit selection and control!