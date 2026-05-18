# Tests for the TOF TCSPC deep-learning scaffold.
import struct
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def write_tch(path: Path, seq: int = 7, width: int = 32, height: int = 32, bins: int = 1024) -> np.ndarray:
    payload = (np.arange(width * height * bins, dtype=np.uint32) % 1024).astype("<u2")
    header = struct.pack(
        "<8sIHHHHQ",
        b"TCHIST1\0",
        seq,
        width,
        height,
        bins,
        2,
        payload.nbytes,
    )
    path.write_bytes(header + payload.tobytes())
    return payload.reshape(height, width, bins)


TORCH_AVAILABLE = find_spec("torch") is not None


class TchReaderTests(unittest.TestCase):
    def test_read_tch_returns_metadata_and_normalized_histogram_without_torch(self):
        from ml.data.tof_dataset import normalize_histogram, read_tch

        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "frame.tch"
            raw = write_tch(source, seq=11)
            loaded = read_tch(source)
            normalized = normalize_histogram(loaded["histogram"])

        self.assertEqual(loaded["seq"], 11)
        self.assertEqual(loaded["width"], 32)
        self.assertEqual(loaded["height"], 32)
        self.assertEqual(loaded["bins"], 1024)
        self.assertEqual(loaded["histogram"].shape, (32, 32, 1024))
        self.assertAlmostEqual(float(normalized.max()), 1.0)
        self.assertAlmostEqual(float(normalized[0, 0, 1]), float(raw[0, 0, 1] / raw.max()))


@unittest.skipUnless(TORCH_AVAILABLE, "torch is not installed")
class TofDatasetTests(unittest.TestCase):
    def test_single_tch_sample_is_normalized_and_has_no_depth(self):
        from ml.data.tof_dataset import TofHistogramDataset

        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "frame.tch"
            raw = write_tch(source)

            sample = TofHistogramDataset(tmp)[0]

        self.assertEqual(tuple(sample["histogram"].shape), (1, 32, 32, 1024))
        self.assertIsNone(sample["depth"])
        self.assertAlmostEqual(float(sample["histogram"].max()), 1.0)
        self.assertAlmostEqual(float(sample["histogram"][0, 0, 0, 1]), float(raw[0, 0, 1] / raw.max()))

    def test_paired_foggy_and_clear_depth_uses_clear_peak_as_depth_target(self):
        from ml.data.tof_dataset import TofHistogramDataset

        with TemporaryDirectory() as tmp:
            foggy = Path(tmp) / "foggy"
            clear = Path(tmp) / "clear"
            foggy.mkdir()
            clear.mkdir()
            write_tch(foggy / "pair.tch")
            clear_hist = write_tch(clear / "pair.tch")

            sample = TofHistogramDataset(foggy_dir=foggy, clear_dir=clear)[0]

        self.assertEqual(tuple(sample["depth"].shape), (1, 32, 32))
        expected_mm = int(clear_hist[0, 0].argmax()) * 55.0 * 0.299792458 / 2.0
        self.assertAlmostEqual(float(sample["depth"][0, 0, 0]), expected_mm, places=4)


@unittest.skipUnless(TORCH_AVAILABLE, "torch is not installed")
class ModelShapeTests(unittest.TestCase):
    def test_hist3d_and_unet_output_depth_maps(self):
        import torch
        from ml.models.hist3d_net import DepthUNet, Hist3DNet

        hist3d = Hist3DNet(base_channels=4)
        unet = DepthUNet(base_channels=4)

        with torch.no_grad():
            hist_out = hist3d(torch.zeros(1, 1, 32, 32, 1024))
            unet_out = unet(torch.zeros(1, 1, 32, 32))

        self.assertEqual(tuple(hist_out.shape), (1, 1, 32, 32))
        self.assertEqual(tuple(unet_out.shape), (1, 1, 32, 32))
        self.assertGreaterEqual(float(hist_out.min()), 0.0)
        self.assertGreaterEqual(float(unet_out.min()), 0.0)


if __name__ == "__main__":
    unittest.main()
