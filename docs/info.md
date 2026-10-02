<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

Sentry is a hardware ransomware detector that monitors a stream of storage operations provided by a storage controller. Each storage event contains compact metadata such as whether the operation is a read or write, its logical block address, request size, and other information used by the selected detection features.

The input decoder reconstructs complete storage events from the limited TinyTapeout I/O interface. The events are then processed by feature-tracking logic over fixed observation windows. At the end of each window, the collected feature values are passed to a hardware classifier, which produces a ransomware suspicion score or prediction.

The design is intended to use only small amounts of state and simple digital logic such as counters, registers, comparators, and adders.

## How to test

The design is tested using cocotb and Icarus Verilog.

From the repository root, run:

```bash
make test