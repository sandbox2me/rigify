#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>

UI_SLIDERS = '''
import bpy
from mathutils import Matrix, Vector
from math import acos, pi

rig_id = "%s"


#######################
## Driver namespace  ##
#######################
member_offset = 0.01
bone_offset = 0.001

def z_index(member_index, flip, bone_index):
    if flip:
        return -member_index * member_offset + bone_index * bone_offset
    else:
        return -member_index * member_offset - bone_index * bone_offset

def z_index_same(member_index, flip, bone_index):
    if flip:
        return -member_index * member_offset + bone_index * bone_offset
    else:
        return member_index * member_offset - bone_index * bone_offset


#######################
## Swapping operator ##
#######################

class Rigify_Swap_Bones(bpy.types.Operator):
    """ Swap left and right bones
    """
    bl_idname = "pose.rigify_swap_bones_" + rig_id
    bl_label = "Rigify Swap left and right selected bones"
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        def swap_LR(name):
            if name[-2:] == '.L':
                return name[:-1] + 'R'
            elif name[-2:] == '.R':
                return name[:-1] + 'L'
            else:
                return None

        for pb in context.selected_pose_bones:
            swapped_name = swap_LR(pb.name)
            if swapped_name is not None:
                other = context.object.pose.bones[swapped_name]
                
                tmp_matrix = pb.matrix_basis.copy()
                pb.matrix_basis = other.matrix_basis
                other.matrix_basis = tmp_matrix
        return {'FINISHED'}


###################################
## Bone Z Index Operators and UI ##
###################################

class Rigify_Fill_Members(bpy.types.Operator):
    """ Construct member and bone structure"""
    bl_idname = "pose.rigify_fill_members" + rig_id
    bl_label = "Construct member and bone structure"
#    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.active_object.type == 'ARMATURE')

    def execute(self, context):
        obj = context.object
        
        obj.data.pantin_members.clear()
        members = {}
        for bone in obj.data.bones:
            # print(bone.name)
            if not bone.use_deform:
                continue
            if not bone['member_index'] in members:
                members[bone['member_index']] = []
            members[bone['member_index']].append((bone['bone_index'], bone.name))
        # print(members)
        
        for member, bones in sorted(members.items(), key=lambda i:i[0]):
            m = obj.data.pantin_members.add()
            m.index = member
            for bone in sorted(bones, key=lambda i:i[0]):
                b = m.bones.add()
                b.index = bone[0]
                b.name = bone[1]
            
        return {'FINISHED'}

class Rigify_Reorder_Bones(bpy.types.Operator):
    """ Change bones' order"""
    bl_idname = "pose.rigify_reorder_bones_" + rig_id
    bl_label = "Change bones' order"

    direction = bpy.props.StringProperty()
    list_member_index = bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.active_object.type == 'ARMATURE')

    def execute(self, context):
        obj = context.object
#        print(self.direction)
#        print(self.list_member_index)
        active_member_index = obj.data.pantin_members[self.list_member_index].index
        active_bone_index = obj.data.pantin_members[self.list_member_index].active_bone
        num_bones = len(obj.data.pantin_members[self.list_member_index].bones)
        for b in obj.data.bones:
            if not b.use_deform:
                continue
            if b['member_index'] == active_member_index and b['bone_index'] == active_bone_index:
                active_bone = b
            if active_bone_index >= 1 and b['member_index'] == active_member_index and b['bone_index'] == active_bone_index - 1 :
                previous_bone = b
            if active_bone_index <= num_bones-2 and b['member_index'] == active_member_index and b['bone_index'] == active_bone_index + 1 :
                next_bone = b
#        print(previous_bone, active_bone, next_bone)
        tmp = active_bone['bone_index']
        if self.direction == 'UP':
            if active_bone_index >= 1:
                # move for real
                active_bone['bone_index'] = previous_bone['bone_index']
                previous_bone['bone_index'] = tmp
                # move in UI
                obj.data.pantin_members[self.list_member_index].bones.move(active_bone_index, active_bone_index - 1)
                obj.data.pantin_members[self.list_member_index].active_bone -= 1
            else:
                pass
                #REPORT ERROR !
        if self.direction == 'DOWN':
            if active_bone_index <= num_bones-2:
                # move for real
                active_bone['bone_index'] = next_bone['bone_index']
                next_bone['bone_index'] = tmp
                # move in UI
                obj.data.pantin_members[self.list_member_index].bones.move(active_bone_index, active_bone_index + 1)
                obj.data.pantin_members[self.list_member_index].active_bone += 1

            else:
                pass
                #REPORT ERROR !
            
        mode = bpy.context.mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode=mode)
        
        # exec("bpy.ops.pose.rigify_fill_members" + rig_id + "()")
        return {'FINISHED'}

class PantinBones(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty()
    index = bpy.props.IntProperty()
#    bone = bpy.props.PointerProperty(type=bpy.types.Bone)

bpy.utils.register_class(PantinBones)
    
class PantinMembers(bpy.types.PropertyGroup):
#    name = bpy.props.StringProperty()
    index = bpy.props.FloatProperty()
    bones = bpy.props.CollectionProperty(type=bpy.types.PantinBones)
    active_bone = bpy.props.IntProperty()


class PANTIN_UL_bones_list(bpy.types.UIList):
    # The draw_item function is called for each item of the collection that is visible in the list.
    #   data is the RNA object containing the collection,
    #   item is the current drawn item of the collection,
    #   icon is the "computed" icon for the item (as an integer, because some objects like materials or textures
    #   have custom icons ID, which are not available as enum items).
    #   active_data is the RNA object containing the active property for the collection (i.e. integer pointing to the
    #   active item of the collection).
    #   active_propname is the name of the active property (use 'getattr(active_data, active_propname)').
    #   index is index of the current item in the collection.
    #   flt_flag is the result of the filtering process for this item.
    #   Note: as index and flt_flag are optional arguments, you do not have to use/declare them here if you don't
    #         need them.
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        arm = data
        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.label(icon='BONE_DATA', text=item.name[4:], translate=False, icon_value=icon)
            row.alignment = 'RIGHT'
            lab = row.label(text=str(item.index), translate=False)
        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


###################
## Rig UI Panels ##
###################

class DATA_PT_members_panel(bpy.types.Panel):
    bl_label = "Members"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_context = "object"
    bl_options = {'DEFAULT_CLOSED'}
    bl_idname = rig_id + "_PT_members"

    @classmethod
    def poll(self, context):
        if context.mode not in ('POSE', 'OBJECT'):
            return False
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        C = context
        layout = self.layout
        obj = context.object

        if obj.mode in {'POSE', 'OBJECT'}:

            id_store = C.object.data

            if id_store.pantin_members and len(id_store.pantin_members):
                box = layout.box()
                col = box.column()
    #            col.template_list("UI_UL_list", "pantin_members", armature_id_store, "pantin_members", armature_id_store, "pantin_active_member")
                
                for i, m in enumerate(id_store.pantin_members):
                    col.label(str(m.index))#name.title()+':')
                    row = col.row()
#                    sub = row.column()
                    row.template_list("PANTIN_UL_bones_list", "bones", id_store.pantin_members[i], "bones", id_store.pantin_members[i], "active_bone")

                    sub = row.column(align=True)
                    op = sub.operator("pose.rigify_reorder_bones_" + rig_id, icon='TRIA_UP', text="")
                    op.list_member_index = i
                    op.direction = 'UP'
                    op = sub.operator("pose.rigify_reorder_bones_" + rig_id, icon='TRIA_DOWN', text="")
                    op.list_member_index = i
                    op.direction = 'DOWN'
    #                col.separator()
            layout.operator("pose.rigify_fill_members" + rig_id)

class RigUI(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rig Main Properties"
    bl_idname = rig_id + "_PT_rig_ui"

    @classmethod
    def poll(self, context):
        if context.mode != 'POSE':
            return False
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        layout = self.layout
        pose_bones = context.active_object.pose.bones
        bones = context.active_object.data.bones
        try:
            selected_bones = [bone.name for bone in context.selected_pose_bones]
            selected_bones += [context.active_pose_bone.name]
        except (AttributeError, TypeError):
            return

        def is_selected(names):
            # Returns whether any of the named bones are selected.
            if type(names) == list:
                for name in names:
                    if name in selected_bones:
                        return True
            elif names in selected_bones:
                return True
            return False

        layout.operator("pose.rigify_swap_bones_" + rig_id)
        layout.separator()

        layout.prop(bones["MCH-Flip"], '["flip"]', text="Flip", slider=True)
        layout.separator()

'''


