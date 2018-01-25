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
from rna_prop_ui import rna_idprop_ui_prop_get
from mathutils import Vector
from math import radians, degrees
import importlib

from ...utils import copy_bone, new_bone, put_bone
from ...utils import make_mechanism_name, make_deformer_name, strip_org
from ...utils import connected_children_names, has_connected_children
from ...utils import align_bone_x_axis

from . import pantin_utils

importlib.reload(pantin_utils)


def create_side_org_bones(obj, org_bones, duplicate, side_suffix):
    """Copy originals with side suffix"""
    bpy.ops.object.mode_set(mode='EDIT')
    eb = obj.data.edit_bones

    side_org_bones = []
    if duplicate:
        for b in org_bones:
            side_org_bone = copy_bone(
                obj, b,
                pantin_utils.strip_LR_numbers(b) + side_suffix)
            side_org_bones.append(side_org_bone)
            eb[side_org_bone].layers = [
                False if i != 31 else True for i in range(32)
            ]
    else:
        side_org_bones = org_bones

    return side_org_bones


class IKLimb:
    def __init__(self,
                 obj,
                 org_bones,
                 side_org_bones,
                 do_flip,
                 pelvis_follow,
                 pelvis_name,
                 side_suffix='',
                 ik_limits=[-150.0, 150.0, 0.0, 160.0]):
        self.obj = obj

        # Get the chain of 3 connected bones
        self.org_bones = org_bones
        self.side_org_bones = side_org_bones

        # Get (optional) parent
        if self.obj.data.bones[org_bones[0]].parent is None:
            self.org_parent = None
        else:
            self.org_parent = self.obj.data.bones[org_bones[0]].parent.name

        self.side_suffix = side_suffix
        self.ik_limits = ik_limits
        self.do_flip = do_flip
        self.pelvis_follow = pelvis_follow
        self.pelvis_name = pelvis_name

    def generate(self):
        bpy.ops.object.mode_set(mode='EDIT')

        eb = self.obj.data.edit_bones

        # Create the control bones
        ulimb_ik = copy_bone(
            self.obj,
            self.org_bones[0],
            pantin_utils.strip_LR_numbers(
                strip_org(self.org_bones[0])) +'.IK' + self.side_suffix)
        flimb_ik = copy_bone(
            self.obj,
            self.org_bones[1],
            make_mechanism_name(
                pantin_utils.strip_LR_numbers(
                    strip_org(self.org_bones[1])) +'.IK' + self.side_suffix))
        elimb_ik = copy_bone(
            self.obj,
            self.org_bones[2],
            pantin_utils.strip_LR_numbers(
                strip_org(self.org_bones[2])) +'.IK' + self.side_suffix)

        ulimb_str = copy_bone(
            self.obj,
            self.org_bones[0],
            make_mechanism_name(
                pantin_utils.strip_LR_numbers(
                    strip_org(
                        self.org_bones[0]
                    )) + ".stretch.ik" + self.side_suffix))
        flimb_str = copy_bone(
            self.obj,
            self.org_bones[1],
            make_mechanism_name(
                pantin_utils.strip_LR_numbers(
                    strip_org(
                        self.org_bones[1]
                    )) + ".stretch.ik" + self.side_suffix))
        elimb_str = copy_bone(
            self.obj,
            self.org_bones[2],
            make_mechanism_name(
                pantin_utils.strip_LR_numbers(
                    strip_org(
                        self.org_bones[2]
                    )) + ".stretch.ik" + self.side_suffix))

        joint_str = new_bone(self.obj,
                             pantin_utils.strip_LR_numbers(
                                 strip_org(self.org_bones[1]))
                             + '.IK' + self.side_suffix)
        eb[joint_str].head = eb[flimb_str].head
        eb[joint_str].tail = (eb[flimb_str].head
                              + Vector((0, 0, 1)) * eb[flimb_str].length/2)
        align_bone_x_axis(self.obj, joint_str, Vector((-1, 0, 0)))
        # put_bone(self.obj, joint_str, Vector(eb[flimb_str].head))

        # Pelvis follow
        elimb_ik_root = copy_bone(
            self.obj,
            self.org_bones[2],
            make_mechanism_name(
                pantin_utils.strip_LR_numbers(
                    strip_org(
                        self.org_bones[2]
                    )) + ".ik_root" + self.side_suffix))
        elimb_ik_parent = copy_bone(
            self.obj,
            self.org_bones[2],
            make_mechanism_name(
                pantin_utils.strip_LR_numbers(
                    strip_org(
                        self.org_bones[2]
                    )) + ".ik_parent" + self.side_suffix))
        elimb_ik_socket = copy_bone(
            self.obj,
            self.org_bones[2],
            make_mechanism_name(
                pantin_utils.strip_LR_numbers(
                    strip_org(
                        self.org_bones[2]
                    )) + ".ik_socket" + self.side_suffix))

        # Get edit bones
        ulimb_ik_e = eb[ulimb_ik]
        flimb_ik_e = eb[flimb_ik]
        elimb_ik_e = eb[elimb_ik]

        ulimb_str_e = eb[ulimb_str]
        flimb_str_e = eb[flimb_str]
        elimb_str_e = eb[elimb_str]

        joint_str_e = eb[joint_str]

        elimb_ik_root_e = eb[elimb_ik_root]
        elimb_ik_parent_e = eb[elimb_ik_parent]
        elimb_ik_socket_e = eb[elimb_ik_socket]

        # Parenting

        # Side org chain
        for b, o_b in zip(self.side_org_bones[1:], self.org_bones[1:]):
            eb[b].parent = eb[
                pantin_utils.strip_LR_numbers(
                    eb[o_b].parent.name) + self.side_suffix]

        if self.org_parent is not None:
            ulimb_ik_e.use_connect = False
            ulimb_ik_e.parent = eb[self.org_parent]

        flimb_ik_e.use_connect = False
        flimb_ik_e.parent = ulimb_ik_e

        elimb_ik_root_e.use_connect = False
        elimb_ik_root_e.parent = None
        elimb_ik_parent_e.use_connect = False
        elimb_ik_parent_e.parent = eb[self.side_org_bones[0]].parent
        elimb_ik_socket_e.use_connect = False
        elimb_ik_socket_e.parent = None
        elimb_ik_e.use_connect = False
        elimb_ik_e.parent = elimb_ik_socket_e

        if self.org_parent is not None:
            ulimb_str_e.use_connect = False
            ulimb_str_e.parent = eb[self.org_parent]

        flimb_str_e.use_connect = False
        flimb_str_e.parent = joint_str_e

        elimb_str_e.use_connect = True
        elimb_str_e.parent = flimb_ik_e

        joint_str_e.use_connect = False
        joint_str_e.parent = ulimb_ik_e

        # Layers
        joint_str_e.layers = elimb_str_e.layers
        # Object mode, get pose bones
        bpy.ops.object.mode_set(mode='OBJECT')
        pb = self.obj.pose.bones

        ulimb_ik_p = pb[ulimb_ik]
        flimb_ik_p = pb[flimb_ik]
        elimb_ik_p = pb[elimb_ik]

        ulimb_str_p = pb[ulimb_str]
        flimb_str_p = pb[flimb_str]
        elimb_str_p = pb[elimb_str]

        joint_str_p = pb[joint_str]

        joint_str_p.lock_location = (False, False, True)
        joint_str_p.lock_rotation = (True, True, False)
        joint_str_p.lock_rotation_w = False
        joint_str_p.lock_scale = (False, False, False)
        joint_str_p.rotation_mode = 'XZY'

        # Set up custom properties
        prop = rna_idprop_ui_prop_get(elimb_ik_p, "pelvis_follow", create=True)
        elimb_ik_p["pelvis_follow"] = int(self.pelvis_follow)
        prop["soft_min"] = 0
        prop["soft_max"] = 1
        prop["min"] = 0
        prop["max"] = 1

        prop = rna_idprop_ui_prop_get(elimb_ik_p, "IK_FK", create=True)
        elimb_ik_p["IK_FK"] = 0
        prop["soft_min"] = 0
        prop["soft_max"] = 1
        prop["min"] = 0
        prop["max"] = 1

        # Constraints
        # Bend hint, ripped off from Rigify' biped
        con = flimb_ik_p.constraints.new('LIMIT_ROTATION')
        con.name = "bend_hint"
        con.use_limit_z = True
        con.min_z = radians(45)
        con.max_z = radians(45)
        con.owner_space = 'LOCAL'

        con = flimb_ik_p.constraints.new('IK')
        con.name = "ik"
        con.target = self.obj
        con.subtarget = elimb_ik
        con.chain_count = 2

        con = ulimb_str_p.constraints.new('COPY_LOCATION')
        con.name = "anchor"
        con.target = self.obj
        con.subtarget = ulimb_ik
        con.target_space = 'LOCAL'
        con.owner_space = 'LOCAL'

        con = elimb_str_p.constraints.new('COPY_ROTATION')
        con.name = "copy rotation"
        con.target = self.obj
        con.subtarget = elimb_ik
        con.target_space = 'POSE'
        con.owner_space = 'POSE'

        con = ulimb_str_p.constraints.new('STRETCH_TO')
        con.name = "stretch to"
        con.target = self.obj
        con.subtarget = joint_str
        con.volume = 'NO_VOLUME'
        con.rest_length = ulimb_str_p.length
        con.keep_axis = 'PLANE_Z'

        con = flimb_str_p.constraints.new('STRETCH_TO')
        con.name = "stretch to"
        con.target = self.obj
        con.subtarget = elimb_str
        con.volume = 'NO_VOLUME'
        con.rest_length = flimb_str_p.length
        con.keep_axis = 'PLANE_Z'

        # Pelvis follow
        con = pb[elimb_ik_socket].constraints.new('COPY_TRANSFORMS')
        con.name = "copy root"
        con.target = self.obj
        con.subtarget = elimb_ik_root

        con = pb[elimb_ik_socket].constraints.new('COPY_TRANSFORMS')
        con.name = "copy socket"
        con.target = self.obj
        con.subtarget = elimb_ik_parent

        # Drivers
        driver = self.obj.driver_add(con.path_from_id("influence"))
        driver.driver.expression = 'pelvis_follow'
        var = driver.driver.variables.new()

        var.type = 'SINGLE_PROP'
        var.name = 'pelvis_follow'
        var.targets[0].id_type = 'OBJECT'
        var.targets[0].id = self.obj
        var.targets[0].data_path = (pb[elimb_ik].path_from_id()
                                       + '["pelvis_follow"]')

        # IK Limits
        ulimb_ik_p.lock_ik_x = True
        ulimb_ik_p.lock_ik_y = True

        flimb_ik_p.lock_ik_x = True
        flimb_ik_p.lock_ik_y = True
        flimb_ik_p.use_ik_limit_z = True
        flimb_ik_p.ik_min_z = radians(self.ik_limits[0])  # 0.0
        flimb_ik_p.ik_max_z = radians(self.ik_limits[1])  # radians(160.0)

        # Arm ik angle fix
        limb_angle = ulimb_ik_p.vector.xz.angle_signed(flimb_ik_p.vector.xz)
        if self.ik_limits[0] < 0:  # folds counterclockwise (arms)
            # has to be slightly less than the original angle
            flimb_ik_p.ik_max_z = -limb_angle - .02
        else:
            # has to be slightly more than the original angle
            flimb_ik_p.ik_min_z = -limb_angle + .02

        return [ulimb_ik, ulimb_str,
                flimb_ik, flimb_str,
                joint_str,
                elimb_ik, elimb_str]


