"""Run with Blender 4.4+: blender --background --factory-startup --python this_file.py"""

import sys
from pathlib import Path

import bpy


ADDON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON_DIR.parent))

import ShapeKeysUtilKF  # noqa: E402


def assert_vector(actual, expected):
    assert tuple(round(value, 6) for value in actual) == expected


def create_object():
    mesh = bpy.data.meshes.new("BlendAllMesh")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (2, 0, 0)], [], [])
    obj = bpy.data.objects.new("BlendAllObject", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    basis = obj.shape_key_add(name="Basis", from_mix=False)
    source = obj.shape_key_add(name="Source", from_mix=False)
    target_a = obj.shape_key_add(name="Target A", from_mix=False)
    target_b = obj.shape_key_add(name="Target B", from_mix=False)

    for point in source.data:
        point.co.y = 4.0
    for point in target_a.data:
        point.co.z = 2.0
    for point in target_b.data:
        point.co.y = -2.0

    return obj, basis, source, target_a, target_b


def main():
    ShapeKeysUtilKF.register()
    obj, basis, source, target_a, target_b = create_object()
    obj.active_shape_key_index = 1

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.vertices[0].select = True
    obj.data.vertices[2].select = True
    bpy.ops.object.mode_set(mode='EDIT')

    result = bpy.ops.mesh.shapekeys_util_blend_active_to_all(
        blend=0.25,
        add=False,
    )
    assert result == {'FINISHED'}
    assert obj.mode == 'EDIT'
    assert obj.active_shape_key_index == 1

    bpy.ops.object.mode_set(mode='OBJECT')

    # Basis and the source key must stay untouched.
    assert_vector(basis.data[0].co, (0.0, 0.0, 0.0))
    assert_vector(source.data[0].co, (0.0, 4.0, 0.0))

    # Selected vertices are blended using the same interpolation as Blender's
    # Blend From Shape operator.
    assert_vector(target_a.data[0].co, (0.0, 1.0, 1.5))
    assert_vector(target_b.data[2].co, (2.0, -0.5, 0.0))

    # Unselected vertices must not be changed.
    assert_vector(target_a.data[1].co, (1.0, 0.0, 2.0))
    assert_vector(target_b.data[1].co, (1.0, -2.0, 0.0))

    print("Blend active shape key to all test passed")


if __name__ == "__main__":
    main()
