import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PhaseATests(unittest.TestCase):
    def test_loader_reads_sparse_spad_raw_bin_and_metadata(self):
        from scipy.io import savemat
        from scipy import sparse

        from sim_spad_loader import load_spad_mat, bin_to_mm

        peak_bins = (np.arange(64 * 64, dtype=np.uint16) % 1024).reshape(64, 64)
        rows = np.arange(64 * 64)
        spad = sparse.coo_matrix(
            (np.full(64 * 64, 3.0), (rows, peak_bins.ravel())),
            shape=(64 * 64, 1024),
        )
        intensity = np.arange(64 * 64, dtype=np.float64).reshape(64, 64)

        tmp = ROOT / "out" / "test_tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        path = tmp / "sample.mat"
        savemat(
            str(path),
            {
                "spad": spad,
                "bin": peak_bins,
                "bin_size": np.array([[8e-11]]),
                "SBR": np.array([[0.2]]),
                "mean_signal_photons": np.array([[2.0]]),
                "intensity": intensity,
                "est_range_bins_argmax": peak_bins + 1,
                "est_range_bins_lmf": peak_bins + 2,
                "est_range_bins_zncc": peak_bins + 3,
            },
        )

        sample = load_spad_mat(path, start_stop="forward")

        self.assertEqual(sample.hist.shape, (64, 64, 1024))
        self.assertEqual(float(sample.hist[0, 5, 5]), 3.0)
        self.assertEqual(sample.bin_size_ps, 80.0)
        np.testing.assert_allclose(
            sample.depth_mm,
            bin_to_mm(peak_bins, bin_size_ps=80.0),
            rtol=1e-6,
        )
        np.testing.assert_array_equal(sample.intensity, intensity)
        np.testing.assert_array_equal(sample.est_argmax_bins, peak_bins + 1)
        np.testing.assert_array_equal(sample.est_lmf_bins, peak_bins + 2)
        np.testing.assert_array_equal(sample.est_zncc_bins, peak_bins + 3)

    def test_argmax_estimate_respects_start_stop_and_min_counts(self):
        from algorithms.argmax import ArgmaxConfig, estimate
        from sim_spad_loader import BINS, SpadSample

        hist = np.zeros((1, 3, BINS), dtype=np.float32)
        hist[0, 0, 10] = 5.0
        hist[0, 1, 20] = 0.5
        hist[0, 2, 30] = 10.0
        sample = SpadSample(
            hist=hist,
            depth_mm=np.ones((1, 3), dtype=np.float32),
            sbr=None,
            mean_signal_photons=None,
            mean_background_photons=None,
            sample_id="synthetic",
            start_stop="reverse",
            bin_size_ps=80.0,
        )

        out = estimate(sample, ArgmaxConfig(min_counts=1.0))

        bin_mm = 80.0 * 0.299792458 / 2.0
        self.assertEqual(out.algo_name, "argmax_v0")
        np.testing.assert_allclose(
            out.depth_mm,
            np.array([[(BINS - 1 - 10) * bin_mm, 0.0, (BINS - 1 - 30) * bin_mm]], dtype=np.float32),
        )
        np.testing.assert_allclose(out.confidence, np.array([[0.5, 0.0, 1.0]], dtype=np.float32))

    def test_metrics_compute_expected_values(self):
        from contracts import DepthEstimate
        from eval.metrics import compute_all, hit_rate, rmse
        from sim_spad_loader import SpadSample

        gt = np.array([[100.0, 200.0], [0.0, 400.0]], dtype=np.float32)
        pred = np.array([[110.0, 260.0], [300.0, 0.0]], dtype=np.float32)
        sample = SpadSample(
            hist=np.zeros((2, 2, 1024), dtype=np.float32),
            depth_mm=gt,
            sbr=0.2,
            mean_signal_photons=2.0,
            mean_background_photons=None,
            sample_id="metrics",
            start_stop="forward",
        )
        estimate = DepthEstimate(
            depth_mm=pred,
            confidence=np.ones((2, 2), dtype=np.float32),
            algo_name="test_algo",
        )

        self.assertAlmostEqual(rmse(pred, gt), np.sqrt((10.0**2 + 60.0**2 + 400.0**2) / 3.0))
        self.assertAlmostEqual(hit_rate(pred, gt, tol_mm=100.0), 2.0 / 3.0)
        metrics = compute_all(estimate, sample, tol_mm=100.0)
        self.assertEqual(metrics["algo"], "test_algo")
        self.assertAlmostEqual(metrics["valid_pred_ratio"], 3.0 / 4.0)
        self.assertAlmostEqual(metrics["valid_gt_ratio"], 3.0 / 4.0)


if __name__ == "__main__":
    unittest.main()
