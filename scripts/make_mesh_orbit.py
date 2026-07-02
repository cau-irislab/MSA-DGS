#!/usr/bin/env python3
"""Render a 360-degree orbital video of a PLY mesh.

Matches the Three.js viewer in index.html:
  - Dark blue-gray background (#1a1f2e)
  - Light gray mesh (MeshStandardMaterial 0xcccccc, roughness 0.55)
  - One key directional light, one cool fill light
  - Camera at fov=45, distance ~3, centered on the normalized mesh

Usage: make_mesh_orbit.py <input.ply> <output.mp4>

Requires: pyvista, numpy, ffmpeg (on PATH).
"""

import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pyvista as pv


def render_orbit(ply_path: str, out_path: str,
                 size: int = 600, n_frames: int = 180, fps: int = 30) -> None:
    pv.OFF_SCREEN = True

    mesh = pv.read(ply_path)

    # Normalize: center at origin, scale so max extent = 2.0.
    center = np.array(mesh.center)
    mesh.translate(-center, inplace=True)
    bounds = mesh.bounds
    extent = max(bounds[1] - bounds[0],
                 bounds[3] - bounds[2],
                 bounds[5] - bounds[4])
    mesh.scale(2.0 / extent, inplace=True)

    plotter = pv.Plotter(off_screen=True, window_size=(size, size),
                         lighting="none")
    plotter.background_color = "#1a1f2e"

    plotter.add_mesh(
        mesh,
        color="#cccccc",
        smooth_shading=True,
        ambient=0.35,
        diffuse=0.75,
        specular=0.15,
        specular_power=18,
    )

    # Key + fill + ambient, roughly matching the Three.js scene.
    plotter.add_light(pv.Light(
        position=(2.0, 3.0, 3.0), focal_point=(0, 0, 0),
        color=(1.0, 1.0, 1.0), intensity=1.1, light_type="scene light",
    ))
    plotter.add_light(pv.Light(
        position=(-2.0, -1.0, -2.0), focal_point=(0, 0, 0),
        color=(0.8, 0.87, 1.0), intensity=0.55, light_type="scene light",
    ))
    plotter.add_light(pv.Light(
        color=(1.0, 1.0, 1.0), intensity=0.35, light_type="headlight",
    ))

    plotter.camera.view_angle = 45

    # Yaw orbit around world Z (mesh's natural vertical), starting 90° offset
    # from the previous version's start. Constant slight elevation gives a
    # gentle "looking down" angle without any up-down bob.
    radius = 3.2
    elev_deg = 12.0
    start_offset = np.pi

    tmpdir = tempfile.mkdtemp(prefix="mesh_orbit_")
    try:
        for i in range(n_frames):
            t = i / n_frames
            az = start_offset + 2.0 * np.pi * t
            el = np.deg2rad(elev_deg)
            x = radius * np.cos(el) * np.cos(az)
            y = radius * np.cos(el) * np.sin(az)
            z = radius * np.sin(el)
            plotter.camera_position = [(x, y, z), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)]
            plotter.render()
            plotter.screenshot(os.path.join(tmpdir, f"f_{i:04d}.png"),
                               return_img=False)

        plotter.close()

        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", os.path.join(tmpdir, "f_%04d.png"),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            out_path,
        ], check=True)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: make_mesh_orbit.py <input.ply> <output.mp4>",
              file=sys.stderr)
        sys.exit(1)
    render_orbit(sys.argv[1], sys.argv[2])
