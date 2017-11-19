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

    def generate(self):

        self.create_mch()
        self.create_def()
        self.create_controls()

        self.make_constraints()
        self.parent_bones()

        return [""]
