# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Build temporary, modifier-evaluated meshes for the stock FBX exporter."""

from array import array
from contextlib import nullcontext

import bpy

from .. import consts


def _modifier_is_exported(modifier, excluded_subsurf=None):
    """Match ShapeKeys Util's render-oriented modifier policy."""
    if modifier.type == 'ARMATURE':
        return False
    if modifier.name.startswith(consts.FORCE_KEEP_MODIFIER_PREFIX):
        return False
    if modifier == excluded_subsurf:
        return False
    return modifier.show_render


def _evaluated_coordinates(source_obj, depsgraph):
    depsgraph.update()
    evaluated_obj = source_obj.evaluated_get(depsgraph)
    evaluated_mesh = evaluated_obj.to_mesh(
        preserve_all_data_layers=False,
        depsgraph=depsgraph,
    )
    try:
        coordinates = array('f', [0.0]) * (len(evaluated_mesh.vertices) * 3)
        evaluated_mesh.vertices.foreach_get("co", coordinates)
        return coordinates
    finally:
        evaluated_obj.to_mesh_clear()


def _copy_shape_key_properties(source_key, target_key):
    target_key.value = source_key.value
    target_key.slider_min = source_key.slider_min
    target_key.slider_max = source_key.slider_max
    target_key.mute = source_key.mute
    target_key.interpolation = source_key.interpolation
    target_key.vertex_group = source_key.vertex_group


def _copy_shape_key_animation(source_keys, target_keys):
    source_animation = source_keys.animation_data
    if source_animation is None or source_animation.action is None:
        return

    target_animation = target_keys.animation_data_create()
    target_animation.action = source_animation.action


def build_evaluated_mesh(source_obj, depsgraph, apply_modifiers=True, use_subsurf=False):
    """Return a temporary mesh containing evaluated Basis and shape keys.

    Non-Armature, render-enabled modifiers are evaluated. Armature and
    ``%KEEP%`` modifiers remain unapplied so the stock exporter can preserve
    skinning and intentionally retained modifiers.
    """
    if source_obj.type != 'MESH':
        raise TypeError(f"Expected a mesh object: {source_obj.name}")

    original_mesh = source_obj.data
    original_shape_keys = original_mesh.shape_keys
    original_show_only = source_obj.show_only_shape_key
    original_active_index = source_obj.active_shape_key_index
    modifier_states = [(modifier, modifier.show_viewport) for modifier in source_obj.modifiers]
    temporary_mesh = None

    try:
        excluded_subsurf = None
        if use_subsurf:
            excluded_subsurf = next((
                modifier for modifier in reversed(source_obj.modifiers)
                if modifier.type == 'SUBSURF'
                and modifier.subdivision_type == 'CATMULL_CLARK'
                and modifier.show_render
            ), None)

        # With nothing to bake, a normal Mesh copy is both faster and more
        # faithful (it preserves the complete shape-key animation data).
        if not apply_modifiers or not any(
                _modifier_is_exported(modifier, excluded_subsurf)
                for modifier in source_obj.modifiers):
            temporary_mesh = original_mesh.copy()
            temporary_mesh.name = f"{original_mesh.name}__SKU_FBX_TEMP__"
            return temporary_mesh

        # Python receives the viewport dependency graph. Make it follow the
        # render-oriented policy used by ShapeKeys Util while evaluating.
        for modifier, _show_viewport in modifier_states:
            modifier.show_viewport = _modifier_is_exported(modifier, excluded_subsurf)

        # Evaluate the raw active key instead of the current shape-key mix.
        source_obj.show_only_shape_key = original_shape_keys is not None
        source_obj.active_shape_key_index = 0
        depsgraph.update()

        evaluated_obj = source_obj.evaluated_get(depsgraph)
        temporary_mesh = bpy.data.meshes.new_from_object(
            evaluated_obj,
            preserve_all_data_layers=True,
            depsgraph=depsgraph,
        )
        temporary_mesh.name = f"{original_mesh.name}__SKU_FBX_TEMP__"
        base_vertex_count = len(temporary_mesh.vertices)

        if original_shape_keys is None or len(original_shape_keys.key_blocks) <= 1:
            return temporary_mesh

        # shape_key_add needs an Object, so briefly attach the evaluated mesh.
        source_obj.data = temporary_mesh
        try:
            source_blocks = list(original_shape_keys.key_blocks)
            target_blocks = []

            basis = source_obj.shape_key_add(name=source_blocks[0].name, from_mix=False)
            _copy_shape_key_properties(source_blocks[0], basis)
            target_blocks.append(basis)

            source_obj.data = original_mesh
            for index, source_key in enumerate(source_blocks[1:], start=1):
                source_obj.active_shape_key_index = index
                coordinates = _evaluated_coordinates(source_obj, depsgraph)
                evaluated_count = len(coordinates) // 3
                if evaluated_count != base_vertex_count:
                    raise ValueError(
                        f"{source_obj.name}: shape key '{source_key.name}' changes the evaluated "
                        f"vertex count ({base_vertex_count} -> {evaluated_count})"
                    )

                source_obj.data = temporary_mesh
                target_key = source_obj.shape_key_add(name=source_key.name, from_mix=False)
                target_key.data.foreach_set("co", coordinates)
                _copy_shape_key_properties(source_key, target_key)
                target_blocks.append(target_key)
                source_obj.data = original_mesh

            source_obj.data = temporary_mesh
            target_key_data = temporary_mesh.shape_keys
            target_key_data.use_relative = original_shape_keys.use_relative
            target_key_data.eval_time = original_shape_keys.eval_time

            for index, source_key in enumerate(source_blocks):
                try:
                    relative_index = source_blocks.index(source_key.relative_key)
                except ValueError:
                    relative_index = 0
                target_blocks[index].relative_key = target_blocks[relative_index]

            _copy_shape_key_animation(original_shape_keys, target_key_data)
        finally:
            source_obj.data = original_mesh

        return temporary_mesh
    except Exception:
        if temporary_mesh is not None and temporary_mesh.users == 0:
            bpy.data.meshes.remove(temporary_mesh)
        raise
    finally:
        source_obj.data = original_mesh
        source_obj.show_only_shape_key = original_show_only
        source_obj.active_shape_key_index = original_active_index
        for modifier, show_viewport in modifier_states:
            modifier.show_viewport = show_viewport
        depsgraph.update()


