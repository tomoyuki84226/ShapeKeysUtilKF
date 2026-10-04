# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

import traceback

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, path_reference_mode

from ..funcs import func_export_fbx_wrapper


_AXES = ('X', 'Y', 'Z', '-X', '-Y', '-Z')


class EXPORT_SCENE_OT_shapekeys_util_fbx(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.shapekeys_util_fbx"
    bl_label = "FBX with Evaluated Shape Keys"
    bl_description = "Export FBX while applying modifiers to shape keys"
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    use_selection: BoolProperty(
        name="Selected Objects",
        description="Export selected and visible objects only",
        default=False,
    )
    use_visible: BoolProperty(
        name="Visible Objects",
        description="Export visible objects only",
        default=False,
    )
    use_active_collection: BoolProperty(
        name="Active Collection",
        description="Export only objects from the active collection (and its children)",
        default=False,
    )
    collection: StringProperty(
        name="Source Collection",
        description="Export only objects from this collection (and its children)",
        default="",
    )
    global_scale: FloatProperty(
        name="Scale",
        description="Scale all data (Some importers do not support scaled armatures!)",
        min=0.001,
        max=1000.0,
        soft_min=0.01,
        soft_max=1000.0,
        default=1.0,
    )
    apply_unit_scale: BoolProperty(name="Apply Unit", default=True)
    apply_scale_options: EnumProperty(
        name="Apply Scalings",
        items=(
            ('FBX_SCALE_NONE', "All Local", ""),
            ('FBX_SCALE_UNITS', "FBX Units Scale", ""),
            ('FBX_SCALE_CUSTOM', "FBX Custom Scale", ""),
            ('FBX_SCALE_ALL', "FBX All", ""),
        ),
        default='FBX_SCALE_NONE',
    )
    use_space_transform: BoolProperty(name="Use Space Transform", default=True)
    bake_space_transform: BoolProperty(name="Apply Transform", default=False)
    merge_parented_meshes: BoolProperty(
        name="子のメッシュを親と統合",
        description=(
            "出力対象の子メッシュを、最上位にある出力対象のメッシュ親へ"
            "一時的に統合します"
        ),
        default=False,
    )
    axis_forward: EnumProperty(
        name="Forward",
        items=tuple((axis, f"{axis} Forward", "") for axis in _AXES),
        default='-Z',
    )
    axis_up: EnumProperty(
        name="Up",
        items=tuple((axis, f"{axis} Up", "") for axis in _AXES),
        default='Y',
    )
    object_types: EnumProperty(
        name="Object Types",
        options={'ENUM_FLAG'},
        items=(
            ('EMPTY', "Empty", ""),
            ('CAMERA', "Camera", ""),
            ('LIGHT', "Lamp", ""),
            ('ARMATURE', "Armature", ""),
            ('MESH', "Mesh", ""),
            ('OTHER', "Other", ""),
        ),
        default={'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'MESH', 'OTHER'},
    )
    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers while preserving shape keys through temporary evaluation",
        default=True,
    )
    use_mesh_modifiers_render: BoolProperty(name="Use Modifiers Render Setting", default=True)
    mesh_smooth_type: EnumProperty(
        name="Smoothing",
        items=(
            ('OFF', "Normals Only", ""),
            ('FACE', "Face", ""),
            ('EDGE', "Edge", ""),
        ),
        default='OFF',
    )
    colors_type: EnumProperty(
        name="Vertex Colors",
        items=(
            ('NONE', "None", ""),
            ('SRGB', "sRGB", ""),
            ('LINEAR', "Linear", ""),
        ),
        default='SRGB',
    )
    prioritize_active_color: BoolProperty(name="Prioritize Active Color", default=False)
    use_subsurf: BoolProperty(name="Export Subdivision Surface", default=False)
    use_mesh_edges: BoolProperty(name="Loose Edges", default=False)
    use_tspace: BoolProperty(name="Tangent Space", default=False)
    use_triangles: BoolProperty(name="Triangulate Faces", default=False)
    use_custom_props: BoolProperty(name="Custom Properties", default=False)
    add_leaf_bones: BoolProperty(name="Add Leaf Bones", default=True)
    primary_bone_axis: EnumProperty(
        name="Primary Bone Axis",
        items=tuple((axis, f"{axis} Axis", "") for axis in _AXES),
        default='Y',
    )
    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        items=tuple((axis, f"{axis} Axis", "") for axis in _AXES),
        default='X',
    )
    use_armature_deform_only: BoolProperty(name="Only Deform Bones", default=False)
    armature_nodetype: EnumProperty(
        name="Armature FBXNode Type",
        items=(
            ('NULL', "Null", ""),
            ('ROOT', "Root", ""),
            ('LIMBNODE', "LimbNode", ""),
        ),
        default='NULL',
    )
    bake_anim: BoolProperty(name="Baked Animation", default=True)
    bake_anim_use_all_bones: BoolProperty(name="Key All Bones", default=True)
    bake_anim_use_nla_strips: BoolProperty(name="NLA Strips", default=True)
    bake_anim_use_all_actions: BoolProperty(name="All Actions", default=True)
    bake_anim_force_startend_keying: BoolProperty(name="Force Start/End Keying", default=True)
    bake_anim_step: FloatProperty(
        name="Sampling Rate",
        min=0.01,
        max=100.0,
        soft_min=0.1,
        soft_max=10.0,
        default=1.0,
    )
    bake_anim_simplify_factor: FloatProperty(
        name="Simplify",
        min=0.0,
        max=100.0,
        soft_min=0.0,
        soft_max=10.0,
        default=1.0,
    )
    path_mode: path_reference_mode
    embed_textures: BoolProperty(name="Embed Textures", default=False)
    batch_mode: EnumProperty(
        name="Batch Mode",
        items=(
            ('OFF', "Off", "Active scene to file"),
            ('SCENE', "Scene", "Each scene as a file"),
            ('COLLECTION', "Collection", "Each collection as a file"),
            ('SCENE_COLLECTION', "Scene Collections", "Each collection of each scene as a file"),
            ('ACTIVE_SCENE_COLLECTION', "Active Scene Collections", "Each collection of the active scene as a file"),
        ),
        default='OFF',
    )
    use_batch_own_dir: BoolProperty(name="Batch Own Dir", default=True)
    use_metadata: BoolProperty(name="Use Metadata", default=True, options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        # Use Blender's installed FBX panel functions for the closest possible
        # visual match, including panel ordering and enabled states.
        from io_scene_fbx import (
            export_main,
            export_panel_animation,
            export_panel_armature,
            export_panel_geometry,
            export_panel_include,
            export_panel_transform,
        )

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        is_file_browser = context.space_data.type == 'FILE_BROWSER'
        export_main(layout, self, is_file_browser)
        export_panel_include(layout, self, is_file_browser)
        export_panel_transform(layout, self)
        layout.prop(self, "merge_parented_meshes")
        export_panel_geometry(layout, self)
        export_panel_armature(layout, self)
        export_panel_animation(layout, self)

    @property
    def check_extension(self):
        return self.batch_mode == 'OFF'

    def _context_objects(self, context):
        if self.use_active_collection:
            objects = context.view_layer.active_layer_collection.collection.all_objects
        elif self.collection:
            collection = bpy.data.collections.get(self.collection)
            objects = collection.all_objects if collection else ()
        else:
            objects = context.view_layer.objects

        if self.use_selection:
            objects = tuple(obj for obj in objects if obj.select_get())
        if self.use_visible:
            objects = tuple(obj for obj in objects if obj.visible_get())
        return objects

    def execute(self, context):
        if self.batch_mode != 'OFF':
            self.report({'ERROR'}, "Batch Mode is not supported by the evaluated shape-key wrapper")
            return {'CANCELLED'}

        source_objects = self._context_objects(context)
        mesh_objects = [
            obj for obj in source_objects
            if obj.type == 'MESH' and 'MESH' in self.object_types
        ]
        keywords = self.as_keywords(ignore=("filter_glob", "check_existing"))
        try:
            func_export_fbx_wrapper.export_with_temporary_meshes(
                context,
                mesh_objects,
                keywords,
                export_objects=source_objects,
            )
        except Exception as error:
            traceback.print_exc()
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported {len(mesh_objects)} evaluated mesh object(s)")
        return {'FINISHED'}


def menu_func_export(self, context):
    self.layout.operator(
        EXPORT_SCENE_OT_shapekeys_util_fbx.bl_idname,
        text="FBX with Evaluated Shape Keys (.fbx)",
    )


def register():
    bpy.utils.register_class(EXPORT_SCENE_OT_shapekeys_util_fbx)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(EXPORT_SCENE_OT_shapekeys_util_fbx)
