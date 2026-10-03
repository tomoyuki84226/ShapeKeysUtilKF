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
import bmesh
import time
from bpy.props import *

bl_info = {
    "name" : "ShapeKeys Util KF",
    "author" : "kisaragiz84@X sleetcat123@Twitter",
    "version" : (3,0,1),
    "blender" : (4, 3, 0),
    "location": "",
    "description" : "",
    "category" : "Object"
}

# Create Left and Right Shape Keys の自動判定で使うやつ
ENABLE_DUPLICATE_TAG="%D%"
ENABLE_SORT_TAG="%S%"

# Apply Modifier用
APPLY_AS_SHAPEKEY_NAME="%AS%" # モディファイア名が%AS%で始まっているならApply as shapekey

### Func - Version Compatible ###
def is_v2_80_later():
    ver = bpy.app.version
    return (ver[0]==2 and 80 <= ver[1]) or (2 < ver[0])

def select_object(obj, value=True):
    if is_v2_80_later()==True:
        obj.select_set(value)
    else:
        obj.select=value

def select_objects(objects, value=True):
    for obj in objects:
        select_object(obj, value)

def get_active_object():
    if is_v2_80_later()==True:
        return bpy.context.view_layer.objects.active
    else:
        return bpy.context.scene.objects.active

def set_active_object(obj):
    if is_v2_80_later()==True:
        bpy.context.view_layer.objects.active=obj
    else:
        bpy.context.scene.objects.active=obj

def hide_object(obj, value=True):
    if is_v2_80_later()==True:
        obj.hide_viewport = value
    else:
        obj.hide = value

def set_object_name(obj, name):
    obj.name=name
    if obj.data:
        obj.data.name=name

def select_axis(mode='POSITIVE', axis='X', threshold=0.0001):
    if is_v2_80_later()==True:
        if mode=='POSITIVE':
            mode='POS'
        elif mode=='NEGATIVE':
            mode='NEG'
        elif mode=='ALIGNED':
            mode='ALIGN'
        bpy.ops.mesh.select_axis(sign=mode, axis=axis, threshold=threshold)
    else:
        axis+='_AXIS'
        bpy.ops.mesh.select_axis(mode=mode, axis=axis, threshold=threshold)

def get_addon_prefs():
    if is_v2_80_later()==True:
        return bpy.context.preferences.addons[__name__].preferences
    else:
        return bpy.context.user_preferences.addons[__name__].preferences

### Translation ###
# Blenderのアドオン翻訳方法がよくわかんなかったから雰囲気で実装

def get_use_translate_tooltips():
    if is_v2_80_later()==True:
        return bpy.context.preferences.view.use_translate_tooltips
    else:
        return bpy.context.user_preferences.system.use_translate_tooltips

def get_use_translate_interface():
    if is_v2_80_later()==True:
        return bpy.context.preferences.view.use_translate_interface
    else:
        return bpy.context.user_preferences.system.use_translate_interface

def get_interface_text(key):
    locale = bpy.app.translations.locale
    if get_use_translate_interface()==True and locale in translation_dict:
        return translation_dict[locale][key]
    else:
        return translation_dict["en_US"][key]

def get_tooltips_text(key):
    locale = bpy.app.translations.locale
    if get_use_translate_tooltips()==True and locale in translation_dict:
        return translation_dict[locale][key]
    else:
        return translation_dict["en_US"][key]

### translation_dict ###
translation_dict = {
    "en_US" : {
            "object.shapekeys_util_apply_modifiers_desc" : "Apply all modifiers except for Armature.\nCan use even if has a shape key.\nWarning: It may take a while",
            "object.shapekeys_util_separateobj_desc" : "Separate objects for each shape keys.\nWarning: It may take a while",
            
            "object.shapekeys_util_apply_modifiers_duplicate" : "Execute the function on the copied object",
            "object.shapekeys_util_separateobj_duplicate" : "Execute the function on the copied object",
            "object.shapekeys_util_separateobj_apply_modifiers" : "Apply modifiers after separation",
            
            "remove_nonrender" : "A non-render modifier will be removed.",
            "verts_count_difference" : "Warn: vertices count has different:\n[{0}]({2}), [{1}]({3})",
        },
    "ja_JP" : {
            "object.shapekeys_util_apply_modifiers_desc" : "Armature以外の全モディファイアを適用します。\nシェイプキーがあっても使用できます。\n注意：少し時間がかかります",
            "object.shapekeys_util_separateobj_desc" : "シェイプキーをそれぞれ別オブジェクトにします。\n注意：少し時間がかかります",
             
            "object.shapekeys_util_apply_modifiers_duplicate" : "対象オブジェクトのコピーに対して処理を行います",
            "object.shapekeys_util_separateobj_duplicate" : "分割前のオブジェクトを残します",
            "object.shapekeys_util_separateobj_apply_modifiers" : "分割後にオブジェクトのモディファイアを適用します",
            
            "remove_nonrender" : "レンダリング無効化状態のモディファイア\n（モディファイア一覧でカメラアイコンが押されていない）\nを削除します。",
            "verts_count_difference" : "シェイプキーの頂点数が異なっているため処理を実行できませんでした。\nミラーモディファイアの\"結合\"で他より多くの頂点が結合されてしまっている、などの原因が考えられます。\n[{0}]({2}), [{1}]({3})",
        },
}

