import bpy
import importlib
from .. import pantin_utils

importlib.reload(pantin_utils)

from ....utils import make_deformer_name
from ....utils import create_bone_widget
from ....utils import connected_children_names, has_connected_children
    

class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.params = params
        self.org_bones = [bone_name] + connected_children_names(obj, bone_name)
        # self.new_name = params.test_param

    def generate(self):
        bpy.ops.object.mode_set(mode='EDIT')
        def_bones = []
        for b in self.org_bones:
            def_bone = pantin_utils.create_deformation(self.obj, b, self.params.Z_index)
            def_bones.append(def_bone)

        bpy.ops.object.mode_set(mode='OBJECT')

        for db in self.org_bones:
            create_bone_widget(self.obj, db)

        script="""ecartement_membres = 0.01
ecartement_os = 0.005

def z_index(indice_membre, retourne, nbr_membres, indice_os):
    if retourne:
        return -(nbr_membres - indice_membre) * ecartement_membres - indice_os * ecartement_os
    else:
        return indice_membre * ecartement_membres + indice_os * ecartement_os

def z_index_same(indice_membre, retourne, indice_os):
    if retourne:
        return -indice_membre * ecartement_membres - indice_os * ecartement_os
    else:
        return indice_membre * ecartement_membres + indice_os * ecartement_os
    
import bpy

# Add variable defined in this script into the drivers namespace.
bpy.app.driver_namespace["z_index"] = z_index
bpy.app.driver_namespace["z_index_same"] = z_index_same
"""

        # return [script]
            
def add_parameters(params):
    params.Z_index = bpy.props.IntProperty(name="Indice Z", default=0, description="Définit l'ordre des membres dans l'espace")
    params.mutable_order = bpy.props.BoolProperty(name="Ordre change", default=True, description="Ce membre peut changer de profondeur")

def parameters_ui(layout, params):
    """ Create the ui for the rig parameters.
    """
    r = layout.row()
    r.prop(params, "Z_index")
    r = layout.row()
    r.prop(params, "mutable_order")

def create_sample(obj):
    pass

