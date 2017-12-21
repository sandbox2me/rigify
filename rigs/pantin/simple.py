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
from mathutils import Vector, Matrix

from rigify.utils import MetarigError
from rigify.utils import new_bone, copy_bone
from rigify.utils import make_deformer_name, make_mechanism_name, strip_org
from rigify.utils import create_bone_widget, create_widget, create_cube_widget
from rigify.utils import connected_children_names, has_connected_children
from rigify.utils import align_bone_z_axis

from . import pantin_utils

# % ctrl_bone, MCH-bone.dyn
script = """
simple = "%s"
if is_selected(simple):
    layout.prop(pose_bones["%s"].constraints["damped_track"], \
'influence', \
text="Dynamics (" + simple + ")", \
slider=True)
"""

class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.params = params

        eb = self.obj.data.edit_bones

        self.org_bones = [bone_name] + connected_children_names(self.obj,
                                                                bone_name)
        if eb[bone_name].parent is not None:
            self.org_parent = eb[bone_name].parent.name
        else:
            self.org_parent = None
        if eb[bone_name].use_connect:
            raise MetarigError(
                "RIGIFY ERROR: Bone %s should not be connected. "
                "Check bone chain for multiple pantin.simple rigs" % (
                    strip_org(self.org_parent)))
        if self.params.chain_type == 'Dynamic' and len(self.org_bones) > 1:
            self.params.chain_type = "Curve"

    def generate(self):
        if self.params.use_parent_Z_index and self.org_parent is not None:
            # Get parent's Z indices
            bpy.ops.object.mode_set(mode='OBJECT')
            pb = self.obj.pose.bones
            def_parent_name = make_deformer_name(strip_org(self.org_parent))
            if (self.params.object_side != ".C" and
                    def_parent_name[-2:] not in ['.L', '.R']):
                def_parent_name += self.params.object_side
            # print("DEF PARENT", def_parent_name)
            if not def_parent_name in pb:
                raise MetarigError(
                    "RIGIFY ERROR: Bone %s does not have a %s side" % (
                        strip_org(self.org_parent), self.params.object_side))
            parent_p = pb[def_parent_name]
            member_Z_index = parent_p['member_index']
            bone_Z_index = 0
            for b in pb:
                if b.bone.use_deform and b.name.startswith('DEF-'):
                    if not 'member_index' in b:
                        raise MetarigError(
                            "RIGIFY ERROR: One rig bone with should not be connected. "
                            "Check armature for connected bones.")
                    if (b['member_index'] == member_Z_index
                            and b['bone_index'] > bone_Z_index):
                        bone_Z_index = b['bone_index']
            bone_Z_index += 1

            bpy.ops.object.mode_set(mode='EDIT')
        else:
            member_Z_index = self.params.member_Z_index
            bone_Z_index = self.params.first_bone_Z_index

        eb = self.obj.data.edit_bones


        ctrl_chain = []
        mch_chain = []
        # def_chain = []

        # if self.params.duplicate_lr:
        #     sides = ['.L', '.R']
        # else:
        side = self.params.object_side
        if side == '.C':
            side = ''

        # IK control bone
        if self.params.chain_type == 'IK':
            last_bone = self.org_bones[-1]
            ctrl_bone = new_bone(self.obj, strip_org(last_bone) + ".ik" + side)
            ctrl_bone_e = eb[ctrl_bone]
            ctrl_bone_e.head = eb[last_bone].tail
            ctrl_bone_e.tail = eb[last_bone].tail + Vector((0.3, 0, 0))
            align_bone_z_axis(self.obj, ctrl_bone, Vector((0, 1, 0)))
            # ctrl_bone_e.layers = layers

        for i, b in enumerate(self.org_bones):
            # Control bones
            if self.params.chain_type in {'Normal', 'Curve', 'Dynamic'}:
                ctrl_bone = copy_bone(self.obj, b, strip_org(b) + side)
                ctrl_bone_e = eb[ctrl_bone]
                ctrl_chain.append(ctrl_bone)

                if self.params.chain_type == 'Curve':
                    ctrl_bone_e.use_connect = False
                    if self.params.curve_parent_to_first:
                        if i > 0:
                            ctrl_bone_e.parent = eb[ctrl_chain[0]]
                    else:
                        ctrl_bone_e.parent = eb[self.org_parent]
                    ctrl_bone_e.tail = (ctrl_bone_e.head
                                    + Vector((0, 0, 1)) * ctrl_bone_e.length)
                    align_bone_z_axis(self.obj, ctrl_bone, Vector((0, 1, 0)))

                elif self.params.chain_type == 'Dynamic':
                    # Create an empty object to use slow parent
                    # What follows is quite dirty.
                    ctrl_bone_e.parent = eb[self.org_parent]

                    empty_name = self.obj.name + "_" + strip_org(b) + '.dyn'
                    if empty_name in bpy.data.objects:
                        empty_obj = bpy.data.objects[empty_name]
                    else:
                        empty_obj = bpy.data.objects.new(empty_name, None)
                    if not empty_name in bpy.context.scene.objects:
                        bpy.context.scene.objects.link(empty_obj)
                    empty_obj.empty_draw_type = 'SPHERE'
                    empty_obj.empty_draw_size = self.obj.data.bones[b].length / 10
                    empty_obj.hide = True

                    empty_obj.parent = self.obj
                    empty_obj.parent_type = 'BONE'
                    empty_obj.parent_bone = ctrl_bone
                    empty_obj.use_slow_parent = True
                    empty_obj.slow_parent_offset = 1.0



            # Mechanism bones
            if self.params.chain_type == 'Curve':
                stretch_bone = copy_bone(
                    self.obj, b,
                    make_mechanism_name(strip_org(b)) + '.stretch' + side)
                stretch_bone_e = eb[stretch_bone]
                stretch_bone_e.use_connect = False
                stretch_bone_e.parent = eb[ctrl_bone]
                mch_chain.append(stretch_bone)

            elif self.params.chain_type == 'IK':
                ik_bone = copy_bone(
                    self.obj, b,
                    make_mechanism_name(strip_org(b)) + '.ik' + side)
                ik_bone_e = eb[ik_bone]
                ik_bone_e.parent = eb[mch_chain[-1] if i > 0 else self.org_parent]
                mch_chain.append(ik_bone)

            elif self.params.chain_type == 'Dynamic':
                dyn_bone = copy_bone(
                    self.obj, b,
                    make_mechanism_name(strip_org(b)) + '.dyn' + side)
                dyn_bone_e = eb[dyn_bone]
                dyn_bone_e.parent = eb[ctrl_bone]
                mch_chain.append(dyn_bone)

            # Parenting
            if self.params.chain_type == 'Normal':
                if i == 0:
                    # First bone
                    # TODO Check if parent still exists,
                    # else check if .L / .R exists, else do nothing
                    if eb[b].parent is not None:
                        bone_parent_name = eb[b].parent.name
                        if bone_parent_name + self.params.object_side in eb:
                            ctrl_bone_e.parent = (eb[bone_parent_name
                                                  + self.params.object_side])
                        elif bone_parent_name in eb:
                            ctrl_bone_e.parent = eb[bone_parent_name]
                        else:
                            raise MetarigError(
                                "RIGIFY ERROR: Bone %s does not have a %s side"
                                % (strip_org(eb[b].parent.name), side))
                    elif 'MCH-Flip' in eb:
                        ctrl_bone_e.parent = eb['MCH-Flip']
                    else:
                        raise MetarigError(
                            "RIGIFY ERROR: Bone %s needs to have a parent"
                            % strip_org(eb[b].name))

            # Def bones
            def_bone = pantin_utils.create_deformation(
                self.obj, b,
                self.params.flip_switch,
                member_Z_index,
                bone_Z_index + i,
                0.0,
                b+side)

        if self.params.chain_type == 'Curve':
            # Curve end bone
            last_bone = self.org_bones[-1]
            ctrl_bone = new_bone(self.obj, strip_org(last_bone) + ".end" + side)
            ctrl_bone_e = eb[ctrl_bone]
            last_bone_e = eb[last_bone]

            ctrl_bone_e.use_connect = False
            if self.params.curve_parent_to_first:
                ctrl_bone_e.parent = eb[ctrl_chain[0]]
            else:
                ctrl_bone_e.parent = eb[self.org_parent]
            ctrl_bone_e.head = last_bone_e.tail
            ctrl_bone_e.tail = (ctrl_bone_e.head
                                + (last_bone_e.tail - last_bone_e.head))
            align_bone_z_axis(self.obj, ctrl_bone, Vector((0, 1, 0)))
            ctrl_chain.append(ctrl_bone)
            ctrl_bone_e.layers = last_bone_e.layers
            # ctrl_bone_e.layers = layers
        bpy.ops.object.mode_set(mode='OBJECT')
        pb = self.obj.pose.bones

        # Pose bone settings
        if self.params.chain_type in ('Curve', 'Dynamic'):
            pbone = pb[ctrl_chain[-1]]
            pbone.rotation_mode = 'XZY'
            pbone.lock_location = (False, False, True)
            pbone.lock_rotation = (True, True, False)
            pbone.lock_rotation_w = False
            pbone.lock_scale = (False, False, False)

        if self.params.chain_type in ('IK', 'Curve', 'Dynamic'):
            # Widgets
            for ctrl_bone in ctrl_chain:
                global_scale = pb[ctrl_bone].length  # self.obj.dimensions[2]
                # member_factor = 0.06
                widget_size = global_scale * 0.3  # * member_factor
                pantin_utils.create_aligned_circle_widget(
                    self.obj, ctrl_bone, radius=widget_size)

            # Constraints
            for org, mch in zip(self.org_bones, mch_chain):
                con = pb[org].constraints.new('COPY_TRANSFORMS')
                con.name = "copy_transforms"
                con.target = self.obj
                con.subtarget = mch
        else:
            # Widgets
            widget_size = 0.5
            for bone in ctrl_chain:
                pantin_utils.create_capsule_widget(
                    self.obj,
                    bone,
                    length=widget_size,
                    width=widget_size*0.1,
                    head_tail=0.5,
                    horizontal=False
                )

            # Constraints
            for org, ctrl in zip(self.org_bones, ctrl_chain):
                con = pb[org].constraints.new('COPY_TRANSFORMS')
                con.name = "copy_transforms"
                con.target = self.obj
                con.subtarget = ctrl

        ui_script = None

        if self.params.chain_type == 'Curve':
            for ctrl, mch in zip(ctrl_chain[1:], mch_chain):
                con = pb[mch].constraints.new('STRETCH_TO')
                con.name = "stretch_to"
                con.target = self.obj
                con.subtarget = ctrl
                con.volume = 'NO_VOLUME'
                con.keep_axis = 'PLANE_Z'

        elif self.params.chain_type == 'IK':
            last_bone = mch_chain[-1]
            con = pb[last_bone].constraints.new('IK')
            con.target = self.obj
            con.subtarget = ctrl_bone
            con.chain_count = len(self.org_bones)

            # # Pelvis follow
            # if self.params.do_flip:
            #     pantin_utils.create_ik_child_of(
            #         self.obj, ctrl_bone, self.params.pelvis_name)

        elif self.params.chain_type == 'Dynamic':
            for ctrl, mch in zip(ctrl_chain, mch_chain):
                con = pb[mch].constraints.new('DAMPED_TRACK')
                con.name = "damped_track"
                con.target = empty_obj
                # con.volume = 'NO_VOLUME'
                # con.keep_axis = 'PLANE_Z'
                # con.rest_length = pb[ctrl].length

            ui_script = script % (ctrl, dyn_bone)  # % ctrl_bone, MCH-bone.dyn

        elif self.params.chain_type == 'Def':
            # Modify constraints to add side suffix
            if side in ('.L', '.R'):
                for b in self.org_bones:
                    for con in pb[b].constraints:
                        if (hasattr(con, 'subtarget')
                                and con.subtarget + side in pb):
                            con.subtarget += side

        if ui_script is not None:
            return [ui_script]


