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
from mathutils import Vector
from math import pi, cos, sin
import re

from ...utils import make_deformer_name, strip_org, copy_bone
from ...utils import create_widget
from ...utils import create_circle_polygon
from ...utils import align_bone_z_axis

def strip_numbers(name):
    """ Returns the name with trailing numbers stripped from it.
    """
    # regexp = re.compile("\.[0-9]+$")
    matches = re.findall("\.[0-9]+$", name)
    if matches:
        return name[:-len(matches[-1])]
    else:
        return name

def create_deformation(obj, bone_name, mutable_order, member_index=0, bone_index=0, extra_offset=0.0, new_name=''):
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
    def_bone_e.tail = org_bone_e.tail
    align_bone_z_axis(obj, def_name, Vector((0, -1, 0)))
    # def_bone_e.tail.z += org_bone_e.length * 0.5

    bpy.ops.object.mode_set(mode='POSE')

    def_bone_p = obj.pose.bones[def_name]
    def_bone_p['member_index'] = member_index
    def_bone_p['bone_index'] = bone_index
    def_bone_p['extra_offset'] = extra_offset

    # Driver
    driver = obj.driver_add('pose.bones["{}"].location'.format(def_name), 2)
    if mutable_order:
        driver.driver.expression = 'z_index(member_index, flip, bone_index, extra_offset)'
    else:
        driver.driver.expression = 'z_index_same(member_index, flip, bone_index, extra_offset)'
    var_mi = driver.driver.variables.new()
    var_bi = driver.driver.variables.new()
    var_flip = driver.driver.variables.new()        
    var_eo = driver.driver.variables.new()        

    var_mi.type = 'SINGLE_PROP'
    var_mi.name = 'member_index'
    var_mi.targets[0].id_type = 'OBJECT'
    var_mi.targets[0].id = obj
    var_mi.targets[0].data_path = 'pose.bones["{}"]["member_index"]'.format(def_name)

    var_bi.type = 'SINGLE_PROP'
    var_bi.name = 'bone_index'
    var_bi.targets[0].id_type = 'OBJECT'
    var_bi.targets[0].id = obj
    var_bi.targets[0].data_path = 'pose.bones["{}"]["bone_index"]'.format(def_name)

    var_eo.type = 'SINGLE_PROP'
    var_eo.name = 'extra_offset'
    var_eo.targets[0].id_type = 'OBJECT'
    var_eo.targets[0].id = obj
    var_eo.targets[0].data_path = 'pose.bones["{}"]["extra_offset"]'.format(def_name)

    var_flip.type = 'SINGLE_PROP'
    var_flip.name = 'flip'
    var_flip.targets[0].id_type = 'OBJECT'
    var_flip.targets[0].id = obj
    var_flip.targets[0].data_path = 'pose.bones["MCH-Flip"]["flip"]'

    bpy.ops.object.mode_set(mode='EDIT')
    return def_name

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

def create_aligned_polygon_widget(rig, bone_name, vertex_points, bone_transform_name=None):
    """ Creates a basic line widget which remains horizontal.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj is not None:
        
        pbone = rig.pose.bones[bone_name]
        
        verts = [Vector((x, 0.0, y)) for x,y in vertex_points]
        edges = []
        for i in range(len(verts)):
            edges.append((i, i+1))
        edges[-1] = (0, len(verts)-1)

        verts = [(pbone.matrix * pbone.length).inverted() * (v) for v in verts]

        mesh = obj.data
        mesh.from_pydata(verts, edges, [])
        mesh.update()

def create_aligned_circle_widget(rig, bone_name, number_verts=32, radius=1.0, head_tail=0.0, bone_transform_name=None):
    """ Creates a circle widget, aligned to view.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj is not None:
        
        pbone = rig.pose.bones[bone_name]
        # print(pbone.matrix.translation)
        pos = pbone.matrix.translation
        
        verts, edges = create_circle_polygon(number_verts, 'Y', radius)
        head_tail_vector = pbone.vector * head_tail
        verts = [(pbone.matrix * pbone.length).inverted() * (pos + Vector(v) + head_tail_vector) for v in verts]

        mesh = obj.data
        mesh.from_pydata(verts, edges, [])
        mesh.update()

