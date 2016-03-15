import bpy

from ....utils import make_deformer_name
from ....utils import create_bone_widget
from ....utils import children_names, has_connected_children
    

class Rig:
    def __init__(self, obj, bone_name, params):
        self.obj = obj
        self.params = params
        self.org_bones = [bone_name] + children_names(obj, bone_name)
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
