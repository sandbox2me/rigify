# ##### BEGIN GPL LICENSE BLOCK #####
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
# ##### END GPL LICENSE BLOCK #####

import bpy
from mathutils import Vector

from ...utils import new_bone, copy_bone
from ...utils import make_mechanism_name, make_deformer_name, strip_org
from ...utils import create_bone_widget, create_widget, create_cube_widget
from ...utils import connected_children_names, has_connected_children
from ...utils import align_bone_x_axis

from . import pantin_utils


class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.params = params

        bones = obj.data.bones
        self.mouth = bone_name
        self.ur, self.uc, self.ul = (
            b.name for b in bones[self.mouth].children_recursive[:3])
        self.lr, self.lc, self.ll = (
            b.name for b in bones[self.ul].children_recursive[:3])

        self.org_bones = [self.mouth,
                          self.ur, self.lr,
                          self.uc, self.lc,
                          self.ul, self.ll
                          ]

        # Get (optional) parent
        if self.obj.data.bones[bone_name].parent is None:
            self.org_parent = None
        else:
            self.org_parent = self.obj.data.bones[bone_name].parent.name

    def generate(self):
        bpy.ops.object.mode_set(mode='EDIT')

        ctrl_chain = []

        eb = self.obj.data.edit_bones

        # Control bones
        # Global control
        ctrl_g = copy_bone(self.obj, self.mouth, strip_org(self.mouth))
        ctrl_g_eb = eb[ctrl_g]
        ctrl_chain.append(ctrl_g)
        if self.org_parent is not None:
            ctrl_g_eb.use_connect = False
            ctrl_g_eb.parent = eb[self.org_parent]
        
        # Right control
        ctrl_r_name = strip_org(self.ur.split('_')[0]+'.R')
        ctrl_r = new_bone(self.obj, ctrl_r_name)
        eb[ctrl_r].head = eb[self.ur].head
        eb[ctrl_r].tail = eb[self.ur].head + Vector((0, 0, 1)) * eb[self.ur].length

        # Left control
        ctrl_l_name = strip_org(self.ul.split('_')[0]+'.L')
        ctrl_l = new_bone(self.obj, ctrl_l_name)
        eb[ctrl_l].head = eb[self.ul].tail
        eb[ctrl_l].tail = eb[self.ul].tail + Vector((0, 0, 1)) * eb[self.ul].length

        # Up control
        ctrl_uc_name = strip_org(self.uc)
        ctrl_uc = new_bone(self.obj, ctrl_uc_name)
        eb[ctrl_uc].head = (eb[self.uc].head + eb[self.uc].tail) / 2
        eb[ctrl_uc].tail = eb[ctrl_uc].head + Vector((0, 0, 1)) * eb[self.uc].length

        # Down control
        ctrl_lc_name = strip_org(self.lc)
        ctrl_lc = new_bone(self.obj, ctrl_lc_name)
        eb[ctrl_lc].head = (eb[self.lc].head + eb[self.lc].tail) / 2
        eb[ctrl_lc].tail = eb[ctrl_lc].head + Vector((0, 0, 1)) * eb[self.lc].length
        
        for b in [ctrl_r, ctrl_uc, ctrl_lc, ctrl_l]:
            align_bone_x_axis(self.obj, b, Vector((-1, 0, 0)))
            eb[b].layers = eb[self.lc].layers
            eb[b].parent = eb[self.mouth]
            ctrl_chain.append(b)
            
        bpy.ops.object.mode_set(mode='OBJECT')
        pb = self.obj.pose.bones
        for b in [ctrl_r, ctrl_uc, ctrl_lc, ctrl_l]:
            pb[b].lock_location = (False, False, True)
            pb[b].lock_rotation = (True, True, False)
            pb[b].lock_rotation_w = False
            pb[b].lock_scale = (False, False, False)
            pb[b].rotation_mode = 'XZY'
        bpy.ops.object.mode_set(mode='EDIT')
        eb = self.obj.data.edit_bones

        # Stretch
        # RIGHT
        stretch_r_chain = []
        for bone in [self.ur, self.lr]:
            mch_b = copy_bone(self.obj, bone,
                              pantin_utils.strip_LR(
                                  make_mechanism_name(
                                      strip_org(bone))) + '.stretch.R')
            mch_eb = eb[mch_b]
            mch_eb.parent = eb[ctrl_r]
            stretch_r_chain.append(mch_b)

        # CENTER
        stretch_c_chain = []
        for bone in [self.uc, self.lc]:
            mch_b = copy_bone(self.obj, bone,
                              pantin_utils.strip_LR(
                                  make_mechanism_name(
                                      strip_org(bone))) + '.stretch')
            mch_eb = eb[mch_b]
            mch_eb.use_connect = False
            mch_eb.parent = eb[strip_org(bone)]
            stretch_c_chain.append(mch_b)

        #LEFT
        stretch_l_chain = []
        for i, bone in enumerate([self.ul, self.ll]):
            mch_b = copy_bone(self.obj, bone,
                              pantin_utils.strip_LR(
                                  make_mechanism_name(
                                      strip_org(bone))) + '.stretch.L')
            mch_eb = eb[mch_b]
            mch_eb.parent = eb[stretch_c_chain[i]]
            stretch_l_chain.append(mch_b)

        # Def bones
        Z_index = self.params.Z_index
        for i, b in enumerate([self.mouth,
                               stretch_l_chain[1],
                               stretch_r_chain[1],
                               stretch_c_chain[1],
                               stretch_l_chain[0],
                               stretch_r_chain[0],
                               stretch_c_chain[0],
                               ]):
            def_bone_name = b.split('.')[0][4:]
            if b[-1] in ('L', 'R'):
                def_bone_name += '.' + b[-1]
            def_bone = pantin_utils.create_deformation(
                self.obj, b,
                self.params.flip_switch,
                member_index=Z_index,
                bone_index=i, new_name=def_bone_name)
            if b == stretch_c_chain[1]:
                pantin_utils.create_deformation(
                    self.obj, b,
                    self.params.flip_switch,
                    member_index=Z_index,
                    bone_index=i+1, new_name=strip_org(self.org_bones[0])+'_int')

        bpy.ops.object.mode_set(mode='OBJECT')
        pb = self.obj.pose.bones

        # Widgets
        wgt_radius = pb[ctrl_uc].length / 3
        for b in [ctrl_r, ctrl_l, ctrl_uc, ctrl_lc]:
            pantin_utils.create_aligned_circle_widget(
                self.obj, b, radius=wgt_radius)
        pantin_utils.create_aligned_circle_widget(
            self.obj, ctrl_g, radius=pb[ctrl_g].length,
            head_tail=0.0, width_ratio=2.0)

        # Constraints
        for src_b, target_b in zip(stretch_r_chain, stretch_c_chain):
            mch_pb = pb[src_b]
            con = mch_pb.constraints.new('STRETCH_TO')
            con.name = "stretch to"
            con.target = self.obj
            con.subtarget = target_b
            con.volume = 'NO_VOLUME'
            con.rest_length = mch_pb.length
            con.keep_axis = 'PLANE_Z'
        for src_b in stretch_l_chain:
            mch_pb = pb[src_b]
            con = mch_pb.constraints.new('STRETCH_TO')
            con.name = "stretch to"
            con.target = self.obj
            con.subtarget = ctrl_l
            con.volume = 'NO_VOLUME'
            con.rest_length = mch_pb.length
            con.keep_axis = 'PLANE_Z'

        for org, ctrl in zip(self.org_bones,
                             [ctrl_g] +
                             stretch_r_chain +
                             stretch_c_chain +
                             stretch_l_chain):
            con = pb[org].constraints.new('COPY_TRANSFORMS')
            con.name = "copy_transforms"
            con.target = self.obj
            con.subtarget = ctrl