def create_aligned_crescent_widget(rig, bone_name, radius=1.0, head_tail=0.0, bone_transform_name=None):
    """ Creates a crescent widget, aligned to view.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj is not None:
        
        pbone = rig.pose.bones[bone_name]
        # print(pbone.matrix.translation)
        pos = pbone.matrix.translation
        
        verts = [Vector((-0.3826834559440613, 3.5762786865234375e-07, 0.9238792061805725)), Vector((-0.5555702447891235, 3.5762786865234375e-07, 0.8314692974090576)), Vector((-0.7071067690849304, 3.5762786865234375e-07, 0.7071064710617065)), Vector((-0.8314696550369263, 2.980232238769531e-07, 0.5555698871612549)), Vector((-0.9238795042037964, 3.2782554626464844e-07, 0.382683128118515)), Vector((-0.9807852506637573, 2.980232238769531e-07, 0.19509007036685944)), Vector((-1.0, 2.84984679410627e-07, -2.0948681367372046e-07)), Vector((-0.9807853102684021, 2.682209014892578e-07, -0.19509048759937286)), Vector((-0.9238795638084412, 2.682209014892578e-07, -0.38268357515335083)), Vector((-0.8314696550369263, 2.384185791015625e-07, -0.5555704832077026)), Vector((-0.7071067690849304, 2.384185791015625e-07, -0.7071070671081543)), Vector((-0.5555701851844788, 2.384185791015625e-07, -0.8314699530601501)), Vector((-0.38268327713012695, 2.384185791015625e-07, -0.9238799214363098)), Vector((-0.19509008526802063, 2.384185791015625e-07, -0.980785608291626)), Vector((3.2584136988589307e-07, 2.384185791015625e-07, -1.000000238418579)), Vector((0.19509072601795197, 2.384185791015625e-07, -0.9807854890823364)), Vector((0.38268381357192993, 2.384185791015625e-07, -0.923284649848938)), Vector((0.22629565000534058, 2.384185791015625e-07, -0.9575635194778442)), Vector((0.06365743279457092, 2.384185791015625e-07, -0.954291045665741)), Vector((-0.09898078441619873, 2.384185791015625e-07, -0.9143458008766174)), Vector((-0.2553688883781433, 2.384185791015625e-07, -0.8406103253364563)), Vector((-0.39949703216552734, 2.384185791015625e-07, -0.737377941608429)), Vector((-0.5258263349533081, 2.384185791015625e-07, -0.6102247834205627)), Vector((-0.6295021176338196, 2.384185791015625e-07, -0.465727299451828)), Vector((-0.7065401673316956, 2.682209014892578e-07, -0.3110540509223938)), Vector((-0.7539799809455872, 2.682209014892578e-07, -0.15349547564983368)), Vector((-0.7699984908103943, 2.84984679410627e-07, -1.378889180614351e-07)), Vector((-0.7539798617362976, 2.980232238769531e-07, 0.153495192527771)), Vector((-0.706540048122406, 3.2782554626464844e-07, 0.31105372309684753)), Vector((-0.6295021176338196, 2.980232238769531e-07, 0.4657267928123474)), Vector((-0.5258263349533081, 3.5762786865234375e-07, 0.6102243065834045)), Vector((-0.3994970917701721, 3.5762786865234375e-07, 0.737377405166626)), Vector((-0.25536900758743286, 3.5762786865234375e-07, 0.8406097292900085)), Vector((-0.09898099303245544, 3.5762786865234375e-07, 0.9143452048301697)), Vector((0.06365716457366943, 3.5762786865234375e-07, 0.9542905688285828)), Vector((0.22629405558109283, 3.5762786865234375e-07, 0.9575631022453308)), Vector((0.3826821446418762, 3.5762786865234375e-07, 0.9232847094535828)), Vector((0.19508881866931915, 3.5762786865234375e-07, 0.9807852506637573)), Vector((0.0, 3.5762786865234375e-07, 0.9999997019767761))]

        edges = []
        for i in range(len(verts)):
            edges.append((i, i+1))
        edges[-1] = (0, len(verts)-1)

        head_tail_vector = pbone.vector * head_tail
        verts = [(pbone.matrix * pbone.length).inverted() * (pos + Vector(v) + head_tail_vector) * radius for v in verts]

        mesh = obj.data
        mesh.from_pydata(verts, edges, [])
        mesh.update()

def create_half_ellipse_polygon(number_verts, width=1.0, height=0.5):
    """ Creates a half ellipse.
        number_verts: number of vertices of the polygon
        radius: the radius of the circle
        head_tail: where along the length of the bone the circle is (0.0=head, 1.0=tail)
    """
    verts = []
    edges = []
    angle = pi / number_verts
    i = 0

    while i <= (number_verts):
        a = cos(i * angle)
        b = sin(i * angle)

        verts.append((a * width, 0.0, b * height))

        if i < (number_verts):
            edges.append((i , i + 1))

        i += 1

    edges.append((0, number_verts))

    return verts, edges

def create_aligned_half_ellipse_widget(rig, bone_name, width, height, bone_transform_name=None, head_tail=0.0):
    """ Creates a half ellipse widget, aligned to view.
    """
    obj = create_widget(rig, bone_name, bone_transform_name)
    if obj is not None:
        
        pbone = rig.pose.bones[bone_name]
        # print(pbone.matrix.translation)
        pos = pbone.matrix.translation
        
        verts, edges = create_half_ellipse_polygon(16, width, height)

        head_tail_vector = pbone.vector * head_tail
        verts = [(pbone.matrix * pbone.length).inverted() * (pos + Vector(v) + head_tail_vector) for v in verts]

        mesh = obj.data
        mesh.from_pydata(verts, edges, [])
        mesh.update()


def assign_bone_group(rig, bone_name, bone_group):
    """ Assign bone to bone group.
    """
    
    if not bone_group in rig.pose.bone_groups:
        rig.pose.bone_groups.new(bone_group)
    rig.pose.bones[bone_name].bone_group = rig.pose.bone_groups[bone_group]
