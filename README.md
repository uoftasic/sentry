# Sentry

Sentry is a hardware ransomware detector designed for TinyTapeout. It monitors a compact stream of block-level storage operations from a storage controller and extracts behavioural features such as write activity, address access patterns, request sizes, and entropy-related information.

These features are accumulated over observation windows and passed to one or more hardware classifiers, which produce ransomware suspicion scores or predictions. The project explores how much useful ransomware detection can be implemented using a small amount of ASIC area and state.

## Project Structure

```text
.
├── src/            # Verilog/SystemVerilog RTL
├── test/           # Cocotb testbenches and simulation infrastructure
│   └── unit/       # Unit tests for individual RTL modules
├── docs/           # TinyTapeout documentation
├── Makefile        # Development and testing commands
├── info.yaml       # TinyTapeout project configuration
└── README.md
```

## Setup

### Windows

Windows users should use **WSL2 with Ubuntu 24.04** for development. The project relies on Linux development tools such as GNU Make, Icarus Verilog, cocotb, and svlint, so native Windows development is not currently recommended.

#### 1. Install WSL2

Open PowerShell as Administrator and run:

```powershell
wsl --install -d Ubuntu-24.04
```

Restart your computer if prompted, then open Ubuntu 24.04 and complete the initial setup.

#### 2. Install Development Tools

Inside the Ubuntu/WSL terminal, run:

```bash
sudo apt update
sudo apt install -y git make iverilog python3 python3-pip python3-venv wget unzip cargo
```

#### 3. Clone the Repository

Clone the repository inside the WSL filesystem:

```bash
cd ~
git clone https://github.com/uoftasic/sentry.git
cd sentry
```

It is recommended to keep the repository inside the Linux filesystem, such as `~/sentry`, rather than under `/mnt/c/`.

#### 4. Create a Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r test/requirements.txt
```

The virtual environment must be activated again when opening a new terminal:

```bash
source .venv/bin/activate
```

#### 5. Install svlint

```bash
SVLINT_VERSION="0.9.3"
SVLINT_ZIP_NAME="svlint-v${SVLINT_VERSION}-x86_64-lnx.zip"
SVLINT_ZIP_URL="https://github.com/dalance/svlint/releases/download/v${SVLINT_VERSION}/${SVLINT_ZIP_NAME}"

mkdir -p /tmp/svlint
cd /tmp/svlint
wget "${SVLINT_ZIP_URL}"
unzip "${SVLINT_ZIP_NAME}"
sudo mv bin/* /usr/local/bin/
cd ~
rm -rf /tmp/svlint

svlint --version
```

If `svlint` is not found after installation, make sure `/usr/local/bin` is included in your `PATH`.

## Testing

Integration tests are placed directly under `test/` and test the complete TinyTapeout design through `tb.sv`.

Unit tests are placed under:

```text
test/unit/
```

Each unit-test filename should match the RTL module it tests. For example:

```text
src/input_decoder.sv
test/unit/test_input_decoder.py
```

A testbench template is available under `test/unit/` and can be copied when creating a new unit test.

## Development Commands

The root `Makefile` provides the main development and testing commands.

### Check Your Environment

Verify that the required tools are installed:

```bash
make doctor
```

### Run Tests

Run all integration tests against the top-level module:

```bash
make test
```

Run the unit test for a specific RTL module:

```bash
make unit MODULE=<module_name>
```

Run all detected unit tests:

```bash
make unit-all
```

Run all unit and integration tests:

```bash
make test-all
```

### Compile the RTL

Compile all `.v` and `.sv` files under `src/` using Icarus Verilog:

```bash
make compile
```

This provides a quick compilation check without running the cocotb testbenches.

### Run the Linter

Run svlint on all RTL source files:

```bash
make lint
```

### Run All Checks

Run linting, compilation, and all tests:

```bash
make check
```

This is the recommended command to run before opening a pull request.

### List Detected RTL Sources

```bash
make sources
```

The Makefile automatically detects `.v` and `.sv` files placed under `src/`.

### Clean Generated Files

```bash
make clean
```

## Adding RTL

Place new Verilog or SystemVerilog modules under:

```text
src/
```

TinyTapeout also requires source files to be added to `info.yaml`, so update the project configuration when adding new modules.

## Viewing Waveforms

Install GTKWave:

```bash
sudo apt install -y gtkwave
```

Or install Surfer:

```bash
cargo install surfer
```

Then open the waveform with:

```bash
gtkwave test/tb.fst
```

or:

```bash
surfer test/tb.fst
```

Unit-test waveforms are generated under:

```text
test/unit/sim_build/<module_name>/
```