### Data ###
### Func ###
# オブジェクトのモディファイアを適用
def apply_modifiers(remove_nonrender=True):
    obj = get_active_object()
    
    print("Apply Modifiers: ["+obj.name+"]")
    # Operators below can remove modifiers; iterate over a stable snapshot.
    for modifier in list(obj.modifiers):
        if modifier.show_render == False:
            # モディファイアがレンダリング対象ではない（モディファイア一覧のカメラアイコンが押されていない）なら無視
            if remove_nonrender==True:
                bpy.ops.object.modifier_remove(modifier=modifier.name)
            continue
        
        if modifier.name.startswith(APPLY_AS_SHAPEKEY_NAME):
            # ここではApply as shapekeyさせたくない
            print("ERROR: apply_as_shapekey")
            bpy.ops.object.modifier_remove(modifier=modifier.name)
        elif modifier.name.startswith("%A%") or modifier.type != 'ARMATURE':
            # 対象モディファイアが処理対象外モディファイアでないなら
            # または、モディファイアの名前欄が%A%で始まっているなら
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            except RuntimeError:
                # 無効なModifier（対象オブジェクトが指定されていないなどの状態）は適用しない
                print("!!! Apply failed !!!: [{0}]".format(modifier.name))
            else:
                try:
                    # なんかここだけUnicodeEncodeErrorが出たり出なかったりする。なんで……？
                    print("Apply: [{0}]".format(modifier.name))
                except UnicodeDecodeError:
                    print("Apply")
    print("Finish Apply Modifiers: [{0}]".format(obj.name))

def apply_as_shapekey(modifier):
    try:
        # 名前の文字列から%AS%を削除する
        modifier.name=modifier.name[len(APPLY_AS_SHAPEKEY_NAME):len(modifier.name)]
        # Apply As Shape
        bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier=modifier.name)
    except RuntimeError:
        # 無効なModifier（対象オブジェクトが指定されていないなどの状態）は適用しない
        print("!!! Apply as shapekey failed !!!: [{0}]".format(modifier.name))
    else:
        try:
            print("Apply as shapekey: [{0}]".format(modifier.name))
        except UnicodeDecodeError:
            print("Apply as shapekey")

