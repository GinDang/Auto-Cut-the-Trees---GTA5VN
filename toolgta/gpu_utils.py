"""
AUTO GTA5VN - GPU Acceleration Utilities
Version 5.0

Optional CUDA-accelerated template matching via OpenCV's CUDA module.
If CUDA is unavailable (no GPU, OpenCV built without CUDA, etc.),
all operations gracefully fall back to CPU-only processing.
"""
from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

logger: logging.Logger = logging.getLogger("AutoGTA")


class GPUAccelerator:
    """Optional GPU-accelerated image processing via OpenCV CUDA.

    The class probes for CUDA availability at construction time.
    If CUDA is not present or fails to initialise, all methods
    transparently fall back to standard CPU implementations.

    Attributes:
        _available: Whether a CUDA device was successfully detected.
        _device_name: Human-readable name of the CUDA device, or ``"N/A"``.
    """

    def __init__(self) -> None:
        """Initialise the accelerator and probe for CUDA devices."""
        self._available: bool = False
        self._device_name: str = "N/A"

        try:
            device_count: int = cv2.cuda.getCudaEnabledDeviceCount()
            if device_count > 0:
                self._available = True
                # Attempt to retrieve the device name
                try:
                    cv2.cuda.setDevice(0)
                    # cv2.cuda.printShortCudaDeviceInfo writes to stdout;
                    # we just note that a device is available.
                    self._device_name = f"CUDA Device 0 (of {device_count})"
                except Exception:
                    self._device_name = f"CUDA ({device_count} device(s))"
                logger.info(
                    "GPU acceleration available: %s", self._device_name
                )
            else:
                logger.info("No CUDA devices found — using CPU only")
        except (AttributeError, cv2.error, Exception) as exc:
            logger.debug("CUDA probe failed (%s) — using CPU only", exc)

    # ----------------------------------------------------------
    #  Properties
    # ----------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Return ``True`` if a usable CUDA device was detected."""
        return self._available

    @property
    def device_name(self) -> str:
        """Return a human-readable name for the active CUDA device."""
        return self._device_name

    # ----------------------------------------------------------
    #  Template matching
    # ----------------------------------------------------------

    def template_match(
        self,
        screen: np.ndarray,
        template: np.ndarray,
        method: int = cv2.TM_CCOEFF_NORMED,
    ) -> np.ndarray:
        """Perform template matching, preferring GPU when available.

        If CUDA is available the images are uploaded to GPU memory and
        matched using ``cv2.cuda.createTemplateMatching``.  On any
        failure the method falls back to ``cv2.matchTemplate`` on the
        CPU.

        Args:
            screen: Grayscale (or preprocessed) screen capture.
            template: Grayscale (or preprocessed) template image.
            method: OpenCV template matching method constant.
                    Defaults to ``cv2.TM_CCOEFF_NORMED``.

        Returns:
            The result matrix from template matching (same as
            ``cv2.matchTemplate`` output).
        """
        if self._available:
            try:
                gpu_screen: Any = cv2.cuda_GpuMat()
                gpu_template: Any = cv2.cuda_GpuMat()
                gpu_screen.upload(screen)
                gpu_template.upload(template)

                matcher = cv2.cuda.createTemplateMatching(
                    screen.dtype, method
                )
                gpu_result: Any = matcher.match(gpu_screen, gpu_template)
                return gpu_result.download()
            except Exception as exc:
                logger.debug(
                    "GPU template match failed (%s) — falling back to CPU",
                    exc,
                )

        # CPU fallback
        return cv2.matchTemplate(screen, template, method)

    # ----------------------------------------------------------
    #  Repr
    # ----------------------------------------------------------

    def __repr__(self) -> str:
        status = "available" if self._available else "unavailable"
        return f"<GPUAccelerator {status} device={self._device_name!r}>"
