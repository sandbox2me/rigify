import bpy, re
from   mathutils      import Vector
from   ...utils       import copy_bone, flip_bone, put_bone
from   ...utils       import org, strip_org, make_deformer_name, connected_children_names, make_mechanism_name
from   ...utils       import create_circle_widget, create_sphere_widget, create_widget, create_cube_widget
from   ...utils       import MetarigError
from   rna_prop_ui    import rna_idprop_ui_prop_get
from   ..widgets import create_face_widget, create_eye_widget, create_eyes_widget, create_ear_widget, create_jaw_widget, create_teeth_widget


class Rig:

    CTRL_SCALE = 0.1

    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.bones = dict()
        self.bones['org'] = [bone_name]

        for edit_bone in self.obj.data.edit_bones[bone_name].children_recursive:
            self.bones['org'].append(edit_bone.name)

        for edit_bone in self.obj.data.edit_bones[bone_name].children_recursive:
            if self.obj.pose.bones[edit_bone.name].rigify_type != "":
                self.bones['org'].remove(edit_bone.name)
                for child in edit_bone.children_recursive:
                    self.bones['org'].remove(child.name)

        self.bones['ctrl'] = dict()

    def create_controls(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        start_bones = []

        for name in self.bones['org'][1:]:
            if not edit_bones[name].use_connect:
                start_bones.append(name)

        for name in start_bones:
            subchain = [name]
            subchain.extend(connected_children_names(self.obj, name))
            self.bones['ctrl'][strip_org(name)] = []

            for subname in subchain:
                ctrl = copy_bone(self.obj, self.bones['org'][0], assign_name=strip_org(subname))
                put_bone(self.obj, ctrl, edit_bones[subname].head)
                edit_bones[ctrl].length *= self.CTRL_SCALE
                self.bones['ctrl'][strip_org(name)].append(ctrl)

            last_name = subchain[-1]
            last_ctrl = copy_bone(self.obj, self.bones['org'][0], assign_name=strip_org(last_name))
            put_bone(self.obj, last_ctrl, edit_bones[last_name].tail)
            edit_bones[last_ctrl].length *= self.CTRL_SCALE
            self.bones['ctrl'][strip_org(name)].append(last_ctrl)

        bpy.ops.object.mode_set(mode='OBJECT')
        for subchain in self.bones['ctrl']:
            for ctrl in self.bones['ctrl'][subchain]:
                create_sphere_widget(self.obj, ctrl)

    def generate(self):

        self.create_controls()

        return [""]