def apply_modifiers_with_shapekeys(self, source_obj, duplicate, remove_nonrender=True):
    bpy.ops.object.select_all(action='DESELECT')
    select_object(source_obj, True)
    set_active_object(source_obj)

    # Apply as shapekey用モディファイアのインデックスを検索
    apply_as_shape_index=-1
    apply_as_shape_modifier=None
    for i, modifier in enumerate(source_obj.modifiers):
        if modifier.name.startswith(APPLY_AS_SHAPEKEY_NAME):
            apply_as_shape_index=i
            apply_as_shape_modifier=modifier
            break
    if apply_as_shape_index==0:
        # Apply as shapekey用のモディファイアが一番上にあったらApply as shapekeyを実行
        print("apply_as_shapekeyB")
        apply_as_shapekey(apply_as_shape_modifier)
        # 関数を再実行して終了
        return apply_modifiers_with_shapekeys(self, source_obj, duplicate, remove_nonrender)
    elif apply_as_shape_index!=-1:
        # 2番目以降にApply as shape用のモディファイアがあったら
        # 一時オブジェクトを作成
        bpy.ops.object.duplicate()
        tempobj=get_active_object()
        select_object(tempobj, True)
        set_active_object(source_obj)
        # モディファイアを一時オブジェクトにコピー
        bpy.ops.object.make_links_data(type='MODIFIERS')

        # Apply as shapekeyとそれよりあとのモディファイアを削除
        for modifier in list(source_obj.modifiers)[apply_as_shape_index:]:
            bpy.ops.object.modifier_remove(modifier=modifier.name)

        # 関数を再実行
        success=apply_modifiers_with_shapekeys(self, source_obj, duplicate, remove_nonrender)
        if success==False:
            # 処理に失敗したら処理前のデータを復元して終了
            select_object(source_obj, True)
            set_active_object(tempobj)
            bpy.ops.object.make_links_data(type='OBDATA')
            bpy.ops.object.make_links_data(type='MODIFIERS')
            return False

        # 削除していたモディファイアを一時オブジェクトから復元
        select_object(source_obj, True)
        set_active_object(tempobj)
        bpy.ops.object.make_links_data(type='MODIFIERS')
        set_active_object(source_obj)
        # 適用済みのモディファイアを削除
        for modifier in list(source_obj.modifiers)[:apply_as_shape_index]:
            bpy.ops.object.modifier_remove(modifier=modifier.name)

        # 一時オブジェクトを削除
        select_object(source_obj, False)
        select_object(tempobj, True)
        bpy.ops.object.delete()
        select_object(source_obj, True)
        set_active_object(source_obj)

        # 関数を再実行して終了
        return apply_modifiers_with_shapekeys(self, source_obj, duplicate, remove_nonrender)

    if source_obj.data.shape_keys==None or len(source_obj.data.shape_keys.key_blocks)==0:
        # シェイプキーがなければモディファイア適用処理だけ実行
        apply_modifiers(remove_nonrender=remove_nonrender)
        if duplicate == True:
            bpy.ops.object.duplicate()
        return True
    
    bpy.ops.object.duplicate()
    source_obj_dup=get_active_object()
    select_object(source_obj_dup, False)
    select_object(source_obj, True)
    set_active_object(source_obj)
    
    # シェイプキーの名前と数値を記憶
    active_shape_key_index = source_obj.active_shape_key_index
    shapekey_name_and_values = []
    for shapekey in source_obj.data.shape_keys.key_blocks:
        shapekey_name_and_values.append((shapekey.name, shapekey.value))
    
    # シェイプキーをそれぞれ別オブジェクトにしてモディファイア適用
    separated_objects = separate_shapekeys(duplicate=False, enable_apply_modifiers=True, remove_nonrender=remove_nonrender)
    
    prev_obj_name=separated_objects[0].name
    prev_vert_count=len(separated_objects[0].data.vertices)
    
    shape_objects=[]
    
    # オブジェクトを1つにまとめなおす
    select_object(source_obj, True)
    set_active_object(source_obj)
    for obj in separated_objects:
        # 前回のシェイプキーと頂点数が違ったら警告して処理を取り消し
        vert_count=len(obj.data.vertices)
        if vert_count != prev_vert_count:
            warn=get_tooltips_text("verts_count_difference").format(prev_obj_name, obj.name, prev_vert_count, vert_count)
            if self:
                self.report({'ERROR'}, warn)
            print(warn)
            # 処理中オブジェクトを削除
            select_object(source_obj, True)
            for child in source_obj.children:
                select_object(child, True)
            bpy.ops.object.delete()
            select_object(source_obj_dup, True)
            set_active_object(source_obj_dup)
            return False
        
        prev_vert_count=vert_count
        prev_obj_name=obj.name
        
        # 一気にjoin_shapesするとシェイプキーの順番がおかしくなるので1つずつ
        select_object(obj, True)
        bpy.ops.object.join_shapes()
        select_object(obj, False)
        
        shape_objects.append(obj)
    
    select_object(source_obj, False)
    # 使い終わったオブジェクトを削除
    select_objects(shape_objects, True)
    bpy.ops.object.delete()
    
    if duplicate==False:
        # 処理が正常に終了したら複製オブジェクトを削除する
        select_object(source_obj_dup, True)
        bpy.ops.object.delete()
    
    # シェイプキーの名前と数値を復元
    source_obj.active_shape_key_index = active_shape_key_index
    for i, shapekey in enumerate(source_obj.data.shape_keys.key_blocks):
        shapekey.name = shapekey_name_and_values[i][0]
        shapekey.value = shapekey_name_and_values[i][1]
    select_object(source_obj, True)
    set_active_object(source_obj)
    return True

