# -*- coding: utf-8 -*-
"""
SafeAlert — redisposição COMPLETA dos sensores (fonte: README + config + geometria Blender).

SISTEMA (lido da documentação/código):
  - Anti-esmagamento: ToF/US no TOPO do guarda-corpo, FoV para CIMA.
  - Cobertura MVP = só o DECK FIXO. Extensão roll-out em X ∈ [0.105, 1.015] FORA do FoV.
  - Classificador geométrico (geometry.h): hits no envelope do fixo; consenso 2+ sensores.
  - Extensão pode abrir sem mover sensores nem tensionar cabo (laço de folga).

GEOMETRIA BLENDER (SJIII 3226):
  Platform_Deck  X[-1.065, 1.065]  Y[-0.375, 0.375]
  Extension_Deck X[ 0.105, 1.015]  ← móvel, SEM sensor
  Deck FIXO útil X[-1.015, 0.050]  Y[±0.355]  (antes do roll-out)
  Top rail Z ≈ 2.16 m
  Postes nos cantos: (±1.015, ±0.355) e intermediários

DISPOSIÇÃO (3 pontos só na TRASEIRA do deck FIXO — longe do limiar X=0.105):
  S0 Traseira_L : (-1.015, +0.355)  canto traseiro +Y
  S1 Traseira_R : (-1.015, -0.355)  canto traseiro -Y
  S2 Lateral_R  : (-0.533, -0.355)  poste no rail -Y (terço traseiro)
                  Longe da junta fixo/extensão; extensão pode abrir livre.

Eixo óptico ToF = local +Z. US legado = local +X (meshes antigos).
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

# --- constantes alinhadas a config.h / modelo ---
YOFF = 4.5
TOP_Z = 2.16
EXT_X0 = 0.105
FOV_TOF = 27.0
# Limite duro: sensores longe do limiar da extensão (X=0.105)
# Terceiro sensor no poste Post_3 / Post_2 (X≈-0.533), NÃO no limiar.
X_SENSOR_MAX = -0.50

# Centro da zona instrumentada (traseira do fixo)
CX = -0.774
CY = 0.0

# (id_legado, nome_doc, pos_local_US)
SENSORS = [
    ("Esquerdo", "Traseira_L", Vector((-1.015, 0.355, TOP_Z))),
    ("Central", "Traseira_R", Vector((-1.015, -0.355, TOP_Z))),
    ("Direito", "Lateral_R", Vector((-0.533, -0.355, TOP_Z))),  # poste traseiro, rail -Y
]

TOF_LAYERS = [
    ("Alcance", 4.00, (0.35, 0.85, 0.95), 0.06),
    ("Amarelo", 2.50, (0.95, 0.85, 0.15), 0.11),
    ("Vermelho", 1.20, (0.95, 0.25, 0.15), 0.17),
    ("Bloqueio", 0.60, (0.25, 0.45, 0.95), 0.28),
]


def aim_up_to_fixed_center(sx: float, sy: float, tilt_deg: float = 8.0) -> Vector:
    dx, dy = CX - sx, CY - sy
    h = math.hypot(dx, dy) or 1.0
    t = math.radians(tilt_deg)
    v = Vector((dx / h * math.sin(t), dy / h * math.sin(t), math.cos(t)))
    return v.normalized()


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
    mz = mat_alpha("MVP_Extensao_Zona", (1.0, 0.45, 0.08), 0.32)

    def one(name, yoff, parent_name):
        # footprint da extensão
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0.56, yoff, 1.162))
        o = bpy.context.active_object
        o.name = name
        o.dimensions = (0.90, 0.66, 0.012)
        bpy.context.view_layer.update()
        o.data.materials.clear()
        o.data.materials.append(mz)
        link(o, zcol)
        root = bpy.data.objects[parent_name]
        parent_keep(o, root)

        # plano vertical no limiar fixo/extensão
        bpy.ops.mesh.primitive_cube_add(size=1, location=(EXT_X0, yoff, 1.65))
        wall = bpy.context.active_object
        wall.name = name + "_Limiar"
        wall.dimensions = (0.01, 0.72, 1.0)
        bpy.context.view_layer.update()
        wall.data.materials.clear()
        wall.data.materials.append(mat_alpha("MVP_Ext_Limiar", (1.0, 0.2, 0.1), 0.2))
        link(wall, zcol)
        parent_keep(wall, root)

        bpy.ops.object.text_add(location=(0.30, yoff + 0.02, 1.22))
        t = bpy.context.active_object
        t.name = name.replace("Zona_", "Label_")
        t.data.body = "EXTENSÃO (móvel)\\nSEM sensor — X≥0,105"
        t.data.body = "EXTENSÃO (móvel)\nSEM sensor — X≥0,105"
        t.data.size = 0.04
        t.data.extrude = 0.001
        t.rotation_euler = (math.radians(90), 0, 0)
        link(t, zcol)
        parent_keep(t, root)

    one("Zona_Extensao_Deck", 0.0, "SJIII_3226_ROOT")
    one("Zona_Extensao_Deck_ToF", YOFF, "SJIII_3226_ToF_ROOT")


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
    M_BODY = mat_solid("ToF_Body", (0.07, 0.12, 0.22), 0.35, 0.25)
    M_WIN = mat_solid("ToF_Window", (0.2, 0.05, 0.3), 0.12, 0.0)
    M_HOOD = mat_solid("MVP_Hood", (0.08, 0.08, 0.08), 0.45, 0.0)
    cable_mats = {
        "Esquerdo": bpy.data.materials.get("MVP_Cable_Orange"),
        "Central": bpy.data.materials.get("MVP_Cable_Blue"),
        "Direito": bpy.data.materials.get("MVP_Cable_Black"),
    }

    print("=== REBUILD ToF (3 cantos do FIXO) ===")
    for old, label, pos in SENSORS:
        assert pos.x <= X_SENSOR_MAX + 1e-6, pos
        assert pos.x < EXT_X0, pos
        world = pos + Vector((0, YOFF, 0))
        direction = aim_up_to_fixed_center(pos.x, pos.y)
        rot3 = direction.to_track_quat("Z", "Y").to_matrix()

        bpy.ops.object.empty_add(type="ARROWS", location=world)
        g = bpy.context.active_object
        g.name = f"Grupo_Sensor_ToF_{old}"
        g.empty_display_size = 0.06
        g["corner"] = label
        g["fixed_only"] = True
        link(g, col)
        set_mw(g, rot3, world)
        parent_keep(g, root)

        # corpo (aplicar escala ANTES do matrix_world)
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

        bpy.ops.object.text_add(location=world + Vector((0.02, -0.02, 0.06)))
        lab = bpy.context.active_object
        lab.name = f"Label_Sensor_ToF_{old}"
        lab.data.body = f"ToF {label}"
        lab.data.size = 0.03
        lab.data.extrude = 0.0008
        lab.rotation_euler = (math.radians(90), 0, 0)
        link(lab, col)
        parent_keep(lab, root)

        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
        hood = bpy.context.active_object
        hood.name = f"MVP_Capuz_{old}"
        hood.scale = (0.048, 0.038, 0.006)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        hood.data.materials.clear()
        hood.data.materials.append(M_HOOD)
        link(hood, inst if inst else col)
        set_mw(hood, rot3, world + direction * 0.032)
        parent_keep(hood, root)

        print(f"  {label}: pos={tuple(round(v,3) for v in world)} dir={tuple(round(v,3) for v in direction)}")

    # Cabos: só rails do FIXO + laço de folga
    esp = bpy.data.objects.get("MVP_ESP32")
    if esp and inst:
        B = esp.matrix_world.translation + Vector((0, 0, -0.035))
        rail_z = 2.145
        y_plus, y_minus = 0.355 + YOFF, -0.355 + YOFF
        for old, label, pos in SENSORS:
            tgt = pos + Vector((0, YOFF, 0))
            offs = {"Esquerdo": -0.028, "Central": 0.0, "Direito": 0.028}[old]
            p0 = B + Vector((offs, 0, 0))
            p_slack = B + Vector((offs, -0.12, 0.10))  # folga
            # sobe para rail +Y (lado do painel) sem entrar na extensão
            p_up = Vector((min(B.x, -0.40), y_plus + 0.025, rail_z))
            pts = [p0, p_slack, p_up]
            if old == "Esquerdo":
                pts += [
                    Vector((-1.015, y_plus + 0.025, rail_z)),
                    tgt + Vector((0.04, 0.04, -0.02)),
                    tgt + Vector((0, 0, -0.015)),
                ]
            elif old == "Central":
                pts += [
                    Vector((-1.015, y_plus + 0.025, rail_z)),
                    Vector((-1.015, y_minus - 0.025, rail_z)),
                    tgt + Vector((0.04, -0.04, -0.02)),
                    tgt + Vector((0, 0, -0.015)),
                ]
            else:  # Lateral_R em X=-0.533, Y=-
                pts += [
                    Vector((-1.015, y_plus + 0.025, rail_z)),
                    Vector((-1.015, y_minus - 0.025, rail_z)),
                    Vector((-0.533, y_minus - 0.025, rail_z)),
                    tgt + Vector((0.04, -0.04, -0.02)),
                    tgt + Vector((0, 0, -0.015)),
                ]
            # nenhum ponto de cabo invade a extensão
            for p in pts:
                if p.x > X_SENSOR_MAX + 0.05:
                    p.x = X_SENSOR_MAX
            cd = bpy.data.curves.new(f"MVP_Cabo_{old}_d", "CURVE")
            cd.dimensions = "3D"
            cd.bevel_depth = 0.0045
            cd.bevel_resolution = 2
            cd.fill_mode = "FULL"
            sp = cd.splines.new("POLY")
            sp.points.add(len(pts) - 1)
            for i, p in enumerate(pts):
                sp.points[i].co = (p.x, p.y, p.z, 1)
            o = bpy.data.objects.new(f"MVP_Cabo_{old}", cd)
            bpy.context.scene.collection.objects.link(o)
            m = cable_mats.get(old)
            if m:
                o.data.materials.append(m)
            link(o, inst)
            parent_keep(o, root)


def rebuild_us():
    """Reposiciona grupos US (volumes no eixo +X) nos mesmos 3 cantos."""
    root = bpy.data.objects["SJIII_3226_ROOT"]
    print("=== REBUILD US (mesmos cantos) ===")
    for old, label, pos in SENSORS:
        g = bpy.data.objects.get(f"Grupo_Sensor_{old}")
        if not g:
            print("  missing", old)
            continue
        direction = aim_up_to_fixed_center(pos.x, pos.y)
        rot3 = direction.to_track_quat("X", "Z").to_matrix()  # US mesh: feixe +X
        set_mw(g, rot3, pos)
        g["corner"] = label
        g["fixed_only"] = True
        if g.parent != root:
            parent_keep(g, root)
        lab = bpy.data.objects.get(f"Label_Sensor_{old}")
        if lab:
            lab.parent = None
            lab.location = pos + Vector((0.02, -0.02, 0.06))
            lab.rotation_euler = (math.radians(90), 0, 0)
            lab.data.body = f"US {label}"
            lab.data.size = 0.03
            parent_keep(lab, root)
        print(f"  {label}: {tuple(round(v,3) for v in pos)}")


def print_dirs_for_config():
    print("--- SENSOR_DIR for config.h ---")
    for old, label, pos in SENSORS:
        d = aim_up_to_fixed_center(pos.x, pos.y)
        print(
            f"  // {label} {tuple(round(v,3) for v in pos)}\n"
            f"  {{ {d.x: .4f}f, {d.y: .4f}f, {d.z: .4f}f }},"
        )


def main():
    rebuild_extension_markers()
    rebuild_tof()
    rebuild_us()
    print_dirs_for_config()
    bpy.context.view_layer.update()
    bpy.ops.wm.save_mainfile()

    # sanity
    for old, label, pos in SENSORS:
        g = bpy.data.objects[f"Grupo_Sensor_ToF_{old}"]
        s = bpy.data.objects[f"Sensor_ToF_{old}"]
        t = g.matrix_world.translation
        assert t.x < EXT_X0
        assert abs(t.x - (pos.x)) < 0.02
        assert s.dimensions.x < 0.08
        z = g.matrix_world.to_3x3() @ Vector((0, 0, 1))
        assert z.z > 0.95, z
    print("SANITY_PASS: 3 sensores na traseira fixa (longe do limiar)")


if __name__ == "__main__":
    main()
