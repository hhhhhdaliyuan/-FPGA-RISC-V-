from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image


def run_cmd(
    cmd: list[str],
    cwd: Path,
    log_path: Path,
    timeout_sec: int | None = None,
) -> tuple[subprocess.CompletedProcess[str] | None, bool]:
    timed_out = False
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_sec,
        )
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        proc = None
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

    log_text = [
        f"$ {' '.join(cmd)}",
        "",
        f"timeout_sec={timeout_sec}",
        f"timed_out={timed_out}",
        "",
        "[stdout]",
        stdout,
        "",
        "[stderr]",
        stderr,
    ]
    log_path.write_text("\n".join(log_text), encoding="utf-8")
    return proc, timed_out


def to_vpath(path: Path) -> str:
    return path.resolve().as_posix()


def write_mem_16bit(values: np.ndarray, path: Path) -> None:
    hex_lines = np.char.mod("%04x", values.astype(np.uint16))
    path.write_text("\n".join(hex_lines.tolist()) + "\n", encoding="utf-8")


def image_to_rgb565_mem(image_path: Path, mem_path: Path) -> tuple[int, int]:
    img = Image.open(image_path).convert("RGB")
    arr = np.asarray(img, dtype=np.uint8)
    h, w = arr.shape[:2]

    r5 = (arr[:, :, 0].astype(np.uint16) >> 3) & 0x1F
    g6 = (arr[:, :, 1].astype(np.uint16) >> 2) & 0x3F
    b5 = (arr[:, :, 2].astype(np.uint16) >> 3) & 0x1F
    rgb565 = ((r5 << 11) | (g6 << 5) | b5).reshape(-1)

    write_mem_16bit(rgb565, mem_path)
    return w, h


