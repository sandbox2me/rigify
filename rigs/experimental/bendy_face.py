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
    MCH_SCALE = 0.3

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

        self.start_bones = self.get_start_bones()
        self.bones['ctrl'] = dict()
        self.bones['mch'] = dict()
        self.bones['def'] = dict()

    def create_mch(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        for name in self.start_bones:
            subchain = [name]
            subchain.extend(connected_children_names(self.obj, name))
            self.bones['mch'][strip_org(name)] = []

            for subname in subchain:
                mch = copy_bone(self.obj, subname, assign_name=make_mechanism_name(strip_org(subname)))
                edit_bones[mch].parent = None
                edit_bones[mch].length *= self.MCH_SCALE
                self.bones['mch'][strip_org(name)].append(mch)

    def create_def(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        for name in self.start_bones:
            subchain = [name]
            subchain.extend(connected_children_names(self.obj, name))
            self.bones['def'][strip_org(name)] = []

            for subname in subchain:
                def_bone = copy_bone(self.obj, subname, assign_name=make_deformer_name(strip_org(subname)))
                edit_bones[def_bone].parent = None
                self.bones['def'][strip_org(name)].append(def_bone)

    def create_controls(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        for name in self.start_bones:
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

        self.aggregate_ctrls()

        bpy.ops.object.mode_set(mode='OBJECT')
        for subchain in self.bones['ctrl']:
            for ctrl in self.bones['ctrl'][subchain]:
                create_sphere_widget(self.obj, ctrl)

    def aggregate_ctrls(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        aggregates = []

        all_ctrls = []

        for subchain in self.start_bones:
            for ctrl in self.bones['ctrl'][strip_org(subchain)]:
                all_ctrls.append(ctrl)

        while 1:
            ctrl = all_ctrls[0]
            aggregate = [ctrl]
            for ctrl2 in all_ctrls[1:]:
                if edit_bones[ctrl].head == edit_bones[ctrl2].head:
                    aggregate.append(ctrl2)
            for element in aggregate:
                all_ctrls.remove(element)
            if len(aggregate) > 1:
                aggregates.append(aggregate)
            if not all_ctrls:
                break

        if aggregates:
            self.bones['ctrl']['aggregate'] = []

        for aggregate in aggregates:
            name = self.get_aggregate_name(aggregate)
            aggregate_ctrl = copy_bone(self.obj, aggregate[0], name)
            self.bones['ctrl']['aggregate'].append(aggregate_ctrl)
            for ctrl in aggregate:
                edit_bones.remove(edit_bones[ctrl])
                for subchain in self.start_bones:
                    if ctrl in self.bones['ctrl'][strip_org(subchain)]:
                        self.bones['ctrl'][strip_org(subchain)].remove(ctrl)
                        continue

        return True

    def get_aggregate_name(self, aggregate):

        total = '.'.join(aggregate)

        root = aggregate[0].split('.')[0]
        for name in aggregate[1:]:
            if name.split('.')[0] not in root:
                root = '.'.join([root, name.split('.')[0]])

        name = root

        t_b = ''
        if 'T' in total and 'B' in total:
            t_b = ''
        elif 'T' in total:
            t_b = 'T'
        elif 'B' in total:
            t_b = 'B'

        if t_b:
            name = '.'.join([name, t_b])

        l_r = ''
        if 'L' in total and 'R' in total:
            l_r = ''
        elif 'L' in total:
            l_r = 'L'
        elif 'R' in total:
            l_r = 'R'

        if l_r:
            name = '.'.join([name, l_r])

        return name

    def get_start_bones(self):
        """
        Returns all the bones starting a subchain of the face
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        start_bones = []

        for name in self.bones['org'][1:]:
            if not edit_bones[name].use_connect:
                start_bones.append(name)

        return start_bones

    def generate(self):

        self.create_mch()
        self.create_def()
        self.create_controls()

        return [""]
