# ### BEGIN GPL LICENSE BLOCK ###
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# #### END GPL LICENSE BLOCK ####

# This addon is included as a part of "Tea's Ultimate Toolkit" for blender.
# All rights reserved by author.

bl_info = {
    "name"          : "UnBevel",
    "author"        : "TeaCrab",
    "blender"       : (3, 0, 0),
    "description"   : "Unbevel in mesh mode, using Ringed-path selection pattern.",
    "location"      : "3D View, Mesh specials menu [W]",
    "category"      : "Mesh",
    }

import bpy, bmesh
from mathutils import geometry
from math import pi
from bpy.utils import register_class, unregister_class

def angle_2vec3(X, Y):
    return X.angle(Y) % pi

def getIntersection(a, b):
    BMEdge = bmesh.types.BMEdge
    ax, bx = (a.verts[0].co, a.verts[1].co) if isinstance(a, BMEdge) else (a[0], a[1])
    ay, by = (b.verts[0].co, b.verts[1].co) if isinstance(b, BMEdge) else (b[0], b[1])
    if angle_2vec3(ax-bx, ay-by) < 0.002:
        return None
    else:
        vec = geometry.intersect_line_line(ax, bx, ay, by)
        return (vec[0] + vec[1]) / 2

def is_edge_end_of_selection(edge, selected):
    for v in edge.verts:
        temp = [e for e in v.link_edges if e in selected]
        if len(temp) == 1:
            return True
    return False

def get_current_edge_loop(edge, selected):
    loop = [edge]
    v_checked = []
    v_next = None
    for v in edge.verts:
        possible = [e for e in v.link_edges if e in selected and e not in loop]
        n = len(possible)
        if n == 0:
            v_checked.append(v)
            v_next = edge.other_vert(v)
            break
        elif n == 1:
            v_checked.append(edge.other_vert(v))
            v_next = v
            break
        else:
            return None

    while v_next not in v_checked:
        possible = [e for e in v_next.link_edges if e in selected and e not in loop]
        n = len(possible)
        if n == 1:
            loop.append(possible[0])
            v_checked.append(v_next)
            v_next = possible[0].other_vert(v_next)
        elif n > 1:
            return None
        else:
            return loop
    return loop

def get_edge_rings(selected_edges):
    edge_rings = [[],]
    context_edges = [e for e in selected_edges if is_edge_end_of_selection(e, selected_edges)]
    if len(context_edges) == 0:
        return None

    for edge in context_edges:
        if edge in [e for ring in edge_rings for e in ring]:
            continue
        else:
            loop = get_current_edge_loop(edge, selected_edges)
            if loop != None:
                if edge_rings[-1] == []:
                    edge_rings[-1] = loop
                else:
                    edge_rings.append(loop)
            else:
                return None
    return edge_rings

class TCA_UnBevel(bpy.types.Operator):
    bl_idname = 'mesh.tca_unbevel'
    bl_label = 'Unbevel (Ringed Path)'
    bl_description = ''
    bl_options = {'REGISTER', 'UNDO'}

    keep_support : bpy.props.BoolProperty(
        name = "Keep Supporting Edges",
        description = "Keep the supporting edges that were used to be the boundaries of the bevel.",
        default = False)

    @classmethod
    def poll(self, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        edges = [e for e in bm.edges if e.select]
        verts = [v for v in bm.verts if v.select]
        edge_rings = get_edge_rings(edges)

        intersection_error = 0
        path_error = 0
        if edge_rings != None:
            for ring in edge_rings:
                if len(ring) < 3:
                    path_error += 1
                    continue
                edge_pair = [e for e in ring if is_edge_end_of_selection(e, edges)]
                if self.keep_support:
                    edge_pair_verts = [v for e in edge_pair for v in e.verts]
                    other_verts = [v for e in ring for v in e.verts if v not in edge_pair_verts]
                else:
                    other_edges = [e for e in ring if e not in edge_pair]
                    other_verts = [v for e in other_edges for v in e.verts]
                intersection = getIntersection(edge_pair[0], edge_pair[1])
                if intersection == None:
                    intersection_error += 1
                else:
                    for v in other_verts:
                        v.co = intersection
            bmesh.ops.remove_doubles(bm, verts = verts, dist = 0.001)
            bmesh.update_edit_mesh(me)
            errors = [intersection_error, path_error]
            if any(errors):
                msg = "Unbevel can't be done on a path with parallel ends: {}\nUnbevel can't be done on a path with less than 3 edges: {}\n".format(intersection_error, path_error)
                self.report({'ERROR'}, msg)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Unrecognizable selection pattern.")
            return {'CANCELLED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "keep_support", toggle = True)

def UI_unbevel(self, context):
    self.layout.operator("mesh.tca_unbevel")

def register():
    register_class(TCA_UnBevel)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(UI_unbevel)

def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(UI_unbevel)
    unregister_class(TCA_UnBevel)

if __name__ == "__main__":
    register()