def load_u8_mem(mem_path: Path, width: int, height: int) -> np.ndarray:
    pix_total = width * height
    vals = np.zeros((pix_total,), dtype=np.uint8)

    if not mem_path.exists() or mem_path.stat().st_size == 0:
        return vals.reshape((height, width))

    lines = [line.strip() for line in mem_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n = min(len(lines), pix_total)

    for i in range(n):
        token = lines[i]
        try:
            vals[i] = int(token, 16) & 0xFF
        except ValueError:
            vals[i] = 0

    return vals.reshape((height, width))


def compile_once(modelsim_dir: Path, tb_dir: Path, src_files: list[Path], tb_file: Path) -> tuple[str, Path]:
    work_name = f"work_steps_{int(time.time())}"

    vlib_log = modelsim_dir / f"{work_name}_vlib.log"
    vlib_proc, vlib_to = run_cmd(["vlib", work_name], modelsim_dir, vlib_log, timeout_sec=120)
    if vlib_to or vlib_proc is None or vlib_proc.returncode != 0:
        raise RuntimeError(f"vlib failed, see {vlib_log}")

    compile_log = modelsim_dir / f"{work_name}_compile.log"
    compile_cmd = [
        "vlog",
        "-sv",
        "-work",
        work_name,
        f"+incdir+{to_vpath(tb_dir)}",
    ]
    compile_cmd.extend([to_vpath(p) for p in src_files])
    compile_cmd.append(to_vpath(tb_file))

    compile_proc, compile_to = run_cmd(compile_cmd, modelsim_dir, compile_log, timeout_sec=600)
    if compile_to or compile_proc is None or compile_proc.returncode != 0:
        raise RuntimeError(f"Compile failed, see {compile_log}")

    return work_name, compile_log


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    project_root = root.parent
    sim_dir = root / "sim"
    tb_dir = sim_dir / "tb"
    modelsim_dir = sim_dir / "modelsim"

    input_dir = root / "input"
    output_root = root / "output"

    sobel_out_dir = output_root / "sobel"
    hsv_out_dir = output_root / "hsv"
    fusion_out_dir = output_root / "fusion"

    sobel_stage_dirs = {
        "gaussian": sobel_out_dir / "1gaussian",
        "gray": sobel_out_dir / "2gray",
        "sobel": sobel_out_dir / "3sobel",
        "close": sobel_out_dir / "4close",
    }
    hsv_stage_dirs = {
        "mask": hsv_out_dir / "1mask",
        "close": hsv_out_dir / "2close",
    }

    src_dir = project_root / "source" / "image_process"
    src_files = [
        tb_dir / "line_buffer_sim.v",
        src_dir / "rgb2gray.v",
        src_dir / "rgb_hsv.v",
        src_dir / "gaussian5x5.v",
        src_dir / "sobel_x3x3.v",
        src_dir / "morph_close_25x3.v",
        src_dir / "binary_frame_out.v",
        src_dir / "image_process.v",
    ]
    tb_file = tb_dir / "tb_image_process_dual.v"

    for exe in ["vlib", "vlog", "vsim"]:
        if shutil.which(exe) is None:
            print(f"[ERROR] Cannot find executable: {exe}")
            return 2

    missing = [p for p in src_files if not p.exists()]
    if missing or (not tb_file.exists()):
        print("[ERROR] Missing source/tb files")
        for p in missing:
            print(f"  missing: {p}")
        print(f"  tb: {tb_file}")
        return 2

    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    images = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in exts])
    if not images:
        print(f"[ERROR] No images found in {input_dir}")
        return 2

    for d in [modelsim_dir, sobel_out_dir, hsv_out_dir, *sobel_stage_dirs.values(), *hsv_stage_dirs.values()]:
        d.mkdir(parents=True, exist_ok=True)
    fusion_out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(images)} images. Compiling once...")
    try:
        work_name, compile_log = compile_once(modelsim_dir, tb_dir, src_files, tb_file)
        print(f"Compile OK. work lib: {work_name}")
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 2

    report_file = output_root / "batch_report_steps.json"
    report: list[dict[str, object]] = []
    ok_count = 0

    for idx, img_path in enumerate(images, start=1):
        stem = img_path.stem
        print(f"\n[{idx}/{len(images)}] {img_path.name}")

        in_mem = modelsim_dir / f"{stem}_in_rgb565.mem"
        sobel_gray_mem = modelsim_dir / f"{stem}_sobel_gray.mem"
        sobel_gauss_mem = modelsim_dir / f"{stem}_sobel_gaussian.mem"
        sobel_sobel_mem = modelsim_dir / f"{stem}_sobel_sobel.mem"
        sobel_close_mem = modelsim_dir / f"{stem}_sobel_close.mem"
        hsv_mask_mem = modelsim_dir / f"{stem}_hsv_mask.mem"
        hsv_close_mem = modelsim_dir / f"{stem}_hsv_close.mem"
        fusion_mem = modelsim_dir / f"{stem}_fusion.mem"

        for p in [sobel_gray_mem, sobel_gauss_mem, sobel_sobel_mem, sobel_close_mem, hsv_mask_mem, hsv_close_mem, fusion_mem]:
            if p.exists():
                p.unlink()

        try:
            w, h = image_to_rgb565_mem(img_path, in_mem)

            run_log = modelsim_dir / f"{stem}_run.log"
            run_cmdline = [
                "vsim",
                "-c",
                f"{work_name}.tb_image_process_dual",
                f"+IMG_W={w}",
                f"+IMG_H={h}",
                f"+IN_MEM_FILE={to_vpath(in_mem)}",
                f"+OUT_SOBEL_GRAY_MEM_FILE={to_vpath(sobel_gray_mem)}",
                f"+OUT_SOBEL_GAUSSIAN_MEM_FILE={to_vpath(sobel_gauss_mem)}",
                f"+OUT_SOBEL_SOBEL_MEM_FILE={to_vpath(sobel_sobel_mem)}",
                f"+OUT_SOBEL_CLOSE_MEM_FILE={to_vpath(sobel_close_mem)}",
                f"+OUT_HSV_MASK_MEM_FILE={to_vpath(hsv_mask_mem)}",
                f"+OUT_HSV_CLOSE_MEM_FILE={to_vpath(hsv_close_mem)}",
                f"+OUT_FUSION_MEM_FILE={to_vpath(fusion_mem)}",
                "-do",
                "run -all; quit -f",
            ]
            run_proc, run_to = run_cmd(run_cmdline, modelsim_dir, run_log, timeout_sec=1800)

            valid_outputs = all(p.exists() and p.stat().st_size > 0 for p in [sobel_gray_mem, sobel_gauss_mem, sobel_sobel_mem, sobel_close_mem, hsv_mask_mem, hsv_close_mem, fusion_mem])
            if (run_to or run_proc is None) and not valid_outputs:
                report.append(
                    {
                        "image": img_path.name,
                        "status": "sim_timeout",
                        "run_log": to_vpath(run_log),
                        "compile_log": to_vpath(compile_log),
                    }
                )
                print("  [FAIL] timeout")
                continue

            sim_rc = run_proc.returncode if run_proc is not None else -1
            if sim_rc != 0 and not valid_outputs:
                report.append(
                    {
                        "image": img_path.name,
                        "status": "sim_failed",
                        "sim_rc": sim_rc,
                        "run_log": to_vpath(run_log),
                        "compile_log": to_vpath(compile_log),
                    }
                )
                print(f"  [FAIL] sim rc={sim_rc}")
                continue

            sobel_gray_img = load_u8_mem(sobel_gray_mem, w, h)
            sobel_gauss_img = load_u8_mem(sobel_gauss_mem, w, h)
            sobel_sobel_img = load_u8_mem(sobel_sobel_mem, w, h)
            sobel_close_img = load_u8_mem(sobel_close_mem, w, h)
            hsv_mask_img = load_u8_mem(hsv_mask_mem, w, h)
            hsv_close_img = load_u8_mem(hsv_close_mem, w, h)
            fusion_img = load_u8_mem(fusion_mem, w, h)

            sobel_gray_png = sobel_stage_dirs["gray"] / f"{stem}_gray.png"
            sobel_gauss_png = sobel_stage_dirs["gaussian"] / f"{stem}_gaussian.png"
            sobel_sobel_png = sobel_stage_dirs["sobel"] / f"{stem}_sobel.png"
            sobel_close_png = sobel_stage_dirs["close"] / f"{stem}_close.png"
            hsv_mask_png = hsv_stage_dirs["mask"] / f"{stem}_mask.png"
            hsv_close_png = hsv_stage_dirs["close"] / f"{stem}_close.png"
            fusion_png = fusion_out_dir / f"{stem}_fusion.png"

            Image.fromarray(sobel_gray_img, mode="L").save(sobel_gray_png)
            Image.fromarray(sobel_gauss_img, mode="L").save(sobel_gauss_png)
            Image.fromarray(sobel_sobel_img, mode="L").save(sobel_sobel_png)
            Image.fromarray(sobel_close_img, mode="L").save(sobel_close_png)
            Image.fromarray(hsv_mask_img, mode="L").save(hsv_mask_png)
            Image.fromarray(hsv_close_img, mode="L").save(hsv_close_png)
            Image.fromarray(fusion_img, mode="L").save(fusion_png)

            ok_count += 1
            report.append(
                {
                    "image": img_path.name,
                    "status": "ok",
                    "sim_rc": sim_rc,
                    "outputs": {
                        "sobel_gray": to_vpath(sobel_gray_png),
                        "sobel_gaussian": to_vpath(sobel_gauss_png),
                        "sobel_sobel": to_vpath(sobel_sobel_png),
                        "sobel_close": to_vpath(sobel_close_png),
                        "hsv_mask": to_vpath(hsv_mask_png),
                        "hsv_close": to_vpath(hsv_close_png),
                        "fusion": to_vpath(fusion_png),
                    },
                    "compile_log": to_vpath(compile_log),
                    "run_log": to_vpath(run_log),
                }
            )
            print("  [OK] stage images saved")

        except Exception as exc:
            report.append({"image": img_path.name, "status": "exception", "error": str(exc)})
            print(f"  [FAIL] exception: {exc}")

        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n========== stage simulation finished ==========")
    print(f"Success: {ok_count}/{len(images)}")
    print(f"Report : {report_file}")

    return 0 if ok_count == len(images) else 1


if __name__ == "__main__":
    sys.exit(main())
