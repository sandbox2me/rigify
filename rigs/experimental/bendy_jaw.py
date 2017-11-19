#############################################
# Bendy jaws contruction rules:
# - make a main bone with a connected children. The tail of the connected children
# is the chin point its head is the jaw pivot
# - make 4 chains for the mouth of the same length. Parent them unconnected to the main bone
# - make a jaw-chin chain the first bone goes under the chin and has a tail as close as possibile to the chin point
# all the other bones follow the chin midline up to the mouth bottom lip
#############################################

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
from .bendy_rig import BendyRig


class Rig(BendyRig):

    def __init__(self, obj, bone_name, params):

        super(Rig, self).__init__(obj, bone_name, params)

        # Rule check
        if len(self.start_bones) != 5:
            raise MetarigError("Exactly 5 disconnected chains must be parented to main bone. 4 belong to the mouth 1 to the chin")
        self.main_mch = None
        self.jaw = self.get_jaw()
        self.lip_len = None
        self.mouth_bones = self.get_mouth()

    def get_jaw(self):
        """
        Gets the main bone of the jaw-chin chain
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        for child in edit_bones[self.bones['org'][0]].children:
            if child.use_connect:
                main_mch = child
                self.main_mch = main_mch.name

        for start_bone in self.start_bones:
            if (edit_bones[start_bone].tail - main_mch.tail).magnitude <= self.POSITION_RELATIVE_ERROR * main_mch.length:
                return start_bone

    def get_mouth(self):
        """
        Returns the main bones of the mouth chain
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        mouth_bones_dict = {'top': [], 'bottom': []}
        mouth_bones = [name for name in self.start_bones if name != self.jaw]
        lip_len = len(edit_bones[mouth_bones[0]].children_recursive)

        for lip in mouth_bones:
            if len(edit_bones[lip].children_recursive) != lip_len:
                raise MetarigError("All lip chains must be the same length")

        self.lip_len = lip_len + 1

        m_b_head_positions = [edit_bones[name].head for name in mouth_bones]
        head_sum = m_b_head_positions[0]
        for h in m_b_head_positions[1:]:
            head_sum = head_sum + h
        mouth_center = head_sum / 4
        chin_tail_position = edit_bones[self.main_mch].tail
        mouth_chin_distance = (mouth_center - chin_tail_position).magnitude
        for m_b in mouth_bones:
            head = edit_bones[m_b].head
            if (head - chin_tail_position).magnitude < mouth_chin_distance:
                mouth_bones_dict['bottom'].append(m_b)
            elif (head - chin_tail_position).magnitude > mouth_chin_distance:
                mouth_bones_dict['top'].append(m_b)

        if not (len(mouth_bones_dict['top']) == len(mouth_bones_dict['bottom']) == 2):
            raise MetarigError("Badly drawn mouth")

        return mouth_bones_dict

    def create_mch(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        main_bone_name = strip_org(self.bones['org'][0])
        mouth_lock_name = make_mechanism_name(main_bone_name + "_lock")
        mouth_lock = copy_bone(self.obj, self.main_mch, mouth_lock_name)

        self.bones['jaw_mch'] = dict()
        self.bones['jaw_mch']['mouth_lock'] = mouth_lock
        self.bones['jaw_mch']['jaw_masters'] = []

        jaw_masters_number = self.lip_len + 3

        for i in range(0, jaw_masters_number):
            jaw_m_name = make_mechanism_name(strip_org(self.jaw) + "_master")
            jaw_m = copy_bone(self.obj, self.main_mch, jaw_m_name)
            div_len = (edit_bones[mouth_lock].length/(jaw_masters_number + 1))
            edit_bones[jaw_m].length = (jaw_masters_number - i) * div_len

            self.bones['jaw_mch']['jaw_masters'].append(jaw_m)

        # create remaining subchain mch-s
        super(Rig, self).create_mch()

    def create_def(self):
        # create remaining subchain def-s
        super(Rig, self).create_def()

    def create_controls(self):
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        self.bones['jaw_ctrl'] = dict()

        jaw_ctrl_name = strip_org(self.jaw) + "_master"

        jaw_ctrl = copy_bone(self.obj, self.main_mch, jaw_ctrl_name)
        self.bones['jaw_ctrl']['jaw'] = jaw_ctrl

        bpy.ops.object.mode_set(mode='OBJECT')
        create_jaw_widget(self.obj, jaw_ctrl_name)

        super(Rig, self).create_controls()

    def make_constraints(self):
        """
        Make constraints
        :return:
        """

        bpy.ops.object.mode_set(mode='OBJECT')
        pose_bones = self.obj.pose.bones

        owner = pose_bones[self.bones['jaw_mch']['mouth_lock']]
        subtarget = self.bones['jaw_ctrl']['jaw']
        make_constraints_from_string(owner, self.obj, subtarget, "CT0.2WW0.0")

        influence_div = 1/len(self.bones['jaw_mch']['jaw_masters'])
        for i, j_m in enumerate(self.bones['jaw_mch']['jaw_masters']):
            owner = pose_bones[j_m]
            subtarget = self.bones['jaw_ctrl']['jaw']
            influence = 1 - i * influence_div
            make_constraints_from_string(owner, self.obj, subtarget, "CT%sWW0.0" % influence)
            if j_m != self.bones['jaw_mch']['jaw_masters'][-1]:
                owner = pose_bones[j_m]
                subtarget = self.bones['jaw_mch']['mouth_lock']
                make_constraints_from_string(owner, self.obj, subtarget, "CT0.0WW0.0")

        # make the standard bendy rig constraints
        super(Rig, self).make_constraints()

    def make_drivers(self):
        """
        Adds properties and drivers driving jaw cns
        :return:
        """

        bpy.ops.object.mode_set(mode ='OBJECT')
        pose_bones = self.obj.pose.bones

        # Add mouth_lock property on jaw_master #
        jaw_master = pose_bones[self.bones['jaw_ctrl']['jaw']]
        prop_name = 'mouth_lock'
        jaw_master[prop_name] = 0.0
        prop = rna_idprop_ui_prop_get(jaw_master, prop_name)
        prop["min"] = 0.0
        prop["max"] = 1.0
        prop["soft_min"] = 0.0
        prop["soft_max"] = 1.0
        prop["description"] = prop_name

        for bone in self.bones['jaw_mch']['jaw_masters'][:-1]:
            drv = pose_bones[bone].constraints[1].driver_add("influence").driver
            drv.type = 'SUM'

            var = drv.variables.new()
            var.name = prop_name
            var.type = "SINGLE_PROP"
            var.targets[0].id = self.obj
            var.targets[0].data_path = jaw_master.path_from_id() + '[' + '"' + prop_name + '"' + ']'

    def parent_bones(self):
        """
        Parent jaw bones
        :return:
        """

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.obj.data.edit_bones

        # Parenting to the jaw_master
        jaw_master = self.bones['jaw_ctrl']['jaw']
        jaw_eb = edit_bones[self.jaw]
        jaw_chain_start = strip_org(self.jaw)
        jaw_ctrl = self.get_ctrls_by_position(jaw_eb.head, jaw_chain_start)[0]
        edit_bones[jaw_ctrl].parent = edit_bones[jaw_master]
        chin_ctrl = self.get_ctrls_by_position(jaw_eb.tail, jaw_chain_start)[0]
        edit_bones[chin_ctrl].parent = edit_bones[jaw_master]

        for chin_bone_name in self.bones['ctrl'][strip_org(self.jaw)][2:]:
            chin_bone = edit_bones[chin_bone_name]
            chin_bone.parent = edit_bones[chin_ctrl]

        # Parenting to jaw MCHs
        jaw_masters = self.bones['jaw_mch']['jaw_masters']
        b_lip_1 = strip_org(self.mouth_bones['bottom'][0])     # 1st bottom lip quarter
        b_lip_2 = strip_org(self.mouth_bones['bottom'][1])

        for i, lip_def in enumerate(self.bones['def'][b_lip_1]):
            lip_def_eb = edit_bones[lip_def]
            lip_ctrl = self.get_ctrls_by_position(lip_def_eb.head, b_lip_1)[0]
            edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i]]
            if lip_def == self.bones['def'][b_lip_1][-1]:
                lip_ctrl = self.get_ctrls_by_position(lip_def_eb.tail, b_lip_1)[0]
                edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i + 1]]

        for i, lip_def in enumerate(self.bones['def'][b_lip_2]):
            lip_def_eb = edit_bones[lip_def]
            lip_ctrl = self.get_ctrls_by_position(lip_def_eb.head, b_lip_2)[0]
            edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i]]
            if lip_def == self.bones['def'][b_lip_2][-1]:
                lip_ctrl = self.get_ctrls_by_position(lip_def_eb.tail, b_lip_2)[0]
                edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[i + 1]]

        t_lip_1 = strip_org(self.mouth_bones['top'][0])     # 1st top lip quarter
        t_lip_2 = strip_org(self.mouth_bones['top'][1])

        for i, lip_def in enumerate(self.bones['def'][t_lip_1]):
            lip_def_eb = edit_bones[lip_def]
            lip_ctrl = self.get_ctrls_by_position(lip_def_eb.head, t_lip_1)[0]
            edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[-2]]

        for i, lip_def in enumerate(self.bones['def'][t_lip_2]):
            lip_def_eb = edit_bones[lip_def]
            lip_ctrl = self.get_ctrls_by_position(lip_def_eb.head, t_lip_2)[0]
            edit_bones[lip_ctrl].parent = edit_bones[jaw_masters[-2]]

        super(Rig, self).parent_bones()

    def generate(self):

        self.create_mch()
        self.create_def()
        self.create_controls()

        self.make_constraints()
        self.parent_bones()
        self.make_drivers()

        return [""]
