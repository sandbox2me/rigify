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
from math import pi, radians
from mathutils import Vector
import importlib

from ...utils import new_bone, copy_bone, flip_bone
from ...utils import make_mechanism_name, make_deformer_name, strip_org
from ...utils import create_bone_widget, create_widget, create_cube_widget
from ...utils import connected_children_names, has_connected_children
from ...utils import align_bone_x_axis
from ...utils import get_layers

from . import pantin_utils
from . import limb_common

importlib.reload(pantin_utils)
importlib.reload(limb_common)

script = """
ik_leg = ["%s", "%s", "%s", "%s"]
fk_leg = ["%s", "%s", "%s", "%s"]
if is_selected(ik_leg):
    layout.prop(pose_bones[ik_leg[2]],
                '["pelvis_follow"]',
                text="Follow pelvis (" + ik_leg[2] + ")",
                slider=True
                )
if is_selected(ik_leg + fk_leg):
    layout.prop(pose_bones[ik_leg[2]],
                '["IK_FK"]',
                text="IK FK (" + ik_leg[2] + ")",
                slider=True
                )
if is_selected(fk_leg):
    layout.prop(pose_bones[fk_leg[0]],
                '["follow"]',
                text="Follow (" + fk_leg[0] + ")",
                slider=True)
"""


