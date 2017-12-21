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
import importlib

from rigify.utils import copy_bone
from rigify.utils import make_deformer_name, strip_org
from rigify.utils import create_bone_widget, create_widget, create_cube_widget
from rigify.utils import connected_children_names, has_connected_children
from rigify.utils import get_layers

from . import pantin_utils
from . import limb_common

importlib.reload(pantin_utils)
importlib.reload(limb_common)

script = """
ik_arm = ["%s", "%s", "%s"]
fk_arm = ["%s", "%s", "%s"]
if is_selected(ik_arm):
    layout.prop(pose_bones[ik_arm[2]],
                '["pelvis_follow"]',
                text="Follow pelvis (" + ik_arm[2] + ")",
                slider=True
                )
if is_selected(ik_arm + fk_arm):
    layout.prop(pose_bones[ik_arm[2]],
                '["IK_FK"]',
                text="IK FK (" + ik_arm[2] + ")",
                slider=True
                )
if is_selected(fk_arm):
    layout.prop(pose_bones[fk_arm[0]],
                '["follow"]',
                text="Follow (" + fk_arm[0] + ")",
                slider=True)
"""


class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.org_bones = ([bone_name]
                          + connected_children_names(obj, bone_name)[:2])
        self.params = params

        if params.duplicate_lr:
            sides = ['.L', '.R']
        else:
            sides = [params.side]

        self.sides = {}
        for s in sides:
            side_org_bones = limb_common.create_side_org_bones(
                self.obj, self.org_bones, params.duplicate_lr, s
            )
            self.sides[s] = [side_org_bones]
            self.sides[s].append(limb_common.IKLimb(obj,
                                                    self.org_bones,
                                                    side_org_bones,
                                                    params.do_flip,
                                                    True,
                                                    params.pelvis_name,
                                                    s,
                                                    ik_limits=[-160.0, 0.0]))
            self.sides[s].append(limb_common.FKLimb(obj,
                                                    self.org_bones,
                                                    side_org_bones,
                                                    params.do_flip,
                                                    True,
                                                    params.pelvis_name,
                                                    s))

    def generate(self):
        ui_script = ""
        for s, limb in self.sides.items():
            side_org_bones, ik_limb, fk_limb = limb
            (ulimb_ik, ulimb_str, flimb_ik, flimb_str, joint_str,
                elimb_ik, elimb_str) = (ik_limb.generate())
            (ulimb_fk, flimb_fk, elimb_fk) = (fk_limb.generate())

            bpy.ops.object.mode_set(mode='EDIT')

            # Def bones
            eb = self.obj.data.edit_bones
            if s == '.L':
                Z_index = -self.params.Z_index
            else:
                Z_index = self.params.Z_index

            for i, b in enumerate(side_org_bones):
                def_bone_name = pantin_utils.strip_LR_numbers(strip_org(b))
                def_bone = pantin_utils.create_deformation(
                    self.obj,
                    b,
                    self.params.flip_switch, member_index=Z_index,
                    bone_index=i, new_name=def_bone_name + s)

            # Set layers if specified
            active_layer = pantin_utils.layers_to_index(eb[ulimb_ik].layers)
            right_offset = self.params.right_offset if self.params.duplicate_lr else 0
            if s == '.R':
                for b in (ulimb_ik, joint_str, elimb_ik):
                    eb[b].layers = get_layers(active_layer
                                              + right_offset)
                for b in (ulimb_fk, flimb_fk, elimb_fk):
                    eb[b].layers = get_layers(active_layer
                                              + self.params.fk_offset
                                              + right_offset)
            elif s == '.L':
                for b in (ulimb_fk, flimb_fk, elimb_fk):
                    eb[b].layers = get_layers(active_layer
                                              + self.params.fk_offset)

            bpy.ops.object.mode_set(mode='OBJECT')
            pb = self.obj.pose.bones

            # Widgets
            # IK
            global_scale = self.obj.dimensions[2]
            member_factor = 0.06
            if s == '.R':
                side_factor = 1.2
            else:
                side_factor = 1.0
            widget_size = global_scale * member_factor * side_factor
            pantin_utils.create_aligned_circle_widget(
                self.obj, ulimb_ik, number_verts=3, radius=widget_size)
            pantin_utils.create_aligned_circle_widget(
                self.obj, joint_str, radius=widget_size * 0.7)
            pantin_utils.create_aligned_circle_widget(
                self.obj, elimb_ik, radius=widget_size)

            # FK
            widget_size = 0.5
            for bone in (ulimb_fk, flimb_fk, elimb_fk):
                pantin_utils.create_capsule_widget(
                    self.obj,
                    bone,
                    length=widget_size,
                    width=widget_size*0.2,
                    head_tail=0.5,
                    horizontal=False,
                    overshoot=True
                )

            # Constraints
            for org, ctrl in zip(side_org_bones, [ulimb_str,
                                                  flimb_str,
                                                  elimb_str]):
                con = pb[org].constraints.new('COPY_TRANSFORMS')
                con.name = "copy_ik"
                con.target = self.obj
                con.subtarget = ctrl

            for org, ctrl in zip(side_org_bones, [ulimb_fk,
                                                  flimb_fk,
                                                  elimb_fk]):
                con = pb[org].constraints.new('COPY_TRANSFORMS')
                con.name = "copy_fk"
                con.target = self.obj
                con.subtarget = ctrl

                # Drivers
                driver = self.obj.driver_add(
                con.path_from_id("influence"))
                driver.driver.expression = 'fk'
                var_fk = driver.driver.variables.new()
                var_fk.type = 'SINGLE_PROP'
                var_fk.name = 'fk'
                var_fk.targets[0].id_type = 'OBJECT'
                var_fk.targets[0].id = self.obj
                var_fk.targets[0].data_path = 'pose.bones["{}"]["IK_FK"]'.format(elimb_ik)

            ui_script += script % (ulimb_ik, joint_str, elimb_ik,
                                   ulimb_fk, flimb_fk, elimb_fk, )

        return [ui_script]


