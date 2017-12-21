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
import importlib

from ...utils import new_bone, copy_bone
from ...utils import make_deformer_name, make_mechanism_name,  strip_org
from ...utils import create_bone_widget, create_widget, create_cube_widget
from ...utils import connected_children_names, has_connected_children
from ...utils import align_bone_x_axis, align_bone_z_axis

from . import pantin_utils

importlib.reload(pantin_utils)


class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.org_bones = [bone_name] + connected_children_names(obj, bone_name)
        self.params = params

    def generate(self):
        bpy.ops.object.mode_set(mode='EDIT')

        eb = self.obj.data.edit_bones

        pelvis = self.org_bones[0]
        pelvis_e = eb[pelvis]

        # # Intermediate root bone
        # root_name = self.params.root_name
        # root = new_bone(self.obj, root_name)
        # root_e = eb[root]
        # root_e.head = Vector((0, 0, 0))
        # root_e.tail = Vector((0, 0, 1)) * pelvis_e.length/2
        # align_bone_x_axis(self.obj, root, Vector((-1, 0, 0)))
        # root_e.layers = [i == 28 for i in range(32)]

        # # Flip bone
        # flip = new_bone(self.obj, make_mechanism_name('Flip'))
        # flip_e = eb[flip]
        #
        # flip_e.head = pelvis_e.head
        # flip_e.tail = flip_e.head + Vector((0, 0, 1)) * pelvis_e.length/2
        # align_bone_x_axis(self.obj, flip, Vector((-1, 0, 0)))

        # root_e = eb[root]

        # flip_e.use_connect = False
        # flip_e.parent = root_e

        ctrl_chain = []
        def_chain = []
        for i, b in enumerate(self.org_bones):
            # Control bones
            ctrl_bone = copy_bone(self.obj, b)
            ctrl_bone_e = eb[ctrl_bone]

            # Name
            ctrl_bone_e.name = ctrl_bone = strip_org(b)

            # Parenting
            if i == 0:
                # First bone

                # Vertical intermediate pelvis (animation helper)
                inter_pelvis = copy_bone(
                    self.obj, b, make_mechanism_name(
                        strip_org(b)+'.intermediate'))

                ctrl_bone_e = eb[ctrl_bone]
                ctrl_bone_e.tail = ctrl_bone_e.head
                ctrl_bone_e.tail[2] += 1.0 * eb[b].length
                align_bone_z_axis(self.obj, ctrl_bone, Vector((0, 1, 0)))

                ctrl_bone_e = eb[ctrl_bone]
                # ctrl_bone_e.parent = eb[self.org_bones[0]].parent
                # eb[ctrl_bone].parent = None
                eb[inter_pelvis].parent = ctrl_bone_e
            elif i == 1:
                ctrl_bone_e.parent = eb[inter_pelvis]
            else:
                # The rest
                ctrl_bone_e.parent = eb[ctrl_chain[-1]]

            # Add to list
            ctrl_chain += [ctrl_bone_e.name]

            # Def bones
            def_bone = pantin_utils.create_deformation(
                self.obj,
                b,
                self.params.flip_switch,
                member_index=self.params.Z_index,
                bone_index=i)
            def_chain.append(def_bone)

        # flip_e = eb[flip]
        pelvis_e = eb[ctrl_chain[0]]
        pelvis_e.use_connect = False
        # pelvis_e.parent = flip_e

        bpy.ops.object.mode_set(mode='OBJECT')
        pb = self.obj.pose.bones

        # # Pose bone settings
        # flip_p = pb[flip]
        # flip_p.rotation_mode = 'XZY'

        # root_p = pb[root]
        # root_p.lock_location = (False, False, True)
        # root_p.lock_rotation = (True, True, False)
        # root_p.lock_rotation_w = False
        # root_p.lock_scale = (False, False, False)
        # root_p.rotation_mode = 'XZY'

        # # Set up custom properties
        # prop = rna_idprop_ui_prop_get(flip_p, "flip", create=True)
        # flip_p["flip"] = 0
        # prop["soft_min"] = 0
        # prop["soft_max"] = 1
        # prop["min"] = 0
        # prop["max"] = 1

        # Widgets
        global_scale = self.obj.dimensions[2]
        member_factor = 0.1
        widget_size = global_scale * member_factor
        pelvis = ctrl_chain[0]
        # abdomen = ctrl_chain[1]
        # torso = ctrl_chain[2]
        # shoulder = ctrl_chain[3]

        # create_cube_widget(self.obj, pelvis, radius=widget_size*4)
        radius = widget_size
        pelvis_center = pb[pelvis].center
        vp = ((-radius*2.0+pelvis_center.x, -radius+pelvis_center.z),
              (-radius*2.0+pelvis_center.x, radius+pelvis_center.z),
              (radius*2.0+pelvis_center.x, radius+pelvis_center.z),
              (radius*2.0+pelvis_center.x, -radius+pelvis_center.z))
        pantin_utils.create_aligned_polygon_widget(
            self.obj, pelvis, vertex_points=vp)
        # pantin_utils.create_aligned_half_ellipse_widget(
        #     self.obj, root, width=widget_size*1.5, height=widget_size)

        for bone in ctrl_chain[1:]:
            pantin_utils.create_capsule_widget(
                self.obj,
                bone,
                length=widget_size,
                width=widget_size*0.1,
                head_tail=0.5)
            # create_widget(self.obj, bone)

        # Drivers
        # driver = self.obj.driver_add(
        #     'pose.bones["{}"].rotation_euler'.format(flip), 1)
        # driver.driver.expression = 'pi*flip'
        # var_flip = driver.driver.variables.new()
        #
        # var_flip.type = 'SINGLE_PROP'
        # var_flip.name = 'flip'
        # var_flip.targets[0].id_type = 'OBJECT'
        # var_flip.targets[0].id = self.obj
        # var_flip.targets[0].data_path = 'pose.bones["root"]["flip"]'.format(flip)

        # Constraints
        # for pelvis
        con = pb[self.org_bones[0]].constraints.new('COPY_TRANSFORMS')
        con.name = "copy_transforms"
        con.target = self.obj
        con.subtarget = inter_pelvis

        # for others
        for org, ctrl in zip(self.org_bones[1:], ctrl_chain[1:]):
            con = pb[org].constraints.new('COPY_TRANSFORMS')
            con.name = "copy_transforms"
            con.target = self.obj
            con.subtarget = ctrl


