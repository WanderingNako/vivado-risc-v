# Repository Guidelines

## Project Structure

This repository builds RISC-V SoCs for AMD/Xilinx FPGAs. The Chisel SoC and core configurations live in `src/main/scala/rocket.scala`. Board-specific Make settings, Vivado scripts, pin constraints, and boot ROM device trees live under `board/<board>/`. Shared integration is in `vivado.tcl`, with peripheral RTL in `uart/`, `sdc/`, and `ethernet/` and wrapper tooling in `vhdl-wrapper/`.

Firmware lives in `bootrom/`, and `bare-metal/hello-world/` provides a hardware smoke test. See `docs/` for setup and flash instructions. Keep generated Vivado projects, bitstreams, and other build output under the ignored `workspace/` directory.

## Build and Development

Use the Vivado/Vitis version and board files described in `README.md`.

- `make update-submodules` initializes dependencies. Add `SKIP_SOFT=1` for FPGA-only work.
- `make BOARD=genesys2 CONFIG=Rocket64x1 bitstream` or `make` builds the FPGA bitstream and flash image. Use the same board and configuration with `vivado-gui` to inspect the block design.
- `make linux bootloader` builds the Linux kernel and the OpenSBI payload with U-Boot.
- `make -C bare-metal/hello-world clean all` builds the smoke-test firmware. See `bare-metal/README.md` for cross-compiler and debugger setup.

## Style and Naming

Match surrounding code. Use two-space indentation in Scala and four spaces in first-party C and Verilog. Use PascalCase for Scala configuration classes, such as `Rocket64x1`, and preserve the existing lowercase, underscore-separated RTL port names. Make recipe lines require tabs.

## Validation

For HDL or board changes, build the affected board and configuration. Changes to peripheral addresses or interrupts should keep the block design and board device tree in sync. When hardware is available, run the bare-metal example or boot Linux over UART and check the affected peripheral. `./qemu/boot_qemu.sh` can smoke-test Linux boot in an emulator. The repository has no top-level automated test suite or coverage threshold.

## Commits and Pull Requests

Use short, action-oriented commit subjects, following examples such as “Update riscv-boom SHA.” In pull requests, explain the change, link related issues when available, and report the board, configuration, Vivado version, and validation results when relevant.