def add_parameters(params):
    params.Z_index = bpy.props.FloatProperty(
        name="Z index", default=0.0, description="Defines member's Z order")
    params.flip_switch = bpy.props.BoolProperty(
        name="Flip Switch", default=False,
        description="This member may change depth when flipped")


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters.
    """
    r = layout.row()
    r.prop(params, "Z_index")
    r = layout.row()
    r.prop(params, "flip_switch")


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('Mouth')
    bone.head[:] = 0.0629, -0.0450, 1.4873
    bone.tail[:] = 0.0629, -0.0450, 1.5074
    bone.roll = 3.1416
    bone.use_connect = False
    bones['Mouth'] = bone.name
    bone = arm.edit_bones.new('Mouth_upper.R')
    bone.head[:] = 0.0417, -0.0450, 1.4935
    bone.tail[:] = 0.0539, -0.0450, 1.4973
    bone.roll = -1.8728
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['Mouth']]
    bones['Mouth_upper.R'] = bone.name
    bone = arm.edit_bones.new('Mouth_upper')
    bone.head[:] = 0.0539, -0.0450, 1.4973
    bone.tail[:] = 0.0718, -0.0450, 1.4973
    bone.roll = -1.5708
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Mouth_upper.R']]
    bones['Mouth_upper'] = bone.name
    bone = arm.edit_bones.new('Mouth_upper.L')
    bone.head[:] = 0.0718, -0.0450, 1.4973
    bone.tail[:] = 0.0841, -0.0450, 1.4935
    bone.roll = -1.2712
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Mouth_upper']]
    bones['Mouth_upper.L'] = bone.name
    bone = arm.edit_bones.new('Mouth_lower.R')
    bone.head[:] = 0.0417, -0.0450, 1.4935
    bone.tail[:] = 0.0539, -0.0450, 1.4898
    bone.roll = -1.2763
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['Mouth_upper.L']]
    bones['Mouth_lower.R'] = bone.name
    bone = arm.edit_bones.new('Mouth_lower')
    bone.head[:] = 0.0539, -0.0450, 1.4898
    bone.tail[:] = 0.0718, -0.0450, 1.4898
    bone.roll = -1.5708
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Mouth_lower.R']]
    bones['Mouth_lower'] = bone.name
    bone = arm.edit_bones.new('Mouth_lower.L')
    bone.head[:] = 0.0718, -0.0450, 1.4898
    bone.tail[:] = 0.0841, -0.0450, 1.4935
    bone.roll = -1.8630
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Mouth_lower']]
    bones['Mouth_lower.L'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Mouth']]
    pbone.rigify_type = 'pantin.mouth'
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Mouth_upper.R']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, True)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Mouth_upper']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, True)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Mouth_upper.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, True)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Mouth_lower.R']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, True)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Mouth_lower']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, True)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Mouth_lower.L']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, True)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'

    bpy.ops.object.mode_set(mode='EDIT')
    for bone in arm.edit_bones:
        bone.select = False
        bone.select_head = False
        bone.select_tail = False
    for b in bones:
        bone = arm.edit_bones[bones[b]]
        bone.select = True
        bone.select_head = True
        bone.select_tail = True
        arm.edit_bones.active = bone
