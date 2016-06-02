import bpy
from rna_prop_ui import rna_idprop_ui_prop_get
from mathutils import Vector
from math import radians
import importlib

from ...utils import copy_bone, new_bone, put_bone
from ...utils import make_mechanism_name, make_deformer_name, strip_org
from ...utils import connected_children_names, has_connected_children
from ...utils import align_bone_x_axis

from . import pantin_utils

importlib.reload(pantin_utils)

class IKLimb:
    def __init__(self, obj, org_bones, stretch_joint_name, do_flip, pelvis_follow, pelvis_name, side_suffix='', follow_org=False, ik_limits=[-150.0, 150.0, 0.0, 160.0]):
        self.obj = obj

        # Get the chain of 3 connected bones
        self.org_bones = org_bones #[bone1, bone2, bone3]

        # Get (optional) parent
        if self.obj.data.bones[org_bones[0]].parent is None:
            self.org_parent = None
        else:
            self.org_parent = self.obj.data.bones[org_bones[0]].parent.name

        self.stretch_joint_name = stretch_joint_name
        self.side_suffix = side_suffix
        self.ik_limits = ik_limits
        self.do_flip = do_flip
        self.pelvis_follow = pelvis_follow
        self.pelvis_name = pelvis_name

    def generate(self):
        bpy.ops.object.mode_set(mode='EDIT')

        eb = self.obj.data.edit_bones

        # Create the control bones
        ulimb_ik = copy_bone(self.obj, self.org_bones[0], pantin_utils.strip_numbers(strip_org(self.org_bones[0])) + self.side_suffix)
        flimb_ik = copy_bone(self.obj, self.org_bones[1], make_mechanism_name(pantin_utils.strip_numbers(strip_org(self.org_bones[1])) + self.side_suffix))
        elimb_ik = copy_bone(self.obj, self.org_bones[2], pantin_utils.strip_numbers(strip_org(self.org_bones[2])) + self.side_suffix)

        # elimb_mch = copy_bone(self.obj, self.org_bones[2], make_mechanism_name(strip_org(self.org_bones[2])))

        ulimb_str = copy_bone(self.obj, self.org_bones[0], make_mechanism_name(pantin_utils.strip_numbers(strip_org(self.org_bones[0])) + ".stretch.ik" + self.side_suffix))
        flimb_str = copy_bone(self.obj, self.org_bones[1], make_mechanism_name(pantin_utils.strip_numbers(strip_org(self.org_bones[1])) + ".stretch.ik" + self.side_suffix))
        elimb_str = copy_bone(self.obj, self.org_bones[2], make_mechanism_name(pantin_utils.strip_numbers(strip_org(self.org_bones[2])) + ".stretch.ik" + self.side_suffix))

        joint_str = new_bone(self.obj, self.stretch_joint_name + self.side_suffix)
        eb[joint_str].head = eb[flimb_str].head
        eb[joint_str].tail = eb[flimb_str].head + Vector((0,0,1)) * eb[flimb_str].length/2
        align_bone_x_axis(self.obj, joint_str, Vector((-1, 0, 0)))
        #put_bone(self.obj, joint_str, Vector(eb[flimb_str].head))
        
        # Get edit bones
        ulimb_ik_e = eb[ulimb_ik]
        flimb_ik_e = eb[flimb_ik]
        elimb_ik_e = eb[elimb_ik]

        ulimb_str_e = eb[ulimb_str]
        flimb_str_e = eb[flimb_str]
        elimb_str_e = eb[elimb_str]

        joint_str_e = eb[joint_str]

        # Parenting
        if self.org_parent is not None:
            ulimb_ik_e.use_connect = False
            ulimb_ik_e.parent = eb[self.org_parent]

        flimb_ik_e.use_connect = False
        flimb_ik_e.parent = ulimb_ik_e

        elimb_ik_e.use_connect = False
        elimb_ik_e.parent = None

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

        # Set up custom properties
        prop = rna_idprop_ui_prop_get(elimb_ik_p, "pelvis_follow", create=True)
        elimb_ik_p["pelvis_follow"] = int(self.pelvis_follow)
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
        # TODO get real bone name. From UI?
        if self.do_flip:
            pelvis_bone_name = self.pelvis_name
            flip_bone_name = 'MCH-Flip'

            con1 = elimb_ik_p.constraints.new('CHILD_OF')
            con1.name = "Child Normal"
            con1.target = self.obj
            con1.subtarget = pelvis_bone_name
            con1.inverse_matrix = pb[pelvis_bone_name].matrix.inverted()

            self.obj.pose.bones[flip_bone_name]["flip"] = 1

            con2 = elimb_ik_p.constraints.new('CHILD_OF')
            con2.name = "Child Flipped"
            con2.target = self.obj
            con2.subtarget = flip_bone_name
            con2.inverse_matrix = pb[flip_bone_name].matrix.inverted()

            self.obj.pose.bones[flip_bone_name]["flip"] = 0

            # Drivers
            driver = self.obj.driver_add(con1.path_from_id("influence"))
            driver.driver.expression = 'pelvis_follow'
            var_pf = driver.driver.variables.new()

            var_pf.type = 'SINGLE_PROP'
            var_pf.name = 'pelvis_follow'
            var_pf.targets[0].id_type = 'OBJECT'
            var_pf.targets[0].id = self.obj
            var_pf.targets[0].data_path = elimb_ik_p.path_from_id() + '["pelvis_follow"]'# 'bones["{}"]["pelvis_follow"]'.format(elimb_ik)
            
            driver = self.obj.driver_add(con2.path_from_id("influence"))
            driver.driver.expression = '1-pelvis_follow'
            var_pf = driver.driver.variables.new()

            var_pf.type = 'SINGLE_PROP'
            var_pf.name = 'pelvis_follow'
            var_pf.targets[0].id_type = 'OBJECT'
            var_pf.targets[0].id = self.obj
            var_pf.targets[0].data_path = elimb_ik_p.path_from_id() + '["pelvis_follow"]'# 'bones["{}"]["pelvis_follow"]'.format(elimb_ik)

        # IK Limits
        ulimb_ik_p.lock_ik_x = True
        ulimb_ik_p.lock_ik_y = True
        ulimb_ik_p.use_ik_limit_z = True
        
        ulimb_ik_p.ik_min_z = radians(self.ik_limits[0]) #radians(-150.0)
        ulimb_ik_p.ik_max_z = radians(self.ik_limits[1]) #radians(150.0)

        flimb_ik_p.lock_ik_x = True
        flimb_ik_p.lock_ik_y = True
        flimb_ik_p.use_ik_limit_z = True
        flimb_ik_p.ik_min_z = radians(self.ik_limits[2]) #0.0
        flimb_ik_p.ik_max_z = radians(self.ik_limits[3]) #radians(160.0)
        

        return [ulimb_ik, ulimb_str, flimb_ik, flimb_str, joint_str, elimb_ik, elimb_str]