# シェイプキーをそれぞれ別のオブジェクトにする
def separate_shapekeys(duplicate, enable_apply_modifiers, remove_nonrender=True):
    source_obj = get_active_object()
    source_obj_name = source_obj.name
    
    bpy.ops.object.select_all(action='DESELECT')
    
    if duplicate == True:
        select_object(source_obj, True)
        set_active_object(source_obj)
        bpy.ops.object.duplicate()
        source_obj = get_active_object()
    
    source_obj_matrix_world_inverted = source_obj.matrix_world.inverted()
    
    print("Separate ShapeKeys: ["+source_obj.name+"]")
    wait_counter=0
    separated_objects = []
    shape_keys_length=len(source_obj.data.shape_keys.key_blocks)
    
    addon_prefs = get_addon_prefs()
    wait_interval=addon_prefs.wait_interval
    wait_sleep=addon_prefs.wait_sleep
    
    select_object(source_obj, True)
    for i, shapekey in enumerate(source_obj.data.shape_keys.key_blocks):
        print("Shape key ["+shapekey.name+"] ["+str(i)+" / "+str(shape_keys_length)+"]")
        
        # CPU負荷が高いっぽいので何回かに一回ウェイトをかける
        wait_counter+=1
        if wait_counter % wait_interval == 0:
            print("wait")
            time.sleep(wait_sleep)

        new_name=source_obj_name + "." + shapekey.name
        # Basisは無視
        if i == 0:
            if duplicate == True:
                set_object_name(source_obj,  new_name)
            continue
        
        # オブジェクトを複製
        set_active_object(source_obj)
        bpy.ops.object.duplicate()
        dup_obj = get_active_object()
        
        # 元オブジェクトの子にする
        # bpy.ops.object.parent_setだと更新処理が走って重くなるのでLowLevelな方法を採用
        dup_obj.parent = source_obj
        dup_obj.matrix_parent_inverse = source_obj_matrix_world_inverted
        
        # シェイプキーの名前を設定
        set_object_name(dup_obj, new_name)
        
        # シェイプキーをsource_objからdup_objにコピー
        select_object(source_obj, True)
        source_obj.active_shape_key_index = i
        #shapekey = source_obj.data.shape_keys.key_blocks[i]
        shapekey.value=1
        if is_v2_80_later()==True:
            dup_obj.shape_key_clear()
        else:
            bpy.ops.object.shape_key_remove(all=True)
        bpy.ops.object.shape_key_transfer()
        
        # シェイプキーを削除し形状を固定
        dup_obj.shape_key_remove(dup_obj.data.shape_keys.key_blocks[0]) # Basisを消す
        dup_obj.shape_key_remove(dup_obj.data.shape_keys.key_blocks[0]) # 固定するシェイプキーを消す
        
        separated_objects.append(dup_obj)
        
        select_object(dup_obj, False)
    
    # 元オブジェクトのシェイプキーを全削除
    bpy.ops.object.select_all(action='DESELECT')
    select_object(source_obj, True)
    set_active_object(source_obj)
    bpy.ops.object.shape_key_remove(all=True)
    
    if enable_apply_modifiers == True:
        apply_modifiers(remove_nonrender=remove_nonrender)
        for obj in separated_objects:
            set_active_object(obj)
            apply_modifiers(remove_nonrender=remove_nonrender)
        set_active_object(source_obj)
    
    # 表示を更新
    update_mesh()
    
    print("Finish Separate ShapeKeys: ["+source_obj.name+"]")
    return separated_objects

# 指定座標を基準にSide of Active
def select_axis_from_point(point=(0,0,0), mode='POSITIVE', axis='X', threshold=0.0001):
    obj = get_active_object()
    if obj.type != 'MESH':
        return
    
    bpy.ops.object.mode_set(mode='EDIT')
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    
    # 頂点選択を有効化
    temp_select_mode = bm.select_mode
    bm.select_mode = {'VERT'}
    
    bpy.ops.mesh.select_all(action='DESELECT')
    # 一時的に頂点を追加し、それを基準にSide of Activeを使う
    v = bm.verts.new(point)
    select_object(v, True)
    bm.select_history.add(v)
    select_axis(mode=mode, axis=axis, threshold=threshold)
    # 追加した頂点を削除
    if is_v2_80_later()==True:
        bmesh.ops.delete(bm, geom=[v], context='VERTS')
    else:
        bmesh.ops.delete(bm, geom=[v], context=1)
    
    bm.select_mode = temp_select_mode
    
    # Blender 4.x makes these optional arguments keyword-only.
    bmesh.update_edit_mesh(me, loop_triangles=False, destructive=True)
    #bpy.ops.object.mode_set(mode='OBJECT')

