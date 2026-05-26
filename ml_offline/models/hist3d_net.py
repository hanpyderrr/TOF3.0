# Neural network models for TCSPC histogram depth estimation.
from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


class ConvBlock2d(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DepthUNet(nn.Module):
    """Small 2D U-Net baseline for noisy 32x32 depth maps."""

    def __init__(self, in_channels: int = 1, base_channels: int = 32) -> None:
        super().__init__()
        self.enc1 = ConvBlock2d(in_channels, base_channels)
        self.enc2 = ConvBlock2d(base_channels, base_channels * 2)
        self.bridge = ConvBlock2d(base_channels * 2, base_channels * 4)

        self.up2 = nn.ConvTranspose2d(base_channels * 4, base_channels * 2, kernel_size=2, stride=2)
        self.dec2 = ConvBlock2d(base_channels * 4, base_channels * 2)
        self.up1 = nn.ConvTranspose2d(base_channels * 2, base_channels, kernel_size=2, stride=2)
        self.dec1 = ConvBlock2d(base_channels * 2, base_channels)
        self.out = nn.Conv2d(base_channels, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(F.max_pool2d(e1, 2))
        bridge = self.bridge(F.max_pool2d(e2, 2))

        d2 = self.up2(bridge)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))
        d1 = self.up1(d2)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))
        return F.relu(self.out(d1))


class Hist3DNet(nn.Module):
    """3D CNN encoder over TCSPC bins followed by a 2D U-Net decoder."""

    def __init__(self, base_channels: int = 16, decoder_channels: int = 32) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv3d(1, base_channels, kernel_size=(1, 1, 16), stride=(1, 1, 4), padding=(0, 0, 6)),
            nn.BatchNorm3d(base_channels),
            nn.ReLU(inplace=True),
            nn.Conv3d(
                base_channels,
                base_channels * 2,
                kernel_size=(1, 1, 8),
                stride=(1, 1, 4),
                padding=(0, 0, 2),
            ),
            nn.BatchNorm3d(base_channels * 2),
            nn.ReLU(inplace=True),
            nn.Conv3d(base_channels * 2, base_channels * 4, kernel_size=(1, 1, 4), stride=(1, 1, 4)),
            nn.BatchNorm3d(base_channels * 4),
            nn.ReLU(inplace=True),
        )
        self.decoder = DepthUNet(in_channels=base_channels * 4 * 16, base_channels=decoder_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(x)
        batch, channels, rows, cols, bins = encoded.shape
        features = encoded.permute(0, 1, 4, 2, 3).reshape(batch, channels * bins, rows, cols)
        return self.decoder(features)