def add_parameters(params):
    params.Z_index = bpy.props.FloatProperty(
        name="Z index",
        default=0.0,
        description="Defines member's Z order")
    params.flip_switch = bpy.props.BoolProperty(
        name="Flip Switch",
        default=False,
        description="This member may change depth when flipped")
    params.root_name = bpy.props.StringProperty(
        name="Root Name",
        default="Root 1",
        description="The name of the intermediate root bone")


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters.
    """
    r = layout.row()
    r.prop(params, "Z_index")
    r = layout.row()
    r.prop(params, "flip_switch")
    r = layout.row()
    r.prop(params, "members_number")
    r = layout.row()
    r.prop(params, "root_name")


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('Pelvis')
    bone.head[:] = -0.0029, 0.0000, 0.8893
    bone.tail[:] = 0.0294, -0.0000, 1.0480
    bone.roll = -2.9413
    bone.use_connect = False
    bones['Pelvis'] = bone.name
    bone = arm.edit_bones.new('Spine')
    bone.head[:] = 0.0294, -0.0000, 1.0480
    bone.tail[:] = -0.0027, 0.0000, 1.1745
    bone.roll = 2.8939
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Pelvis']]
    bones['Spine'] = bone.name
    bone = arm.edit_bones.new('Thorax')
    bone.head[:] = -0.0027, 0.0000, 1.1745
    bone.tail[:] = -0.0135, 0.0000, 1.3005
    bone.roll = 3.0550
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Spine']]
    bones['Thorax'] = bone.name
    bone = arm.edit_bones.new('Chest')
    bone.head[:] = -0.0135, 0.0000, 1.3005
    bone.tail[:] = 0.0005, 0.0000, 1.4038
    bone.roll = -3.0064
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Thorax']]
    bones['Chest'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Pelvis']]
    pbone.rigify_type = 'pantin.torso'
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (True, True, True)
    pbone.rotation_mode = 'XZY'
    try:
        pbone.rigify_parameters.Z_index = 1.0
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.flip_switch = False
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.root_name = "Root"
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['Spine']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (True, True, True)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Thorax']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Chest']]
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
