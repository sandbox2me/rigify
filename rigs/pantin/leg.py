import bpy
import importlib

from ...utils import copy_bone
from ...utils import make_deformer_name, strip_org
from ...utils import create_bone_widget, create_widget, create_cube_widget
from ...utils import connected_children_names, has_connected_children

from . import pantin_utils
from . import limb_common

importlib.reload(pantin_utils)
importlib.reload(limb_common)

script = """
ik_leg = ["%s", "%s", "%s"]
if is_selected(ik_leg):
    layout.prop(pose_bones[ik_leg[2]], '["pelvis_follow"]', text="Follow pelvis (" + ik_leg[2] + ")", slider=True)
"""

class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj

        bones = obj.data.bones
        leg = bone_name
        shin = bones[leg].children[0].name
        for b in bones[shin].children:
            if not len(b.children):
                heel = b.name
            else:
                foot = b.name
        print(heel, foot)
        toe = bones[foot].children[0].name
        roll = bones[toe].children[0].name

        self.org_bones = [leg, shin, foot, heel, toe, roll]# + connected_children_names(obj, bone_name)[:2]
        self.params = params
        if "right_layers" in params:
            self.right_layers = [bool(l) for l in params["right_layers"]]
        else:
            self.right_layers = None
        joint_name = self.params.joint_name

        if params.duplicate_lr:
            sides = ['.L', '.R']
        else:
            sides = ['']
        
        self.ik_limbs = {}
        for s in sides:
            self.ik_limbs[s] = limb_common.IKLimb(obj, self.org_bones[:3], joint_name, s, ik_limits=[-150.0, 150.0, 0.0, 160.0])

    def generate(self):
        ui_script = ""
        for s, ik_limb in self.ik_limbs.items():
            ulimb_ik, ulimb_str, flimb_str, joint_str, elimb_ik, elimb_str = ik_limb.generate()

            bpy.ops.object.mode_set(mode='EDIT')

            # Def bones
            eb = self.obj.data.edit_bones
            if s == '.L':
                Z_index = self.params.Z_index
            else:
                Z_index = 5-self.params.Z_index
                
            for i, b in enumerate([elimb_str, flimb_str, ulimb_str]):
                def_bone = pantin_utils.create_deformation(self.obj, b, self.params.mutable_order, Z_index, i, b[4:-13]+s)

            # Set layers if specified
            if s == '.R' and self.right_layers:
                eb[ulimb_ik].layers = self.right_layers
                eb[joint_str].layers = self.right_layers
                eb[elimb_ik].layers = self.right_layers

            bpy.ops.object.mode_set(mode='OBJECT')
            pb = self.obj.pose.bones

            pantin_utils.create_aligned_circle_widget(self.obj, ulimb_ik, radius=0.1)
            pantin_utils.create_aligned_circle_widget(self.obj, joint_str, radius=0.1)
            pantin_utils.create_aligned_circle_widget(self.obj, elimb_ik, radius=0.1)

            # Constraints
            if s == '.R':
                for org, ctrl in zip(self.org_bones, [ulimb_str, flimb_str, elimb_str]):
                    con = pb[org].constraints.new('COPY_TRANSFORMS')
                    con.name = "copy_transforms"
                    con.target = self.obj
                    con.subtarget = ctrl

            ui_script += script % (ulimb_ik, joint_str, elimb_ik)

        return [ui_script]
                    
def add_parameters(params):
    params.Z_index = bpy.props.IntProperty(name="Z index", default=0, description="Defines member's Z order")
    params.mutable_order = bpy.props.BoolProperty(name="Ordre change", default=True, description="This member may change depth when flipped")
    params.duplicate_lr = bpy.props.BoolProperty(name="Duplicate LR", default=True, description="Create two limbs for left and right")
    params.joint_name = bpy.props.StringProperty(name="Joint Name", default="Joint", description="Name of the middle joint")
    params.right_layers = bpy.props.BoolVectorProperty(size=32, description="Layers for the duplicated limb to be on")