class FKLimb:
    def __init__(self,
                 obj,
                 org_bones,
                 side_org_bones,
                 do_flip,
                 pelvis_follow,
                 pelvis_name,
                 side_suffix='',):
        self.obj = obj

        # Get the chain of 3 connected bones
        self.org_bones = org_bones  # [bone1, bone2, bone3]
        self.side_org_bones = side_org_bones  # [bone1, bone2, bone3]

        # Get (optional) parent
        if self.obj.data.bones[org_bones[0]].parent is None:
            self.org_parent = None
        else:
            self.org_parent = self.obj.data.bones[org_bones[0]].parent.name

        self.side_suffix = side_suffix
        self.do_flip = do_flip
        self.pelvis_follow = pelvis_follow
        self.pelvis_name = pelvis_name

    def generate(self):
        bpy.ops.object.mode_set(mode='EDIT')

        eb = self.obj.data.edit_bones

        # Create the control bones

        ulimb_fk_name = pantin_utils.strip_LR_numbers(
            strip_org(self.org_bones[0])) + '.FK' + self.side_suffix
        follow_name = pantin_utils.strip_LR_numbers(
            make_mechanism_name(
                strip_org(
                    self.org_bones[0])
                )
            ) + '.FK.follow' + self.side_suffix
        target = eb[self.org_bones[0]].parent_recursive[-1].name
        target = strip_org(target)
        ulimb_fk, ulimb_follow = pantin_utils.make_follow(
            self.obj,
            self.org_bones[0],
            target,
            ctrl_name=ulimb_fk_name,
            follow_name=follow_name)
        flimb_fk = copy_bone(
            self.obj,
            self.org_bones[1],
            pantin_utils.strip_LR_numbers(
                strip_org(self.org_bones[1])) + '.FK' + self.side_suffix)
        elimb_fk = copy_bone(
            self.obj,
            self.org_bones[2],
            pantin_utils.strip_LR_numbers(
                strip_org(self.org_bones[2])) + '.FK' + self.side_suffix)

        # Get edit bones
        ulimb_fk_e = eb[ulimb_fk]
        flimb_fk_e = eb[flimb_fk]
        elimb_fk_e = eb[elimb_fk]

        # Parenting

        # Side org chain
        for b, o_b in zip(self.side_org_bones[1:], self.org_bones[1:]):
            eb[b].parent = eb[
                pantin_utils.strip_LR_numbers(
                    eb[o_b].parent.name) + self.side_suffix]


        flimb_fk_e.parent = ulimb_fk_e
        elimb_fk_e.parent = flimb_fk_e

        # Object mode, get pose bones
        bpy.ops.object.mode_set(mode='OBJECT')
        pb = self.obj.pose.bones

        ulimb_fk_p = pb[ulimb_fk]
        flimb_fk_p = pb[flimb_fk]
        elimb_fk_p = pb[elimb_fk]

        # Set up custom properties
        prop = rna_idprop_ui_prop_get(ulimb_fk_p, "pelvis_follow", create=True)
        ulimb_fk_p["pelvis_follow"] = int(self.pelvis_follow)
        prop["soft_min"] = 0
        prop["soft_max"] = 1
        prop["min"] = 0
        prop["max"] = 1


        return [ulimb_fk,
                flimb_fk,
                elimb_fk]
