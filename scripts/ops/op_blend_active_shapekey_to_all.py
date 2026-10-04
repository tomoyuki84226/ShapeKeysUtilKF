# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from bpy.props import BoolProperty, FloatProperty


class MESH_OT_shapekeys_util_blend_active_to_all(bpy.types.Operator):
    bl_idname = "mesh.shapekeys_util_blend_active_to_all"
    bl_label = "Blend Active Shape Key to All"
    bl_description = (
        "Blend the active shape key into every other shape key except Basis "
        "for the selected vertices"
    )
    bl_options = {'REGISTER', 'UNDO'}

    blend: FloatProperty(
        name="Blend",
        description="Blending factor",
        default=1.0,
        min=-1000.0,
        max=1000.0,
        soft_min=-2.0,
        soft_max=2.0,
    )

    add: BoolProperty(
        name="Add",
        description="Add rather than blend between shapes",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and obj.data.shape_keys is not None
            and len(obj.data.shape_keys.key_blocks) > 1
            and 0 <= obj.active_shape_key_index < len(obj.data.shape_keys.key_blocks)
        )

    def execute(self, context):
        obj = context.edit_object
        key_blocks = obj.data.shape_keys.key_blocks
        source_index = obj.active_shape_key_index
        source_name = key_blocks[source_index].name
        target_indices = [
            index for index in range(1, len(key_blocks))
            if index != source_index
        ]

        if not target_indices:
            self.report({'WARNING'}, "There are no other shape keys to blend into")
            return {'CANCELLED'}

        try:
            for target_index in target_indices:
                obj.active_shape_key_index = target_index
                result = bpy.ops.mesh.blend_from_shape(
                    shape=source_name,
                    blend=self.blend,
                    add=self.add,
                )
                if 'FINISHED' not in result:
                    self.report({'ERROR'}, "Failed to blend a shape key")
                    return {'CANCELLED'}
        finally:
            obj.active_shape_key_index = source_index

        self.report(
            {'INFO'},
            f'Blended "{source_name}" into {len(target_indices)} shape keys',
        )
        return {'FINISHED'}


translations_dict = {
    "ja_JP": {
        ("*", "Blend Active Shape Key to All"): "選択中のシェイプキーを全てにブレンド",
        (
            "*",
            "Blend the active shape key into every other shape key except Basis for the selected vertices",
        ): "選択頂点について、選択中のシェイプキーをBasis以外の全シェイプキーにブレンドします",
        ("*", "There are no other shape keys to blend into"): "ブレンド先のシェイプキーがありません",
        ("*", "Failed to blend a shape key"): "シェイプキーのブレンドに失敗しました",
    },
}


def register():
    bpy.utils.register_class(MESH_OT_shapekeys_util_blend_active_to_all)
    bpy.app.translations.register(__name__, translations_dict)


def unregister():
    bpy.app.translations.unregister(__name__)
    bpy.utils.unregister_class(MESH_OT_shapekeys_util_blend_active_to_all)
