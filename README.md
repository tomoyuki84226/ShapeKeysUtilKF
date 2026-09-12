# ShapeKeysUtilKF

## Introduction

[日本語](README.ja.md)

ShapeKeysUtilKF is a Blender add-on that lets you apply modifiers to objects that have shape keys.

Based on an add-on originally created by [Mizore Nekoyanagi](https://twitter.com/sleetcat123), this version has been updated to support Blender 4.3 and later.

[Download the add-on here](https://github.com/tomoyuki84226/ShapeKeysUtilKF/releases)

---

## Important Notice (1)

Some features of this add-on can take a long time (several seconds or more) when used on objects with many shape keys.  
The current version of the add-on does not allow you to cancel an operation once it has started. If you absolutely need to stop it, you will have to force Blender to quit.  
Blender may also occasionally crash while an operation is in progress. As a temporary workaround, retrying the operation a few times may allow it to complete without crashing.  
For these reasons, we recommend saving your work and creating a backup in a separate file before running any command.

## Important Notice (2)

Blender may enter a "Not Responding" state during time-consuming operations, but the operation is still running normally.  
Please wait for it to finish.

(You can monitor the progress by opening the log window via **Window → Toggle System Console** before starting the operation.)

## Features

### Apply Modifiers

`Right-click in Object Mode → ShapeKeys Util → Apply Modifiers`

Applies all modifiers except Armature modifiers.

- Prefixing a modifier's name with `%A%` allows an Armature modifier to be applied as well.

- Prefixing a modifier's name with `%AS%` applies the modifier as a shape key (**Apply as Shape Key**). This is useful for creating shape keys with Lattice or Armature modifiers. The `%AS%` prefix is removed from the name when the modifier is applied as a shape key. Be careful with modifiers such as Mirror that may change the number of vertices.

Modifiers that are disabled for rendering (those whose camera icon is turned off in the modifier list) are not applied.

This feature can be used even when the object has shape keys.

**Note:** This operation may take some time.

**Caution:**  
The operation cannot be completed if any shape key has a different vertex count after the modifiers are applied.  
In that case, the error message will show the name and vertex count of the shape key causing the problem. Use that information to correct it.  
(If an error occurs, we recommend pressing Ctrl+Z to undo the operation.)  
(The Merge option of a Mirror modifier or a Boolean modifier may cause this issue.)

---

If you suspect that a Mirror modifier is causing the issue, try the following:

1. Change the Mirror modifier's **Merge Limit** from the default 1 mm to a smaller value, such as 0.01 mm. Setting it to 0 appears to disable vertex merging entirely.

2. If that does not resolve the issue, move the vertices in the problematic shape key slightly away from the mirror boundary.

3. If the issue still persists, clear the **Merge** checkbox in the Mirror modifier, run **Apply Modifiers**, and then merge duplicate vertices manually.

---

- Tool settings

  - **Duplicate**  
    When enabled, the operation is performed on a copy of the target object.

  - **Remove NonRender**  
    When enabled, modifiers that are disabled for rendering are removed.  
    (Disabled for rendering means that the camera icon is turned off in the modifier list.)

### Separate Objects

`Right-click in Object Mode → ShapeKeys Util → Separate Objects`

Separates each shape key into its own object.  
**Note:** This operation may take some time.

- Settings

  - **Duplicate**  
    When enabled, the original object is kept before separation.

  - **Apply Modifiers**  
    When enabled, the object's modifiers are applied after separation.

  - **Remove NonRender**  
    When enabled together with **Apply Modifiers**, modifiers that are disabled for rendering are removed.  
    (Disabled for rendering means that the camera icon is turned off in the modifier list.)

### Copy Shapekeys

`Right-click in Object Mode → ShapeKeys Util → Copy Shapekeys`

Copies the active object's shape to the other selected objects using `bpy.ops.object.join_shapes()`.

### Side of Active from Point

`Right-click in Edit Mode → ShapeKeys Util → Side of Active from Point`

This feature was created as a by-product of developing the add-on.  
It runs **Side of Active** using the specified coordinates as the reference point.

- Settings

  - **Point**  
    The coordinates used as the reference point.

## Add-on Preferences

These settings can be changed in the add-on installation/preferences screen.

- **Wait Interval**  
  Sets the interval between wait operations used during certain processes.  
  Increasing this value can reduce processing time when there are many shape keys, but it also increases CPU load.

- **Wait Sleep**  
  Sets the duration of wait operations used during certain processes.  
  Decreasing this value can reduce processing time when there are many shape keys, but it also increases CPU load.  
  If the additional load does not cause problems on your system, lowering this value may shorten the processing time.

## Troubleshooting

This add-on is built using Blender's standard API. If a problem occurs, immediately using **Undo (Ctrl+Z)** should restore the state from before the add-on operation was run.  
If you saved immediately before using the feature, reloading the file is a more reliable way to restore your data.

## Contact

If you send feature requests or details about any problems you encounter to the contact below, the information may help with future fixes.

[Kisaragi Fumm on X](https://x.com/kisaragiz84)
