"""
SafeAlert — modelo forte de disposição (deck FIXO, só CANTOS do rail).

Regras:
  1) Sensores só no TOPO do guarda-corpo do deck PRINCIPAL.
  2) Nunca no miolo do cesto (Y≈0 no meio) nem no meio do comprimento.
  3) Nunca em X ≥ EXTENSAO_X (roll-out).
  4) 3 cantos do retângulo fixo + cabo com laço de folga.
  5) Eixo óptico ToF = local +Z.

Cantos (metros, Z = topo rail 2.16):
  Traseira L: (-1.015, +0.355)
  Traseira R: (-1.015, -0.355)
  Frente L (limiar fixo): (+0.050, +0.355)
"""

import bpy
import math
from mathutils import Vector, Matrix

EXT_X = 0.105
TOP_Z = 2.16
YOFF = 4.5
FOV = 27.0

# Centro do deck FIXO (para leve convergência do FoV)
CX = (-1.015 + 0.050) * 0.5  # ≈ -0.4825
CY = 0.0


def aim_toward_fixed_center(sx, sy, tilt_deg=9.0):
    dx, dy = CX - sx, CY - sy
    horiz = math.hypot(dx, dy) or 1.0
    t = math.radians(tilt_deg)
    return Vector((dx / horiz * math.sin(t), dy / horiz * math.sin(t), math.cos(t))).normalized()


# (legacy_suffix, new_label, pos_US)
CORNERS = [
    ("Esquerdo", "Traseira_L", Vector((-1.015, 0.355, TOP_Z))),
    ("Central", "Traseira_R", Vector((-1.015, -0.355, TOP_Z))),
    ("Direito", "Frente_L", Vector((0.050, 0.355, TOP_Z))),
]

LAYERS = [
    ("Alcance", 4.00, (0.35, 0.85, 0.95), 0.07),
    ("Amarelo", 2.50, (0.95, 0.85, 0.15), 0.12),
    ("Vermelho", 1.20, (0.95, 0.25, 0.15), 0.18),
    ("Bloqueio", 0.60, (0.25, 0.45, 0.95), 0.30),
]


def mat_alpha(name, color, alpha):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Roughness"].default_value = 0.4
    m.blend_method = "BLEND"
    if hasattr(m, "shadow_method"):
        m.shadow_method = "NONE"
    return m


def mat_solid(name, color, rough=0.4, metal=0.1):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
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


