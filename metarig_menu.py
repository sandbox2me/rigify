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

# <pep8 compliant>

import os
from string import capwords

import bpy

from . import utils
from . import template_list



class ArmatureSubMenu(bpy.types.Menu):
    # bl_idname = 'ARMATURE_MT_armature_class'

    def draw(self, context):
        layout = self.layout
        layout.label(self.bl_label)
        for op, name in self.operators:
            text = capwords(name.replace("_", " ")) + " (Meta-Rig)"
            layout.operator(op, icon='OUTLINER_OB_ARMATURE', text=text)


def get_metarig_list(path, mode='relative', depth=0):
    """ Searches for metarig modules, and returns a list of the
        imported modules.
    """
    if mode == 'relative':
        base_path = ''
        MODULE_DIR = os.path.dirname(__file__)
        METARIG_DIR_ABS = os.path.join(MODULE_DIR, utils.METARIG_DIR)
        SEARCH_DIR_ABS = os.path.join(METARIG_DIR_ABS, path)
    elif mode == 'absolute':
        base_path = path
        SEARCH_DIR_ABS = path
    else:
        return

    metarigs_dict = dict()
    metarigs = []
    files = os.listdir(SEARCH_DIR_ABS)
    files.sort()

    for f in files:
        is_dir = os.path.isdir(os.path.join(SEARCH_DIR_ABS, f))  # Whether the file is a directory

        # Stop cases
        if f[0] in [".", "_"]:
            continue
        if f.count(".") >= 2 or (is_dir and "." in f):
            print("Warning: %r, filename contains a '.', skipping" % os.path.join(SEARCH_DIR_ABS, f))
            continue

        if is_dir:
            # Check directories
            if mode == 'relative':
                module_name = os.path.join(path, f).replace(os.sep, ".")
                metarig = utils.get_metarig_module(module_name, base_path=base_path)
            else:
                module_name = "__init__"
                metarig = utils.get_metarig_module(module_name, base_path=os.path.join(base_path, f, ''))

            # Check for sub-rigs
            metarigs_dict[f] = get_metarig_list(os.path.join(path, f, ""), mode=mode, depth=1)  # "" adds a final slash
        elif f.endswith(".py"):
            # Check straight-up python files
            t = f[:-3]
            if mode == 'relative':
                module_name = os.path.join(path, t).replace(os.sep, ".")
                metarig = utils.get_metarig_module(module_name, base_path=base_path)
            else:
                custom_folder = bpy.context.user_preferences.addons['rigify'].preferences.custom_folder
                custom_metarigs_folder = os.path.join(custom_folder, utils.METARIG_DIR, '')
                module_name = os.path.join(path, t).replace(custom_metarigs_folder, '').replace(os.sep, ".")
                metarig = utils.get_metarig_module(module_name, base_path=custom_metarigs_folder)
            metarigs += [metarig]

    if depth == 1:
        return metarigs

    metarigs_dict[utils.METARIG_DIR] = metarigs
    return metarigs_dict


def make_metarig_add_execute(m):
    """ Create an execute method for a metarig creation operator.
    """
    def execute(self, context):
        # Add armature object
        bpy.ops.object.armature_add()
        obj = context.active_object
        obj.name = "metarig"
        obj.data.name = "metarig"

        # Remove default bone
        bpy.ops.object.mode_set(mode='EDIT')
        bones = context.active_object.data.edit_bones
        bones.remove(bones[0])

        template_list.fill_ui_template_list(obj)

        # Create metarig
        m.create(obj)

        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}
    return execute


def make_metarig_menu_func(bl_idname, text):
    """ For some reason lambda's don't work for adding multiple menu
        items, so we use this instead to generate the functions.
    """
    def metarig_menu(self, context):
        self.layout.operator(bl_idname, icon='OUTLINER_OB_ARMATURE', text=text)
    return metarig_menu


def make_submenu_func(bl_idname, text):
    def metarig_menu(self, context):
        self.layout.menu(bl_idname, icon='OUTLINER_OB_ARMATURE', text=text)
    return metarig_menu


# Get the metarig modules
metarigs_dict = get_metarig_list("")
metarig_ops = {}
armature_submenus = []
menu_funcs = []


def create_metarig_ops(dic=metarigs_dict):
    """Create metarig add Operators"""
    for metarig_class in dic:
        if metarig_class == "external":
            create_metarig_ops(dic[metarig_class])
            continue
        metarig_ops[metarig_class] = []
        for m in dic[metarig_class]:
            name = m.__name__.rsplit('.', 1)[1]

            # Dynamically construct an Operator
            T = type("Add_" + name + "_Metarig", (bpy.types.Operator,), {})
            T.bl_idname = "object.armature_" + name + "_metarig_add"
            T.bl_label = "Add " + name.replace("_", " ").capitalize() + " (metarig)"
            T.bl_options = {'REGISTER', 'UNDO'}
            T.execute = make_metarig_add_execute(m)

            metarig_ops[metarig_class].append((T, name))

def create_menu_funcs():
    global menu_funcs
    for mop, name in metarig_ops[utils.METARIG_DIR]:
        text = capwords(name.replace("_", " ")) + " (Meta-Rig)"
        menu_funcs += [make_metarig_menu_func(mop.bl_idname, text)]

def create_armature_submenus(dic=metarigs_dict):
    global menu_funcs
    metarig_classes = list(dic.keys())
    metarig_classes.sort()
    for metarig_class in metarig_classes:
        # Create menu functions
        if metarig_class == "external":
            create_armature_submenus(dic=metarigs_dict["external"])
            continue
        if metarig_class == utils.METARIG_DIR:
            continue

        armature_submenus.append(type('Class_' + metarig_class + '_submenu', (ArmatureSubMenu,), {}))
        armature_submenus[-1].bl_label = metarig_class + ' (submenu)'
        armature_submenus[-1].bl_idname = 'ARMATURE_MT_%s_class' % metarig_class
        armature_submenus[-1].operators = []
        menu_funcs += [make_submenu_func(armature_submenus[-1].bl_idname, metarig_class)]

        for mop, name in metarig_ops[metarig_class]:
            arm_sub = next((e for e in armature_submenus if e.bl_label == metarig_class + ' (submenu)'), '')
            arm_sub.operators.append((mop.bl_idname, name,))

create_metarig_ops()
create_menu_funcs()
create_armature_submenus()

def register():
    for cl in metarig_ops:
        for mop, name in metarig_ops[cl]:
            bpy.utils.register_class(mop)

    for arm_sub in armature_submenus:
        bpy.utils.register_class(arm_sub)

    for mf in menu_funcs:
        bpy.types.INFO_MT_armature_add.append(mf)

def unregister():
    for cl in metarig_ops:
        for mop, name in metarig_ops[cl]:
            bpy.utils.unregister_class(mop)

    for arm_sub in armature_submenus:
        bpy.utils.unregister_class(arm_sub)

    for mf in menu_funcs:
        bpy.types.INFO_MT_armature_add.remove(mf)

def get_external_metarigs(custom_metarigs_folder):
    unregister()

    if custom_metarigs_folder:
        metarigs_dict['external'] = get_metarig_list(custom_metarigs_folder, mode='absolute')

    metarig_ops.clear()
    armature_submenus.clear()
    menu_funcs.clear()

    create_metarig_ops()
    create_menu_funcs()
    create_armature_submenus()
    register()
