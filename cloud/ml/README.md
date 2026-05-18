# TOF Single-Photon ML Scaffold

This directory contains the first deep-learning pipeline for fog-robust PF32 TOF imaging from TCSPC histograms.

## Structure

- `data/tof_dataset.py`: loads `.tch` TCSPC histogram files and paired foggy/clear samples.
- `models/hist3d_net.py`: `Hist3DNet` for `(B,1,32,32,1024)` histograms and `DepthUNet` for `(B,1,32,32)` baseline depth maps.
- `train/train.py`: trains `hist3d` or `unet` with L1 + SSIM loss, AdamW, and cosine LR scheduling.
- `export/to_onnx.py`: exports checkpoints to ONNX opset 17 and verifies ONNX Runtime output.
- `infer/run_infer.py`: runs CPU ONNX inference on one `.tch` file and writes a `.npy` depth map.
- `tests/`: lightweight scaffold tests.

## Data Format

`.tch` files use little-endian layout:

```text
Header:
  magic        8B  "TCHIST1\0"
  seq          4B  uint32
  width        2B  uint16, expected 32
  height       2B  uint16, expected 32
  bins         2B  uint16, expected 1024
  sampleBytes  2B  uint16, expected 2
  payloadBytes 8B  uint64
Payload:
  uint16[height * width * bins], reshaped to (32, 32, 1024)
```

Histograms are normalized per sample by dividing by `max(histogram)`. Paired training expects foggy and clear directories with matching `.tch` file names. The current target depth baseline is derived from the clear histogram peak bin:

```text
depth_mm = peak_bin * 55ps * 0.299792458 mm/ps / 2
```

## Training

Install dependencies in the target Python environment:

```bash
pip install -r ml/requirements.txt
```

Train the 3D TCSPC model:

```bash
python ml/train/train.py \
  --model hist3d \
  --data-dir data/foggy \
  --clear-dir data/clear \
  --epochs 20 \
  --lr 0.001 \
  --batch-size 2 \
  --output-dir ml/runs/hist3d \
  --device cpu
```

Train the 2D U-Net baseline:

```bash
python ml/train/train.py \
  --model unet \
  --data-dir data/foggy \
  --clear-dir data/clear \
  --epochs 20 \
  --lr 0.001 \
  --batch-size 8 \
  --output-dir ml/runs/unet \
  --device cpu
```

## Export

```bash
python ml/export/to_onnx.py \
  --model hist3d \
  --checkpoint ml/runs/hist3d/best_model.pth \
  --output ml/runs/hist3d/best_model.onnx
```

## Inference

```bash
python ml/infer/run_infer.py \
  --model-path ml/runs/hist3d/best_model.onnx \
  --input-tch data/foggy/frame_000001.tch \
  --output-npy output/depth_000001.npy
```