def layers_ui(layers, layout):
    """ Turn a list of booleans + a list of names into a layer UI.
    """

    code = '''
class RigLayers(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Rig Layers"
    bl_idname = rig_id + "_PT_rig_layers"

    @classmethod
    def poll(self, context):
        try:
            return (context.active_object.data.get("rig_id") == rig_id)
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        layout = self.layout
        col = layout.column()
'''
    rows = {}
    for i in range(28):
        if layers[i]:
            if layout[i][1] not in rows:
                rows[layout[i][1]] = []
            rows[layout[i][1]] += [(layout[i][0], i)]

    keys = list(rows.keys())
    keys.sort()

    for key in keys:
        code += "\n        row = col.row()\n"
        i = 0
        for l in rows[key]:
            if i > 3:
                code += "\n        row = col.row()\n"
                i = 0
            code += "        row.prop(context.active_object.data, 'layers', index=%s, toggle=True, text='%s')\n" % (str(l[1]), l[0])
            i += 1

    # Def layer (for parenting)
    code += "\n        row = col.row()"
    code += "\n        row.separator()"
    code += "\n        row = col.row()"
    code += "\n        row.separator()\n"
    code += "\n        row = col.row()\n"
    code += "        row.prop(context.active_object.data, 'layers', index=29, toggle=True, text='Deformation')\n"

    # Root layer
    code += "\n        row = col.row()\n"
    code += "        row.prop(context.active_object.data, 'layers', index=28, toggle=True, text='Root')\n"

    return code


