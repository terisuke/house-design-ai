#!/bin/bash

# Set environment variables
export PYTHONPATH=.
export STREAMLIT_SERVER_RUNONSAVE=false

# Run Streamlit with hot reload disabled
streamlit run house_design_app/main.py --server.runOnSave false

