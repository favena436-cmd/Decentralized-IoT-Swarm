# Samsung Galaxy SM-S921U — Hardware Profile

## Device Identity
- Model: SM-S921U (Samsung Galaxy S24)
- Hardware: Qualcomm (qcom)
- Board: pineapple
- Android: 16 (SDK 36)

## CPU
- Architecture: ARM64 (arm64-v8a), ARMv8
- Implementer: 0x41 (ARM)
- Features: fp, asimd, evtstrm, aes, pmull, sha1, sha2, crc32, atomics, fphp, asimdhp, cpuid, asimdrdm, jscvt, fcma, lrcpc, dcpop, sha3, sm3, sm4, asimddp, sha512, asimdfhm, dit, uscat, ilrcpc, flagm, sb, paca, pacg, dcpodp, flagm2, frint, i8mm, bf16, dgh, bti, ecf, afp
- 8 cores (big.LITTLE Qualcomm Snapdragon)

## GPU
- Renderer: Qualcomm Adreno 750
- OpenGL ES: 3.2 V@0762.41
- GPU Vendor: adreno

## Memory
- Total RAM: 7,283,372 KB (~7.1 GB)
- Available: ~1.7 GB (phone was under heavy use during scan)

## Display
- Resolution: 1080 x 2340 pixels

## Battery
- Status: 5 (FULL)
- Health: 2 (GOOD)
- Level: 100%
- Voltage: 4241 mV

## Thermal
- CPU temp: 36.8°C (at time of scan)

## Storage
- Data partition: 109 GB total, ~1.9 GB free (99% used)

## Connectivity
- USB debugging: ENABLED (ADB interface active)
- ADB device ID: RFCWC1BW4DH
- Connection: USB (TCP/IP not yet configured)

## Hardware Acceleration Available
- ✅ Adreno 750 GPU (OpenCL, Vulkan, OpenGL ES 3.2)
- ✅ ARM NEON instructions (asimd)
- ✅ Qualcomm NPU (via QNN/HTP for AI inference)
- ✅ Hardware video encode/decode

## Access Methods
- ADB USB: `adb -s RFCWC1BW4DH shell` or `adb -s RFCWC1BW4DH exec-out`
- ADB WiFi: `adb -s 192.168.12.190:5555 shell` (port 5555)
- MTP: Not working (Samsung firmware bug, reverts to CDC ACM)
- PTP: Partially working (camera mode, but gvfs auto-mount interferes)

## ADB WiFi Setup
1. Phone and laptop on same WiFi network
2. USB cable plugged in first time only
3. `adb -s <serial> tcpip 5555`
4. `adb connect <phone_ip>:5555`
5. Unplug USB — WiFi ADB persists until reboot
6. If connection lost: `adb connect 192.168.12.190:5555`

---
Scanned: 2026-06-25 | ADB WiFi configured: 2026-06-25
