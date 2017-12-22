#====================== BEGIN GPL LICENSE BLOCK ======================
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
#======================= END GPL LICENSE BLOCK ========================

import os

from . import utils


def get_template_list(path=''):
    """ Searches for template types, and returns a list.
    """
    if not path:
        MODULE_DIR = os.path.dirname(__file__)
        TEMPLATE_DIR_ABS = os.path.join(MODULE_DIR, utils.TEMPLATE_DIR)
    else:
        TEMPLATE_DIR_ABS = path
    files = os.listdir(TEMPLATE_DIR_ABS)
    files.sort()

    files = [f for f in files if f.endswith(".py")]
    return files


def fill_ui_template_list(obj):
    """Fill rig's UI template list
    """
    armature_id_store = obj.data
    for i in range(0, len(armature_id_store.rigify_templates)):
        armature_id_store.rigify_templates.remove(0)

    for t in template_list:
        a = armature_id_store.rigify_templates.add()
        a.name = t[:-3]


# Public variables
template_list = get_template_list()


def get_external_templates(custom_templates_folder):
    global template_list
    template_list = get_template_list()
    if custom_templates_folder:
        external_templates_list = get_template_list(custom_templates_folder)
        template_list.extend(external_templates_list)