class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj

        bones = obj.data.bones
        leg = bone_name
        shin = bones[leg].children[0].name
        for b in bones[shin].children:
            if not b.use_connect:
                continue
            print(b.name)
            if b.children:
                foot = b.name
            else:
                heel = b.name
        for b in bones[foot].children:
            if b.use_connect:
                toe = b.name
        # toe = bones[foot].children[0].name
        # roll = bones[toe].children[0].name

        self.org_bones = [leg, shin, foot, heel, toe]
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
            self.sides[s].append(limb_common.IKLimb(
                                 obj,
                                 self.org_bones[:3],
                                 side_org_bones,
                                 params.do_flip,
                                 False,
                                 params.pelvis_name,
                                 s,
                                 ik_limits=[0.0, 160.0]))
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
                elimb_ik, elimb_str) = ik_limb.generate()

            ulimb_fk, flimb_fk, elimb_fk = fk_limb.generate()

            bpy.ops.object.mode_set(mode='EDIT')
            eb = self.obj.data.edit_bones

            # Foot rig
            foot_fr = copy_bone(
                self.obj, self.org_bones[2],
                pantin_utils.strip_LR_numbers(
                    make_mechanism_name(
                        strip_org(self.org_bones[2]))) + '.fr' + s)
            foot_tgt = copy_bone(
                self.obj, self.org_bones[2],
                pantin_utils.strip_LR_numbers(
                    make_mechanism_name(
                        strip_org(self.org_bones[2]))) + '.tgt' + s)
            heel_fr = copy_bone(
                self.obj, self.org_bones[3],
                pantin_utils.strip_LR_numbers(
                    make_mechanism_name(
                        strip_org(self.org_bones[3]))) + '.fr' + s)
            toe_fr = copy_bone(
                self.obj, self.org_bones[4],
                pantin_utils.strip_LR_numbers(
                    make_mechanism_name(
                        strip_org(self.org_bones[4]))) + '.fr' + s)
            toe_ik_ctl = copy_bone(
                self.obj, self.org_bones[4],
                pantin_utils.strip_LR_numbers(
                    strip_org(self.org_bones[4])) + '.IK' + s)
            toe_fk_ctl = copy_bone(
                self.obj, self.org_bones[4],
                pantin_utils.strip_LR_numbers(
                    strip_org(self.org_bones[4])) + '.FK' + s)
            toe_pos = copy_bone(
                self.obj, self.org_bones[4],
                pantin_utils.strip_LR_numbers(
                    make_mechanism_name(
                        strip_org(self.org_bones[4]))) + '.pos' + s)
            roll_fr = new_bone(
                self.obj, "Foot roll" + s)

            # Position
            eb[roll_fr].head = (eb[elimb_str].head
                                + Vector(
                                    (-1, 0, 0)
                                    ) * eb[elimb_str].length * 2)
            eb[roll_fr].tail = (eb[elimb_str].head
                                + Vector(
                                    (-1, 0, 1)
                                    ) * eb[elimb_str].length * 2)
            eb[roll_fr].layers = eb[elimb_ik].layers

            # IK foot horizontal and starting at heel
            eb[elimb_ik].head = eb[heel_fr].tail
            eb[elimb_ik].tail.z = eb[heel_fr].tail.z
            align_bone_x_axis(self.obj, elimb_ik, Vector((0, 0, 1)))

            align_bone_x_axis(self.obj, roll_fr, Vector((-1, 0, 0)))
            align_bone_x_axis(self.obj, foot_fr, Vector((-1, 0, 0)))
            align_bone_x_axis(self.obj, heel_fr, Vector((-1, 0, 0)))
            align_bone_x_axis(self.obj, toe_fr, Vector((-1, 0, 0)))

            # Parenting
            eb[foot_fr].parent = None
            eb[heel_fr].parent = None
            eb[toe_fr].parent = None

            flip_bone(self.obj, foot_fr)
            flip_bone(self.obj, heel_fr)
            flip_bone(self.obj, toe_fr)

            eb[foot_fr].use_connect = True
            eb[foot_fr].parent = eb[toe_fr]

            eb[foot_tgt].use_connect = True
            eb[foot_tgt].parent = eb[foot_fr]

            eb[toe_fr].use_connect = False
            eb[toe_fr].parent = eb[heel_fr]

            eb[toe_ik_ctl].use_connect = True
            eb[toe_ik_ctl].parent = eb[toe_fr]

            eb[toe_fk_ctl].use_connect = True
            eb[toe_fk_ctl].parent = eb[elimb_fk]

            eb[toe_pos].use_connect = False
            eb[toe_pos].parent = eb[elimb_str]

            eb[heel_fr].use_connect = False
            eb[heel_fr].parent = eb[elimb_ik]

            eb[roll_fr].use_connect = False
            eb[roll_fr].parent = eb[elimb_ik]

            if self.params.do_stretch:
                eb[elimb_str].use_connect = False

            # Def bones
            if s == '.L':
                Z_index = -self.params.Z_index
            else:
                Z_index = self.params.Z_index

            side_org_bones = side_org_bones[:3] + side_org_bones[-1:] # Ignore heel
            for i, b in enumerate(side_org_bones):
                def_bone_name = pantin_utils.strip_LR_numbers(strip_org(b))
                def_bone = pantin_utils.create_deformation(
                    self.obj, b,
                    self.params.flip_switch,
                    member_index=Z_index,
                    bone_index=i, new_name=def_bone_name+s)


            # Set layers if specified
            active_layer = pantin_utils.layers_to_index(eb[ulimb_ik].layers)
            right_offset = self.params.right_offset if self.params.duplicate_lr else 0
            if s == '.R':
                for b in (ulimb_ik, joint_str, elimb_ik, roll_fr, toe_ik_ctl):
                    eb[b].layers = get_layers(active_layer
                                              + right_offset)
                for b in (ulimb_fk, flimb_fk, elimb_fk, toe_fk_ctl):
                    eb[b].layers = get_layers(active_layer
                                              + self.params.fk_offset
                                              + right_offset)
            elif s == '.L':
                for b in (ulimb_fk, flimb_fk, elimb_fk, toe_fk_ctl):
                    eb[b].layers = get_layers(active_layer
                                              + self.params.fk_offset)

            bpy.ops.object.mode_set(mode='OBJECT')
            pb = self.obj.pose.bones

            # Bone settings
            pb[roll_fr].rotation_mode = 'XZY'
            pb[roll_fr].lock_location = [True]*3
            pb[roll_fr].lock_rotation = [True, True, False]
            pb[roll_fr].lock_scale = [True]*3
            pb[foot_fr].rotation_mode = 'XZY'

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
                self.obj, joint_str, radius=widget_size)

            # FK
            widget_size = 0.5
            for bone in (ulimb_fk, flimb_fk, elimb_fk, toe_fk_ctl):
                pantin_utils.create_capsule_widget(
                    self.obj,
                    bone,
                    length=widget_size,
                    width=widget_size*0.2,
                    head_tail=0.5,
                    horizontal=False,
                    overshoot=True
                )

                # Default follow value
                pb[ulimb_fk]["follow"] = 0.0

            # Foot WGT
            down = pb[heel_fr].head.z
            left = pb[heel_fr].head.x - (side_factor - 1) * pb[heel_fr].length
            right = pb[foot_fr].head.x
            up = pb[foot_fr].tail.z + (side_factor - 1) * pb[heel_fr].length

            foot_verts = (
                (left, down),
                (left, up),
                (right, down + (up - down) * 2 / 3),
                (right, down))
            pantin_utils.create_aligned_polygon_widget(
                self.obj, elimb_ik, foot_verts)

            # Toe WGT
            left = right
            right = pb[toe_fr].head.x + (side_factor - 1) * pb[heel_fr].length
            up = down + (up - down) * 2 / 3

            # TODO investigate why moving an edit bones
            # screws up widgets' matrices (foot_ik has moved)
            toe_verts = (
                (left, down),
                (left, up),
                (right, down + (up - down) * 2 / 3),
                (right, down))
            pantin_utils.create_aligned_polygon_widget(
                self.obj, toe_ik_ctl, toe_verts)

            pantin_utils.create_aligned_crescent_widget(
                self.obj, roll_fr, radius=side_factor * pb[roll_fr].length / 2)

            # Constraints
            foot_fr_p = pb[foot_fr]
            heel_fr_p = pb[heel_fr]
            toe_fr_p = pb[toe_fr]
            roll_fr_p = pb[roll_fr]

            hor_vector = Vector((1, 0, 0))
            foot_rotation = (foot_fr_p.vector.
                             rotation_difference(hor_vector).to_euler('XZY'))
            toe_rotation = toe_fr_p.vector.rotation_difference(
                hor_vector).to_euler('XZY')

            foot_vertical_rot = foot_rotation[1] - pi/2
            toe_vertical_rot = toe_rotation[1] - pi/2

            con = foot_fr_p.constraints.new('TRANSFORM')
            con.name = "roll"
            con.target = self.obj
            con.subtarget = roll_fr
            con.map_from = 'ROTATION'
            con.map_to = 'ROTATION'
            con.from_min_z_rot = radians(0.0)
            con.from_max_z_rot = radians(60.0)
            con.to_min_z_rot = radians(0.0)
            con.to_max_z_rot = foot_vertical_rot
            con.target_space = 'LOCAL'
            con.owner_space = 'LOCAL'

            con = heel_fr_p.constraints.new('TRANSFORM')
            con.name = "roll"
            con.target = self.obj
            con.subtarget = roll_fr
            con.map_from = 'ROTATION'
            con.map_to = 'ROTATION'
            con.from_min_z_rot = radians(-60.0)
            con.from_max_z_rot = 0.0
            con.to_min_z_rot = radians(-60.0)
            con.to_max_z_rot = 0.0
            con.target_space = 'LOCAL'
            con.owner_space = 'LOCAL'

            con = toe_fr_p.constraints.new('TRANSFORM')
            con.name = "roll"
            con.target = self.obj
            con.subtarget = roll_fr
            con.map_from = 'ROTATION'
            con.map_to = 'ROTATION'
            con.from_min_z_rot = radians(60.0)
            con.from_max_z_rot = radians(90.0)
            con.to_min_z_rot = radians(0.0)
            con.to_max_z_rot = toe_vertical_rot
            con.target_space = 'LOCAL'
            con.owner_space = 'LOCAL'

            # Compensate foot for heel
            con = foot_fr_p.constraints.new('TRANSFORM')
            con.name = "roll_compensate"
            con.target = self.obj
            con.subtarget = roll_fr
            con.map_from = 'ROTATION'
            con.map_to = 'ROTATION'
            con.from_min_z_rot = radians(60.0)
            con.from_max_z_rot = radians(90.0)
            con.to_min_z_rot = radians(0.0)
            con.to_max_z_rot = -toe_vertical_rot
            con.target_space = 'LOCAL'
            con.owner_space = 'LOCAL'

            # Roll limits
            con = roll_fr_p.constraints.new('LIMIT_ROTATION')
            con.name = "limit rotation"
            con.use_limit_z = True
            con.min_z = radians(-60.0)
            con.max_z = radians(90.0)
            con.owner_space = 'LOCAL'

            # Edit IK to follow the rolled foot instead of ik control
            con = pb[flimb_ik].constraints["ik"]
            con.subtarget = foot_tgt
            con = pb[elimb_str].constraints["copy rotation"]
            con.subtarget = foot_tgt

            con = pb[toe_pos].constraints.new('COPY_ROTATION')
            con.name = "copy rotation"
            con.target = self.obj
            con.subtarget = toe_ik_ctl
            #con.invert_x = True
            con.target_space = 'POSE'
            con.owner_space = 'POSE'

            # Optional stretch to the foot
            if self.params.do_stretch:
                con1 = pb[flimb_str].constraints.new('STRETCH_TO')
                con1.name = "stretch to foot"
                con1.target = self.obj
                con1.subtarget = foot_tgt
                con1.volume = 'NO_VOLUME'
                con1.rest_length = pb[flimb_str].length
                con1.keep_axis = 'PLANE_Z'

                con2 = pb[elimb_str].constraints.new('COPY_LOCATION')
                con2.name = "copy foot location"
                con2.target = self.obj
                con2.subtarget = foot_tgt
                con2.target_space = 'POSE'
                con2.owner_space = 'POSE'

                # Set up custom properties
                prop = rna_idprop_ui_prop_get(
                    pb[elimb_ik], "foot_stretch", create=True)
                pb[elimb_ik]["foot_stretch"] = 1  # int(self.foot_stretch)
                prop["soft_min"] = 0
                prop["soft_max"] = 1
                prop["min"] = 0
                prop["max"] = 1

                # Drivers
                for c in (con1, con2):
                    driver = self.obj.driver_add(c.path_from_id("influence"))
                    driver.driver.expression = 'foot_stretch'
                    var_fs = driver.driver.variables.new()

                    var_fs.type = 'SINGLE_PROP'
                    var_fs.name = 'foot_stretch'
                    var_fs.targets[0].id_type = 'OBJECT'
                    var_fs.targets[0].id = self.obj
                    var_fs.targets[0].data_path = (pb[elimb_ik].path_from_id()
                                                   + '["foot_stretch"]')

            for org, ctrl in zip(
                    side_org_bones, [ulimb_str, flimb_str, elimb_str, toe_ik_ctl]):
                con = pb[org].constraints.new('COPY_TRANSFORMS')
                con.name = "copy_ik"
                con.target = self.obj
                con.subtarget = ctrl

            for org, ctrl in zip(side_org_bones, [ulimb_fk,
                                                  flimb_fk,
                                                  elimb_fk,
                                                  toe_fk_ctl]):
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


            ui_script += script % (ulimb_ik, joint_str, elimb_ik, toe_ik_ctl,
                                   ulimb_fk, flimb_fk, elimb_fk, toe_fk_ctl,
                                   )

            if self.params.do_stretch:
                ui_script += """    layout.prop(pose_bones[ik_leg[2]], \
'["foot_stretch"]', \
text="Foot stretch (" + ik_leg[2] + ")", slider=True)
    """

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
        items=(('.L', 'Left', ""), ('.R', 'Right', "")))
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
    params.do_stretch = bpy.props.BoolProperty(
        name="Do Stretch",
        default=False,
        description="Create stretch constraint on lower leg")


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters.
    """
    r = layout.row()
    r.prop(params, "Z_index")
    r.prop(params, "flip_switch")
    r = layout.row()
    r.prop(params, "do_stretch")
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

    bone = arm.edit_bones.new('Thigh')
    bone.head[:] = -0.0029, 0.0000, 0.8893
    bone.tail[:] = -0.0283, 0.0000, 0.4894
    bone.roll = 0.0634
    bone.use_connect = False
    bones['Thigh'] = bone.name
    bone = arm.edit_bones.new('Shin')
    bone.head[:] = -0.0283, 0.0000, 0.4894
    bone.tail[:] = -0.0587, 0.0000, 0.0736
    bone.roll = 0.0731
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Thigh']]
    bones['Shin'] = bone.name
    bone = arm.edit_bones.new('Foot')
    bone.head[:] = -0.0587, 0.0000, 0.0736
    bone.tail[:] = -0.0030, 0.0000, 0.0227
    bone.roll = -0.8301
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Shin']]
    bones['Foot'] = bone.name
    bone = arm.edit_bones.new('Heel')
    bone.head[:] = -0.0587, 0.0000, 0.0736
    bone.tail[:] = -0.0954, 0.0000, 0.0000
    bone.roll = 0.4628
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Shin']]
    bones['Heel'] = bone.name
    bone = arm.edit_bones.new('Toe')
    bone.head[:] = -0.0030, 0.0000, 0.0227
    bone.tail[:] = 0.0558, 0.0000, 0.0000
    bone.roll = -1.2031
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Foot']]
    bones['Toe'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Thigh']]
    pbone.rigify_type = 'pantin.leg'
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    try:
        pbone.rigify_parameters.Z_index = 2.0
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
    pbone = obj.pose.bones[bones['Shin']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Foot']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Heel']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Toe']]
    pbone.rigify_type = ''
    pbone.lock_location = (True, True, True)
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