def _parented_mesh_groups(mesh_objects):
    """Return exported mesh hierarchies keyed by their highest mesh parent."""
    mesh_objects = list(mesh_objects)
    exported_meshes = set(mesh_objects)
    groups = {}

    for mesh_object in mesh_objects:
        root = mesh_object
        while root.parent in exported_meshes:
            root = root.parent
        groups.setdefault(root, []).append(mesh_object)

    return [
        [root] + [member for member in members if member != root]
        for root, members in groups.items()
        if len(members) > 1
    ]


def _join_temporary_objects(context, mesh_objects):
    """Join copies of evaluated mesh objects and return the resulting mesh."""
    temporary_collection = bpy.data.collections.new("__SKU_FBX_MERGE__")
    context.scene.collection.children.link(temporary_collection)
    copies = []
    copy_names = []
    copied_meshes = []

    try:
        for source_obj in mesh_objects:
            object_copy = source_obj.copy()
            mesh_copy = source_obj.data.copy()
            object_copy.data = mesh_copy
            object_copy.animation_data_clear()
            object_copy.modifiers.clear()
            temporary_collection.objects.link(object_copy)
            object_copy.matrix_world = source_obj.matrix_world
            copies.append(object_copy)
            copy_names.append(object_copy.name)
            copied_meshes.append(mesh_copy)

        active_copy = copies[0]
        override = {
            "active_object": active_copy,
            "object": active_copy,
            "selected_objects": copies,
            "selected_editable_objects": copies,
        }
        with context.temp_override(**override):
            result = bpy.ops.object.join()
        if 'FINISHED' not in result:
            raise RuntimeError(f"Could not merge mesh hierarchy rooted at {mesh_objects[0].name}")

        merged_mesh = active_copy.data
        merged_mesh.name = f"{mesh_objects[0].data.name}__SKU_FBX_MERGED__"
        return merged_mesh
    except Exception:
        merged_mesh = None
        raise
    finally:
        for object_name in copy_names:
            object_copy = bpy.data.objects.get(object_name)
            if object_copy is not None:
                bpy.data.objects.remove(object_copy, do_unlink=True)
        for mesh_copy in copied_meshes:
            if mesh_copy != merged_mesh and mesh_copy.users == 0:
                bpy.data.meshes.remove(mesh_copy)
        bpy.data.collections.remove(temporary_collection)


def export_with_temporary_meshes(
        context, mesh_objects, export_keywords, export_objects=None):
    """Swap evaluated meshes in only for the duration of stock FBX export."""
    depsgraph = context.evaluated_depsgraph_get()
    prepared = []
    merged = []
    stock_keywords = export_keywords.copy()
    apply_modifiers = stock_keywords.pop("use_mesh_modifiers", True)
    stock_keywords.pop("use_mesh_modifiers_render", None)
    merge_parented_meshes = stock_keywords.pop("merge_parented_meshes", False)
    use_subsurf = stock_keywords.get("use_subsurf", False)

    try:
        # Build all meshes before swapping so cross-object modifiers always see
        # the original scene.
        for source_obj in mesh_objects:
            temporary_mesh = build_evaluated_mesh(
                source_obj,
                depsgraph,
                apply_modifiers=apply_modifiers,
                use_subsurf=use_subsurf,
            )
            prepared.append((source_obj, source_obj.data, temporary_mesh))

        for source_obj, _original_mesh, temporary_mesh in prepared:
            source_obj.data = temporary_mesh

        excluded_objects = set()
        if merge_parented_meshes:
            for mesh_group in _parented_mesh_groups(mesh_objects):
                root_object = mesh_group[0]
                merged_mesh = _join_temporary_objects(context, mesh_group)
                root_object.data = merged_mesh
                merged.append((root_object, merged_mesh))
                excluded_objects.update(mesh_group[1:])

        export_context = nullcontext()
        if merge_parented_meshes and export_objects is not None:
            selected_objects = [
                obj for obj in export_objects
                if obj not in excluded_objects
            ]
            stock_keywords["use_selection"] = True
            # ``source_collection + use_selection`` makes the stock exporter
            # read each object's real selection flag instead of the overridden
            # selected_objects context. The caller already resolved the exact
            # source collection, so export that resolved list directly.
            stock_keywords["use_active_collection"] = False
            stock_keywords["collection"] = ""
            export_context = context.temp_override(selected_objects=selected_objects)

        with export_context:
            result = bpy.ops.export_scene.fbx(
                **stock_keywords,
                use_mesh_modifiers=False,
            )
        if 'FINISHED' not in result:
            raise RuntimeError("The standard FBX exporter did not finish")
        return result
    finally:
        for source_obj, original_mesh, _temporary_mesh in reversed(prepared):
            source_obj.data = original_mesh
        for _root_object, merged_mesh in merged:
            if merged_mesh.users == 0:
                bpy.data.meshes.remove(merged_mesh)
        for _source_obj, _original_mesh, temporary_mesh in prepared:
            if temporary_mesh.users == 0:
                bpy.data.meshes.remove(temporary_mesh)

