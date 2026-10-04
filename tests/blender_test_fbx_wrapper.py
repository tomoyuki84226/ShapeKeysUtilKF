"""Run with Blender 4.4+: blender --background --factory-startup --python this_file.py"""

import os
import sys

import bpy


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(PROJECT_ROOT))

import ShapeKeysUtilKF  # noqa: E402
from ShapeKeysUtilKF.scripts.funcs import func_export_fbx_wrapper  # noqa: E402


def make_test_object():
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = "EvaluatedShapeKeysTest"
    basis = obj.shape_key_add(name="Basis", from_mix=False)
    smile = obj.shape_key_add(name="Smile", from_mix=False)
    smile.data[0].co.x += 0.5
    smile.slider_min = -0.5
    smile.slider_max = 1.5
    smile.relative_key = basis

    modifier = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    modifier.levels = 1
    modifier.render_levels = 1
    return obj


def main():
    ShapeKeysUtilKF.register()
    stock_properties = set(bpy.ops.export_scene.fbx.get_rna_type().properties.keys())
    wrapper_properties = set(bpy.ops.export_scene.shapekeys_util_fbx.get_rna_type().properties.keys())
    missing_properties = stock_properties - wrapper_properties
    assert not missing_properties, f"Missing stock FBX properties: {sorted(missing_properties)}"

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    source_obj = make_test_object()
    bpy.ops.mesh.primitive_plane_add(location=(3.0, 0.0, 0.0))
    all_objects_target = bpy.context.object
    all_objects_target.name = "AllObjectsTarget"
    all_objects_target.modifiers.new(name="Solidify", type='SOLIDIFY').thickness = 0.1
    all_objects_target.parent = source_obj
    all_objects_target.select_set(False)
    source_obj.select_set(True)
    bpy.context.view_layer.objects.active = source_obj

    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = None
    assert bpy.ops.export_scene.shapekeys_util_fbx.poll()
    source_obj.select_set(True)
    bpy.context.view_layer.objects.active = source_obj
    original_mesh = source_obj.data
    original_active_index = source_obj.active_shape_key_index

    merge_groups = func_export_fbx_wrapper._parented_mesh_groups(
        [all_objects_target, source_obj]
    )
    assert merge_groups == [[source_obj, all_objects_target]]

    depsgraph = bpy.context.evaluated_depsgraph_get()
    control_mesh = func_export_fbx_wrapper.build_evaluated_mesh(
        source_obj,
        depsgraph,
        apply_modifiers=False,
    )
    try:
        assert len(control_mesh.vertices) == len(original_mesh.vertices)
    finally:
        bpy.data.meshes.remove(control_mesh)

    subdivision_control_mesh = func_export_fbx_wrapper.build_evaluated_mesh(
        source_obj,
        depsgraph,
        use_subsurf=True,
    )
    try:
        assert len(subdivision_control_mesh.vertices) == len(original_mesh.vertices)
    finally:
        bpy.data.meshes.remove(subdivision_control_mesh)

    temporary_mesh = func_export_fbx_wrapper.build_evaluated_mesh(source_obj, depsgraph)
    try:
        assert source_obj.data == original_mesh
        assert len(temporary_mesh.vertices) > len(original_mesh.vertices)
        assert temporary_mesh.shape_keys is not None
        assert list(temporary_mesh.shape_keys.key_blocks.keys()) == ["Basis", "Smile"]
        assert temporary_mesh.shape_keys.key_blocks["Smile"].slider_min == -0.5
        assert temporary_mesh.shape_keys.key_blocks["Smile"].slider_max == 1.5
    finally:
        bpy.data.meshes.remove(temporary_mesh)

    output_path = os.path.join(PROJECT_ROOT, "tests", "wrapper_test.fbx")
    result = bpy.ops.export_scene.shapekeys_util_fbx(
        filepath=output_path,
        bake_anim=False,
        add_leaf_bones=False,
    )
    assert result == {'FINISHED'}
    assert os.path.isfile(output_path)
    assert source_obj.data == original_mesh
    assert source_obj.active_shape_key_index == original_active_index
    assert len(source_obj.data.vertices) == 8
    assert len(source_obj.data.shape_keys.key_blocks) == 2

    merged_output_path = os.path.join(PROJECT_ROOT, "tests", "wrapper_merged_test.fbx")
    result = bpy.ops.export_scene.shapekeys_util_fbx(
        filepath=merged_output_path,
        bake_anim=False,
        add_leaf_bones=False,
        merge_parented_meshes=True,
    )
    assert result == {'FINISHED'}
    assert os.path.isfile(merged_output_path)
    assert source_obj.data == original_mesh
    assert all_objects_target.parent == source_obj
    assert len(bpy.data.objects) == 2

    mesh_count = len(bpy.data.meshes)
    try:
        func_export_fbx_wrapper.export_with_temporary_meshes(
            bpy.context,
            [source_obj, all_objects_target],
            {
                "filepath": output_path,
                "merge_parented_meshes": True,
                "not_a_real_fbx_option": True,
            },
            export_objects=[source_obj, all_objects_target],
        )
    except TypeError:
        pass
    else:
        raise AssertionError("Expected the stock FBX exporter to reject an invalid option")
    assert source_obj.data == original_mesh
    assert len(bpy.data.meshes) == mesh_count
    assert len(bpy.data.objects) == 2

    source_obj.modifiers.clear()
    copied_mesh = func_export_fbx_wrapper.build_evaluated_mesh(source_obj, depsgraph)
    try:
        assert copied_mesh != original_mesh
        assert copied_mesh.shape_keys is not None
        assert list(copied_mesh.shape_keys.key_blocks.keys()) == ["Basis", "Smile"]
    finally:
        bpy.data.meshes.remove(copied_mesh)

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.fbx(filepath=output_path)
    imported_meshes = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    assert len(imported_meshes) == 2
    imported = next(obj for obj in imported_meshes if obj.name == "EvaluatedShapeKeysTest")
    imported_all_target = next(obj for obj in imported_meshes if obj.name == "AllObjectsTarget")
    assert len(imported_all_target.data.vertices) > 4
    assert len(imported.data.vertices) > 8
    assert imported.data.shape_keys is not None
    assert list(imported.data.shape_keys.key_blocks.keys()) == ["Basis", "Smile"]
    imported_basis = imported.data.shape_keys.key_blocks["Basis"]
    imported_smile = imported.data.shape_keys.key_blocks["Smile"]
    imported_vertex_count = len(imported.data.vertices)
    assert any(
        (shape_vertex.co - basis_vertex.co).length > 0.001
        for basis_vertex, shape_vertex in zip(imported_basis.data, imported_smile.data)
    )

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.fbx(filepath=merged_output_path)
    merged_imported_meshes = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    assert len(merged_imported_meshes) == 1
    merged_imported = merged_imported_meshes[0]
    assert merged_imported.name == "EvaluatedShapeKeysTest"
    assert len(merged_imported.data.vertices) > imported_vertex_count
    assert merged_imported.data.shape_keys is not None
    assert list(merged_imported.data.shape_keys.key_blocks.keys()) == ["Basis", "Smile"]
    print("ShapeKeysUtilKF FBX wrapper test passed")


if __name__ == "__main__":
    main()