def add_parameters(params):
    params.use_parent_Z_index = bpy.props.BoolProperty(
        name="Use parent's Z Index",
        default=True,
        description="The object will use its parent's Z index")
    params.member_Z_index = bpy.props.FloatProperty(
        name="Z index",
        default=0.0,
        description="Defines member's Z order")
    params.first_bone_Z_index = bpy.props.FloatProperty(
        name="First Bone Z index",
        default=0.0,
        description="Defines bone's Z order")
    params.flip_switch = bpy.props.BoolProperty(
        name="Flip Switch",
        default=False,
        description="This member may change depth when flipped")

    params.object_side = bpy.props.EnumProperty(
        name="Side",
        default='.C',
        description="If the limb is not to be duplicated, choose its side",
        items=(('.L', 'Left', ""),
               ('.C', 'Center', ""),
               ('.R', 'Right', ""),
               ))
    params.do_flip = bpy.props.BoolProperty(
        name="Do Flip",
        default=True,
        description="True if the rig has a torso with flip system")
    params.pelvis_name = bpy.props.StringProperty(
        name="Pelvis Name",
        default="Pelvis",
        description="Name of the pelvis bone in whole rig")
    params.chain_type = bpy.props.EnumProperty(
        name="Chain Type",
        items=(('Normal',)*3, ('IK',)*3, ('Curve',)*3, ('Dynamic',)*3, ('Def',)*3,),
        default="Normal",
        description="Type of chain to be generated")
    params.curve_parent_to_first = bpy.props.BoolProperty(
        name="Parent to first",
        default=False,
        description="Parent all control bones to the first")

