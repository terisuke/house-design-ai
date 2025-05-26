# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

House Design AI system that combines YOLO-based computer vision, CP-SAT constraint optimization, and FreeCAD integration to automate architectural design workflows.

## Critical Development Commands

### Virtual Environment Setup (IMPORTANT)
Due to protobuf version conflicts, use separate virtual environments:
```bash
# For GCP/Cloud operations
source venv_base/bin/activate

# For OR-Tools/CP-SAT operations  
source venv_ortools/bin/activate

# Always set PYTHONPATH before running commands
export PYTHONPATH=.
```

### Common Commands
```bash
# Run tests
python -m pytest tests/ -v

# Train model locally
python src/train.py --data_yaml config/data.yaml --epochs 100 --imgsz 640

# Run inference
python src/inference.py --image path/to/image.jpg --weights path/to/weights.pt

# Generate layout with CP-SAT solver
python src/cli.py layout-generate --site-width 15 --site-height 12 --num-floors 2

# Start Streamlit app
streamlit run house_design_app/main.py

# Start FreeCAD API
cd freecad_api && python main.py
```

### Deployment Commands
```bash
# Build and push FreeCAD API to GCP
bash scripts/build_and_push_freecad.sh

# Build and push Streamlit app
bash scripts/build_and_push_streamlit.sh

# Run Vertex AI training job
./scripts/build_and_run_vertex_training.sh --epochs 600 --batch-size 2
```

## Architecture Patterns

### Two-Layer Architecture
1. **Generation Layer**: Creates initial layouts using Graph-to-Plan (primary) + VAE (complement)
2. **Constraint Solver Layer**: OR-Tools CP-SAT ensures 100% building code compliance

### Data Flow
YOLO annotations → JSON (Polygon + Graph format) → CP-SAT solver → FreeCAD API → 3D models

### Key Modules
- `src/processing/yolo_to_vector.py`: Converts YOLO masks to vector polygons
- `src/optimization/cp_sat_solver.py`: Implements building constraints (910mm grid, 60% coverage ratio, daylight requirements)
- `src/cloud/`: Vertex AI training and GCS integration
- `freecad_api/`: REST API for 3D model generation

### Constraint Rules
- 910mm grid system for all dimensions
- Building coverage ratio: 60% max
- Floor area ratio: 200% max
- Minimum room sizes enforced
- Stair dimensions: 2.1m x 0.91m per floor
- Daylight requirements for habitable rooms

## Important Notes

### Dependency Conflicts
- **Never** install ortools and google-cloud packages in the same environment
- Use `venv_base` for cloud operations, `venv_ortools` for CP-SAT solver

### Cross-Platform Considerations
- Development on ARM64 Mac, deployment on AMD64 Linux
- Docker buildx used for multi-platform images
- FreeCAD requires special Qt configuration in containers

### Testing Approach
- Unit tests in `tests/unit/`
- Integration tests require FreeCAD API running
- Use `pytest -v` for verbose output
- Mock cloud services in tests

### Deployment Architecture
- Cloud Run for services (FreeCAD API, Streamlit)
- Vertex AI for model training
- Workload Identity for authentication
- Terraform manages all infrastructure