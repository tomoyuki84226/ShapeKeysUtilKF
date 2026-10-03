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
import traceback
from ..funcs import func_separate_shapekeys
from ..funcs.utils import func_object_utils
from ..funcs import func_apply_selected_modifier


class OBJECT_OT_mizore_shapekeys_util_apply_selected_modifiers(bpy.types.Operator):
    bl_idname = "object.shapekeys_util_apply_selected_modifiers"
    bl_label = "Apply Selected Modifiers"
    bl_description = "Apply Selected Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(
            not obj.hide_viewport
            and not obj.hide_get()
            and obj.type == 'MESH'
            and obj.modifiers
            and obj.modifiers.active
            for obj in context.selected_objects
            )

    def execute(self, context):
        try:
            original_active = context.view_layer.objects.active
            original_selection = list(context.selected_objects)
            targets = [
                obj for obj in original_selection
                if not obj.hide_viewport
                and not obj.hide_get()
                and obj.type == 'MESH'
                and obj.modifiers
                and obj.modifiers.active
            ]

            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(targets, True)
            func_object_utils.set_active_object(
                original_active if original_active in targets else targets[0]
            )
            # リンクされたオブジェクトのモディファイアは適用できないので予めリンクを解除しておく
            bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True, material=False, animation=False)

            for obj in targets:
                func_apply_selected_modifier.apply_selected_modifier(obj)
            # 元の選択状態に戻す
            func_object_utils.deselect_all_objects()
            func_object_utils.select_objects(original_selection, True)
            func_object_utils.set_active_object(original_active)
            return {'FINISHED'}
        except Exception as e:
            bpy.ops.ed.undo_push(message = "Restore point")
            bpy.ops.ed.undo()
            bpy.ops.ed.undo_push(message = "Restore point")
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}


translations_dict = {
    "ja_JP": {       
        ("*", "Apply Selected Modifiers"):
            "詳細はRead-me.txtを参照。\n名前の最後が_leftまたは_rightのシェイプキーには使えません",
    },
}


def register():
    bpy.utils.register_class(OBJECT_OT_mizore_shapekeys_util_apply_selected_modifiers)
    bpy.app.translations.register(__name__, translations_dict)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mizore_shapekeys_util_apply_selected_modifiers)
    bpy.app.translations.unregister(__name__)
