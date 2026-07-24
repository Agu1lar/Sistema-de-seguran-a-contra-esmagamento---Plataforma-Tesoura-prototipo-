# -*- coding: utf-8 -*-
"""
SafeAlert — disposição ORIGINAL restaurada + ponta na extensão.

Modelo (começo do projeto):
  S0 Ponta_A  (-1.015, +0.355)  traseira, rail +Y   → FIXO
  S1 Meio     ( 0.000, -0.355)  meio, rail -Y       → FIXO
  S2 Ponta_B  (+1.015,  0.000)  ponta dianteira     → na Extension_Deck
       FoV cobre o volume do cesto; quando o roll-out abre, S2 vai junto
       (cabo com grande laço de folga a partir do deck fixo).

Eixo ToF = local +Z. US legado = local +X.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

YOFF = 4.5
TOP_Z = 2.16
EXT_X0 = 0.105
FOV_TOF = 27.0

# Poses stowed (extensão recolhida) — iguais ao início do projeto
SENSORS = [
    # old_key, label, pos_US_world_stowed, on_extension
    ("Esquerdo", "Ponta_A", Vector((-1.015, 0.355, TOP_Z)), False),
    ("Central", "Meio", Vector((0.000, -0.355, TOP_Z)), False),
    ("Direito", "Ponta_B_Ext", Vector((1.015, 0.000, TOP_Z)), True),
]

# Aims originais (cobertura do volume)
AIMS = {
    "Esquerdo": Vector((0.1045, -0.1564, 0.9821)).normalized(),
    "Central": Vector((0.0000, 0.1736, 0.9848)).normalized(),
    "Direito": Vector((-0.1564, 0.0000, 0.9877)).normalized(),
}

TOF_LAYERS = [
    ("Alcance", 4.00, (0.35, 0.85, 0.95), 0.06),
    ("Amarelo", 2.50, (0.95, 0.85, 0.15), 0.11),
    ("Vermelho", 1.20, (0.95, 0.25, 0.15), 0.17),
    ("Bloqueio", 0.60, (0.25, 0.45, 0.95), 0.28),
]


def mat_alpha(name, rgb, alpha):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Roughness"].default_value = 0.4
    m.blend_method = "BLEND"
    if hasattr(m, "shadow_method"):
        m.shadow_method = "NONE"
    return m


def mat_solid(name, rgb, rough=0.4, metal=0.1):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metal
    return m


def wipe(prefixes):
    for o in list(bpy.data.objects):
        if any(o.name.startswith(p) for p in prefixes):
            bpy.data.objects.remove(o, do_unlink=True)


def link(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def set_mw(obj, rot3, origin: Vector):
    mw = rot3.to_4x4()
    mw.translation = origin.copy()
    obj.matrix_world = mw


def parent_keep(child, parent):
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw


def ensure_col(name):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(col)
    return col


def rebuild_extension_markers():
    wipe(["Zona_Extensao_", "Label_Extensao_", "Label_Zona_"])
    zcol = ensure_col("Zona_Extensao")
    mz = mat_alpha("MVP_Extensao_Zona", (1.0, 0.55, 0.1), 0.28)

    def one(name, yoff, parent_name, note):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0.56, yoff, 1.162))
        o = bpy.context.active_object
        o.name = name
        o.dimensions = (0.90, 0.66, 0.012)
        bpy.context.view_layer.update()
        o.data.materials.clear()
        o.data.materials.append(mz)
        link(o, zcol)
        parent_keep(o, bpy.data.objects[parent_name])

        bpy.ops.mesh.primitive_cube_add(size=1, location=(EXT_X0, yoff, 1.65))
        wall = bpy.context.active_object
        wall.name = name + "_Limiar"
        wall.dimensions = (0.008, 0.72, 1.0)
        bpy.context.view_layer.update()
        wall.data.materials.clear()
        wall.data.materials.append(mat_alpha("MVP_Ext_Limiar", (1.0, 0.15, 0.1), 0.22))
        link(wall, zcol)
        parent_keep(wall, bpy.data.objects[parent_name])

        bpy.ops.object.text_add(location=(0.28, yoff + 0.02, 1.22))
        t = bpy.context.active_object
        t.name = name.replace("Zona_", "Label_")
        t.data.body = note
        t.data.size = 0.038
        t.data.extrude = 0.001
        t.rotation_euler = (math.radians(90), 0, 0)
        link(t, zcol)
        parent_keep(t, bpy.data.objects[parent_name])

    one(
        "Zona_Extensao_Deck",
        0.0,
        "SJIII_3226_ROOT",
        "EXTENSÃO (móvel)\nPonta_B vai junto + cabo folga",
    )
    one(
        "Zona_Extensao_Deck_ToF",
        YOFF,
        "SJIII_3226_ToF_ROOT",
        "EXTENSÃO (móvel)\nPonta_B vai junto + cabo folga",
    )


def make_tof_sensor(old, label, world, direction, parent_obj, col, inst):
    rot3 = direction.to_track_quat("Z", "Y").to_matrix()
    M_BODY = mat_solid("ToF_Body", (0.07, 0.12, 0.22), 0.35, 0.25)
    M_WIN = mat_solid("ToF_Window", (0.2, 0.05, 0.3), 0.12, 0.0)
    M_HOOD = mat_solid("MVP_Hood", (0.08, 0.08, 0.08), 0.45, 0.0)

    bpy.ops.object.empty_add(type="ARROWS", location=world)
    g = bpy.context.active_object
    g.name = f"Grupo_Sensor_ToF_{old}"
    g.empty_display_size = 0.06
    g["corner"] = label
    g["on_extension"] = label.startswith("Ponta_B")
    link(g, col)
    set_mw(g, rot3, world)
    parent_keep(g, parent_obj)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    body = bpy.context.active_object
    body.name = f"Sensor_ToF_{old}"
    body.scale = (0.034, 0.026, 0.015)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    body.data.materials.clear()
    body.data.materials.append(M_BODY)
    link(body, col)
    set_mw(body, rot3, world)
    parent_keep(body, g)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.0055, depth=0.003, location=(0, 0, 0))
    win = bpy.context.active_object
    win.name = f"Sensor_ToF_{old}_Window"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    win.data.materials.clear()
    win.data.materials.append(M_WIN)
    link(win, col)
    set_mw(win, rot3, world + direction * 0.01)
    parent_keep(win, g)

    for layer, length, rgb, alpha in TOF_LAYERS:
        radius = math.tan(math.radians(FOV_TOF * 0.5)) * length
        bpy.ops.mesh.primitive_cone_add(
            vertices=48, radius1=0.0, radius2=radius, depth=length, location=(0, 0, 0)
        )
        cone = bpy.context.active_object
        cone.name = f"Volume_ToF_{layer}_{old}"
        cone.location.z = length * 0.5
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        cone.data.materials.clear()
        cone.data.materials.append(mat_alpha(f"ToFVol_{layer}", rgb, alpha))
        link(cone, col)
        set_mw(cone, rot3, world)
        parent_keep(cone, g)
        if layer == "Alcance":
            cone.hide_set(True)

    root_label = bpy.data.objects["SJIII_3226_ToF_ROOT"]
    bpy.ops.object.text_add(location=world + Vector((0.02, 0.02, 0.06)))
    lab = bpy.context.active_object
    lab.name = f"Label_Sensor_ToF_{old}"
    lab.data.body = f"ToF {label}" + ("\n(na extensão)" if "Ext" in label else "")
    lab.data.size = 0.03
    lab.data.extrude = 0.0008
    lab.rotation_euler = (math.radians(90), 0, 0)
    link(lab, col)
    parent_keep(lab, root_label)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    hood = bpy.context.active_object
    hood.name = f"MVP_Capuz_{old}"
    hood.scale = (0.048, 0.038, 0.006)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    hood.data.materials.clear()
    hood.data.materials.append(M_HOOD)
    link(hood, inst if inst else col)
    set_mw(hood, rot3, world + direction * 0.032)
    parent_keep(hood, g)  # hood follows sensor (incl. extension)

    return g


def cable_poly(name, world_pts, radius, material, col, root):
    """Cabo com pontos em LOCAL do ROOT (perimetro externo; nao corta o cesto)."""
    from mathutils import Matrix

    cd = bpy.data.curves.new(name + "_d", "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth = radius
    cd.bevel_resolution = 4
    cd.fill_mode = "FULL"
    sp = cd.splines.new("POLY")
    sp.points.add(len(world_pts) - 1)
    inv = root.matrix_world.inverted()
    for i, wp in enumerate(world_pts):
        lp = inv @ wp
        sp.points[i].co = (lp.x, lp.y, lp.z, 1)
    o = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(o)
    if material:
        o.data.materials.append(material)
    link(o, col)
    o.parent = root
    o.matrix_basis = Matrix.Identity(4)
    return o


def ensure_cable_mats():
    return {
        "Esquerdo": mat_solid("MVP_Cable_Orange", (0.95, 0.45, 0.08), 0.55, 0.0),
        "Central": mat_solid("MVP_Cable_Blue", (0.18, 0.40, 0.90), 0.55, 0.0),
        "Direito": mat_solid("MVP_Cable_Black", (0.06, 0.06, 0.06), 0.55, 0.0),
    }


def rebuild_cables_tof(inst, root):
    """Cabos so na FACE EXTERNA dos top rails — nunca atravessam o volume do cesto."""
    wipe(["MVP_Cabo_", "Label_Cabo_"])
    if not bpy.data.objects.get("MVP_ESP32") or not inst:
        print("skip cables (no ESP/inst)")
        return

    mats = ensure_cable_mats()
    g0 = bpy.data.objects["MVP_Gland_0"].matrix_world.translation.copy()
    g1 = bpy.data.objects["MVP_Gland_1"].matrix_world.translation.copy()
    g2 = bpy.data.objects["MVP_Gland_2"].matrix_world.translation.copy()

    y_out_p = 0.355 + YOFF + 0.030
    y_out_m = -0.355 + YOFF - 0.030
    x_rear = -1.015 - 0.030
    x_front = 1.015 + 0.030
    z_rail = 2.158
    z_drop = 1.58

    sens_a = Vector((-1.015, 0.355 + YOFF, TOP_Z))
    cable_poly(
        "MVP_Cabo_Esquerdo",
        [
            g0 + Vector((0, 0.01, -0.015)),
            Vector((g0.x, y_out_p, g0.z)),
            Vector((g0.x, y_out_p, z_rail)),
            Vector((-0.40, y_out_p, z_rail)),
            Vector((x_rear + 0.02, y_out_p, z_rail)),
            Vector((sens_a.x, y_out_p, TOP_Z - 0.01)),
            Vector((sens_a.x, sens_a.y, TOP_Z - 0.006)),
        ],
        0.0065,
        mats["Esquerdo"],
        inst,
        root,
    )

    sens_m = Vector((0.0, -0.355 + YOFF, TOP_Z))
    cable_poly(
        "MVP_Cabo_Central",
        [
            g1 + Vector((0, 0.01, -0.015)),
            Vector((g1.x, y_out_p, g1.z)),
            Vector((g1.x, y_out_p, z_rail)),
            Vector((-0.55, y_out_p, z_rail)),
            Vector((x_rear, y_out_p, z_rail)),
            Vector((x_rear, YOFF, z_rail)),
            Vector((x_rear, y_out_m, z_rail)),
            Vector((-0.40, y_out_m, z_rail)),
            Vector((0.00, y_out_m, z_rail)),
            Vector((sens_m.x, y_out_m, TOP_Z - 0.01)),
            Vector((sens_m.x, sens_m.y, TOP_Z - 0.006)),
        ],
        0.0065,
        mats["Central"],
        inst,
        root,
    )

    sens_b = Vector((1.015, YOFF, TOP_Z))
    sx = 0.06
    cable_poly(
        "MVP_Cabo_Direito",
        [
            g2 + Vector((0, 0.01, -0.015)),
            Vector((g2.x, y_out_p, g2.z)),
            Vector((g2.x, y_out_p, z_rail)),
            Vector((sx, y_out_p, z_rail)),
            Vector((sx, y_out_p + 0.025, z_rail)),
            Vector((sx, y_out_p + 0.025, 1.90)),
            Vector((sx, y_out_p + 0.035, z_drop)),
            Vector((sx + 0.05, y_out_p + 0.035, z_drop)),
            Vector((sx + 0.05, y_out_p + 0.025, 1.90)),
            Vector((sx + 0.05, y_out_p + 0.025, z_rail)),
            Vector((0.55, y_out_p, z_rail)),
            Vector((x_front, y_out_p, z_rail)),
            Vector((x_front, YOFF + 0.12, z_rail)),
            Vector((x_front, sens_b.y, z_rail)),
            Vector((sens_b.x, sens_b.y, TOP_Z - 0.006)),
        ],
        0.007,
        mats["Direito"],
        inst,
        root,
    )
    bpy.context.view_layer.update()
    print("cables rebuilt: outer-rail perimeter only")


def rebuild_tof():
    wipe(
        [
            "Grupo_Sensor_ToF_",
            "Sensor_ToF_",
            "Volume_ToF_",
            "Label_Sensor_ToF_",
            "MVP_Capuz_",
            "MVP_Cabo_",
        ]
    )
    col = ensure_col("Sensores_ToF")
    inst = bpy.data.collections.get("Instalacao_MVP_ToF")
    root = bpy.data.objects["SJIII_3226_ToF_ROOT"]
    ext = bpy.data.objects["Extension_Deck_ToFClone"]

    print("=== RESTORE ORIGINAL + Ponta_B on Extension ===")
    for old, label, pos, on_ext in SENSORS:
        world = pos + Vector((0, YOFF, 0))
        direction = AIMS[old]
        parent = ext if on_ext else root
        make_tof_sensor(old, label, world, direction, parent, col, inst)
        print(f"  {label}: {tuple(round(v,3) for v in world)} parent={parent.name}")

    rebuild_cables_tof(inst, root)


def rebuild_us():
    root = bpy.data.objects["SJIII_3226_ROOT"]
    ext = bpy.data.objects["Extension_Deck"]
    print("=== US same layout ===")
    for old, label, pos, on_ext in SENSORS:
        g = bpy.data.objects.get(f"Grupo_Sensor_{old}")
        if not g:
            print(" missing", old)
            continue
        direction = AIMS[old]
        rot3 = direction.to_track_quat("X", "Z").to_matrix()
        set_mw(g, rot3, pos)
        g["corner"] = label
        g["on_extension"] = on_ext
        parent = ext if on_ext else root
        parent_keep(g, parent)
        lab = bpy.data.objects.get(f"Label_Sensor_{old}")
        if lab:
            lab.parent = None
            lab.location = pos + Vector((0.02, 0.02, 0.06))
            lab.rotation_euler = (math.radians(90), 0, 0)
            lab.data.body = f"US {label}" + ("\n(extensão)" if on_ext else "")
            lab.data.size = 0.03
            parent_keep(lab, root)
        print(f"  {label}: parent={parent.name}")


def main():
    rebuild_extension_markers()
    rebuild_tof()
    rebuild_us()
    bpy.context.view_layer.update()
    bpy.ops.wm.save_mainfile()

    # sanity
    g_ext = bpy.data.objects["Grupo_Sensor_ToF_Direito"]
    assert g_ext.parent and "Extension" in g_ext.parent.name, g_ext.parent
    g_fix = bpy.data.objects["Grupo_Sensor_ToF_Esquerdo"]
    assert "Extension" not in (g_fix.parent.name if g_fix.parent else "")
    for old, _, _, _ in SENSORS:
        s = bpy.data.objects[f"Sensor_ToF_{old}"]
        assert s.dimensions.x < 0.08
    print("SANITY_PASS: original coverage + Ponta_B on extension")


if __name__ == "__main__":
    main()
