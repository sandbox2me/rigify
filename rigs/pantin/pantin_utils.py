import bpy
from mathutils import Vector
from math import pi, cos, sin

from ...utils import make_deformer_name, strip_org, copy_bone
from ...utils import create_widget
from ...utils import create_circle_polygon

def create_deformation(obj, bone_name, mutable_order, member_index=0, bone_index=0, new_name=''):
    bpy.ops.object.mode_set(mode='EDIT')
    eb = obj.data.edit_bones

    org_bone_e = eb[bone_name]
    def_bone_e = eb.new(bone_name)

#    bone = copy_bone(obj, bone_name, strip_org(bone_name))
#    bone_e = eb[bone]

    if new_name == '':
        new_name = bone_name
    def_name = make_deformer_name(strip_org(new_name))
    def_bone_e.name = def_name
#    def_bone_e.name = strip_org(bone_name)

    def_bone_e.parent = org_bone_e
    def_bone_e.use_connect = False

    def_bone_e.head = org_bone_e.head
    def_bone_e.tail = org_bone_e.head
    def_bone_e.tail.z += 0.1

    def_bone_e['member_index'] = member_index
    def_bone_e['bone_index'] = bone_index

    bpy.ops.object.mode_set(mode='OBJECT')

    # bones = obj.pose.bones

    driver = obj.driver_add('pose.bones["{}"].location'.format(def_name), 2)
    if mutable_order:
        driver.driver.expression = 'z_index(member_index, flip, members_number, bone_index)'
    else:
        driver.driver.expression = 'z_index_same(member_index, flip, bone_index)'
    var_mi = driver.driver.variables.new()
    var_bi = driver.driver.variables.new()
    var_flip = driver.driver.variables.new()
    if mutable_order:
        var_mn = driver.driver.variables.new()

        var_mn.type = 'SINGLE_PROP'
        var_mn.name = 'members_number'
        var_mn.targets[0].id_type = 'ARMATURE'
        var_mn.targets[0].id = obj.data
        var_mn.targets[0].data_path = 'bones["Flip"]["members_number"]'

        

    var_mi.type = 'SINGLE_PROP'
    var_mi.name = 'member_index'
    var_mi.targets[0].id_type = 'ARMATURE'
    var_mi.targets[0].id = obj.data
    var_mi.targets[0].data_path = 'bones["{}"]["member_index"]'.format(def_name)

    var_bi.type = 'SINGLE_PROP'
    var_bi.name = 'bone_index'
    var_bi.targets[0].id_type = 'ARMATURE'
    var_bi.targets[0].id = obj.data
    var_bi.targets[0].data_path = 'bones["{}"]["bone_index"]'.format(def_name)

    var_flip.type = 'SINGLE_PROP'
    var_flip.name = 'flip'
    var_flip.targets[0].id_type = 'ARMATURE'
    var_flip.targets[0].id = obj.data
    var_flip.targets[0].data_path = 'bones["Flip"]["flip"]'

    bpy.ops.object.mode_set(mode='EDIT')
    return def_bone_e.name

def create_axis_line_widget(rig, bone_name, length=1, axis='X', bone_transform_name=None):
    """ Creates a basic line widget which remains horizontal.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj is not None:
        
        pbone = rig.pose.bones[bone_name]
        # print(pbone.matrix.translation)
        pos = pbone.matrix.translation
        
        assert(axis in 'XYZ')
        if axis == 'X':
            verts = [(-1,0,0), (1,0,0)]
        if axis == 'Y':
            verts = [(0,-1,0), (0,1,0)]
        if axis == 'Z':
            verts = [(0,0,-1), (0,0,1)]

        verts = [pbone.matrix.inverted() * (pos + Vector(v)*length) for v in verts]

        edges = [(0,1)]
        mesh = obj.data
        mesh.from_pydata(verts, edges, [])
        mesh.update()


def create_capsule_polygon(number_verts, width, height=0.1):
    """ Creates a capsule shape.
        number_verts: number of vertices of the poligon
        width: the width of the capsule
        height: the height of the capsule
    """

    verts = []
    edges = []

    v_ind = 0
    for side in [-1,1]:
        for i in range(0, number_verts//2+1):
            angle = 2*pi*i/number_verts - pi / 2 - (side+1) * (pi/2)
            verts.append((cos(angle) * height/2 - (width - height/2)*side, 0, sin(angle) * height/2))
            if v_ind < number_verts+1:
                edges.append((v_ind, v_ind+1))
                v_ind += 1

    edges.append((0, number_verts + 1))

    return verts, edges

def create_capsule_widget(rig, bone_name, width=None, height=None, head_tail=0.0, bone_transform_name=None):
    """ Creates a basic line widget which remains horizontal.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj is not None:
        
        pbone = rig.pose.bones[bone_name]
        # print(pbone.matrix.translation)
        pos = pbone.matrix.translation
        
        if width is None:
            width = pbone.length * 2
        if height is None:
            height = width * 0.1

        verts, edges = create_capsule_polygon(32, width, height)
        head_tail_vector = pbone.vector * head_tail
        verts = [(pbone.matrix * pbone.length).inverted() * (pos + Vector(v) + head_tail_vector) for v in verts]

        mesh = obj.data
        mesh.from_pydata(verts, edges, [])
        mesh.update()


def create_aligned_circle_widget(rig, bone_name, radius=1.0, head_tail=0.0, bone_transform_name=None):
    """ Creates a basic line widget which remains horizontal.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj is not None:
        
        pbone = rig.pose.bones[bone_name]
        # print(pbone.matrix.translation)
        pos = pbone.matrix.translation
        
        verts, edges = create_circle_polygon(32, 'Y', radius, head_tail)
        head_tail_vector = pbone.vector * head_tail
        verts = [(pbone.matrix * pbone.length).inverted() * (pos + Vector(v) + head_tail_vector) for v in verts]

        mesh = obj.data
        mesh.from_pydata(verts, edges, [])
        mesh.update()