def update_mesh():
    obj = get_active_object()
    if obj.mode=='OBJECT':
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
    else:
        mode_cache=obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode=mode_cache)

### AddonPreferences ###
class addon_preferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    wait_interval: IntProperty(name="Wait Interval", default=5, min=1, soft_min=1)
    wait_sleep: FloatProperty(name="Wait Sleep", default=0.5, min=0, soft_min=0, max=2, soft_max=2)
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "wait_interval")
        layout.prop(self, "wait_sleep")

### Object Operator ###
class OBJECT_OT_specials_shapekeys_util_apply_modifiers(bpy.types.Operator):
    bl_idname = "object.shapekeys_util_apply_modifiers"
    bl_label = "Apply Modifiers"
    bl_description = get_tooltips_text(bl_idname+"_desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    duplicate: BoolProperty(name="Duplicate", default=False, description=get_tooltips_text(bl_idname+"_duplicate"))
    remove_nonrender: BoolProperty(name="Remove NonRender", default=True, description=get_tooltips_text("remove_nonrender"))
    
    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.selected_objects)
    
    def execute(self, context):
        original_active = context.view_layer.objects.active
        original_selection = list(context.selected_objects)
        targets = [obj for obj in original_selection if obj.type == 'MESH']

        # Linked object data cannot have modifiers applied. Make every target
        # single-user before starting the batch.
        bpy.ops.object.select_all(action='DESELECT')
        select_objects(targets, True)
        set_active_object(original_active if original_active in targets else targets[0])
        bpy.ops.object.make_single_user(
            type='SELECTED_OBJECTS',
            object=True,
            obdata=True,
            material=False,
            animation=False,
        )

        success = True
        for obj in targets:
            if not apply_modifiers_with_shapekeys(
                    self, obj, self.duplicate, self.remove_nonrender):
                success = False
                break

        bpy.ops.object.select_all(action='DESELECT')
        select_objects(original_selection, True)
        set_active_object(original_active)
        return {'FINISHED'} if success else {'CANCELLED'}