def set_world(obj, rot3, origin):
    mw = rot3.to_4x4()
    mw.translation = origin
    obj.matrix_world = mw


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
    col = bpy.data.collections.get("Sensores_ToF") or bpy.data.collections.new("Sensores_ToF")
    if col.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects["SJIII_3226_ToF_ROOT"]
    inst = bpy.data.collections.get("Instalacao_MVP_ToF")
    M_BODY = mat_solid("ToF_Body", (0.08, 0.12, 0.22), 0.35, 0.2)
    M_WIN = mat_solid("ToF_Window", (0.15, 0.05, 0.25), 0.15, 0.0)
    M_HOOD = mat_solid("MVP_Hood", (0.1, 0.1, 0.1), 0.45, 0.0)

    cable_mats = {
        "Esquerdo": bpy.data.materials.get("MVP_Cable_Orange"),
        "Central": bpy.data.materials.get("MVP_Cable_Blue"),
        "Direito": bpy.data.materials.get("MVP_Cable_Black"),
    }

    print("CORNER_MODEL ToF")
    for old, label, pos in CORNERS:
        assert pos.x < EXT_X
        world = pos + Vector((0, YOFF, 0))
        direction = aim_toward_fixed_center(pos.x, pos.y)
        rot3 = direction.to_track_quat("Z", "Y").to_matrix()

        bpy.ops.object.empty_add(type="ARROWS", location=world)
        g = bpy.context.active_object
        g.name = f"Grupo_Sensor_ToF_{old}"
        g.empty_display_size = 0.07
        g["corner"] = label
        g["fixed_deck_only"] = True
        link(g, col)
        set_world(g, rot3, world)
        mw = g.matrix_world.copy()
        g.parent = root
        g.matrix_world = mw

        # body — apply scale BEFORE matrix_world
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
        body = bpy.context.active_object
        body.name = f"Sensor_ToF_{old}"
        body.scale = (0.036, 0.028, 0.016)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        body.data.materials.clear()
        body.data.materials.append(M_BODY)
        link(body, col)
        set_world(body, rot3, world)
        mw = body.matrix_world.copy()
        body.parent = g
        body.matrix_world = mw

        bpy.ops.mesh.primitive_cylinder_add(radius=0.006, depth=0.003, location=(0, 0, 0))
        win = bpy.context.active_object
        win.name = f"Sensor_ToF_{old}_Window"
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        win.data.materials.clear()
        win.data.materials.append(M_WIN)
        link(win, col)
        wpos = world + direction * 0.010
        set_world(win, rot3, wpos)
        mw = win.matrix_world.copy()
        win.parent = g
        win.matrix_world = mw

        for layer, length, rgb, alpha in LAYERS:
            radius = math.tan(math.radians(FOV * 0.5)) * length
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
            set_world(cone, rot3, world)
            mw = cone.matrix_world.copy()
            cone.parent = g
            cone.matrix_world = mw
            if layer == "Alcance":
                cone.hide_set(True)

        bpy.ops.object.text_add(location=world + Vector((0.03, 0.03, 0.07)))
        lab = bpy.context.active_object
        lab.name = f"Label_Sensor_ToF_{old}"
        lab.data.body = f"ToF {label}\ncanto fixo"
        lab.data.size = 0.035
        lab.data.extrude = 0.001
        lab.rotation_euler = (math.radians(90), 0, 0)
        link(lab, col)
        mw = lab.matrix_world.copy()
        lab.parent = root
        lab.matrix_world = mw

        # hood
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
        hood = bpy.context.active_object
        hood.name = f"MVP_Capuz_{old}"
        hood.scale = (0.05, 0.04, 0.006)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        hood.data.materials.clear()
        hood.data.materials.append(M_HOOD)
        if inst:
            link(hood, inst)
        else:
            link(hood, col)
        hpos = world + direction * 0.035
        set_world(hood, rot3, hpos)
        mw = hood.matrix_world.copy()
        hood.parent = root
        hood.matrix_world = mw

        print(f"  {label}: {tuple(round(v,3) for v in world)} aim={tuple(round(v,3) for v in direction)}")

    # cables with slack loops (folga) along fixed rails only
    esp = bpy.data.objects.get("MVP_ESP32")
    if esp and inst:
        B = esp.matrix_world.translation + Vector((0, 0, -0.04))
        rail_z = 2.148
        y_plus = 0.355 + YOFF
        y_minus = -0.355 + YOFF
        for old, label, pos in CORNERS:
            tgt = pos + Vector((0, YOFF, 0))
            offs = {"Esquerdo": -0.03, "Central": 0.0, "Direito": 0.03}[old]
            # path: gland → drip loop → rail → along fixed rails → small slack at sensor
            p0 = B + Vector((offs, 0, 0))
            p_loop = B + Vector((offs, -0.08, 0.06))  # laço de folga perto da caixa
            p_rail = Vector((B.x + offs, y_plus + 0.03, rail_z))
            pts = [p0, p_loop, p_rail]
            if old == "Esquerdo":
                pts += [
                    Vector((-1.015, y_plus + 0.03, rail_z)),
                    tgt + Vector((0.04, 0.04, -0.02)),
                    tgt + Vector((0, 0, -0.02)),
                ]
            elif old == "Central":
                pts += [
                    Vector((-1.015, y_plus + 0.03, rail_z)),
                    Vector((-1.015, y_minus - 0.03, rail_z)),
                    tgt + Vector((0.04, -0.04, -0.02)),
                    tgt + Vector((0, 0, -0.02)),
                ]
            else:  # Frente_L
                pts += [
                    Vector((0.05, y_plus + 0.03, rail_z)),
                    tgt + Vector((-0.04, 0.04, -0.02)),
                    tgt + Vector((0, 0, -0.02)),
                ]
            cd = bpy.data.curves.new(f"MVP_Cabo_{old}_d", "CURVE")
            cd.dimensions = "3D"
            cd.bevel_depth = 0.005
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
            mw = o.matrix_world.copy()
            o.parent = root
            o.matrix_world = mw


def rebuild_us_aims():
    """US legado: volumes no +X — reposiciona grupos nos 3 cantos."""
    root = bpy.data.objects["SJIII_3226_ROOT"]
    print("CORNER_MODEL US")
    for old, label, pos in CORNERS:
        g = bpy.data.objects.get(f"Grupo_Sensor_{old}")
        if not g:
            print("  missing", old)
            continue
        direction = aim_toward_fixed_center(pos.x, pos.y)
        # US mesh beam = local +X
        rot3 = direction.to_track_quat("X", "Z").to_matrix()
        mw = rot3.to_4x4()
        mw.translation = pos
        g.matrix_world = mw
        if g.parent != root:
            mw2 = g.matrix_world.copy()
            g.parent = root
            g.matrix_world = mw2
        g["corner"] = label
        lab = bpy.data.objects.get(f"Label_Sensor_{old}")
        if lab:
            lab.parent = None
            lab.location = pos + Vector((0.03, 0.03, 0.07))
            lab.rotation_euler = (math.radians(90), 0, 0)
            lab.data.body = f"US {label}"
            lab.data.size = 0.035
            mw = lab.matrix_world.copy()
            lab.parent = root
            lab.matrix_world = mw
        print(f"  {label}: {tuple(round(v,3) for v in pos)}")


def main():
    rebuild_tof()
    rebuild_us_aims()
    bpy.context.view_layer.update()
    bpy.ops.wm.save_mainfile()
    # sanity
    for old, label, pos in CORNERS:
        g = bpy.data.objects[f"Grupo_Sensor_ToF_{old}"]
        s = bpy.data.objects[f"Sensor_ToF_{old}"]
        assert g.matrix_world.translation.x < EXT_X
        assert abs(g.matrix_world.translation.y - (pos.y + YOFF)) < 0.02
        assert s.dimensions.x < 0.1
        z = g.matrix_world.to_3x3() @ Vector((0, 0, 1))
        assert z.z > 0.9
    print("SANITY_PASS corner-only model")


if __name__ == "__main__":
    main()