def parameters_ui(layout, params):
    """ Create the ui for the rig parameters.
    """
    r = layout.row()
    r.prop(params, "use_parent_Z_index")

    if not params.use_parent_Z_index:
        r = layout.row()
        r.prop(params, "member_Z_index")
        r.prop(params, "first_bone_Z_index")
    r = layout.row()
    r.prop(params, "flip_switch")
    col = layout.column(align=True)
    r = col.row()
    r.label("Side:")
    r = col.row()
    r.prop(params, "object_side", expand=True)
    c = layout.column()
    c.prop(params, "do_flip")
    c.prop(params, "pelvis_name")

    col = layout.column()
    r = col.row()
    r.prop(params, "chain_type")
    if params.chain_type == "Curve":
        r.prop(params, "curve_parent_to_first")
    elif params.chain_type == "Dynamic":
        col.label(text="Only one bone allowed in dynamic chain", icon="ERROR")

def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('Prop')
    bone.head[:] = -0.1701, 0.0000, 0.7032
    bone.tail[:] = -0.3672, 0.0000, 0.0000
    bone.roll = 0.2706
    bone.use_connect = False
    bones['Prop'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Prop']]
    pbone.rigify_type = 'pantin.simple'
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    try:
        pbone.rigify_parameters.object_side = ".R"
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.use_parent_Z_index = True
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.create_ik = False
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.flip_switch = False
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.pelvis_name = "Pelvis"
    except AttributeError:
        pass

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