UI_REGISTER = '''

def register():
    bpy.utils.register_class(Rigify_Swap_Bones)
    bpy.utils.register_class(RigUI)
    bpy.utils.register_class(RigLayers)

    bpy.app.driver_namespace["z_index"] = z_index
    bpy.app.driver_namespace["z_index_same"] = z_index_same

    bpy.utils.register_class(Rigify_Fill_Members)
    bpy.utils.register_class(Rigify_Reorder_Bones)
    bpy.utils.register_class(PantinMembers)
    bpy.utils.register_class(PANTIN_UL_bones_list)
    bpy.utils.register_class(DATA_PT_members_panel)
    bpy.types.Armature.pantin_members = bpy.props.CollectionProperty(type=PantinMembers)

def unregister():
    bpy.utils.unregister_class(Rigify_Swap_Bones)
    bpy.utils.unregister_class(RigUI)
    bpy.utils.unregister_class(RigLayers)

    del bpy.app.driver_namespace["z_index"]
    del bpy.app.driver_namespace["z_index_same"]

    del bpy.types.Armature.pantin_members
    bpy.utils.unregister_class(Rigify_Fill_Members)
    bpy.utils.unregister_class(Rigify_Reorder_Bones)
    bpy.utils.unregister_class(PANTIN_UL_bones_list)
    bpy.utils.unregister_class(DATA_PT_members_panel)
    bpy.utils.unregister_class(PantinMembers)
    bpy.utils.unregister_class(PantinBones)

register()
'''
