######################################################################
# Bendy rig is a base-class for subchain-based rigs with bendy bones #
# and glue bones                                                     #
######################################################################

import bpy
import re
from mathutils import Vector
from ...utils import copy_bone, flip_bone, put_bone
from ...utils import org, strip_org, strip_def, make_deformer_name, connected_children_names, make_mechanism_name
from ...utils import create_circle_widget, create_sphere_widget, create_widget, create_cube_widget
from ...utils import MetarigError
from ...utils import make_constraints_from_string
from rna_prop_ui import rna_idprop_ui_prop_get
from ..widgets import create_face_widget, create_eye_widget, create_eyes_widget, create_ear_widget, create_jaw_widget, create_teeth_widget


class BendyRig:

    CTRL_SCALE = 0.1
    MCH_SCALE = 0.3

    POSITION_RELATIVE_ERROR = 1e-3  # error below which two positions are considered equal (relative to bone len)

    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.params = params
        self.bones = dict()
        self.bones['org'] = [bone_name]
        self.base_bone = bone_name

        # Get all the recursive ORG children of the base bone
        for edit_bone in self.obj.data.edit_bones[bone_name].children_recursive:
            self.bones['org'].append(edit_bone.name)

        # Remove other rig_types from ORGs
        for edit_bone in self.obj.data.edit_bones[bone_name].children_recursive:
            if self.obj.pose.bones[edit_bone.name].rigify_type != "":
                self.bones['org'].remove(edit_bone.name)
                for child in edit_bone.children_recursive:
                    self.bones['org'].remove(child.name)

        self.start_bones = self.get_start_bones()
        self.bones['glue'] = self.get_glue_bones()
        self.bones['ctrl'] = dict()
        self.bones['mch'] = dict()
        self.bones['def'] = dict()

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

    def get_glue_bones(self):
        """
        Get names of pose bones with glue prop
        :return:
        """

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        glue_bones = []

        for pose_bone in pose_bones:
            if pose_bone.rigify_glue != "":
                if pose_bone.bone.children or pose_bone.bone.parent.name != self.bones['org'][0]:
                    raise MetarigError("ERROR: Glue bones must parented to main bone and have no children!")
                else:
                    glue_bones.append(pose_bone.name)
                    # todo remove from start_bones depending on glue prop
                    self.start_bones.remove(pose_bone.name)

        return glue_bones

    def get_ctrls_by_position(self, position, subchain='', relative_error=0):
        """
        Returns the controls closest to position in given relative_error range and subchain
        checking subchain first and then aggregates
        :param subchain:
        :type subchain: str
        :param position:
        :type subchain: Vector
        :return:
        :rtype: list(str)
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        bones_in_range = []

        if subchain:
            subchain = strip_org(subchain)
            keys = [subchain]
            if 'aggregate' in self.bones['ctrl']:
                keys.append('aggregate')
        else:
            keys = self.bones['ctrl'].keys()

        if not relative_error:
            relative_error = self.POSITION_RELATIVE_ERROR

        for chain in keys:
            for name in self.bones['ctrl'][chain]:
                error = edit_bones[name].length * relative_error
                if (edit_bones[name].head - position).magnitude <= error:
                    bones_in_range.append(name)

        return bones_in_range

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

    def make_constraints(self):
        """
        Make constraints for each bone subgroup
        :return:
        """

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        ### Constrain DEF-bones ###
        for subchain in self.bones['def']:
            for name in self.bones['def'][subchain]:
                owner_pb = pose_bones[name]

                subtarget = make_mechanism_name(strip_def(name))
                const = owner_pb.constraints.new('COPY_LOCATION')
                const.target = self.obj
                const.subtarget = subtarget

                tail_subtargets = self.get_ctrls_by_position(owner_pb.bone.tail, subchain=subchain)

                if tail_subtargets:
                    const = owner_pb.constraints.new('DAMPED_TRACK')
                    const.target = self.obj
                    const.subtarget = tail_subtargets[0]

                    const = owner_pb.constraints.new('STRETCH_TO')
                    const.target = self.obj
                    const.subtarget = tail_subtargets[0]

        ### Glue bones Constraints
        for glue_bone in self.bones['glue']:
            head_ctrls = self.get_ctrls_by_position(pose_bones[glue_bone].head)
            if not head_ctrls:
                continue
            tail_ctrls = self.get_ctrls_by_position(pose_bones[glue_bone].tail)
            if not tail_ctrls:
                continue
            owner_pb = pose_bones[tail_ctrls[0]]
            make_constraints_from_string(owner_pb, target=self.obj, subtarget=head_ctrls[0],
                                         fstring=pose_bones[glue_bone].rigify_glue)

    def parent_bones(self):
        """
        Specify bone parenting
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        ### PARENT MCH-bones ###
        for subchain in self.bones['mch']:
            for name in self.bones['mch'][subchain]:
                mch_bone = edit_bones[name]
                parents = self.get_ctrls_by_position(mch_bone.head, subchain=subchain)

                if parents:
                    mch_bone.parent = edit_bones[parents[0]]

    def get_aggregate_name(self, aggregate):
        """
        Returns the collective name for an aggregatable bones name list
        :param aggregate:
        :type aggregate: list(str)
        :return:
        """

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

    def generate(self):
        pass