class OBJECT_OT_specials_shapekeys_util_separateobj(bpy.types.Operator):
    bl_idname = "object.shapekeys_util_separateobj"
    bl_label = "Separate Objects"
    bl_description = get_tooltips_text(bl_idname+"_desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    duplicate: BoolProperty(name="Duplicate", default=False, description=get_tooltips_text(bl_idname+"_duplicate"))
    apply_modifiers: BoolProperty(name="Apply Modifiers", default=False, description=get_tooltips_text(bl_idname+"_apply_modifiers"))
    remove_nonrender: BoolProperty(name="Remove NonRender", default=True, description=get_tooltips_text("remove_nonrender"))
    
    @classmethod
    def poll(cls, context):
        return any(
            obj.type == 'MESH'
            and obj.data.shape_keys is not None
            and len(obj.data.shape_keys.key_blocks) > 0
            for obj in context.selected_objects
        )
    
    def execute(self, context):
        original_active = context.view_layer.objects.active
        original_selection = list(context.selected_objects)
        targets = [
            obj for obj in original_selection
            if obj.type == 'MESH'
            and obj.data.shape_keys is not None
            and len(obj.data.shape_keys.key_blocks) > 0
        ]

        # When the originals are modified, detach shared object/mesh data so
        # an unselected linked object is not changed as a side effect.
        if not self.duplicate:
            bpy.ops.object.select_all(action='DESELECT')
            select_objects(targets, True)
            set_active_object(original_active if original_active in targets else targets[0])
            bpy.ops.object.make_single_user(
                type='SELECTED_OBJECTS',
                object=True,
                obdata=True,
                material=False,
                animation=False,
            )

        for source_obj in targets:
            bpy.ops.object.select_all(action='DESELECT')
            select_object(source_obj, True)
            set_active_object(source_obj)
            separate_shapekeys(
                self.duplicate,
                self.apply_modifiers,
                self.remove_nonrender,
            )

        bpy.ops.object.select_all(action='DESELECT')
        select_objects(original_selection, True)
        set_active_object(original_active)
        return {'FINISHED'}



### Mesh Operator ###
class MESH_OT_specials_shapekeys_util_sideofactive_point(bpy.types.Operator):
    bl_idname = "edit_mesh.shapekeys_util_sideofactive_point"
    bl_label = "Side of Active from Point"
    bl_description = "指定座標を基準にSide of active"
    bl_options = {'REGISTER', 'UNDO'}
    
    point: FloatVectorProperty(name="Point")
    
    mode: EnumProperty(
        name="Axis Mode",
        default='NEGATIVE',
        items=(
            ('POSITIVE', "Positive Axis", ""),
            ('NEGATIVE', "Negative Axis", ""),
            ('ALIGNED', "Aligned Axis", ""),
        )
    )
    
    axis: EnumProperty(
        name="Axis",
        default='X',
        items=(
            ('X', "X", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
        )
    )
    
    threshold: FloatProperty(
        name="Threshold",
        min=0.000001, max=50.0,
        soft_min=0.00001, soft_max=10.0,
        default=0.0001,
    )
    
    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'MESH'
    
    def execute(self, context):
        select_axis_from_point(self.point, self.mode, self.axis, self.threshold)
        
        return {'FINISHED'}

### Init Menu ###
# エディットモード　Special → ShapeKeys Util を登録する
def INFO_MT_edit_mesh_specials_shapekeys_util_menu(self, context):
    self.layout.menu(VIEW3D_MT_edit_mesh_specials_shapekeys_util.bl_idname)

# オブジェクトモード　Special → ShapeKeys Util を登録する
def INFO_MT_object_specials_shapekeys_util_menu(self, context):
    self.layout.menu(VIEW3D_MT_object_specials_shapekeys_util.bl_idname)

# エディットモード　Special → ShapeKeys Util にコマンドを登録するクラス
class VIEW3D_MT_edit_mesh_specials_shapekeys_util(bpy.types.Menu):
    bl_label = "ShapeKeys Util"
    bl_idname = "INFO_MT_edit_mesh_specials_shapekeys_util_menu"
    
    def draw(self, context):
        self.layout.operator(MESH_OT_specials_shapekeys_util_sideofactive_point.bl_idname)

# オブジェクトモード　Special → ShapeKeys Util にコマンドを登録するクラス
class VIEW3D_MT_object_specials_shapekeys_util(bpy.types.Menu):
    bl_label = "ShapeKeys Util"
    bl_idname = "VIEW3D_MT_object_specials_shapekeys_util"
    
    def draw(self, context):
        layout = self.layout
        layout.operator(OBJECT_OT_specials_shapekeys_util_apply_modifiers.bl_idname)
        layout.operator(OBJECT_OT_specials_shapekeys_util_separateobj.bl_idname)
        #layout.operator(OBJECT_OT_specials_shapekeys_util_wip.bl_idname)

### Init ###
classes = [
    VIEW3D_MT_object_specials_shapekeys_util,
    VIEW3D_MT_edit_mesh_specials_shapekeys_util,
    
    OBJECT_OT_specials_shapekeys_util_apply_modifiers,
    OBJECT_OT_specials_shapekeys_util_separateobj,
    #OBJECT_OT_specials_shapekeys_util_wip,
    
    MESH_OT_specials_shapekeys_util_sideofactive_point,
    
    addon_preferences,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    if is_v2_80_later() == True:
        bpy.types.VIEW3D_MT_object_context_menu.append(INFO_MT_object_specials_shapekeys_util_menu)
        bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(INFO_MT_edit_mesh_specials_shapekeys_util_menu)
    else:
        bpy.types.VIEW3D_MT_object_specials.append(INFO_MT_object_specials_shapekeys_util_menu)
        bpy.types.VIEW3D_MT_edit_mesh_specials.append(INFO_MT_edit_mesh_specials_shapekeys_util_menu)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    if is_v2_80_later() == True:
        bpy.types.VIEW3D_MT_object_context_menu.remove(INFO_MT_object_specials_shapekeys_util_menu)
        bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(INFO_MT_edit_mesh_specials_shapekeys_util_menu)
    else:
        bpy.types.VIEW3D_MT_object_specials.remove(INFO_MT_object_specials_shapekeys_util_menu)
        bpy.types.VIEW3D_MT_edit_mesh_specials.remove(INFO_MT_edit_mesh_specials_shapekeys_util_menu)

if __name__ == "__main__":
    register()