def parameters_ui(layout, params):
    """ Create the ui for the rig parameters.
    """
    r = layout.row()
    r.prop(params, "Z_index")
    r = layout.row()
    r.prop(params, "mutable_order")
    r = layout.row()
    r.prop(params, "joint_name")
    r = layout.row()
    r.prop(params, "duplicate_lr")

    r = layout.row()
    r.active = params.duplicate_lr
    
    # Layers for the right arm
    col = r.column(align=True)
    row = col.row(align=True)
    row.prop(params, "right_layers", index=0, toggle=True, text="")
    row.prop(params, "right_layers", index=1, toggle=True, text="")
    row.prop(params, "right_layers", index=2, toggle=True, text="")
    row.prop(params, "right_layers", index=3, toggle=True, text="")
    row.prop(params, "right_layers", index=4, toggle=True, text="")
    row.prop(params, "right_layers", index=5, toggle=True, text="")
    row.prop(params, "right_layers", index=6, toggle=True, text="")
    row.prop(params, "right_layers", index=7, toggle=True, text="")
    row = col.row(align=True)
    row.prop(params, "right_layers", index=16, toggle=True, text="")
    row.prop(params, "right_layers", index=17, toggle=True, text="")
    row.prop(params, "right_layers", index=18, toggle=True, text="")
    row.prop(params, "right_layers", index=19, toggle=True, text="")
    row.prop(params, "right_layers", index=20, toggle=True, text="")
    row.prop(params, "right_layers", index=21, toggle=True, text="")
    row.prop(params, "right_layers", index=22, toggle=True, text="")
    row.prop(params, "right_layers", index=23, toggle=True, text="")

    col = r.column(align=True)
    row = col.row(align=True)
    row.prop(params, "right_layers", index=8, toggle=True, text="")
    row.prop(params, "right_layers", index=9, toggle=True, text="")
    row.prop(params, "right_layers", index=10, toggle=True, text="")
    row.prop(params, "right_layers", index=11, toggle=True, text="")
    row.prop(params, "right_layers", index=12, toggle=True, text="")
    row.prop(params, "right_layers", index=13, toggle=True, text="")
    row.prop(params, "right_layers", index=14, toggle=True, text="")
    row.prop(params, "right_layers", index=15, toggle=True, text="")
    row = col.row(align=True)
    row.prop(params, "right_layers", index=24, toggle=True, text="")
    row.prop(params, "right_layers", index=25, toggle=True, text="")
    row.prop(params, "right_layers", index=26, toggle=True, text="")
    row.prop(params, "right_layers", index=27, toggle=True, text="")
    row.prop(params, "right_layers", index=28, toggle=True, text="")
    row.prop(params, "right_layers", index=29, toggle=True, text="")
    row.prop(params, "right_layers", index=30, toggle=True, text="")
    row.prop(params, "right_layers", index=31, toggle=True, text="")
def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('Jambe haut')
    bone.head[:] = 0.0515, -0.0000, 0.8916
    bone.tail[:] = 0.0261, -0.0000, 0.4917
    bone.roll = 0.0634
    bone.use_connect = False
    bones['Jambe haut'] = bone.name
    bone = arm.edit_bones.new('Main')
    bone.head[:] = 0.0383, -0.0000, 0.8731
    bone.tail[:] = 0.0383, -0.0000, 0.7657
    bone.roll = 0.0000
    bone.use_connect = False
    bones['Main'] = bone.name
    bone = arm.edit_bones.new('Jambe bas')
    bone.head[:] = 0.0261, -0.0000, 0.4917
    bone.tail[:] = -0.0053, 0.0000, 0.0769
    bone.roll = 0.0757
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Jambe haut']]
    bones['Jambe bas'] = bone.name
    bone = arm.edit_bones.new('Pied')
    bone.head[:] = -0.0053, 0.0000, 0.0769
    bone.tail[:] = 0.0532, -0.0000, 0.0250
    bone.roll = -0.8451
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Jambe bas']]
    bones['Pied'] = bone.name
    bone = arm.edit_bones.new('Talon')
    bone.head[:] = -0.0053, 0.0000, 0.0769
    bone.tail[:] = -0.0410, -0.0000, 0.0027
    bone.roll = -2.6932
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Jambe bas']]
    bones['Talon'] = bone.name
    bone = arm.edit_bones.new('Orteil')
    bone.head[:] = 0.0532, -0.0000, 0.0250
    bone.tail[:] = 0.1154, -0.0000, 0.0230
    bone.roll = -1.5391
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['Pied']]
    bones['Orteil'] = bone.name
    bone = arm.edit_bones.new('Pointe')
    bone.head[:] = 0.1071, -0.0000, 0.0021
    bone.tail[:] = 0.1892, -0.0000, 0.0021
    bone.roll = -1.5708
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['Orteil']]
    bones['Pointe'] = bone.name
    bone = arm.edit_bones.new('Cou_pied.ik')
    bone.head[:] = -0.0952, -0.0000, 0.0890
    bone.tail[:] = -0.1901, -0.0000, 0.0890
    bone.roll = 1.5708
    bone.use_connect = False
    bone.parent = arm.edit_bones[bones['Pointe']]
    bones['Cou_pied.ik'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Jambe haut']]
    pbone.rigify_type = 'pantin.leg'
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    try:
        pbone.rigify_parameters.Z_index = 1
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.joint_name = "Genou"
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.right_layers = [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, True, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['Main']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Jambe bas']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Pied']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Talon']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Orteil']]
    pbone.rigify_type = ''
    pbone.lock_location = (True, True, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Pointe']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'XZY'
    pbone = obj.pose.bones[bones['Cou_pied.ik']]
    pbone.rigify_type = ''
    pbone.lock_location = (True, True, True)
    pbone.lock_rotation = (True, True, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (True, True, True)
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
