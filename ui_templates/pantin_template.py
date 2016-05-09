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
bone_offset = 0.005

def z_index(member_index, flip, members_number, bone_index):
    if flip:
        return -(members_number - member_index) * member_offset - bone_index * bone_offset
    else:
        return member_index * member_offset + bone_index * bone_offset

def z_index_same(member_index, flip, bone_index):
    if flip:
        return -member_index * member_offset - bone_index * bone_offset
    else:
        return member_index * member_offset + bone_index * bone_offset


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
                
                tmp_matrix = pb.matrix
                pb.matrix = other.matrix
                other.matrix = tmp_matrix
        return {'FINISHED'}


###################
## Rig UI Panels ##
###################

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

    # Root layer
    code += "\n        row = col.row()"
    code += "\n        row.separator()"
    code += "\n        row = col.row()"
    code += "\n        row.separator()\n"
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


def unregister():
    bpy.utils.unregister_class(Rigify_Swap_Bones)
    bpy.utils.unregister_class(RigUI)
    bpy.utils.unregister_class(RigLayers)

    del bpy.app.driver_namespace["z_index"]
    del bpy.app.driver_namespace["z_index_same"]


register()
'''