def add_parameters(params):
    params.Z_index = bpy.props.FloatProperty(
        name="Z index",
        default=0.0,
        description="Defines member's Z order")
    params.flip_switch = bpy.props.BoolProperty(
        name="Flip Switch",
        default=True,
        description="This member may change depth when flipped")
    params.duplicate_lr = bpy.props.BoolProperty(
        name="Duplicate LR",
        default=True,
        description="Create two limbs for left and right")
    params.side = bpy.props.EnumProperty(
        name="Side",
        default='.R',
        description="If the limb is not to be duplicated, choose its side",
        items=(('.L', 'Left', ""),
               ('.R', 'Right', "")))
    params.do_flip = bpy.props.BoolProperty(
        name="Do Flip",
        default=True,
        description="True if the rig has a torso with flip system")
    params.pelvis_name = bpy.props.StringProperty(
        name="Pelvis Name",
        default="Pelvis",
        description="Name of the pelvis bone in whole rig")
    params.right_offset = bpy.props.IntProperty(
        name="Right Offset",
        default=16,
        description="Number of layers to offset the right side")
    params.fk_offset = bpy.props.IntProperty(
        name="FK Offset",
        default=1,
        description="Number of layers to offset the FK controls")
    # params.right_layers = bpy.props.BoolVectorProperty(
    #     size=32,
    #     description="Layers for the duplicated limb to be on")


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters.
    """
    r = layout.row()
    r.prop(params, "Z_index")
    r.prop(params, "flip_switch")
    c = layout.column()
    c.prop(params, "do_flip")
    c.prop(params, "pelvis_name")
    c.prop(params, "fk_offset")
    r = layout.row()
    r.prop(params, "duplicate_lr")

    if params.duplicate_lr:
        r.prop(params, "right_offset")
    else:
        r.prop(params, "side", expand=True)
        if params.side == ".R":
            layout.prop(params, "right_offset")


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('Arm')
    bone.head[:] = -0.0488, 0.0000, 1.3385
    bone.tail[:] = -0.0929, 0.0000, 1.1169
    bone.roll = 0.1969
    bone.use_connect = False
    bones['Arm'] = bone.name
    bone = arm.edit_bones.new('Forearm')
    bone.head[:] = -0.0929, 0.0000, 1.1169
    bone.tail[:] = -0.0646, 0.0000, 0.8523
    bone.roll = -0.1069
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Arm']]
    bones['Forearm'] = bone.name
    bone = arm.edit_bones.new('Hand')
    bone.head[:] = -0.0646, 0.0000, 0.8523
    bone.tail[:] = -0.0646, 0.0000, 0.7518
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Forearm']]
    bones['Hand'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Arm']]
    pbone.rigify_type = 'pantin.arm'
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    try:
        pbone.rigify_parameters.right_layers = [False, False, False, False,
                                                False, False, False, False,
                                                False, False, False, False,
                                                False, False, False, False,
                                                False, False, False, False,
                                                True, False, False, False,
                                                False, False, False, False,
                                                False, False, False, False]
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.pelvis_name = "Pelvis"
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.duplicate_lr = True
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.Z_index = 3.0
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['Forearm']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Hand']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
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
