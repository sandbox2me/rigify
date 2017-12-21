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

from ...utils import copy_bone
from ...utils import make_mechanism_name, make_deformer_name, strip_org
from ...utils import create_bone_widget, create_widget, create_cube_widget
from ...utils import connected_children_names, has_connected_children

from . import pantin_utils

class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.params = params

        # self.head = connected_children_names(self.obj, bone_name)[0]

        self.org_bone = bone_name

    def generate(self):
        bpy.ops.object.mode_set(mode='EDIT')

        eb = self.obj.data.edit_bones

        trackers = []
        flaps = []

        # Left and right tracking bones
        for side in ['.L', '.R']:
            tracker = copy_bone(
                self.obj, self.org_bone,
                make_mechanism_name(
                    strip_org(self.org_bone)) + side
            )
            trackers.append(tracker)

        # Front and rear bones
        for i, flap in enumerate(['.Front', '.Rear']):
            flap_b = copy_bone(
                self.obj, self.org_bone,
                make_mechanism_name(
                    strip_org(self.org_bone)) + flap
            )
            flaps.append(flap_b)

            # Def bones
            def_bone = pantin_utils.create_deformation(
                self.obj, flap_b,
                flip_switch=True,
                member_index=self.params.Z_index,
                bone_index=i,
                new_name=strip_org(self.org_bone) + flap)

        # Parenting
        if self.params.detach:
            eb[self.head].use_connect = False

        bpy.ops.object.mode_set(mode='OBJECT')
        pb = self.obj.pose.bones

        # Constraints

        for f, shin in zip(trackers, (self.params.shin_name_l,
                                   self.params.shin_name_r)
                           ):
            con = pb[f].constraints.new('DAMPED_TRACK')
            con.name = "Track " + shin
            con.target = self.obj
            con.subtarget = "ORG-" + shin

        for f_i, f in enumerate(flaps):
            for s_i, shin in enumerate((self.params.shin_name_l, self.params.shin_name_r)):
                con = pb[f].constraints.new('DAMPED_TRACK')
                con.name = "Track " + shin
                con.target = self.obj
                con.subtarget = "ORG-" + shin

                # Drivers
                driver = self.obj.driver_add(con.path_from_id("influence"))

                # Relative component: which leg to track
                if f_i != s_i:
                    relative = 'L > R'
                else:
                    relative = 'L <= R'

                if s_i == 0:  # Left
                    absolute = 'L '
                else:  # Right
                    absolute = 'R '

                # Absolute component: do not track if rotation is below / above 0
                if f_i == 0:  # Front
                    absolute += ' < 0'
                else:  # Rear
                    absolute += ' > 0'

                driver.driver.expression = '1 if {} and {} else 0'.format(relative, absolute)

                var = driver.driver.variables.new()
                var.type = 'TRANSFORMS'
                var.name = 'L'
                var.targets[0].id = self.obj
                var.targets[0].bone_target = trackers[0]
                var.targets[0].transform_type = 'ROT_Z'
                var.targets[0].transform_space = 'LOCAL_SPACE'

                var = driver.driver.variables.new()
                var.type = 'TRANSFORMS'
                var.name = 'R'
                var.targets[0].id = self.obj
                var.targets[0].bone_target = trackers[1]
                var.targets[0].transform_type = 'ROT_Z'
                var.targets[0].transform_space = 'LOCAL_SPACE'

        #     # hack: apply bas rotation
        # for f in trackers:
        #     # bpy.ops.object.mode_set(mode='OBJECT')
        #     m = self.obj.pose.bones[f].matrix.copy()
        #     bpy.ops.object.mode_set(mode='EDIT')
        #     self.obj.data.edit_bones[f].matrix = m
        #     bpy.ops.object.mode_set(mode='OBJECT')
        # return []


def add_parameters(params):
    params.Z_index = bpy.props.FloatProperty(
        name="Z index", default=0.0, description="Defines member's Z order")
    params.shin_name_l = bpy.props.StringProperty(
        name="Left Shin Name", default="Shin.L",
        description="The left shin bone for the skirt to track")
    params.shin_name_r = bpy.props.StringProperty(
        name="Right Shin Name", default="Shin.R",
        description="The right shin bone for the skirt to track")


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters.
    """
    r = layout.row()
    r.prop(params, "Z_index")
    r = layout.row()
    r.prop(params, "shin_name_l")
    r = layout.row()
    r.prop(params, "shin_name_r")


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('Skirt')
    bone.head[:] = -0.0029, 0.0000, 0.8893
    bone.tail[:] = -0.0242, 0.0000, 0.5546
    bone.roll = 0.0634
    bone.use_connect = False
    bones['Skirt'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Skirt']]
    pbone.rigify_type = 'pantin.skirt'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
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
